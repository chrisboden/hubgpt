# HubGPT API

The HubGPT API is a FastAPI-based backend service that powers the HubGPT agent framework. It provides endpoints for managing AI advisors, conversations, and file operations with a focus on multi-user support and database persistence.

NOTE: Test harness is at api/index.html

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
    messages JSON NOT NULL,  -- Required array of system messages
    gateway VARCHAR,
    tools JSON,
    created_at DATETIME,
    updated_at DATETIME
);
```

Important Notes:
- The `messages` field is required and must be a JSON array of message objects
- Each message object must have `role` and `content` fields
- At least one system message is required
- Example message format:
```json
{
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant..."
        }
    ]
}
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
Response: List of advisor objects with full details including IDs
Example Response:
[
    {
        "id": "db2d282a-abae-4fcd-b900-eb0b43f743ee",
        "name": "default",
        "model": "gpt-4o-mini",
        ...
    }
]

GET /advisors/{advisor_id}
Description: Get advisor details by ID (not name)
Response: Full advisor object
Example: GET /advisors/db2d282a-abae-4fcd-b900-eb0b43f743ee

PUT /advisors/{advisor_id}
Description: Update advisor by ID
Body: AdvisorUpdate object
Note: Name cannot be changed after creation

DELETE /advisors/{advisor_id}
Description: Delete advisor
Response: Success message
```

### Chat

```http
GET /chat/advisor/{advisor_id}/history
Description: List all conversations for an advisor
Response: List of conversation metadata
Example: GET /chat/advisor/db2d282a-abae-4fcd-b900-eb0b43f743ee/history

GET /chat/advisor/{advisor_id}/latest
Description: Get or create latest conversation
Response: ConversationHistory object

POST /chat/advisor/{advisor_id}/new
Description: Create new conversation with advisor
Response: Conversation object with ID
Example: POST /chat/advisor/db2d282a-abae-4fcd-b900-eb0b43f743ee/new

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
GET /api/v1/files
Description: List all files for the current user
Response: List[FileResponse]

GET /api/v1/files/{file_path}/content
Description: Get file contents
Response: File content
Auth: Bearer token required

POST /api/v1/files/{file_path}
Description: Create or update file
Body: multipart/form-data
Fields:
  - file: File data
  - is_public: boolean (optional)
Response: FileResponse

PATCH /api/v1/files/{file_path}
Description: Rename file
Body: JSON
{
    "new_name": string
}
Response: FileResponse

DELETE /api/v1/files/{file_path}
Description: Delete file
Response: Success message
Auth: Bearer token required

POST /api/v1/files/{file_path}/share
Description: Share file with another user
Body: JSON
{
    "shared_with_id": string,
    "permissions": {
        "read": boolean,
        "write": boolean
    }
}
Response: FileShareResponse

GET /api/v1/files/{file_path}/shares
Description: List all shares for a file
Response: List[FileShareResponse]

DELETE /api/v1/files/{file_path}/share/{user_id}
Description: Remove file share
Response: Success message
```

### File Management Features

1. Core Features ✅
   - [x] User-specific storage spaces with proper isolation
   - [x] Database-backed file metadata tracking
   - [x] File path sanitization and validation
   - [x] Access control system
   - [x] Automatic directory creation
   - [x] File type detection
   - [x] Content type tracking
   - [x] Public/private file support

2. File Operations ✅
   - [x] File upload via multipart/form-data
   - [x] File content retrieval
   - [x] File renaming with path updates
   - [x] File deletion with cleanup
   - [x] Directory listing with tree structure
   - [x] File sharing between users

3. Access Control ✅
   - [x] Private by default
   - [x] Optional public flag
   - [x] Owner-based access
   - [x] Share-based access
   - [x] Database-tracked permissions

4. Error Handling ✅
   - [x] Failed upload cleanup
   - [x] Access validation
   - [x] Path validation
   - [x] Duplicate handling
   - [x] Proper error messages

### File Storage Structure

The system uses a structured storage system for user files:

```
storage/
├── users/
│   ├── {user_id}/
│   │   ├── files/
│   │   │   ├── content/       # User file content
│   │   │   ├── uploads/       # Temporary upload storage
│   │   │   └── temp/         # Processing files
│   │   └── ...
│   └── ...
└── shared/                   # Shared resources
    └── ...
```

### Database Schema

```sql
CREATE TABLE user_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    is_public BOOLEAN DEFAULT false,
    file_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, file_path)
);

CREATE TABLE file_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID REFERENCES user_files(id),
    shared_with_id UUID REFERENCES users(id),
    permissions JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Example Usage

```javascript
// Create/update file
const formData = new FormData();
formData.append('file', new File(['content'], 'test.txt'));
formData.append('is_public', false);

await fetch('/api/v1/files/path/to/test.txt', {
    method: 'POST',
    headers: {
        Authorization: `Bearer ${token}`
    },
    body: formData
});

// Rename file
await fetch('/api/v1/files/path/to/test.txt', {
    method: 'PATCH',
    headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
        new_name: 'new_test.txt'
    })
});

// Share file
await fetch('/api/v1/files/path/to/test.txt/share', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
        shared_with_id: 'user123',
        permissions: {
            read: true,
            write: false
        }
    })
});
```

### Security Considerations

1. File Access Control
   - Files are private by default
   - Access requires authentication
   - Path traversal prevention
   - Content type validation
   - Size limits enforcement

2. User Isolation
   - Each user has their own storage space
   - Files are stored under user-specific directories
   - Database tracks ownership and permissions
   - Share-based access control

3. Error Handling
   - Proper cleanup on failed operations
   - Secure error messages
   - Transaction support for database operations
   - Automatic directory management

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

## File Inclusion System

The API includes a powerful file inclusion system that allows dynamic content injection into advisor messages. This is handled by the `prompt_utils.py` module.

### Tag Formats

1. **File Inclusion**: `<$file:path/to/file$>`
   - Example: `<$file:files/me/aboutme.md$>`
   - Paths are relative to workspace root
   - Supports both shared and user-specific files
   - Shared files are in `files/` directory
   - User files are in `storage/users/{user_id}/files/`

2. **Directory Inclusion**: `<$dir:path/to/directory/*.ext$>`
   - Example: `<$dir:files/knowledge/*.txt$>`
   - Includes all matching files in alphabetical order
   - Content is combined with file headers

3. **DateTime**: `<$datetime[:format]$>`
   - Example: `<$datetime:%Y-%m-%d$>`
   - Default format: "%Y-%m-%d %H:%M:%S"
   - Supports any valid Python datetime format

### Example Advisor Message

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Hi! I'm an AI assistant. Today is <$datetime$>.\n\nAbout me:\n<$file:files/me/aboutme.md$>\n\nKnowledge base:\n<$dir:files/knowledge/*.md$>"
    }
  ]
}
```

### Common Issues

1. **File Not Found Errors**:
   - Check that file paths are relative to workspace root
   - Verify file exists in correct location
   - Use `files/` prefix for shared files
   - Check file permissions

2. **Tag Processing Issues**:
   - Ensure correct tag format with both opening and closing markers
   - File paths should include `file:` prefix
   - Directory paths should include `dir:` prefix
   - DateTime format should be valid Python strftime format

3. **Database Storage**:
   - Tags must be properly escaped in JSON
   - Use proper JSON functions when updating via SQLite
   - Example SQL for updating advisor message:
   ```sql
   UPDATE advisors 
   SET messages = json_array(
     json_object(
       'role', 'system',
       'content', 'Message with <$file:files/me/aboutme.md$>'
     )
   )
   WHERE name = 'advisor_name';
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

### Key Concepts

#### Advisor Management
Advisors are the core entities in HubGPT. Each advisor has:
- A unique ID (UUID)
- A unique name
- Model configuration
- System messages
- Tool settings

```sql
-- Example advisor record
{
    "id": "db2d282a-abae-4fcd-b900-eb0b43f743ee",
    "name": "default",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": true,
    "messages": [{"role": "system", "content": "You are a helpful assistant..."}],
    "tools": ["use_reasoning", "search_web"],
    "gateway": "openrouter"
}
```

#### Chat Management
Chats (conversations) are always associated with:
- An advisor (via advisor_id)
- A user (via user_id)
- A sequence of messages

### API Endpoints

#### Chat Management
```http
GET /chat/advisor/{advisor_id}/conversation/{conversation_id}/messages
Description: Get messages for a specific conversation
Response: List of messages in sequence
Example: GET /chat/advisor/db2d282a-abae-4fcd-b900-eb0b43f743ee/conversation/123e4567-e89b-12d3-a456-426614174000/messages
```

### Important Notes

1. **ID vs Name Usage**
   - Advisors are always referenced by their UUID in API calls
   - Names are unique but are used only for display/creation
   - All endpoints expecting an advisor reference use the ID

2. **Data Structures**
   - Advisor objects always include their full configuration
   - Messages array in advisor config contains system prompts
   - Tools are stored as string arrays
   - All timestamps are in ISO format

3. **Common Gotchas**
   - Using advisor names instead of IDs in endpoints will fail
   - Trying to modify advisor names after creation will fail
   - Chat endpoints require both advisor_id and conversation_id
   - Missing system messages in advisor creation will fail

4. **Authentication**
   - Both JWT and Basic Auth are supported
   - JWT: `Authorization: Bearer <token>`
   - Basic: `Authorization: Basic <base64(username:password)>`
   - Default admin credentials: admin/admin

### Example Usage

```javascript
// Get advisor by ID
const response = await fetch('/advisors/db2d282a-abae-4fcd-b900-eb0b43f743ee');
const advisor = await response.json();
// {
//     "id": "db2d282a-abae-4fcd-b900-eb0b43f743ee",
//     "name": "default",
//     "model": "gpt-4o-mini",
//     ...
// }

// Update advisor
await fetch('/advisors/db2d282a-abae-4fcd-b900-eb0b43f743ee', {
    method: 'PUT',
    body: JSON.stringify({
        model: "gpt-4",
        temperature: 0.8,
        messages: [{"role": "system", "content": "New system message"}]
    })
});

// Get chat history
const chats = await fetch('/chat/advisor/db2d282a-abae-4fcd-b900-eb0b43f743ee/history');
// [
//     {
//         "id": "123e4567-e89b-12d3-a456-426614174000",
//         "created_at": "2024-02-01T12:00:00Z",
//         "message_count": 10
//     }
// ]
```

# HubGPT API Documentation

## Overview
The HubGPT API provides endpoints for managing advisors, conversations, and file storage. This document outlines the key endpoints and their usage.

## Authentication
The API supports two authentication methods:
1. JWT Token (preferred): Send Bearer token in Authorization header
2. Basic Auth (fallback): Use username/password credentials

## Key Endpoints

### Advisors
- `GET /advisors/`: List all advisors
- `GET /advisors/{advisor_id}`: Get advisor details by ID
- `POST /advisors/`: Create new advisor
- `PUT /advisors/{advisor_id}`: Update advisor by ID
- `DELETE /advisors/{advisor_id}`: Delete advisor

Note: Advisors are referenced by their UUID, not by name. The advisor ID should be used in all API calls.

### Chat
- `GET /chat/advisor/{advisor_id}/history`: Get conversation history for an advisor
- `POST /chat/advisor/{advisor_id}/new`: Create a new conversation
- `GET /chat/messages/{conversation_id}`: Get messages for a specific conversation
- `POST /chat/{conversation_id}/message`: Send a message in a conversation
- `POST /chat/{conversation_id}/cancel`: Cancel ongoing message generation

### Files
- `GET /files/`: List all files
- `POST /files/{path}`: Create file or directory
- `GET /files/{path}`: Get file content
- `PUT /files/{path}`: Update file
- `DELETE /files/{path}`: Delete file
- `PATCH /files/{path}`: Rename file
- `GET /files/{path}/shares`: List file shares
- `POST /files/{path}/share`: Share file with user
- `DELETE /files/{path}/share/{user_id}`: Remove file share

## Database Schema

### Users Table
- id (UUID): Primary key
- username (String): Unique username
- email (String): User email
- hashed_password (String): Encrypted password
- is_active (Boolean): Account status

### Advisors Table
- id (UUID): Primary key
- name (String): Unique advisor name
- model (String): LLM model identifier
- gateway (String): API gateway (openrouter, google, openai, etc.)
- temperature (Float): Model temperature
- max_tokens (Integer): Maximum response tokens
- stream (Boolean): Enable streaming responses
- messages (JSON): System messages and context
- tools (JSON): Available tools configuration

### Conversations Table
- id (UUID): Primary key
- advisor_id (UUID): Reference to advisor
- user_id (UUID): Reference to user
- created_at (Timestamp): Creation time
- updated_at (Timestamp): Last update time

### Messages Table
- id (UUID): Primary key
- conversation_id (UUID): Reference to conversation
- role (String): Message role (user/assistant)
- content (Text): Message content
- created_at (Timestamp): Message timestamp

## Common Issues and Solutions

1. Advisor Updates (404 Error):
   - Use advisor's UUID instead of name in API calls
   - Endpoint should be `/advisors/{advisor_id}` not `/advisors/{name}`

2. Chat History Loading (404 Error):
   - Use `/chat/messages/{conversation_id}` to fetch messages
   - Conversation ID is required, not just advisor ID

3. Authentication:
   - JWT token is preferred but may expire
   - System falls back to basic auth if JWT fails
   - Register endpoint returns 400 if user exists (expected behavior)

## Best Practices

1. Always use UUIDs for referencing resources (advisors, conversations, etc.)
2. Handle both streaming and non-streaming responses in chat
3. Implement proper error handling for API responses
4. Store and manage authentication tokens appropriately
5. Use appropriate content types for requests (application/json)