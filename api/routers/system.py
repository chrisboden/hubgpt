from fastapi import APIRouter
from pathlib import Path
import os
import shutil
import logging
from datetime import datetime
from .. import config

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": config.API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }

@router.get("/volume-status")
async def get_volume_status():
    """Get status of the mounted volume"""
    try:
        volume_path = Path("/files")
        if not volume_path.exists():
            return {
                "status": "error",
                "message": "Volume not mounted",
                "path": str(volume_path)
            }
            
        # Get volume stats
        total, used, free = shutil.disk_usage(volume_path)
        
        # List top-level directories
        dirs = [d.name for d in volume_path.iterdir() if d.is_dir()]
        
        return {
            "status": "ok",
            "path": str(volume_path),
            "space": {
                "total_gb": total // (2**30),
                "used_gb": used // (2**30),
                "free_gb": free // (2**30),
                "used_percent": (used * 100) // total
            },
            "directories": dirs,
            "is_writable": os.access(volume_path, os.W_OK)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "path": str(volume_path)
        } 