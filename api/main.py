from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import logging
import sys
import os
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

# Get the directory containing this file
current_dir = Path(__file__).parent.absolute()
static_dir = current_dir / "static"
static_dir.mkdir(exist_ok=True)

# Mount static files using absolute path
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(advisors.router, tags=["advisors"])
app.include_router(chat.router, tags=["chat"])

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the index.html file"""
    try:
        # Try the direct path first
        index_path = current_dir / "index.html"
        if not index_path.exists():
            # Try the static directory as fallback
            index_path = static_dir / "index.html"
            if not index_path.exists():
                logger.error(f"index.html not found in either {current_dir} or {static_dir}")
                return HTMLResponse(
                    content="<h1>Error: index.html not found</h1>",
                    status_code=404
                )
        
        logger.info(f"Serving index.html from {index_path}")
        with open(index_path) as f:
            content = f.read()
            return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Error serving index.html: {str(e)}")
        return HTMLResponse(
            content=f"<h1>Error: {str(e)}</h1>",
            status_code=500
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": config.API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }


