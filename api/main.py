from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import sys
from datetime import datetime
from pathlib import Path

from .routers import advisors, chat
from . import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOGS_DIR / f"api_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=config.CORS_ALLOW_METHODS,
    allow_headers=config.CORS_ALLOW_HEADERS,
)

# Mount static files using absolute path
static_dir = config.BASE_DIR / "api"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(advisors.router, tags=["advisors"])
app.include_router(chat.router, tags=["chat"])

@app.get("/")
async def read_root():
    """Serve the index.html file"""
    index_path = static_dir / "index.html"
    if not index_path.exists():
        logger.error(f"index.html not found at {index_path}")
        return {"error": "index.html not found"}
    return FileResponse(str(index_path))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": config.API_VERSION,
        "timestamp": datetime.now().isoformat()
    }


