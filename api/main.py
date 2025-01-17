from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
from typing import List, Optional, Dict
from pydantic import BaseModel
from openai import OpenAI
import re
import json
from datetime import datetime
import asyncio
import time
import psycopg2.pool
from functools import lru_cache
import httpx
from supabase import create_client, Client

# Load environment variables
load_dotenv()

app = FastAPI(title="HubGPT API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add root redirect
@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: Optional[datetime] = None

class ChatSession(BaseModel):
    id: int
    advisor_id: int
    created_at: datetime
    messages: List[ChatMessage]

class ChatRequest(BaseModel):
    message: str
    temperature_override: Optional[float] = None
    system_message_override: Optional[str] = None
    chat_id: Optional[int] = None  # For continuing existing chats

# Create a connection pool
pool = None

def get_pool():
    global pool
    if pool is None:
        db_url = urlparse(os.getenv('dbpoolrconnxn'))
        pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            dbname=db_url.path[1:],
            user=db_url.username,
            password=db_url.password,
            host=db_url.hostname,
            port=db_url.port
        )
    return pool

class Advisor(BaseModel):
    id: int
    name: str
    description: str | None = None
    model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    stream: bool
    system_message: str
    tools: List[str] | None = None

class Include(BaseModel):
    path: str
    content: str
    hash: str | None = None

# Add Supabase client setup
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')  # Use SUPABASE_KEY instead of SUPABASE_ANON_KEY for admin access
)

@lru_cache(maxsize=100)
async def get_resolved_advisor(advisor_name: str) -> Dict:
    """Get advisor and resolve includes directly from Supabase Storage."""
    try:
        # Get advisor from database
        response = supabase.table('advisors').select('*').eq('name', advisor_name).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Advisor {advisor_name} not found")
        
        advisor = response.data[0]
        
        # Find all includes in the system message
        pattern = r'<\$([^$]+)\$>'
        includes = re.findall(pattern, advisor['system_message'])
        
        # Fetch all includes in parallel
        async def fetch_include(path: str):
            try:
                # Extract bucket name from path (everything before first /)
                bucket = path.split('/')[0]
                # Get file path within bucket (everything after first /)
                file_path = '/'.join(path.split('/')[1:])
                
                # Fix common path issues
                if file_path == 'aboutme.md':
                    file_path = 'about_me.md'  # Match actual filename in storage
                    
                print(f"Fetching from bucket: {bucket}, path: {file_path}")
                
                response = supabase.storage.from_(bucket).download(file_path)
                return path, response.decode()
            except Exception as e:
                print(f"Error fetching include {path}: {str(e)}")
                return path, f"[Include {path} not found]"
        
        # Create tasks for parallel execution
        tasks = [fetch_include(path) for path in includes]
        include_contents = await asyncio.gather(*tasks)
        
        # Replace all includes in the system message
        resolved_message = advisor['system_message']
        for path, content in include_contents:
            resolved_message = resolved_message.replace(f'<${path}$>', content)
        
        # Return resolved advisor
        advisor['system_message'] = resolved_message
        return advisor
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving advisor: {str(e)}")

@app.get("/advisors", response_model=List[Advisor])
async def get_advisors():
    try:
        # Get database connection
        db_url = urlparse(os.getenv('dbpoolrconnxn'))
        conn = psycopg2.connect(
            dbname=db_url.path[1:],
            user=db_url.username,
            password=db_url.password,
            host=db_url.hostname,
            port=db_url.port
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all advisors
        cur.execute("""
            SELECT * FROM advisors 
            ORDER BY name ASC
        """)
        
        advisors = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return advisors
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/includes/{path:path}", response_model=Include)
async def get_include(path: str):
    try:
        # Get database connection
        db_url = urlparse(os.getenv('dbpoolrconnxn'))
        conn = psycopg2.connect(
            dbname=db_url.path[1:],
            user=db_url.username,
            password=db_url.password,
            host=db_url.hostname,
            port=db_url.port
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # URL decode the path
        decoded_path = unquote(path)
        print(f"Looking for include: {decoded_path}")  # Debug log
        
        # Get include content
        cur.execute("""
            SELECT path, content, hash 
            FROM prompt_includes 
            WHERE path = %s
        """, (decoded_path,))
        
        include = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not include:
            print(f"Include not found: {decoded_path}")  # Debug log
            raise HTTPException(status_code=404, detail=f"Include {decoded_path} not found")
        
        print(f"Found include: {decoded_path}")  # Debug log
        return include
        
    except Exception as e:
        print(f"Error getting include: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))

async def process_includes(content: str, conn) -> str:
    """Process include tags in content."""
    pattern = r'<\$([^$]+)\$>'
    includes_found = re.findall(pattern, content)
    
    if includes_found:
        # Batch fetch all needed includes in one query
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT path, content FROM prompt_includes WHERE path = ANY(%s)", (includes_found,))
        includes = {inc['path']: inc['content'] for inc in cur.fetchall()}
        cur.close()
        
        # Process all includes
        for include in includes_found:
            include_content = includes.get(include, f"[Include {include} not found]")
            content = content.replace(f'<${include}$>', include_content)
    
    return content

@app.get("/test/jim_collins")
async def test_jim_collins():
    """Test endpoint that gets Jim Collins advisor and streams LLM response."""
    try:
        start_time = time.time()
        conn = None
        
        print(f"\nStarting Jim Collins test...")
        
        # Get resolved advisor from edge function
        advisor_start = time.time()
        print(f"Fetching advisor with resolved includes...")
        advisor = await get_resolved_advisor('Jim_Collins')
        print(f"Advisor fetch time: {time.time() - advisor_start:.2f}s")
        
        if not advisor:
            raise HTTPException(status_code=404, detail="Jim Collins advisor not found")
            
        # Convert Decimal values to float
        for key in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']:
            if advisor[key] is not None:
                advisor[key] = float(advisor[key])
        
        # Get database connection from pool
        db_start = time.time()
        print(f"Getting connection from pool...")
        conn = get_pool().getconn()
        print(f"DB connection time: {time.time() - db_start:.2f}s")
        
        # Create chat session
        chat_start = time.time()
        chat_id = await create_chat(advisor['id'], conn)
        print(f"Created chat session: {chat_id}")
        print(f"Chat session time: {time.time() - chat_start:.2f}s")
        
        # Initialize OpenAI client with OpenRouter
        client_start = time.time()
        print(f"Initializing OpenAI client...")
        client = OpenAI(
            base_url=os.getenv('API_BASE_URL'),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={
                'HTTP-Referer': 'https://hubgpt.ai',
                'X-Title': 'HubGPT',
            }
        )
        print(f"Client init time: {time.time() - client_start:.2f}s")
        
        # Prepare messages using system message from resolved advisor
        messages = [
            {"role": "system", "content": advisor['system_message']},
            {
                "role": "user", 
                "content": "What kind of leaders can take companies from good to great? What are their key characteristics and behaviors?"
            }
        ]
        
        # Make LLM call with streaming
        print(f"Making LLM API call...")
        print(f"Total prep time before LLM call: {time.time() - start_time:.2f}s")

        response = client.chat.completions.create(
            model=advisor['model'],
            messages=messages,
            temperature=advisor['temperature'],
            max_tokens=advisor['max_tokens'] if advisor['max_tokens'] else 1000,
            top_p=advisor['top_p'] if advisor['top_p'] else 1,
            frequency_penalty=advisor['frequency_penalty'] if advisor['frequency_penalty'] else 0,
            presence_penalty=advisor['presence_penalty'] if advisor['presence_penalty'] else 0,
            stream=True
        )
        
        async def stream_response():
            try:
                stream_start = time.time()
                first_chunk = True
                chunk_count = 0
                
                # First yield debug info if DEBUG mode is enabled
                if os.getenv('DEBUG') == 'true':
                    debug_info = {
                        "advisor": advisor['name'],
                        "model": advisor['model'],
                        "temperature": advisor['temperature'],
                        "system_message_length": len(advisor['system_message']),
                        "system_message_preview": advisor['system_message'][:200] + "...",
                        "chat_id": chat_id,
                        "message_count": len(messages) - 1,  # Excluding system message
                        "streaming": True,
                        "prep_time": time.time() - start_time
                    }
                    yield f"data: {json.dumps(debug_info)}\n\n"
                    await asyncio.sleep(0)  # Force flush
                
                # Buffer for collecting the complete response
                complete_response = []
                
                # Then stream the LLM response
                print(f"Starting to stream response...")  # Debug log
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        if first_chunk:
                            print(f"Time to first token: {time.time() - stream_start:.2f}s")
                            first_chunk = False
                        
                        content = chunk.choices[0].delta.content
                        chunk_count += 1
                        complete_response.append(content)
                        yield f"data: {content}\n\n"
                        await asyncio.sleep(0)  # Force flush after each chunk
                
                # Save complete response to chat history
                print(f"Streaming complete in {time.time() - stream_start:.2f}s")
                print(f"Total chunks: {chunk_count}")
                print(f"Average chunk time: {(time.time() - stream_start) / chunk_count:.3f}s")
                
                save_start = time.time()
                print(f"Saving assistant response...")  # Debug log
                await save_message(chat_id, "assistant", "".join(complete_response), conn)
                print(f"Save time: {time.time() - save_start:.2f}s")
                
            except Exception as e:
                print(f"Error in stream_response: {str(e)}")  # Debug log
                yield f"data: Error: {str(e)}\n\n"
                await asyncio.sleep(0)  # Force flush error message
            finally:
                if cur:
                    cur.close()
                if conn:
                    get_pool().putconn(conn)
                print(f"Total request time: {time.time() - start_time:.2f}s")  # Debug log
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "X-Chat-ID": str(chat_id),
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "Content-Encoding": "identity",
                "Transfer-Encoding": "chunked"
            }
        )
        
    except Exception as e:
        print(f"Error in test_jim_collins: {str(e)}")  # Debug log
        import traceback
        print(f"Traceback: {traceback.format_exc()}")  # Debug log
        if cur:
            cur.close()
        if conn:
            get_pool().putconn(conn)
        raise HTTPException(status_code=500, detail=str(e))

async def get_chat_history(chat_id: int, conn) -> List[Dict]:
    """Get chat history from database."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT role, content, created_at
        FROM chat_messages 
        WHERE chat_id = %s 
        ORDER BY created_at ASC
    """, (chat_id,))
    messages = cur.fetchall()
    cur.close()
    return messages

async def create_chat(advisor_id: int, conn) -> int:
    """Create a new chat session."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        INSERT INTO chats (advisor_id) 
        VALUES (%s) 
        RETURNING id
    """, (advisor_id,))
    chat_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    return chat_id

async def save_message(chat_id: int, role: str, content: str, conn):
    """Save a message to chat history."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get the next sequence number for this chat
    cur.execute("""
        SELECT COALESCE(MAX(sequence), 0) + 1 as next_sequence
        FROM chat_messages 
        WHERE chat_id = %s
    """, (chat_id,))
    next_sequence = cur.fetchone()['next_sequence']
    
    # Insert message with sequence
    cur.execute("""
        INSERT INTO chat_messages (chat_id, sequence, role, content) 
        VALUES (%s, %s, %s, %s)
    """, (chat_id, next_sequence, role, content))
    
    conn.commit()
    cur.close()

@app.post("/chat/{advisor_name}")
async def chat_with_advisor(advisor_name: str, request: ChatRequest):
    """Generic chat endpoint that handles includes and streams responses."""
    conn = None
    cur = None  # Define cur at the start
    start_time = time.time()
    try:
        print(f"\nStarting chat with advisor: {advisor_name}")
        
        # Get resolved advisor from edge function
        advisor_start = time.time()
        print(f"Fetching advisor with resolved includes...")
        advisor = await get_resolved_advisor(advisor_name)
        print(f"Advisor fetch time: {time.time() - advisor_start:.2f}s")
        
        if not advisor:
            raise HTTPException(status_code=404, detail=f"Advisor {advisor_name} not found")
        
        print(f"Found advisor: {advisor['name']}")
        
        # Convert Decimal values to float
        for key in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']:
            if advisor[key] is not None:
                advisor[key] = float(advisor[key])
        
        # Get database connection from pool
        db_start = time.time()
        print(f"Getting connection from pool...")
        conn = get_pool().getconn()
        print(f"DB connection time: {time.time() - db_start:.2f}s")
        
        # Get or create chat session
        chat_start = time.time()
        chat_id = request.chat_id
        if not chat_id:
            print(f"Creating new chat session...")
            chat_id = await create_chat(advisor['id'], conn)
            print(f"Created chat session: {chat_id}")
        else:
            print(f"Using existing chat session: {chat_id}")
        print(f"Chat session time: {time.time() - chat_start:.2f}s")
        
        # Use system message (already resolved from edge function)
        system_message = request.system_message_override or advisor['system_message']
        
        # Initialize OpenAI client with OpenRouter
        client_start = time.time()
        print(f"Initializing OpenAI client...")  # Debug log
        client = OpenAI(
            base_url=os.getenv('API_BASE_URL'),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={
                'HTTP-Referer': 'https://hubgpt.ai',  # Required for OpenRouter
                'X-Title': 'HubGPT',  # Optional, but good practice
            }
        )
        print(f"Client init time: {time.time() - client_start:.2f}s")
        
        # Prepare messages
        messages = [{"role": "system", "content": system_message}]
        
        # Add chat history if this is a continuation
        history_start = time.time()
        if request.chat_id:
            print(f"Fetching chat history...")  # Debug log
            history = await get_chat_history(request.chat_id, conn)
            print(f"Found {len(history)} previous messages")  # Debug log
            messages.extend([{
                "role": msg["role"],
                "content": msg["content"]
            } for msg in history])
        print(f"History fetch time: {time.time() - history_start:.2f}s")
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Save user message to history
        save_start = time.time()
        print(f"Saving user message...")  # Debug log
        await save_message(chat_id, "user", request.message, conn)
        print(f"Message save time: {time.time() - save_start:.2f}s")
        
        # Make LLM call with streaming
        print(f"Making LLM API call...")  # Debug log
        print(f"Total prep time before LLM call: {time.time() - start_time:.2f}s")
        
        response = client.chat.completions.create(
            model=advisor['model'],
            messages=messages,
            temperature=request.temperature_override or advisor['temperature'],
            max_tokens=advisor['max_tokens'] if advisor['max_tokens'] else 1000,
            top_p=advisor['top_p'] if advisor['top_p'] else 1,
            frequency_penalty=advisor['frequency_penalty'] if advisor['frequency_penalty'] else 0,
            presence_penalty=advisor['presence_penalty'] if advisor['presence_penalty'] else 0,
            stream=True  # Force streaming
        )
        
        async def stream_response():
            try:
                stream_start = time.time()
                first_chunk = True
                chunk_count = 0
                
                # First yield debug info if DEBUG mode is enabled
                if os.getenv('DEBUG') == 'true':
                    debug_info = {
                        "advisor": advisor['name'],
                        "model": advisor['model'],
                        "temperature": request.temperature_override or advisor['temperature'],
                        "system_message_length": len(system_message),
                        "system_message_preview": system_message[:200] + "...",
                        "chat_id": chat_id,
                        "message_count": len(messages) - 1,  # Excluding system message
                        "streaming": True,
                        "prep_time": time.time() - start_time
                    }
                    yield f"data: {json.dumps(debug_info)}\n\n"
                    await asyncio.sleep(0)  # Force flush
                
                # Buffer for collecting the complete response
                complete_response = []
                
                # Then stream the LLM response
                print(f"Starting to stream response...")  # Debug log
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        if first_chunk:
                            print(f"Time to first token: {time.time() - stream_start:.2f}s")
                            first_chunk = False
                        
                        content = chunk.choices[0].delta.content
                        chunk_count += 1
                        complete_response.append(content)
                        yield f"data: {content}\n\n"
                        await asyncio.sleep(0)  # Force flush after each chunk
                
                # Save complete response to chat history
                print(f"Streaming complete in {time.time() - stream_start:.2f}s")
                print(f"Total chunks: {chunk_count}")
                print(f"Average chunk time: {(time.time() - stream_start) / chunk_count:.3f}s")
                
                save_start = time.time()
                print(f"Saving assistant response...")  # Debug log
                await save_message(chat_id, "assistant", "".join(complete_response), conn)
                print(f"Save time: {time.time() - save_start:.2f}s")
                
            except Exception as e:
                print(f"Error in stream_response: {str(e)}")  # Debug log
                yield f"data: Error: {str(e)}\n\n"
                await asyncio.sleep(0)  # Force flush error message
            finally:
                if cur:
                    cur.close()
                if conn:
                    get_pool().putconn(conn)
                print(f"Total request time: {time.time() - start_time:.2f}s")  # Debug log
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "X-Chat-ID": str(chat_id),
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "Content-Encoding": "identity",
                "Transfer-Encoding": "chunked"
            }
        )
        
    except Exception as e:
        print(f"Error in chat_with_advisor: {str(e)}")  # Debug log
        import traceback
        print(f"Traceback: {traceback.format_exc()}")  # Debug log
        if cur:
            cur.close()
        if conn:
            get_pool().putconn(conn)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 