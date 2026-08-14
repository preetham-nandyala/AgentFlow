import json
import datetime
from core.config import settings
from groq import Groq
from agent.registry import registry
from models.schema import Session

groq_client = Groq(api_key=settings.GROQ_API_KEY)

def generate_plan(session: Session, user_input: str) -> list[dict]:
    """
    Takes the user input and current session, and returns a JSON plan of tools to execute.
    """
    tools_list = registry.list_tools()
    
    # Get last 20 messages for context
    history = session.conversation_history[-20:]
    history_str = json.dumps(history, indent=2)
    
    # Inject current time so the LLM can resolve "tomorrow" or "next week"
    current_time_str = datetime.datetime.now().isoformat()
    
    prompt = f"""You are an AI Planner for an autonomous Executive Assistant that communicates via WhatsApp.
Your job is to analyze the user's request and output a precise JSON plan of tools to execute.

Available Tools:
{json.dumps(tools_list, indent=2)}

Current Date and Time (ISO): {current_time_str}

Recent Conversation History (up to 20 messages):
{history_str}

User's Request: "{user_input}"
Pending Approval State: {session.pending_approval_state}

RULES:
1. ONLY return a JSON array of objects. No markdown, no explanation, no extra text.
2. Each object MUST have a "tool" key and optionally an "args" key.
3. Emails are returned with an "Id: 6". You MUST pass this ID as `email_id` to `gmail.compose` or `gmail.send`.
4. If the user asks to modify a draft (e.g. "Add that we will meet on zoom to 6"), call `gmail.compose` with `email_id: 6` and the new instruction.
5. If the user asks to compose a completely NEW email to an email address, pass `to_email: "address@domain.com"` to `gmail.compose` INSTEAD of `email_id`.
6. If the user asks to "Send 6", pass `email_id: 6` to `gmail.send`. If they ask to "Send address@domain.com", pass `to_email` to `gmail.send`.
7. If the user asks to start a new conversation or clear memory, use "util.clear_memory".
8. If the request is NOT about emails (general knowledge, jokes, explanations), use "util.answer".
9. If the user asks to find, search, or retrieve a specific past email based on keywords or company names, use "gmail.search".
10. If the user asks to read, view, or summarize a specific email by ID (e.g. "read id 7" or "summarize 7"), you MUST use "gmail.read" first. If they want a summary, chain it: `[{{"tool": "gmail.read", "args": {{"email_id": 7}}}}, {{"tool": "util.summarize"}}]`
11. If you cannot determine the right tool, use "util.answer" as a fallback.

EXAMPLES:

User: "What is the latest mail?"
[{{"tool": "gmail.get_latest", "args": {{"count": 1}}}}]

User: "Find emails about invoices"
[{{"tool": "gmail.search", "args": {{"query": "invoices"}}}}]

User: "give me the talentsprint mail"
[{{"tool": "gmail.search", "args": {{"query": "talentsprint"}}}}]

User: "compose a mail to john@example.com that I am busy"
[{{"tool": "gmail.compose", "args": {{"instruction": "I am busy", "to_email": "john@example.com"}}}}]

User: "Read email 7"
[{{"tool": "gmail.read", "args": {{"email_id": 7}}}}]

User: "Summarize id 7"
[{{"tool": "gmail.read", "args": {{"email_id": 7}}}}, {{"tool": "util.summarize"}}]

User: "Reply to 6 that I am not available tomorrow"
[{{"tool": "gmail.compose", "args": {{"instruction": "I am not available tomorrow", "email_id": 6}}}}]

User: "Id: 6 Draft a mail that sure I am available on that day"
[{{"tool": "gmail.compose", "args": {{"instruction": "sure I am available on that day", "email_id": 6}}}}]

User: "Add that we will meet in zoom at 6pm to 6"
[{{"tool": "gmail.compose", "args": {{"instruction": "Add that we will meet in zoom at 6pm", "email_id": 6}}}}]

User: "What is machine learning?"
[{{"tool": "util.answer", "args": {{"question": "What is machine learning?"}}}}]

User: "Send 6"
[{{"tool": "gmail.send", "args": {{"email_id": 6}}}}]

User: "Id: 6 Send it"
[{{"tool": "gmail.send", "args": {{"email_id": 6}}}}]

User: "Start a new conversation"
[{{"tool": "util.clear_memory"}}]

User: "Am I free tomorrow morning?"
[{{"tool": "calendar.get_schedule", "args": {{"days": 2}}}}]

User: "Schedule a 30m meeting with Id 6 for tomorrow at 2pm"
[{{"tool": "calendar.schedule_meeting", "args": {{"summary": "Meeting", "start_iso": "YYYY-MM-DDT14:00:00", "end_iso": "YYYY-MM-DDT14:30:00", "email_id": 6}}}}]

User: "Schedule a meeting for tomorrow at 10am"
[{{"tool": "calendar.schedule_meeting", "args": {{"summary": "Meeting", "start_iso": "YYYY-MM-DDT10:00:00", "end_iso": "YYYY-MM-DDT10:30:00"}}}}]

User: "Id 6 schedule a 30m catchup for tomorrow at 2pm and draft a mail sending them the link"
[{{"tool": "calendar.schedule_meeting", "args": {{"summary": "Catchup", "start_iso": "YYYY-MM-DDT14:00:00", "end_iso": "YYYY-MM-DDT14:30:00", "email_id": 6}}}}, {{"tool": "gmail.compose", "args": {{"instruction": "Send them the meeting link", "email_id": 6}}}}]

Now generate the plan for the user's request:"""

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.0
        )
        
        content = response.choices[0].message.content.strip()
        
        # Robust JSON array extraction
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1:
            clean_content = content[start_idx:end_idx+1]
        else:
            clean_content = content
            
        try:
            plan = json.loads(clean_content)
            return plan
        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON. Raw LLM output:\n{content}")
            # Fallback: treat it as a general question
            return [{"tool": "util.answer", "args": {"question": user_input}}]
            
    except Exception as e:
        print(f"❌ Planner Error: {e}")
        return [{"tool": "util.answer", "args": {"question": user_input}}]
