import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_VERSION = "0.1.0"
API_TITLE = "HubGPT API"
API_DESCRIPTION = "API backend for HubGPT - AI advisor framework"

# File paths - handle both development and production paths
if os.getenv("RAILWAY_ENVIRONMENT"):
    # In production, use the mounted volume for persistent storage
    BASE_DIR = Path("/files")
    # Create a directory for this specific deployment
    DEPLOYMENT_DIR = BASE_DIR / "hubgpt"
else:
    BASE_DIR = Path(".")
    DEPLOYMENT_DIR = BASE_DIR

# Application directories
ADVISORS_DIR = DEPLOYMENT_DIR / "advisors"
CHATS_DIR = ADVISORS_DIR / "chats"
ARCHIVE_DIR = ADVISORS_DIR / "archive"
LOGS_DIR = DEPLOYMENT_DIR / "logs"

# Ensure required directories exist
DEPLOYMENT_DIR.mkdir(parents=True, exist_ok=True)
ADVISORS_DIR.mkdir(parents=True, exist_ok=True)
CHATS_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# CORS settings
CORS_ORIGINS = ["*"]  # TODO: Configure properly for production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# OpenRouter settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = "gpt-4-0125-preview"  # Default model to use
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' 