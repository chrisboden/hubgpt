import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment
ENV = os.getenv("ENV", "development")
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None

# Determine base directory based on environment
if IS_RAILWAY:
    BASE_DIR = Path("/app")
else:
    BASE_DIR = Path(__file__).resolve().parent

# Directory Structure
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
TEMP_DIR = BASE_DIR / "temp"
STATIC_DIR = BASE_DIR / "static"
ADVISORS_DIR = BASE_DIR / "advisors"
FILES_DIR = BASE_DIR / "files"
CHATS_DIR = ADVISORS_DIR / "chats"
ARCHIVE_DIR = ADVISORS_DIR / "archive"
UPLOADS_DIR = DATA_DIR / "uploads"

# Create directories if they don't exist
for dir_path in [DATA_DIR, LOGS_DIR, TEMP_DIR, STATIC_DIR, ADVISORS_DIR, 
                 FILES_DIR, CHATS_DIR, ARCHIVE_DIR, UPLOADS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Settings
API_TITLE = "HubGPT API"
API_DESCRIPTION = "API for HubGPT agent framework"
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# CORS settings
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://localhost",
    "https://localhost:8000",
    "https://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# OpenRouter settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")

# Auth settings
API_USERNAME = os.getenv("API_USERNAME", "admin")
API_PASSWORD = os.getenv("API_PASSWORD", "password")

# JWT Settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-for-development")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Database Settings
DB_TYPE = "sqlite"
if IS_RAILWAY:
    # Railway PostgreSQL URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Local SQLite URL
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///hubgpt.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# File Upload
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

# Default User
DEFAULT_USER_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "admin@example.com")

# LLM Settings
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1000"))

# File Storage
if IS_RAILWAY:
    # Railway Volume storage
    STORAGE_ROOT = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data"))
else:
    # Local storage
    STORAGE_ROOT = Path(os.getenv("STORAGE_PATH", Path(__file__).parent.parent / "storage"))

# Ensure storage directories exist
USERS_ROOT = STORAGE_ROOT / "users"
SHARED_ROOT = STORAGE_ROOT / "shared"

# Create directories if they don't exist (local development only)
if not IS_RAILWAY:
    USERS_ROOT.mkdir(parents=True, exist_ok=True)
    SHARED_ROOT.mkdir(parents=True, exist_ok=True)

# App Settings
DEBUG = ENV != "production" 