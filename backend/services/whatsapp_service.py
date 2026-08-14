from core.config import settings
from twilio.rest import Client

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_alert(message: str) -> bool:
    """Utility function to proactively message the user."""
    try:
        msg = twilio_client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=settings.MY_PERSONAL_NUMBER
        )
        print(f"✅ WhatsApp Alert sent! SID: {msg.sid}")
        return True
    except Exception as e:
        print(f"❌ Error sending WhatsApp: {e}")
        return False