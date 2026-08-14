from groq import Groq
from core.config import settings

import re

groq_client = Groq(api_key=settings.GROQ_API_KEY)


def draft_email_reply(instruction: str, original_email: str = None, extra_context: str = None) -> tuple[str, str]:
    """
    Drafts an email using Groq. 
    Returns a tuple of (subject, body).
    """
    
    context_injection = f"\n\nADDITIONAL CONTEXT (e.g., Meeting Links):\n{extra_context}" if extra_context else ""
    
    if original_email:
        prompt = f"""
        You are an expert Executive Assistant. 
        Read the following original email and write a professional reply based on the user's instructions.
        
        User's Instruction: {instruction}
        Original Email: {original_email}{context_injection}
        
        Format your response EXACTLY like this:
        SUBJECT: [Write an appropriate subject line here]
        BODY: [Write the exact email body here]

        CRITICAL RULES:
        1. Look at the "From:" field in the original email to find the recipient's name. Use their actual name (e.g., "Dear John,").
        2. NEVER use placeholders like [Recipient's Name], [Your Name], or brackets.
        3. ALWAYS sign off the email as "Preetham".
        4. ONLY output the SUBJECT and BODY fields. DO NOT output any conversational filler, explanations, or apologies.
        """
    else:
        prompt = f"""
        You are an expert Executive Assistant. 
        Write a professional email based on the user's instructions.
        
        User's Instruction: {instruction}{context_injection}
        
        Format your response EXACTLY like this:
        SUBJECT: [Write an appropriate subject line here]
        BODY: [Write the exact email body here]

        CRITICAL RULES:
        1. NEVER use placeholders like [Recipient's Name], [Your Name], or brackets.
        2. ALWAYS sign off the email as "Preetham".
        3. ONLY output the SUBJECT and BODY fields. DO NOT output any conversational filler, explanations, or apologies.
        """

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant", 
            temperature=0.7 
        )
        
        draft = response.choices[0].message.content.strip()
        
        # Parse the output using Regex to cleanly extract Subject and Body
        subject_match = re.search(r'SUBJECT:\s*(.*)', draft, re.IGNORECASE)
        body_match = re.search(r'BODY:\s*(.*)', draft, re.IGNORECASE | re.DOTALL)
        
        # Fallbacks just in case the LLM disobeys the formatting rules
        subject = subject_match.group(1).strip() if subject_match else "New Message"
        body = body_match.group(1).strip() if body_match else draft
        
        print(f"🧠 LLM drafted Subject: {subject}")
        return subject, body
        
    except Exception as e:
        print(f"❌ LLM Drafting Error: {e}")
        raise e




def summarize_text(text: str) -> str:
    """Summarizes any given text using the LLM."""
    prompt = f"""You are a concise executive assistant. Summarize the following content in 2-3 sentences.
Be direct and highlight the key points.

Content to summarize:
{text}

Summary:"""

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ LLM Summarization Error: {e}")
        return f"Could not summarize: {e}"


def answer_question(question: str, context: str = None) -> str:
    """General-purpose Q&A function. Acts as a search engine / conversational AI."""
    if context:
        prompt = f"""You are a helpful AI assistant. Answer the user's question using the provided context.

Context:
{context}

Question: {question}

Answer concisely and helpfully:"""
    else:
        prompt = f"""You are a helpful AI assistant. Answer the following question concisely and helpfully.

Question: {question}

Answer:"""

    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ LLM Q&A Error: {e}")
        return f"Sorry, I couldn't answer that: {e}"