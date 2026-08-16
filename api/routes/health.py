"""
LAURA - Health API
"""

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health_check():
    """Check whether the API is running."""

    return {
        "status": "healthy",
        "service": "LAURA",
    }