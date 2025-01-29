from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
import secrets

from api.routers import advisors, chat, files
from api import config

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

# Initialize HTTP Basic Auth
security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Auth credentials"""
    is_username_correct = secrets.compare_digest(credentials.username, config.API_USERNAME)
    is_password_correct = secrets.compare_digest(credentials.password, config.API_PASSWORD)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

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
root_dir = current_dir.parent

# Ensure static directories exist
static_dir = root_dir / "static"
static_dir.mkdir(exist_ok=True)
(static_dir / "app").mkdir(exist_ok=True)
(static_dir / "app" / "lib").mkdir(exist_ok=True)

# Copy static files if they don't exist in the target location
if not (static_dir / "app" / "lib" / "api-client.js").exists():
    import shutil
    # Copy app files
    if (current_dir / "static" / "app").exists():
        shutil.copytree(
            current_dir / "static" / "app",
            static_dir / "app",
            dirs_exist_ok=True
        )

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount API files
app.mount("/api", StaticFiles(directory=str(current_dir)), name="api")

# Include routers
app.include_router(advisors.router, tags=["advisors"], dependencies=[Depends(verify_auth)])
app.include_router(chat.router, tags=["chat"], dependencies=[Depends(verify_auth)])
app.include_router(files.router, tags=["files"], dependencies=[Depends(verify_auth)])

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the index.html file"""
    try:
        # Try the direct path first
        index_path = current_dir / "index.html"
        if not index_path.exists():
            # Try the static directory as fallback
            index_path = current_dir / "static" / "index.html"
            if not index_path.exists():
                logger.error(f"index.html not found in either {current_dir} or {current_dir / 'static'}")
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

@app.get("/auth/verify")
async def verify_credentials(username: str = Depends(verify_auth)):
    """Verify credentials and return success"""
    return {"status": "success", "username": username}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": config.API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }
