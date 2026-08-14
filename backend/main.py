import sys
import os

# Fix Windows console encoding for emoji/unicode characters
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.routes import api_router
from api.webhooks import webhook_router
import tools.gmail_tools
import tools.calendar_tools
from core.config import settings
from services.gmail_service import sync_unread_emails

from core.database import engine, Base
import models.schema # Important: import schema before create_all

async def email_polling_loop():
    """Background task that runs every 10 minutes."""
    while True:
        await asyncio.to_thread(sync_unread_emails)
        await asyncio.sleep(600) # Wait 10 minutes before checking again

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database Tables
    print("📦 Creating Database Tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    
    print("🚀 Starting Background Email Watcher (10m interval)...")
    polling_task = asyncio.create_task(email_polling_loop())
    
    yield # Server is running
    
    print("🛑 Shutting down Background Email Watcher...")
    polling_task.cancel()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Include the routers
app.include_router(api_router, prefix="/api")
app.include_router(webhook_router, prefix="/webhook")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)