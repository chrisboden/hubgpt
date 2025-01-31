from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import os
from pathlib import Path
import logging
import secrets
from sqlalchemy.orm import Session

from .routers import auth, advisors, chat, files
from .database import engine, Base, get_db
from .models.users import User
from .services.auth_service import get_current_user, get_current_user_or_default, create_default_user
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HubGPT API",
    description="API for HubGPT agent framework",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
@app.on_event("startup")
async def startup_event():
    """Create database tables and default user on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Create required directories
        config.CHATS_DIR.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create default user
        db = next(get_db())
        create_default_user(db)
        logger.info("Default user created successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise e

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(advisors.router, prefix="/advisors", tags=["advisors"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(files.router, prefix="/files", tags=["files"])

# Serve static files
static_dir = Path(__file__).parent
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse, description="Serve the index.html file")
async def read_root():
    """Serve the index.html file"""
    try:
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        else:
            return HTMLResponse("<h1>Welcome to HubGPT API</h1>")
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return HTMLResponse("<h1>Welcome to HubGPT API</h1>")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/verify", dependencies=[Depends(get_current_user_or_default)])
async def verify_credentials():
    """Verify credentials endpoint"""
    return {"status": "ok"}
