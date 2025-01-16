# HubGPT API

FastAPI-based API for HubGPT that handles advisor management, prompt includes, and LLM interactions.

## Core Features

- Advisor management with Supabase integration
- Automatic processing of file includes in prompts
- Streaming LLM responses using OpenRouter
- Persistent chat history with conversation continuity
- Error handling and debug information

## Key Endpoints

### GET /advisors
Returns a list of all available advisors.

### GET /includes/{path}
Retrieves content for a specific include file.

### POST /chat/{advisor_name}
Streams a chat response from a specific advisor. Supports:
- New conversations (no chat_id)
- Continuing existing conversations (with chat_id)
- Temperature and system message overrides
- Automatic include processing
- Chat history persistence

## Technical Details

### Database Integration
- Uses PostgreSQL through Supabase
- Tables: 
  - `advisors`: Stores advisor configurations
  - `prompt_includes`: Stores file includes
  - `chats`: Stores chat sessions
  - `chat_messages`: Stores conversation history
- Handles decimal types by converting to float for JSON serialization

### Include Processing
- Syntax: `<$path/to/file$>`
- Automatically fetches and replaces includes from database
- Caches content using content hashes

### Chat History
- Automatic session creation for new conversations
- Message persistence for both user and assistant
- Conversation continuity via chat_id
- Messages ordered by timestamp

### LLM Integration
- Uses OpenRouter API
- Supports streaming responses
- Configurable parameters per advisor (temperature, tokens, etc.)
- Includes full conversation context in each request

## Environment Variables

```
dbpoolrconnxn=postgresql://...
API_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your_key_here
DEBUG=true  # Optional: enables debug output
```

## Example Usage

```python
# Start new chat
curl -N -X POST http://localhost:8000/chat/jim_collins \
  -H "Content-Type: application/json" \
  -d '{"message": "What makes a great leader?"}'

# Continue existing chat (note the chat_id from X-Chat-ID header)
curl -N -X POST http://localhost:8000/chat/jim_collins \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you elaborate on Level 5 Leadership?",
    "chat_id": 123
  }'

# Override temperature for specific response
curl -N -X POST http://localhost:8000/chat/jim_collins \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What makes a great leader?",
    "temperature_override": 0.8
  }'

# Get advisor details
curl http://localhost:8000/advisors

# Get specific include content
curl http://localhost:8000/includes/me/aboutme.md
```

## Response Headers

- `X-Chat-ID`: Returned in chat responses, use this ID to continue the conversation 