# HubGPT API

The HubGPT API is a FastAPI-based backend service that powers the HubGPT agent framework. It provides endpoints for managing AI advisors, conversations, and file operations with a focus on multi-user support and database persistence.

## System Architecture

### Core Components

- **FastAPI Application**: Main web framework with CORS support and proper middleware
- **SQLite Database**: Current storage backend (with planned PostgreSQL support)
- **Alembic Migrations**: Database schema version control
- **JWT + Basic Auth**: Dual authentication system for backward compatibility

### Database Schema

#### Key Tables

1. **users**
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR NOT NULL,
    created_at DATETIME,
    settings JSON
);
```

2. **advisors**
```sql
CREATE TABLE advisors (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description VARCHAR,
    model VARCHAR,
    temperature FLOAT,
    max_tokens INTEGER,
    stream BOOLEAN,
    messages JSON,
    gateway VARCHAR,
    tools JSON,
    created_at DATETIME,
    updated_at DATETIME
);
```

3. **conversations**
```sql
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,
    advisor_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36),
    status VARCHAR NOT NULL,
    message_count INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(advisor_id) REFERENCES advisors(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

4. **messages**
```sql
CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT,
    sequence INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);
```

5. **tool_calls**
```sql
CREATE TABLE tool_calls (
    id VARCHAR(36) PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL,
    tool_call_id VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    function_name VARCHAR NOT NULL,
    function_arguments JSON NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(message_id) REFERENCES messages(id)
);
```

## API Endpoints

### Authentication

```http
POST /auth/register
Description: Register a new user
Body: {
    "username": string,
    "email": string,
    "password": string
}
Response: UserResponse object

POST /auth/login
Description: Login and get access token
Body: {
    "username": string,
    "password": string
}
Response: Token object with access_token

POST /auth/logout
Description: Invalidate current session
Headers: Authorization: Bearer <token>
Response: Success message

GET /verify
Description: Verify current credentials
Auth: Basic or Bearer Token
Response: UserResponse object
```

### Advisors

```http
GET /advisors
Description: List all available advisors
Response: List of AdvisorSummary objects

POST /advisors
Description: Create new advisor
Body: {
    "name": string,
    "description": string,
    "model": string,
    "temperature": float,
    "max_tokens": integer,
    "stream": boolean,
    "messages": array,
    "gateway": string,
    "tools": array
}
Response: Advisor object

GET /advisors/{advisor_id}
Description: Get advisor details
Response: Advisor object

PUT /advisors/{advisor_id}
Description: Update advisor
Body: Same as POST /advisors
Response: Updated Advisor object

DELETE /advisors/{advisor_id}
Description: Delete advisor
Response: Success message
```

### Chat

```http
GET /chat/advisor/{advisor_id}/history
Description: List conversations for advisor
Response: List of ConversationMetadata objects

GET /chat/advisor/{advisor_id}/latest
Description: Get or create latest conversation
Response: ConversationHistory object

POST /chat/advisor/{advisor_id}/new
Description: Create new conversation
Response: ConversationHistory object

POST /chat/{conversation_id}/message
Description: Send message to conversation
Body: {
    "message": string
}
Response: ChatResponse object or StreamingResponse

DELETE /chat/{conversation_id}
Description: Delete conversation
Response: Success message
```

### Files

```http
GET /files
Description: List all files recursively
Response: FileList object

GET /files/{path}
Description: Get file contents
Response: File content as text

POST /files/{path}
Description: Create file or directory
Body: {
    "content": string  // Optional, if not provided creates directory
}
Response: Success message

PUT /files/{path}
Description: Update file contents
Body: {
    "content": string
}
Response: Success message

PATCH /files/{path}
Description: Rename file or directory
Body: {
    "new_name": string
}
Response: Success message

DELETE /files/{path}
Description: Delete file or directory
Response: Success message
```

## Authentication

The system supports two authentication methods:

1. **JWT Authentication** (New)
   - Used for the new multi-user system
   - Token-based with proper session management
   - Required for all new feature development

2. **Basic Authentication** (Legacy)
   - Maintained for backward compatibility
   - Uses admin:admin credentials by default
   - Will be phased out in future versions

## Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up the database:
```bash
# Initialize migrations
alembic upgrade head
```

3. Run the development server:
```bash
uvicorn api.main:app --reload
```

## Testing

The API includes a built-in test harness at `/` (index.html) for interactive testing. For command-line testing:

```bash
# Health check
curl http://localhost:8000/health

# Create conversation (with basic auth)
curl -X POST http://localhost:8000/chat/advisor/default/new -u admin:admin

# Send message
curl -X POST http://localhost:8000/chat/{conversation_id}/message \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

## LLM Integration

The system uses OpenRouter as the default gateway for LLM access, supporting multiple models:
- openai/gpt-4o-mini (default)
- google/gemini-pro
- anthropic/claude-2
- meta/llama2

Configure the model and parameters in the advisor definition:
```json
{
    "name": "My Advisor",
    "model": "openai/gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": true,
    "gateway": "openrouter",
    "tools": ["use_reasoning", "get_weather"]
}
```

## Current Status

The API is transitioning from a single-user file-based system to a multi-user database-backed architecture. Key features:

✅ **Working**
- Basic and JWT authentication
- Advisor management
- Chat conversations with streaming
- Tool integration
- Database persistence

🔄 **In Progress**
- User management improvements
- Data isolation between users
- Sharing capabilities
- Tool access controls

⏳ **Planned**
- PostgreSQL migration
- Team workspaces
- Advanced permission system
- Usage analytics

## Common Issues

1. **404 on Chat Endpoints**: Ensure you're using the correct URL pattern:
   - ✅ `/chat/advisor/{advisor_id}/new`
   - ❌ `/chat/{advisor_id}/new`

2. **Advisor Not Found**: Verify the advisor exists in the database:
   ```sql
   SELECT * FROM advisors WHERE name = 'advisor_name';
   ```

3. **Authentication Errors**: The system accepts both:
   - Basic Auth: `-u admin:admin`
   - Bearer Token: `-H "Authorization: Bearer <token>"`

## Directory Structure

```
api/
├── __init__.py
├── main.py              # FastAPI application
├── database.py          # Database configuration
├── config.py            # Application settings
├── routers/            
│   ├── auth.py         # Authentication routes
│   ├── advisors.py     # Advisor management
│   ├── chat.py         # Chat functionality
│   └── files.py        # File operations
├── models/             
│   ├── users.py        # User models
│   ├── chat.py         # Chat models
│   └── advisors.py     # Advisor models
├── services/           
│   └── auth_service.py # Authentication logic
├── api_utils/          
│   ├── chat_utils.py   # Chat helpers
│   ├── llm_utils.py    # LLM integration
│   └── tool_utils.py   # Tool management
└── migrations/         
    └── versions/       # Database migrations
```

## Contributing

1. All new features should use the database backend
2. Maintain backward compatibility with basic auth
3. Add proper error handling and logging
4. Include database migrations for schema changes
5. Update tests for new functionality

## Next Steps

1. Complete user management features
2. Implement conversation sharing
3. Add tool access controls
4. Migrate to PostgreSQL
5. Add usage analytics

For questions or issues, please contact the team lead or refer to the PRD document at `api/multi_user_prd.md`.

## Tips for New Contributors

### Getting Started

1. **Setup Your Development Environment**
   ```bash
   # Clone the repository
   git clone <repo-url>
   cd hubgpt/api
   
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Setup environment variables
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Database Setup**
   ```bash
   # Initialize the database
   alembic upgrade head
   
   # Verify tables were created
   sqlite3 hubgpt.db ".tables"
   
   # Inspect table schema
   sqlite3 hubgpt.db ".schema users"
   sqlite3 hubgpt.db ".schema advisors"
   sqlite3 hubgpt.db ".schema conversations"
   ```

3. **Quick Data Inspection**
   ```bash
   # View all advisors
   sqlite3 hubgpt.db "SELECT name, model, tools FROM advisors;"
   
   # Check conversation history
   sqlite3 hubgpt.db "SELECT id, advisor_id, message_count FROM conversations;"
   
   # View recent messages
   sqlite3 hubgpt.db "SELECT conversation_id, role, content FROM messages ORDER BY created_at DESC LIMIT 5;"
   ```

4. **Testing the API**
   ```bash
   # Start the development server
   uvicorn api.main:app --reload
   
   # Test health endpoint
   curl http://localhost:8000/health
   
   # Create test advisor
   curl -X POST http://localhost:8000/advisors \
     -H "Content-Type: application/json" \
     -d '{"name":"test","model":"gpt-4","temperature":0.7,"stream":true}'
   ```

### Development Tips

1. **Understanding the Flow**
   - Start with `main.py` to see how routes are registered
   - Check `routers/` for endpoint implementations
   - Models in `models/` define data structures
   - Business logic lives in `services/`

2. **Common Development Tasks**
   - Adding a new endpoint: Create route in appropriate router file
   - Database changes: Create new Alembic migration
   - Adding features: Follow existing patterns in similar endpoints

3. **Debugging**
   - Use FastAPI's automatic docs: http://localhost:8000/docs
   - Check logs in `logs/api.log`
   - Use SQLite Browser for database inspection
   - FastAPI debug mode shows detailed error traces

4. **Best Practices**
   - Follow FastAPI patterns (dependency injection, Pydantic models)
   - Add type hints to all functions
   - Document new endpoints in OpenAPI format
   - Write tests for new features

5. **Common Issues**
   - Database locked: Check for concurrent connections
   - Auth errors: Verify token/credentials format
   - 422 errors: Check request body against models
   - Stream hanging: Ensure proper client disconnection

### Making Changes

1. **Adding New Features**
   ```bash
   # Create new branch
   git checkout -b feature/my-feature
   
   # Create database migration if needed
   alembic revision -m "add_new_table"
   
   # Run tests
   pytest tests/
   ```

2. **Code Style**
   - Follow PEP 8
   - Use Black for formatting
   - Add docstrings to functions
   - Keep functions focused and small

3. **Testing**
   - Write unit tests for new features
   - Test both success and error cases
   - Verify database migrations
   - Check API responses match models

4. **Documentation**
   - Update API documentation
   - Add docstrings to new functions
   - Document environment variables
   - Update README if needed