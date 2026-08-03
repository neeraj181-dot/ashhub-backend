from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(tags=["Health Check"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """System health check endpoint verifying API and DB connection status."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "ok" else "unhealthy",
        "service": "AshHub Backend API",
        "database": db_status
    }
