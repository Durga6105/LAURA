"""
LAURA - FastAPI Application

Main backend application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    analysis,
    health,
    qa,
)
from config.settings import settings


app = FastAPI(
    title=settings.app_name,
    description=(
        "LAURA - Legal AI Understanding & Risk Analyzer"
    ),
    version="1.0.0",
    debug=settings.debug,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
#
# Allows the HTML frontend running through VS Code
# Live Server to communicate with the FastAPI backend.
#
# Frontend:
#     http://127.0.0.1:5500
#
# Backend:
#     http://127.0.0.1:8000
#
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

app.include_router(
    health.router,
    tags=["Health"],
)

app.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["Analysis"],
)

app.include_router(
    qa.router,
    prefix="/qa",
    tags=["Q&A"],
)


@app.get("/")
async def root():
    """Root endpoint."""

    return {
        "application": settings.app_name,
        "status": "running",
        "message": (
            "LAURA Legal AI backend is running."
        ),
    }