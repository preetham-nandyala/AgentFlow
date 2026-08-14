from googleapiclient.discovery import build
import datetime
from services.gmail_service import get_google_credentials

def get_calendar_service():
    """Builds and returns the Google Calendar API service using the shared credentials."""
    creds = get_google_credentials()
    return build('calendar', 'v3', credentials=creds)

def get_upcoming_events(days: int = 3):
    """Fetches upcoming events from the primary calendar."""
    service = get_calendar_service()
    
    # Get current time in UTC formatted for Google API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  
    
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=now,
        maxResults=10, 
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    if not events:
        return "No upcoming events found."
        
    output = "Upcoming Events:\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # Parse it nicely if possible
        try:
            dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
            start_str = dt.strftime("%b %d, %Y at %I:%M %p")
        except:
            start_str = start
            
        summary = event.get('summary', 'Busy')
        output += f"- {start_str}: {summary}\n"
        
    return output

def create_calendar_event(summary: str, start_iso: str, end_iso: str, attendees_emails: list = None):
    """
    Creates a calendar event.
    start_iso and end_iso should be ISO format datetime strings (e.g., '2026-07-31T14:00:00')
    """
    service = get_calendar_service()
    
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_iso,
            'timeZone': 'Asia/Kolkata',  # Assuming user's timezone from their metadata
        },
        'end': {
            'dateTime': end_iso,
            'timeZone': 'Asia/Kolkata',
        },
        # Automatically generate Google Meet link
        'conferenceData': {
            'createRequest': {
                'requestId': f"req_{int(datetime.datetime.now().timestamp())}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }
    
    if attendees_emails:
        event['attendees'] = [{'email': email} for email in attendees_emails]
        
    try:
        created_event = service.events().insert(
            calendarId='primary', 
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all' # Sends email invite to attendees
        ).execute()
        
        meet_link = created_event.get('hangoutLink')
        if not meet_link:
            try:
                # Consumer @gmail.com accounts put the link in entryPoints
                entry_points = created_event.get('conferenceData', {}).get('entryPoints', [])
                for ep in entry_points:
                    if ep.get('entryPointType') == 'video':
                        meet_link = ep.get('uri')
                        break
            except Exception:
                pass
                
        if not meet_link:
            meet_link = "Could not generate Meet link."
            
        return f"Event '{summary}' scheduled successfully!\nLink: {meet_link}\nStart: {start_iso}"
    except Exception as e:
        return f"Failed to schedule event: {str(e)}"
