import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Executive Assistant"
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    MY_PERSONAL_NUMBER: str
    GROQ_API_KEY:str
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    class Config:
        env_file = ".env"

settings = Settings()