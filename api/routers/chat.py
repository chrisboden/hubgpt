from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
import logging
import os
import json
from datetime import datetime
from pathlib import Path
import asyncio

from ..models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationMetadata,
    ConversationHistory,
    NewConversation
)
from ..api_utils.chat_utils import (
    load_chat_history,
    save_chat_history,
    archive_chat_history,
    clear_chat_history
)
from ..api_utils.llm_utils import (
    LLMParams,
    ToolManager,
    ResponseHandler,
    ChatHistoryManager
)
from ..api_utils.prompt_utils import load_prompt, load_advisor_data
from ..api_utils.tool_utils import load_tools, execute_tool
from ..api_utils.client import get_llm_client

router = APIRouter()
logger = logging.getLogger(__name__)

# Load tools during router initialization
tools_loaded = False
try:
    load_tools("tools")
    tools_loaded = True
    logger.info("Tools loaded successfully")
except Exception as e:
    logger.error(f"Error loading tools: {e}")

def ensure_chat_dirs():
    """Ensure chat directories exist"""
    Path("advisors/chats").mkdir(parents=True, exist_ok=True)
    Path("advisors/archive").mkdir(parents=True, exist_ok=True)

@router.get("/chat/advisor/{advisor_id}/history", response_model=List[ConversationMetadata])
async def get_conversation_history(advisor_id: str):
    """Get conversation history for an advisor"""
    try:
        ensure_chat_dirs()
        history = []
        
        # Check current chat
        current_path = f"advisors/chats/{advisor_id}.json"
        if os.path.exists(current_path):
            messages = load_chat_history(current_path)
            if messages:
                history.append(ConversationMetadata(
                    id=advisor_id,
                    advisor_id=advisor_id,
                    message_count=len(messages),
                    created_at=datetime.fromtimestamp(os.path.getctime(current_path)),
                    updated_at=datetime.fromtimestamp(os.path.getmtime(current_path))
                ))
        
        # Check archived chats
        archive_dir = Path("advisors/archive")
        if archive_dir.exists():
            for file in archive_dir.glob(f"{advisor_id}_*.json"):
                messages = load_chat_history(str(file))
                if messages:
                    chat_id = file.stem  # Get filename without extension
                    history.append(ConversationMetadata(
                        id=chat_id,
                        advisor_id=advisor_id,
                        message_count=len(messages),
                        created_at=datetime.fromtimestamp(os.path.getctime(file)),
                        updated_at=datetime.fromtimestamp(os.path.getmtime(file))
                    ))
        
        # Sort by updated_at descending
        history.sort(key=lambda x: x.updated_at, reverse=True)
        return history
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/advisor/{advisor_id}/latest", response_model=ConversationHistory)
async def get_latest_conversation(advisor_id: str):
    """Get the latest conversation for an advisor"""
    try:
        ensure_chat_dirs()
        
        # Try to load from current chats
        chat_history_path = f"advisors/chats/{advisor_id}.json"
        chat_history = load_chat_history(chat_history_path)
        
        if chat_history:
            # Ensure chat_history is a list of messages
            messages = [
                ChatMessage(**msg) if isinstance(msg, dict) else msg 
                for msg in (chat_history if isinstance(chat_history, list) else [])
            ]
            
            return ConversationHistory(
                id=advisor_id,
                advisor_id=advisor_id,
                messages=messages,
                created_at=datetime.fromtimestamp(os.path.getctime(chat_history_path)),
                updated_at=datetime.fromtimestamp(os.path.getmtime(chat_history_path))
            )
            
        # Create new conversation if none exists
        new_chat = ConversationHistory(
            id=advisor_id,
            advisor_id=advisor_id,
            messages=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        save_chat_history([], chat_history_path)
        return new_chat
        
    except Exception as e:
        logger.error(f"Error getting latest conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/{conversation_id}/message")
async def add_message(
    conversation_id: str,
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """Add a message to a conversation and get response (streaming or non-streaming)"""
    try:
        # First check if this is a current chat
        current_path = f"advisors/chats/{conversation_id}.json"
        if os.path.exists(current_path):
            chat_history_path = current_path
            advisor_id = conversation_id
        # Then check if it's an archived chat
        elif '_' in conversation_id and len(conversation_id.split('_')[-1]) == 6:
            chat_history_path = f"advisors/archive/{conversation_id}.json"
            advisor_id = '_'.join(conversation_id.split('_')[:-1])
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        logger.info(f"Adding message to chat: {chat_history_path}")
            
        chat_history = load_chat_history(chat_history_path)
        messages = chat_history if isinstance(chat_history, list) else []
            
        # Create and add user message (only role and content)
        user_message = {
            "role": "user",
            "content": request.message
        }
        messages.append(user_message)
        
        # Save updated history with user message
        save_chat_history(messages, chat_history_path)
        
        # Load advisor data and build API params
        try:
            advisor_data = load_advisor_data(advisor_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Advisor {advisor_id} not found")
            
        # Initialize LLM client and response handler
        client = get_llm_client()
        handler = ResponseHandler(client)
        
        # Get tools from advisor config and resolve them
        tool_names = advisor_data.get('tools', [])
        if tool_names and not tools_loaded:
            logger.error("Tools requested but not loaded. Attempting to load tools.")
            try:
                load_tools("tools")
            except Exception as e:
                logger.error(f"Failed to load tools: {e}")
                tool_names = []  # Clear tool names if loading fails
        
        # Resolve tools to get their full metadata
        tools = ToolManager.resolve_tools(tool_names) if tool_names else []
        logger.info(f"Resolved tools: {json.dumps(tools, indent=2)}")
        
        # Build API parameters using LLMParams
        default_params = LLMParams.get_default()
        api_params = LLMParams.build_api_params(
            default_params=default_params,
            overrides=advisor_data,
            messages=advisor_data['messages'] + messages,  # Combine system messages with chat history
            tools=tools  # Pass resolved tools with metadata
        )

        # Check if streaming is requested (from request or advisor config)
        should_stream = api_params.get('stream', False)
        logger.info(f"Stream parameter from config: {should_stream}")
        
        if should_stream:
            async def event_generator():
                try:
                    # Get streaming response using ResponseHandler
                    stream = handler._make_streaming_request(api_params)
                    
                    # Process stream using existing handler
                    async for content in handler.handle_streamed_response(stream):
                        # Format as SSE event with proper data prefix
                        event_data = {
                            "conversation_id": conversation_id,
                            "message": {
                                "role": "assistant",
                                "content": content
                            }
                        }
                        # Send chunk and flush immediately
                        chunk = f"data: {json.dumps(event_data)}\n\n"
                        yield chunk
                        await asyncio.sleep(0)  # Allow the event loop to send the chunk
                    
                    # Save final response to chat history
                    messages.append({
                        "role": "assistant",
                        "content": handler.full_response
                    })
                    save_chat_history(messages, chat_history_path)
                    
                    # Send done event and flush
                    yield "event: done\ndata: {}\n\n"
                    await asyncio.sleep(0)
                    
                except Exception as e:
                    logger.error(f"Error in stream processing: {str(e)}", exc_info=True)
                    error_data = {
                        "conversation_id": conversation_id,
                        "message": {
                            "role": "assistant",
                            "content": f"Error: {str(e)}"
                        }
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Handle non-streaming response
            response, error = handler._make_llm_request(api_params)
            if error:
                raise HTTPException(status_code=500, detail=error)
            
            # Get content from response
            content = response.choices[0].message.content
            
            # Add assistant's response to messages and save
            messages.append({
                "role": "assistant",
                "content": content
            })
            save_chat_history(messages, chat_history_path)
            
            # Return regular JSON response
            return ChatResponse(
                conversation_id=conversation_id,
                message={
                    "role": "assistant",
                    "content": content
                }
            )
            
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """Get a specific conversation by ID"""
    try:
        ensure_chat_dirs()
        
        # If ID has hex suffix, it's an archived chat
        if '_' in conversation_id and len(conversation_id.split('_')[-1]) == 6:
            chat_history_path = f"advisors/archive/{conversation_id}.json"
        else:
            chat_history_path = f"advisors/chats/{conversation_id}.json"
            
        logger.info(f"Loading chat from: {chat_history_path}")
        
        if not os.path.exists(chat_history_path):
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        chat_history = load_chat_history(chat_history_path)
        if not chat_history:
            raise HTTPException(status_code=404, detail="Conversation is empty")
            
        # Extract advisor_id from conversation_id (remove hex suffix if present)
        advisor_id = conversation_id.split('_')[0] if '_' in conversation_id else conversation_id
        
        # Ensure chat_history is a list of messages
        messages = [
            ChatMessage(**msg) if isinstance(msg, dict) else msg 
            for msg in (chat_history if isinstance(chat_history, list) else [])
        ]
            
        return ConversationHistory(
            id=conversation_id,
            advisor_id=advisor_id,
            messages=messages,
            created_at=datetime.fromtimestamp(os.path.getctime(chat_history_path)),
            updated_at=datetime.fromtimestamp(os.path.getmtime(chat_history_path))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/advisor/{advisor_id}/new")
async def create_new_chat(advisor_id: str):
    """Create a new chat for an advisor"""
    try:
        ensure_chat_dirs()
        
        # Generate a unique ID for the new chat
        timestamp = datetime.now().strftime("%H%M%S")
        new_chat_id = f"{advisor_id}_{timestamp}"
        
        # Archive current chat if it exists
        current_path = f"advisors/chats/{advisor_id}.json"
        if os.path.exists(current_path):
            # Archive with proper directory paths
            archive_chat_history(
                chat_history_path=current_path,
                advisors_dir="advisors",
                advisor_filename=f"{advisor_id}.json"
            )
        
        # Create new empty chat
        save_chat_history([], current_path)
        
        # Return new chat info
        return ConversationHistory(
            id=advisor_id,
            advisor_id=advisor_id,
            messages=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error creating new chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 