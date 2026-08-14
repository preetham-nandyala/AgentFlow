from sqlalchemy import or_
from agent.registry import registry
from services.gmail_service import send_email_via_gmail, sync_unread_emails
from services.llm_service import draft_email_reply, summarize_text, answer_question
from models.schema import Email
from core.embedder import get_embedder
import random

def _format_email(email: Email) -> str:
    """Formats an email to the exact requested layout."""
    name, email_addr = email.sender, email.sender
    if "<" in email.sender and ">" in email.sender:
        parts = email.sender.split("<", 1)
        name = parts[0].strip().replace('"', '')
        email_addr = parts[1].replace(">", "").strip()
        
    return f"Id: {email.id}\nName: {name}\nMail: {email_addr}\nSubject: {email.subject}\n\n"


@registry.register("gmail.get_latest", "Get the N most recent emails from the database. Arguments: count (int, optional, default 3).")
def get_latest_emails(count: int = 3, context: dict = None) -> str:
    if not context or "db" not in context:
        return "Database context missing."
    
    # Sync latest unread emails first
    sync_unread_emails()
    
    db = context["db"]
    results = db.query(Email).order_by(Email.timestamp.desc()).limit(count).all()
    
    if not results:
        return "No emails found in the database yet. New emails will appear here as they arrive."
    
    summary = f"Latest {len(results)} email(s):\n\n"
    for r in results:
        summary += _format_email(r)
    return summary


@registry.register("gmail.read", "Read the full content of a specific email. Arguments: email_id (int).")
def read_email(email_id: int, context: dict = None) -> str:
    if not context or "db" not in context:
        return "Database context missing."
    
    db = context["db"]
    email = db.query(Email).filter(Email.id == int(email_id)).first()
    
    if not email:
        return f"Could not find Email {email_id}."
        
    return f"Id: {email.id}\nSender: {email.sender}\nSubject: {email.subject}\nBody:\n{email.body}"


@registry.register("gmail.search", "Search past emails using natural language. Arguments: query (str).")
def search_emails(query: str, context: dict = None) -> str:
    if not context or "db" not in context:
        return "Database context missing."
    
    db = context["db"]
    embedder = get_embedder()
    
    if embedder:
        # Vector search (semantic)
        query_vector = embedder.encode(query).tolist()
        results = db.query(Email).order_by(Email.embedding.cosine_distance(query_vector)).limit(5).all()
    else:
        # Fallback: keyword search using SQL ILIKE
        search_term = f"%{query}%"
        results = db.query(Email).filter(
            or_(
                Email.subject.ilike(search_term),
                Email.sender.ilike(search_term),
                Email.body.ilike(search_term)
            )
        ).order_by(Email.timestamp.desc()).limit(5).all()
    
    if not results:
        return "No matching emails found."
        
    summary = "Found these emails:\n\n"
    for r in results:
        summary += _format_email(r)
    return summary


@registry.register("gmail.compose", "Draft a new email or modify an existing draft. Arguments: instruction (str), email_id (int, optional), to_email (str, optional).")
def compose_email(instruction: str, email_id=None, to_email: str = None, context: dict = None) -> str:
    if not context or "session_obj" not in context:
        return "Session context missing."
    
    session_obj = context["session_obj"]
    drafts = list(session_obj.draft_history)
    db = context["db"]
    
    is_new_email = (email_id is None and to_email is not None)
    
    if is_new_email:
        # Generate a short temporary ID for the new draft
        email_id = random.randint(10000, 99999)
    
    draft_identifier = str(email_id)
    
    # Check if a draft already exists for this identifier
    existing_draft = None
    for d in drafts:
        if str(d.get("email_id")) == draft_identifier:
            existing_draft = d
            break
            
    if existing_draft:
        original_context = f"CURRENT DRAFT TO EDIT:\nSubject: {existing_draft['subject']}\nBody: {existing_draft['body']}"
        drafts.remove(existing_draft)
    elif not is_new_email:
        email = db.query(Email).filter(Email.id == int(email_id)).first()
        original_context = f"ORIGINAL EMAIL TO REPLY TO:\nFrom: {email.sender}\nSubject: {email.subject}\nBody: {email.body}" if email else None
    else:
        original_context = None
        
    extra_context = context.get("previous_output") or ""
    if is_new_email:
        extra_context = f"Recipient Address: {to_email}\n" + extra_context
    
    # Use the LLM to draft or edit it
    subject, body = draft_email_reply(instruction, original_context, extra_context=extra_context)
    
    # Save the draft
    drafts.append({
        "email_id": email_id,
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "instruction": instruction
    })
    session_obj.draft_history = drafts
    db.commit()
    
    return f"Draft Ready for {to_email if is_new_email else 'Email ' + str(email_id)}\n\nSubject: {subject}\nBody:\n{body}\n\nReply 'Send {email_id}' to confirm, or 'Edit {email_id}: [changes]'."


@registry.register("gmail.send", "Sends a specific draft email. Arguments: email_id (int, optional), to_email (str, optional).")
def send_email(email_id=None, to_email: str = None, context: dict = None) -> str:
    if not context or "session_obj" not in context:
        return "Session context missing."
        
    session_obj = context["session_obj"]
    db = context["db"]
    
    if not session_obj.draft_history:
        return "No pending drafts found."
        
    draft_identifier = str(email_id) if email_id is not None else str(to_email)
        
    # Find the specific draft
    draft_to_send = None
    for d in session_obj.draft_history:
        if str(d.get("email_id")) == draft_identifier or str(d.get("to_email")) == draft_identifier:
            draft_to_send = d
            break
            
    if not draft_to_send:
        return f"Could not find a draft for ID {draft_identifier}."
        
    # Determine the recipient email address
    final_to_email = None
    if draft_to_send.get("to_email"):
        final_to_email = draft_to_send.get("to_email")
    elif draft_to_send.get("email_id"):
        original_email = db.query(Email).filter(Email.id == int(draft_to_send["email_id"])).first()
        if original_email:
            final_to_email = original_email.sender
            if "<" in final_to_email and ">" in final_to_email:
                final_to_email = final_to_email.split("<")[1].replace(">", "").strip()
        
    if not final_to_email:
        return "Could not determine the recipient email address."
    
    try:
        send_email_via_gmail(
            to_email=final_to_email,
            subject=draft_to_send["subject"],
            body_text=draft_to_send["body"]
        )
        
        # Remove from history
        drafts = list(session_obj.draft_history)
        drafts.remove(draft_to_send)
        session_obj.draft_history = drafts
        
        db = context["db"]
        db.commit()
        
        return f"Successfully sent email to {to_email}!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@registry.register("util.summarize", "Summarize text or the output from a previous tool step. Arguments: text (str, optional - uses previous step output if not provided).")
def summarize_tool(text: str = None, context: dict = None) -> str:
    # If no text argument was passed, use the output from the previous tool step
    if not text and context and context.get("previous_output"):
        text = context["previous_output"]
    
    if not text:
        return "Nothing to summarize. Try asking for emails first."
    
    return summarize_text(text)


@registry.register("util.answer", "Answer a general question or have a conversation. Use this for anything that is NOT email-related. Arguments: question (str).")
def answer_tool(question: str, context: dict = None) -> str:
    # If there's previous output, use it as context for a better answer
    extra_context = None
    if context and context.get("previous_output"):
        extra_context = context["previous_output"]
    
    return answer_question(question, extra_context)


@registry.register("util.clear_memory", "Clears the conversation memory to start a fresh conversation.")
def clear_memory(context: dict = None) -> str:
    if not context or "session_obj" not in context:
        return "Session context missing."
    
    session_obj = context["session_obj"]
    session_obj.conversation_history = []
    
    db = context["db"]
    db.commit()
    
    return "Started a new fresh conversation. Memory cleared."
