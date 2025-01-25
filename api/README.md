# HubGPT API

FastAPI backend for HubGPT - AI advisor framework that allows creation of personalized advisors with tool support. Features real-time streaming responses via Server-Sent Events (SSE).

## Architecture

The API follows a modular architecture with clear separation of concerns:

```
api/
├── main.py              # FastAPI app initialization and routing
├── config.py            # Configuration and environment variables
├── dependencies.py      # FastAPI dependencies and middleware
├── routers/            # API route handlers
│   ├── __init__.py
│   ├── advisors.py     # Advisor-related endpoints
│   └── chat.py         # Chat-related endpoints
├── models/             # Pydantic data models
│   ├── __init__.py
│   ├── advisors.py     # Advisor models
│   └── chat.py         # Chat/Message models
├── services/           # Business logic
│   ├── __init__.py
│   ├── advisor_service.py    # Advisor operations
│   ├── chat_service.py      # Chat operations
│   └── storage_service.py   # File storage operations
├── index.html         # Test harness
└── README.md         # Documentation

```

### Component Responsibilities

1. **Models (`models/`)**: Pydantic models for data validation and serialization
   - `advisors.py`: Models for advisor configuration and creation
   - `chat.py`: Models for chat messages and conversation history

2. **Routers (`routers/`)**: FastAPI route handlers and endpoint definitions
   - `advisors.py`: Endpoints for managing advisors
   - `chat.py`: Endpoints for chat functionality

3. **Services (`services/`)**: Business logic and data operations
   - `advisor_service.py`: Advisor file operations and parsing
   - `chat_service.py`: Chat history and message management
   - `storage_service.py`: Generic file storage operations

4. **Configuration (`config.py`)**:
   - Environment variables
   - File paths
   - API settings
   - CORS configuration

5. **Dependencies (`dependencies.py`)**:
   - FastAPI dependency injection
   - Request validation
   - Common middleware

## File Storage

The API uses a file-based storage system:

- `/advisors/`: Root directory for all advisor-related files
  - `/*.json` or `/*.md`: Advisor configuration files
  - `/chats/`: Current chat files (e.g., `Yuval_Harari.json`)
  - `/archive/`: Archived chat files with hex suffix (e.g., `Yuval_Harari_e5ba7d.json`)

### Chat File Formats

1. **Current Chats** (`/advisors/chats/`):
   ```json
   {
     "id": "advisor_id",
     "advisor_id": "advisor_id",
     "messages": [
       {"role": "user", "content": "..."},
       {"role": "assistant", "content": "..."}
     ],
     "created_at": "2024-01-17T10:30:00",
     "updated_at": "2024-01-17T10:35:00"
   }
   ```

2. **Archived Chats** (`/advisors/archive/`):
   - Same format as current chats
   - Filename includes unique hex suffix

## API Endpoints

### Advisors

- `GET /advisors`: List all available advisors
- `GET /advisors/{advisor_id}`: Get specific advisor
- `POST /advisors`: Create new advisor

### Chat

- `GET /chat/advisor/{advisor_id}/latest`: Get latest conversation
- `GET /chat/advisor/{advisor_id}/history`: List previous conversations
- `POST /chat/advisor/{advisor_id}/new`: Create new conversation
- `GET /chat/{conversation_id}`: Get specific conversation
- `POST /chat/{conversation_id}/message`: Add message to conversation
  - Supports both streaming and non-streaming responses
  - Streaming uses Server-Sent Events (SSE)
  - Content-Type: text/event-stream for streaming
  - Content-Type: application/json for non-streaming
- `POST /chat/{conversation_id}/clear`: Archive current conversation
- `DELETE /chat/{conversation_id}`: Delete conversation

## Chat Management

1. **Current Chat**:
   - One active chat per advisor
   - Stored in `/advisors/chats/{advisor_id}.json`
   - Created automatically if doesn't exist

2. **Chat History**:
   - Previous chats archived with unique ID
   - Stored in `/advisors/archive/{advisor_id}_{hex}.json`
   - Hex suffix ensures unique filenames

3. **Chat Operations**:
   - Clear: Archives current chat and creates new blank one
   - Delete: 
     - For archived chats: Permanently deletes the file
     - For current chat: Deletes and creates new blank chat

4. **Response Streaming**:
   - Configurable via advisor template (`stream: true`)
   - Uses Server-Sent Events for real-time updates
   - Automatic fallback to non-streaming when not configured
   - Returns plain text content for frontend rendering

## Test Harness

The included test harness (`index.html`) provides a simple interface for testing the API:

1. **Features**:
   - Advisor selection and management
   - Real-time streaming chat responses
   - Client-side markdown rendering
   - Chat history viewing and navigation
   - New chat creation
   - Clear/delete operations

2. **Technical Details**:
   - Uses EventSource for SSE handling
   - Marked library for markdown parsing
   - Real-time UI updates during streaming
   - Proper error handling and recovery
   - Client-side message formatting

## Development

### Adding New Features

1. Define Pydantic models in `models/`
2. Implement business logic in `services/`
3. Add endpoints in `routers/`
4. Update documentation

### Error Recovery

The API includes automatic file repair functionality:
- Creates backups with `.json.bak` extension
- Attempts to fix common JSON formatting issues
- Logs all repair attempts

## Environment Variables

None required for basic functionality. Future versions will require:
- OpenRouter API key
- Authentication configuration
- CORS settings