# HubGPT Product Requirements Document

### 1.1 Purpose

The **hubgpt** system currently runs locally using Streamlit as a front-end. This PRD aims to define requirements for:
1. Building a **FastAPI** backend that exposes all core AI/chat functionality via RESTful (or similar) APIs.
2. Providing a minimal, separate **HTML/JS** front end (styled with **Tailwind** for layout and design) that consumes these APIs to demonstrate functionality in a cloud-deployable manner.
3. Preserving the existing file-based logic (flat files, DuckDB) as much as possible to avoid introducing a new database technology at this stage.
4. Re-using the existing utils, tools, and advisors as much as possible.

### 1.2 Goals & Objectives

1. **Cloud Deployability**: Enable hosting the system in the cloud with minimal friction.
2. **Separation of Concerns**: Decouple front-end from back-end so each can scale or be modified independently.
3. **Maintain Current Features**: Replicate the existing features (advisor creation, conversation histories, notepads, file inclusion, etc.) through new endpoints.
4. **Minimize Disruption**: Reuse existing modules (tools, advisors, utils, etc.) wherever possible, avoiding large-scale rewrites.

### 1.3 Non-Goals

### Completed (Milestone A)
- ✅ Basic FastAPI backend structure
- ✅ Advisor configuration loading from JSON/MD files
- ✅ OpenRouter API integration
- ✅ Basic chat functionality
- ✅ File-based storage system

### Completed (Milestone B)
- ✅ Modular code architecture with clear separation of concerns
  - Models, routers, and services clearly separated
  - Each component has single responsibility
  - Dependencies properly managed
- ✅ Chat history management with archival support
  - Reliable file storage system
  - Clear distinction between current and archived chats
  - Consistent file naming conventions
- ✅ Test harness with chat interface
  - Advisor selection
  - Chat history viewing
  - Message sending/receiving
  - Chat management operations
  - Frontend markdown rendering
  - Real-time streaming display
- ✅ Improved error handling and logging
  - Automatic file repair
  - Detailed error messages
  - Operation logging
  - Streaming response error handling
- ✅ Chat deletion functionality
  - Different behavior for current vs archived chats
  - Automatic new chat creation
  - Safe deletion operations
- ✅ Streaming response support
  - Server-Sent Events (SSE) implementation
  - Real-time token streaming
  - Configurable per advisor
  - Graceful fallback to non-streaming

### Current Architecture

The API follows a modular architecture with clear separation of concerns:

```
api/
├── main.py              # FastAPI app initialization and routing
├── config.py            # Configuration and environment variables
├── dependencies.py      # FastAPI dependencies and middleware
├── routers/            # API route handlers
│   ├── advisors.py     # Advisor-related endpoints
│   └── chat.py         # Chat-related endpoints
├── models/             # Pydantic data models
│   ├── advisors.py     # Advisor models
│   └── chat.py         # Chat/Message models
├── services/           # Business logic
│   ├── advisor_service.py    # Advisor operations
│   ├── chat_service.py      # Chat operations
│   └── storage_service.py   # File storage operations
└── index.html         # Test harness
```

### File Storage System

The API uses a structured file-based storage system designed for reliability and easy management:

```
/advisors/
├── *.json/*.md         # Advisor configuration files
├── chats/             # Current chat files
│   └── {advisor_id}.json
└── archive/           # Archived chat files
    └── {advisor_id}_{hex}.json
```

### Chat Management Features
- One active chat per advisor
- Automatic archival of previous chats
- Unique hex suffixes for archived chats
- Clear/Delete operations with appropriate behavior
- Automatic creation of blank chats when needed
- Streaming and non-streaming response support
- Real-time message updates via SSE

### Upcoming (Milestone C)
- [ ] Authentication system
  - User authentication
  - Session management
  - Role-based access control
- [ ] User management
  - User profiles
  - Preferences storage
  - Usage tracking
- [ ] Rate limiting
  - Per-user limits
  - Global API limits
  - Quota management
- [ ] API key management
  - Key generation
  - Usage tracking
  - Revocation system
- [ ] Enhanced CORS configuration
  - Domain whitelisting
  - Method restrictions
  - Header management



## Architecture Diagram

```
[Client] ←→ [FastAPI Backend] ←→ [OpenRouter API]
   ↑              ↑
   |              |
[Test Harness] [File Storage]
```

## Development Guidelines

1. **Code Organization**
   - Keep components focused and single-purpose
   - Use clear naming conventions
   - Maintain separation of concerns

2. **Error Handling**
   - Provide informative error messages
   - Implement proper logging
   - Include error recovery mechanisms

3. **Testing**
   - Write unit tests for new features
   - Use the test harness for integration testing
   - Document test scenarios

4. **Documentation**
   - Keep README up to date
   - Document new endpoints
   - Include usage examples

## Next Steps

1. Implement authentication system
   - Design user model
   - Set up authentication middleware
   - Add login/logout endpoints

2. Add user management
   - Create user database
   - Implement CRUD operations
   - Add profile management

3. Enhance security features
   - Set up rate limiting
   - Implement API key system
   - Configure CORS properly

4. Develop notepad functionality
   - Design storage system
   - Create CRUD endpoints
   - Add search capability

5. Expand tool support
   - Create tool registry
   - Implement discovery system
   - Add parameter validation


### 7.2 Chat / Conversation

**Requirement**: Provide endpoints to initiate and manage conversations with a chosen advisor.

1. **Get Latest Conversation**
   - **Endpoint**: `GET /chat/advisor/{advisor_id}/latest`
   - **Response**: 
     - If exists: Latest conversation object with messages
     - If none: Creates and returns a new blank conversation
   - **Logic**: 
     - Scans `/chats` directory for most recent conversation with advisor
     - Leverages `chat_utils.py` and `message_utils.py` for conversation management
     - Creates new conversation if none found

2. **List Previous Conversations**
   - **Endpoint**: `GET /chat/advisor/{advisor_id}/history`
   - **Response**: Array of conversation metadata (id, timestamps, message count)
   - **Logic**:
     - Scans `/chats` directory for conversations with specified advisor
     - Uses `chat_utils.py` for conversation retrieval
     - Sorts by timestamp descending

3. **Create New Conversation**
   - **Endpoint**: `POST /chat/advisor/{advisor_id}/new`
   - **Response**: 
     - `conversation_id`: Newly created conversation ID
     - Initial conversation state
   - **Logic**:
     - Creates new conversation file in `/chats`
     - Initializes with advisor system prompt
     - Uses `chat_utils.py` and `message_utils.py` for setup

4. **Delete Conversation**
   - **Endpoint**: `DELETE /chat/{conversation_id}`
   - **Response**: Success confirmation
   - **Logic**:
     - Validates conversation exists
     - Optional: Moves to archive directory before deletion
     - Uses `file_utils.py` for safe file operations

5. **Send Message**  
   - **Endpoint**: `POST /chat/{conversation_id}/message`  
   - **Body**:
     - `user_message`: The user's text  
   - **Response**:
     - `assistant_message`: The AI's reply  
   - **Logic**:
     - Reads conversation context from memory or from file
     - Passes user message to the AI agent (with system instructions, tools, etc.)
     - Persists updated conversation history to `/chats`

6. **Retrieve Chat History**  
   - **Endpoint**: `GET /chat/{conversation_id}`  
   - **Response**: The entire conversation history (list of user/assistant messages)
   - **Logic**: Reads from the JSON transcript in `/chats/{conversation_id}.json`

7. **Clear/Archive Conversation**  
   - **Endpoint**: `POST /chat/{conversation_id}/clear`  
   - **Response**: Confirmation  
   - **Logic**:
     - Moves or copies the conversation file to `/archive` directory
     - Creates a fresh conversation file if continuing the session

### 7.3 Notepads Management

**Requirement**: Provide endpoints for managing notepads (similar to the current Streamlit approach).

1. **List Notepads**  
   - **Endpoint**: `GET /notepads`  
   - **Response**: Array of notepad objects (id, name, timestamps, etc.).  

2. **Create Notepad**  
   - **Endpoint**: `POST /notepads`  
   - **Body**:  
     - `title`: Name of the notepad  
     - (Optional) `description`  
   - **Response**:  
     - `notepad_id`  

3. **Upload Files**  
   - **Endpoint**: `POST /notepads/{notepad_id}/files`  
   - **Body**: Files to upload  
   - **Response**: Confirmation + list of uploaded file references  

4. **Chat with Notepad Context**  
   - **Endpoint**: `POST /notepads/{notepad_id}/chat`  
   - **Body**: 
     - `user_message`  
     - (Optional) `advisor_id` – if we want to combine notepad + advisor.  
   - **Response**: AI reply that includes context gleaned from associated files.  

5. **Retrieve Notepad Chat**  
   - **Endpoint**: `GET /notepads/{notepad_id}/chat`  
   - **Response**: The chat history for this notepad.  

### 7.4 Tools Invocation

**Requirement**: Tools remain discoverable in the `tools/` directory. The AI agent determines if/when to call them.

- **Implementation Detail**:  
  - Calls to tools typically happen internally in the agent logic.  
  - If we want direct user access (admin or debug), we can have a route like `POST /tools/execute` with parameters to specify which tool, but this might be optional.  

### 7.5 File and DuckDB Persistence

1. **File Storage**:
   - Use existing directories (`/advisors`, `/chats`, `/archive`, `/notepads`) for reading/writing.  
   - Maintain the same JSON/MD file formats.  

2. **DuckDB** (Optional/Existing):
   - Keep existing usage in `utils/db_utils.py`.  
   - No new tables or schema changes unless required to store session indexes, etc.  

---

## 8. Non-Functional Requirements

1. **Performance**:  
   - Must handle multiple simultaneous requests from the front end.  
   - Avoid re-loading large files on each request if possible (in-memory caching or per-request caching strategies are acceptable).  

2. **Scalability**:  
   - The separation of front end and back end allows for horizontal scaling.  
   - Should not rely on local server-specific features that hamper deployment to common PaaS platforms (e.g., Heroku, AWS ECS, etc.).  

3. **Security**:  
   - Basic token-based or header-based auth can be implemented if needed.  
   - File reads/writes must be validated to prevent path traversal.  

4. **Maintainability**:  
   - Minimal code changes.  
   - Leverage existing modules for business logic and keep them well-structured.  
   - Provide docstrings and type hints for new FastAPI code.  

5. **Observability**:  
   - Implement logging (reuse `log_utils.py`) for each request at the API layer.  
   - Retain or expand upon existing logs in `/logs` directory if helpful.  

---

## 9. Success Criteria

1. **Core Feature Parity**: All major features from the Streamlit version (advisor-based chats, file inclusion, notepads) are accessible via the new FastAPI endpoints.
2. **Cloud-Ready**: The system can be deployed and run from a remote server without the performance issues encountered by the Streamlit approach.
3. **Minimal Refactoring**: Most existing modules (`utils`, `tools`, `advisors.py`, etc.) remain intact with only minor modifications to accommodate the new endpoints.
4. **Demonstrable UI**: A simple HTML/JS site, styled with Tailwind, can create a conversation, send messages, and display responses from advisors.

---

## 10. Open Questions & Future Considerations

1. **Streaming Responses**:  
   - Do we need token-by-token streaming? If so, consider a WebSocket or Server-Sent Events endpoint in FastAPI.
2. **Authentication**:  
   - For now, a simple system without user-level permissions. Future iteration could add JWT or token-based auth.
3. **Scalability of Tools**:  
   - Tools that make external API calls might need timeouts or concurrency limits when heavily used in the cloud.
4. **File Handling in Production**:  
   - Large file uploads could require an S3 bucket or other storage in real-world deployments. For this iteration, storing directly on the server's filesystem is sufficient.

---

### End of PRD

# Chat Endpoints Implementation Plan

## Overview

The chat functionality is the core of the HubGPT system. Rather than reimplementing proven functionality, we will adapt our existing utils to work with FastAPI endpoints.

## Architecture

### Core Utils (Existing)

1. **LLM Utils** (`api/utils/llm_utils.py`)
   - OpenRouter API interaction
   - Streaming response handling
   - Tool call management
   - Message processing

2. **Chat Utils** (`api/utils/chat_utils.py`)
   - Chat history management
   - File operations for conversations
   - Message formatting
   - Archive handling

3. **Prompt Utils** (`api/utils/prompt_utils.py`)
   - System message preparation
   - Template processing
   - File inclusion handling
   - Tool configuration

4. **Tool Utils** (`api/utils/tool_utils.py`)
   - Tool discovery and loading
   - Parameter validation
   - Execution handling
   - Result formatting

### FastAPI Integration

1. **Chat Router** (`routers/chat.py`)
   - Endpoint definitions
   - Request validation
   - Response formatting
   - Error handling
   - SSE streaming setup

2. **Adapters** (Only if needed)
   - Minimal wrappers to convert between Streamlit and FastAPI patterns
   - Async support where needed
   - Stream handling adaptations
   - Error translation

## Implementation Strategy

### Phase 1: Direct Utils Integration
1. Map existing util functions to endpoints
2. Identify Streamlit dependencies
3. Create minimal adapters where needed
4. Preserve existing business logic

### Phase 2: Streaming Adaptation
1. Adapt `llm_utils.py` streaming for SSE
2. Maintain existing chunking logic
3. Add FastAPI-specific stream handling
4. Keep tool call streaming intact

### Phase 3: Error Handling
1. Map util errors to HTTP status codes
2. Add FastAPI error handlers
3. Preserve existing error messages
4. Maintain logging patterns

### Phase 4: Testing & Optimization
1. Verify utils work as expected
2. Test streaming performance
3. Validate tool execution
4. Ensure file operations work

## Endpoint Specifications

### 1. Send Message
```
POST /chat/{conversation_id}/message
```

Uses:
- `llm_utils.get_llm_response()` for LLM interaction
- `chat_utils.save_chat_history()` for persistence
- `prompt_utils.load_prompt()` for context
- `tool_utils.load_tools()` for tool support

#### Request
```json
{
  "message": "string",
  "stream": true,
  "context": {
    "files": ["optional array of file references"],
    "tools": ["optional array of tool names to enable"]
  }
}
```

#### Processing Flow
1. Load conversation using `chat_utils`
2. Prepare prompt using `prompt_utils`
3. Get LLM response using `llm_utils`
4. Save history using `chat_utils`
5. Stream response if requested

### 2. Tool Call Flow

Leverages existing tool handling from `llm_utils.py`:
- Tool detection
- Execution via `tool_utils`
- Response accumulation
- History updates

## Migration Notes

1. **Util Modifications**
   - Keep changes minimal
   - Only remove Streamlit-specific code
   - Preserve core functionality
   - Add async support where needed

2. **New Code**
   - FastAPI endpoint definitions
   - Request/response models
   - SSE streaming adapters
   - Error handlers

## Success Criteria

1. **Functionality**
   - Utils work same as in Streamlit
   - No loss of features
   - Tool calls work identically
   - File operations maintained

2. **Code Quality**
   - Minimal changes to utils
   - Clear adapter patterns
   - Good error handling
   - Proper async support

3. **Performance**
   - Fast response times
   - Efficient streaming
   - Reliable tool execution

## Next Steps

1. Audit utils for Streamlit dependencies
2. Create FastAPI endpoint shells
3. Add minimal adapters
4. Test core functionality
5. Implement streaming
6. Add error handling

## Notes

- The existing utils have been battle-tested in Streamlit
- They handle complex scenarios like tool calling
- File operations are proven reliable
- Error handling is mature
- Changes should be minimal and focused
