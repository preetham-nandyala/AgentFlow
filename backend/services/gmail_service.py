import os
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from services.whatsapp_service import send_whatsapp_alert

from core.database import SessionLocal
from core.embedder import get_embedder
from models.schema import Email

import time
STARTUP_TIME = int(time.time() * 1000)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', 
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar.events'
]

def get_google_credentials():
    """Handles Google OAuth and returns the valid credentials."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return creds

def authenticate_gmail():
    """Handles Google OAuth and creates the Gmail API service."""
    creds = get_google_credentials()
    return build('gmail', 'v1', credentials=creds)

def send_email_via_gmail(to_email: str, subject: str, body_text: str):
    """Sends an actual email using the Gmail API."""
    try:
        service = authenticate_gmail()
        
        message = EmailMessage()
        message.set_content(body_text)
        message['To'] = to_email
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        sent_message = service.users().messages().send(userId='me', body=create_message).execute()
        print(f"Email successfully sent via Gmail API! ID: {sent_message['id']}")
        return sent_message
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise e

def sync_unread_emails():
    """Polls Gmail for unread messages and saves new ones to the database."""
    print("Checking inbox for unread emails...")
    try:
        service = authenticate_gmail()
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            maxResults=5,
            q="is:unread category:primary newer_than:1d -from:noreply -from:no-reply -from:mailer-daemon -from:notifications -label:spam -label:trash"
        ).execute()
        messages = results.get('messages', [])

        if not messages:
            return

        db = SessionLocal()
        embedder = get_embedder()  # Lazy load — may be None on low-RAM machines

        for message in messages:
            msg_id = message['id']
            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            internal_date = int(msg.get('internalDate', 0))
            if internal_date < STARTUP_TIME:
                print(f"Skipping old unread email {msg_id}.")
                service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                continue
                
            headers = msg['payload'].get('headers', [])
            sender_header = next((header['value'] for header in headers if header['name'].lower() == 'from'), "Unknown Sender")
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), "No Subject")
            snippet = msg.get('snippet', '')
            
            # Extract name and email from "Name <email@domain.com>"
            name = sender_header
            email_addr = sender_header
            if "<" in sender_header and ">" in sender_header:
                name, email_addr = sender_header.split("<", 1)
                name = name.strip().replace('"', '')
                email_addr = email_addr.replace(">", "").strip()

            print(f"New Email from {name} ({email_addr}): {subject}")

            # Save to database
            existing = db.query(Email).filter(Email.message_id == msg_id).first()
            if not existing:
                vector = None
                if embedder:
                    try:
                        vector = embedder.encode(f"{subject} {snippet}").tolist()
                    except Exception as e:
                        print(f"Embedding failed for {msg_id}: {e}")
                
                new_email = Email(
                    message_id=msg_id,
                    sender=sender_header,
                    subject=subject,
                    body=snippet,
                    embedding=vector
                )
                db.add(new_email)
                db.commit()
                db.refresh(new_email)
                
                # Alert WhatsApp
                print("Alerting WhatsApp...")
                alert_msg = f"NEW EMAIL\nId: {new_email.id}\nName: {name}\nMail: {email_addr}\nSubject: {subject}\n"
                send_whatsapp_alert(alert_msg)

            # Mark as Read
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
            print(f"Marked email {msg_id} as READ.")
            
        db.close()

    except Exception as e:
        print(f"Gmail API Error: {e}")