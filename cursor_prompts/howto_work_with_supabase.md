# Supabase Integration Guide

## Database Setup

The HubGPT application uses Supabase as its database backend. The database is hosted at:
```
Host: aws-0-us-east-1.pooler.supabase.com
Database: postgres
```

### Environment Variables

Required environment variables in `.env`:
```bash
SUPABASE_URL=https://vbqcmspqteqpfbhffebu.supabase.co
SUPABASE_KEY=your_anon_key
dbpoolrconnxn=postgresql://postgres.vbqcmspqteqpfbhffebu:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

## Database Schema

### Advisors Table

The `advisors` table stores all AI advisor configurations with the following schema:

```sql
CREATE TABLE public.advisors (
    id bigint NOT NULL,
    name text NOT NULL,
    description text,
    model text NOT NULL,
    temperature numeric NOT NULL,
    max_tokens integer NOT NULL,
    top_p numeric NOT NULL,
    frequency_penalty numeric NOT NULL,
    presence_penalty numeric NOT NULL,
    stream boolean NOT NULL,
    system_message text NOT NULL,
    tools jsonb,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);
```

#### Constraints:
- `temperature`: Must be between 0 and 2 (typical values: 0.7-1.2)
- `top_p`: Must be between 0 and 1
- `frequency_penalty`: Must be between -2 and 2
- `presence_penalty`: Must be between -2 and 2

#### Common Temperature Values:
- 1.15: Most advisors (Elon_Musk, David_Deutsch, Mr_Promptmaker, etc.)
- 1.2: Some specialized advisors (Mr_Member, Shane_Parrish, Mr_Feedreader)
- 1.125: Agent advisors (Execution_Agent, Observation_Agent)
- 1.0: Base advisors (Jim_Collins, Naval_Ravikant)
- 0.7: Special cases (Mr_Linkedin)

### Prompt Includes System

The application uses a dedicated system to handle file includes in prompts (e.g., `<$path/to/file.txt$>`). This is managed through two tables:

#### prompt_includes Table
```sql
CREATE TABLE public.prompt_includes (
    id bigint NOT NULL,
    path text NOT NULL,
    content text NOT NULL,
    hash text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
```

- `path`: Original file path (e.g., "me/aboutme.md")
- `content`: The actual content of the included file
- `hash`: SHA-256 hash of content for change detection
- `created_at/updated_at`: Timestamps for tracking changes

#### chat_includes Table
```sql
CREATE TABLE public.chat_includes (
    id bigint NOT NULL,
    chat_id bigint NOT NULL,
    include_id bigint NOT NULL,
    sequence integer NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
```

- Links includes to specific chats
- Maintains order of includes via `sequence`
- Allows tracking which includes are used where

### Common Include Patterns

Advisors typically use includes for:
1. User context: `<$me/aboutme.md$>`
2. Custom instructions: `<$me/custom_instructions.txt$>`
3. Knowledge bases: `<$content/filename.json$>`

## Working with Advisors

### Python Client

The `tools/supabase_api.py` module provides a Python client for interacting with advisors:

```python
from tools.supabase_api import get_supabase_client

# Get client instance
client = get_supabase_client()

# Common operations
advisors = await client.get_advisors()  # Get all advisors
advisor = await client.get_advisor(1)    # Get specific advisor
results = await client.search_advisors("Elon")  # Search advisors
```

### Migrating Advisors

To migrate advisors from JSON files to Supabase:

1. Ensure your advisor JSON files are in the `advisors/` directory
2. Files should follow this structure:
```json
{
    "model": "model_name",
    "temperature": 1.15,  // Values between 0-2 are supported
    "max_tokens": 4096,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "stream": true,
    "messages": [
        {
            "role": "system",
            "content": "system prompt here"
        }
    ],
    "tools": ["tool1", "tool2"]
}
```

3. Use the migration tools:
```bash
# Test database connection
python tools/test_supabase.py

# Migrate a specific advisor
python tools/migrate_advisors.py Elon_Musk

# Migrate all advisors
python tools/migrate_advisors.py
```

### Temperature Updates

If you need to update temperature constraints or values:

```bash
# Update temperature constraint (0-2 range)
python tools/update_constraints.py

# Update advisor temperatures from JSON files
python tools/update_temperatures.py
```

### Troubleshooting

Common issues and solutions:

1. Permission Denied:
   - Ensure you're using the correct connection string
   - Check if you have the necessary permissions in Supabase

2. Value Constraints:
   - Temperature must be between 0 and 2
   - Top_p must be between 0 and 1
   - Frequency/Presence penalties must be between -2 and 2
   - Missing required fields will raise an error

3. Connection Issues:
   - Verify your environment variables
   - Ensure you're using the pooled connection string for better reliability

## Working with Includes

### Migrating Includes

Use the includes migration tools:

```bash
# Migrate includes for a specific advisor
python tools/migrate_includes.py Elon_Musk

# Default to Jim_Collins if no advisor specified
python tools/migrate_includes.py
```

The migration process:
1. Extracts include paths from system messages
2. Reads the content of each included file
3. Calculates a SHA-256 hash of the content
4. Stores or updates in `prompt_includes` table
5. Handles duplicates by comparing hashes

### Include Features

- **Change Detection**: Uses content hashing to detect and track changes
- **Deduplication**: Same files are stored only once
- **Path Preservation**: Original file paths are maintained
- **Automatic Updates**: Updates content if file changes detected

### Troubleshooting Includes

Common issues and solutions:

1. Missing Files:
   - Ensure all referenced files exist in the correct paths
   - Check file permissions

2. Hash Mismatches:
   - Usually indicates content has changed
   - Will automatically update in database

3. Include Syntax:
   - Must follow pattern: `<$path/to/file.ext$>`
   - Paths are relative to workspace root

## Development Tools

### Testing Connection
```bash
python tools/test_supabase.py
```

### Viewing Latest Advisor
```bash
python tools/test_supabase.py
```

### Database Constraints
To view all table constraints:
```sql
SELECT con.conname as constraint_name,
       pg_get_constraintdef(con.oid) as constraint_definition
FROM pg_constraint con
JOIN pg_namespace nsp ON nsp.oid = con.connamespace
WHERE nsp.nspname = 'public'
AND con.conrelid = 'advisors'::regclass;
```

## Edge Functions

Supabase Edge Functions are serverless functions that run on Deno at the edge (globally distributed). They're ideal for:
1. Processing data before/after database operations
2. Integrating with external services
3. Running scheduled tasks
4. Handling webhook events

### Use Cases in HubGPT

#### 1. Include Processing
```typescript
// process-includes.ts
export async function processIncludes(system_message: string) {
  const includes = extractIncludes(system_message);
  const processedIncludes = await Promise.all(
    includes.map(async (include) => {
      const hash = await calculateHash(include.content);
      return { path: include.path, content: include.content, hash };
    })
  );
  return processedIncludes;
}
```
- Pre-process includes before storing in database
- Handle file content validation
- Compute hashes at the edge

#### 2. Advisor Validation
```typescript
// validate-advisor.ts
export async function validateAdvisor(advisor: Advisor) {
  // Validate temperature ranges
  if (advisor.temperature < 0 || advisor.temperature > 2) {
    throw new Error('Temperature must be between 0 and 2');
  }
  
  // Validate tools exist
  if (advisor.tools) {
    const availableTools = await getAvailableTools();
    advisor.tools.forEach(tool => {
      if (!availableTools.includes(tool)) {
        throw new Error(`Tool ${tool} not found`);
      }
    });
  }
  
  return advisor;
}
```
- Validate advisor configurations
- Check tool availability
- Enforce constraints

#### 3. Chat History Management
```typescript
// manage-chat-history.ts
export async function processChatHistory(chatId: string) {
  const history = await getChatHistory(chatId);
  const processedHistory = await Promise.all(
    history.map(async (msg) => {
      // Process includes in messages
      if (msg.includes) {
        msg.includes = await processIncludes(msg.includes);
      }
      return msg;
    })
  );
  return processedHistory;
}
```
- Process chat histories
- Handle include resolution
- Manage chat storage

### Deploying Edge Functions

1. Create function:
```bash
supabase functions new process-includes
```

2. Deploy:
```bash
supabase functions deploy process-includes
```

3. Invoke from application:
```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
result = supabase.functions.invoke(
    'process-includes',
    invoke_options={'body': {'message': system_message}}
)
```

### Best Practices

1. **Error Handling**
```typescript
try {
  const result = await processFunction();
  return { success: true, data: result };
} catch (error) {
  return { 
    success: false, 
    error: error.message,
    details: process.env.ENVIRONMENT === 'development' ? error.stack : undefined
  };
}
```

2. **Environment Variables**
```bash
# .env
SUPABASE_FUNCTION_KEY=your_function_key
```

3. **Rate Limiting**
```typescript
import { RateLimit } from 'https://deno.land/x/rate_limit/mod.ts';

const limiter = new RateLimit({
  requests: 10,
  window: 60000, // 1 minute
});
```

### Monitoring and Debugging

1. View logs:
```bash
supabase functions logs process-includes
```

2. Test locally:
```bash
supabase functions serve process-includes
```

3. Monitor metrics in Supabase Dashboard:
- Execution time
- Error rates
- Memory usage 

## Chat History Migration

### Database Schema

The chat history is stored across three tables:

#### chats Table
```sql
CREATE TABLE public.chats (
    id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    advisor_id bigint NOT NULL REFERENCES advisors(id),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
```

#### chat_messages Table
```sql
CREATE TABLE public.chat_messages (
    id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    chat_id bigint NOT NULL REFERENCES chats(id),
    sequence integer NOT NULL,
    role text NOT NULL,
    content text,
    tool_name text,
    tool_call_id text,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
```

#### message_tool_calls Table
```sql
CREATE TABLE public.message_tool_calls (
    id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    message_id bigint NOT NULL REFERENCES chat_messages(id),
    tool_call_id text NOT NULL,
    tool_name text NOT NULL,
    arguments jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);
```

### Migrating Chat Histories

To migrate chat histories from JSON files to Supabase:

1. Ensure your chat history JSON files are in the `advisors/chats/` directory
2. Files should follow this structure:
```json
[
    {
        "role": "user",
        "content": "message content"
    },
    {
        "role": "assistant",
        "content": "response content",
        "tool_calls": [
            {
                "id": "call_id",
                "function": {
                    "name": "tool_name",
                    "arguments": "json_string"
                }
            }
        ]
    },
    {
        "role": "tool",
        "name": "tool_name",
        "tool_call_id": "call_id",
        "content": "tool response"
    }
]
```

3. Use the migration tools:
```bash
# Update database schema if needed
python tools/update_schema.py

# Migrate a specific advisor's chat history
python tools/migrate_chat_history.py Elon_Musk

# Default to Jim_Collins if no advisor specified
python tools/migrate_chat_history.py
```

### Working with Chat History

The Python client provides methods for chat history:

```python
from tools.supabase_api import get_supabase_client

# Get client instance
client = get_supabase_client()

# Get chat history for advisor
chats = await client.get_advisor_chats(advisor_id)

# Get messages for chat
messages = await client.get_chat_messages(chat_id)

# Get tool calls for message
tool_calls = await client.get_message_tool_calls(message_id)
``` 