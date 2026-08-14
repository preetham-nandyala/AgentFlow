import urllib.parse
from fastapi import APIRouter, Request, Depends
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session as DBSession

from core.database import get_db
from agent.session import SessionManager
from agent.planner import generate_plan
from agent.executor import execute_plan

# Ensure tools are registered before routing!
import tools.gmail_tools 

webhook_router = APIRouter()

@webhook_router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: DBSession = Depends(get_db)):
    """
    Controller for handling inbound messages from Twilio.
    Routes entirely through the Plan-and-Execute Agent architecture.
    """
    body = await request.body()
    parsed_body = urllib.parse.parse_qs(body.decode('utf-8'))
    
    incoming_msg = parsed_body.get('Body', [''])[0].strip()
    sender_number = parsed_body.get('From', [''])[0]

    print(f"📩 Received instruction from {sender_number}: {incoming_msg}")

    # 1. Initialize Agent Context
    session_manager = SessionManager(sender_number)
    session_manager.append_conversation(db, "user", incoming_msg)
    session_obj = session_manager.get_or_create_session(db)

    # 2. Plan
    print("🧠 Planning Execution...")
    plan = generate_plan(session_obj, incoming_msg)
    
    # 3. Execute
    if plan:
        print(f"📋 Generated Plan: {plan}")
        final_response = execute_plan(db, session_manager, plan)
    else:
        final_response = "I couldn't figure out a plan for that. Could you clarify?"

    # 4. Save and Respond
    session_manager.append_conversation(db, "agent", final_response)

    twiml_response = MessagingResponse()
    twiml_response.message(final_response)

    return PlainTextResponse(str(twiml_response), media_type="application/xml")