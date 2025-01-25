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

@router.post("/setup")
async def setup_environment():
    """Initialize the environment with required directories and files"""
    try:
        from ..config import (
            DEPLOYMENT_DIR,
            ADVISORS_DIR,
            CHATS_DIR,
            ARCHIVE_DIR,
            LOGS_DIR
        )
        
        # Create directory structure
        for dir_path in [DEPLOYMENT_DIR, ADVISORS_DIR, CHATS_DIR, ARCHIVE_DIR, LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Copy default advisors if none exist
        if not any(ADVISORS_DIR.glob("*.json")) and not any(ADVISORS_DIR.glob("*.md")):
            # Create a basic advisor for testing
            from ..services.advisor_service import create_json_content
            from ..models.advisors import AdvisorCreate, Message
            from ..services.storage_service import write_json_file
            
            test_advisor = AdvisorCreate(
                name="Test_Advisor",
                model="gpt-4-0125-preview",
                temperature=0.7,
                max_tokens=1000,
                stream=True,
                messages=[
                    Message(
                        role="system",
                        content="You are a test advisor to verify the system is working."
                    )
                ],
                format="json"
            )
            
            content = create_json_content(test_advisor)
            test_path = ADVISORS_DIR / "Test_Advisor.json"
            success = write_json_file(test_path, content)
            
            if not success:
                raise Exception("Failed to write test advisor file")
            
        return {
            "status": "success",
            "message": "Environment initialized",
            "directories": {
                "deployment": str(DEPLOYMENT_DIR),
                "advisors": str(ADVISORS_DIR),
                "chats": str(CHATS_DIR),
                "archive": str(ARCHIVE_DIR),
                "logs": str(LOGS_DIR)
            }
        }
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Setup failed: {str(e)}"
        } 