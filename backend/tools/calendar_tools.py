from agent.registry import registry
from services.calendar_service import get_upcoming_events, create_calendar_event
from models.schema import Email

@registry.register("calendar.get_schedule", "Check the user's upcoming Google Calendar schedule. Arguments: days (int, optional).")
def check_schedule(days: int = 3, context: dict = None) -> str:
    return get_upcoming_events(days)


@registry.register("calendar.schedule_meeting", "Schedule a meeting on Google Calendar. Arguments: summary (str), start_iso (str), end_iso (str), email_id (int, optional).")
def schedule_meeting(summary: str, start_iso: str, end_iso: str, email_id: int = None, context: dict = None) -> str:
    attendees = []
    
    # If the user asked to schedule with a specific email thread, automatically invite them!
    if email_id and context and "db" in context:
        db = context["db"]
        original_email = db.query(Email).filter(Email.id == int(email_id)).first()
        if original_email:
            to_email = original_email.sender
            if "<" in to_email and ">" in to_email:
                to_email = to_email.split("<")[1].replace(">", "").strip()
            attendees.append(to_email)
            
    # Create the event
    result = create_calendar_event(summary, start_iso, end_iso, attendees)
    
    return result
