"""Main entry point for TravelChatBot FastAPI Backend.

This module initializes the FastAPI web application, configures CORS middleware,
automatically sets up database tables on startup, registers all API routers,
and serves a health check endpoint.

Author: TravelChatBot Team
Version: 1.0.0
"""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine
from backend.models import Base
from backend.routers.auth import router as auth_router
from backend.routers.user import router as user_router
from backend.routers.chat import router as chat_router
from backend.routers.api_v1 import router as api_v1_router

# Initialize FastAPI app
app = FastAPI(
    title="TravelChatBot Backend API",
    description="REST API for RAG-based travel guide recommendations with vision and speech inputs.",
    version="1.0.0"
)

# Configure CORS (Cross-Origin Resource Sharing)
# Allows frontend clients (e.g., React, Next.js, Vite) to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production to allow specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Startup trigger to ensure all SQLite database tables are fully generated."""
    print("⏳ [Startup] Verifying database structure...")
    Base.metadata.create_all(bind=engine)
    print("✅ [Startup] Database verified and tables ready.")


@app.get("/")
def health_check():
    """Simple API health check endpoint."""
    return {
        "status": "online",
        "app": "TravelChatBot Backend API",
        "version": "1.0.0",
        "documentation": "/docs"  # Swagger docs route
    }


# Register sub-routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(api_v1_router)


if __name__ == "__main__":
    # Standard entry point to execute backend server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
