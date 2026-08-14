from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "AI Executive Assistant is running."}