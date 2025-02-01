from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
import logging
import os
import json
from datetime import datetime
from pathlib import Path
import asyncio
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationMetadata,
    ConversationHistory,
    NewConversation,
    Message,
    Conversation,
    ToolCall
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
from ..database import get_db
from .. import config

# Initialize router without prefix - it will be added in main.py
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
    config.CHATS_DIR.mkdir(parents=True, exist_ok=True)
    config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/advisor/{advisor_id}/history", response_model=List[ConversationMetadata])
async def get_conversation_history(advisor_id: str, db: Session = Depends(get_db)):
    """Get conversation history for an advisor"""
    try:
        # Query conversations for this advisor
        conversations = db.query(Conversation).filter(
            Conversation.advisor_id == advisor_id
        ).order_by(desc(Conversation.updated_at)).all()
        
        return [
            ConversationMetadata(
                id=conv.id,
                advisor_id=conv.advisor_id,
                message_count=conv.message_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            ) for conv in conversations
        ]
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/advisor/{advisor_id}/latest", response_model=ConversationHistory)
async def get_latest_conversation(advisor_id: str, db: Session = Depends(get_db)):
    """Get the latest conversation for an advisor"""
    try:
        # Get latest active conversation
        conversation = db.query(Conversation).filter(
            Conversation.advisor_id == advisor_id,
            Conversation.status == 'active'
        ).order_by(desc(Conversation.updated_at)).first()
        
        if not conversation:
            # Create new conversation if none exists
            conversation = Conversation(
                id=str(uuid4()),
                advisor_id=advisor_id,
                status='active',
                message_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(conversation)
            db.commit()
            
        # Get messages for conversation
        messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.sequence).all()
        
        # Convert to ChatMessage format
        chat_messages = []
        for msg in messages:
            tool_calls = None
            if msg.tool_calls:
                tool_calls = [
                    {
                        "id": tc.tool_call_id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function_name,
                            "arguments": tc.function_arguments
                        }
                    } for tc in msg.tool_calls
                ]
            
            chat_messages.append(ChatMessage(
                role=msg.role,
                content=msg.content or "",
                tool_calls=tool_calls
            ))
            
        return ConversationHistory(
            id=conversation.id,
            advisor_id=advisor_id,
            messages=chat_messages,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error getting latest conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/cancel")
async def cancel_stream(conversation_id: str):
    """Cancel an ongoing stream for a conversation"""
    try:
        response_handler = active_streams.get(conversation_id)
        if response_handler:
            response_handler.cancel()
            active_streams.pop(conversation_id)
            return {"status": "cancelled"}
        return {"status": "no_active_stream"}
    except Exception as e:
        logger.error(f"Error cancelling stream: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Track active streams
active_streams = {}

@router.post("/{conversation_id}/message")
async def add_message(
    conversation_id: str,
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Add a message to a conversation and get response"""
    try:
        # Get conversation
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        # Create and add user message
        user_message = Message(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=request.message,
            sequence=conversation.message_count + 1,
            created_at=datetime.utcnow()
        )
        db.add(user_message)
        
        # Update conversation
        conversation.message_count += 1
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        # Load advisor data
        try:
            advisor_data = load_advisor_data(conversation.advisor_id)
            logger.info(f"Loaded advisor data for {conversation.advisor_id}")
        except Exception as e:
            logger.error(f"Error loading advisor data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error loading advisor data: {str(e)}")
            
        # Get message history
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.sequence).all()
        
        # Convert to format expected by LLM
        message_history = []
        for msg in messages:
            message_dict = {"role": msg.role, "content": msg.content or ""}
            if msg.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.tool_call_id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function_name,
                            "arguments": tc.function_arguments
                        }
                    } for tc in msg.tool_calls
                ]
            message_history.append(message_dict)
            
        # Initialize LLM client and response handler
        client = get_llm_client(gateway=advisor_data.get('gateway', 'openrouter'))
        response_handler = ResponseHandler(client, messages=message_history)
        
        # Get tools from advisor config
        tool_names = advisor_data.get('tools', [])
        if tool_names and not tools_loaded:
            logger.error("Tools requested but not loaded")
            tool_names = []
            
        # Resolve tools
        tools = ToolManager.resolve_tools(tool_names) if tool_names else []
        
        # Build API parameters
        default_params = LLMParams.get_default()
        api_params = LLMParams.build_api_params(
            default_params=default_params,
            overrides=advisor_data,
            messages=advisor_data['messages'] + message_history,
            tools=tools
        )
        
        should_stream = api_params.get('stream', False)
        
        if should_stream:
            async def event_generator():
                try:
                    response = response_handler._make_streaming_request(api_params)
                    assistant_message = {"role": "assistant", "content": ""}
                    
                    # Create initial message in DB
                    db_message = Message(
                        id=str(uuid4()),
                        conversation_id=conversation_id,
                        role="assistant",
                        content="",
                        sequence=conversation.message_count + 1,
                        created_at=datetime.utcnow()
                    )
                    db.add(db_message)
                    conversation.message_count += 1
                    db.commit()
                    
                    accumulated_content = ""
                    first_chunk = True
                    last_db_update = datetime.utcnow()
                    
                    async for chunk in response_handler.handle_streamed_response(response):
                        # Handle both string chunks and OpenAI chunk objects
                        content = ""
                        if isinstance(chunk, str):
                            content = chunk
                        elif hasattr(chunk, 'choices') and chunk.choices:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, 'content'):
                                content = delta.content or ""
                        
                        # Capture message ID from first chunk
                        if first_chunk:
                            if hasattr(chunk, 'id'):
                                db_message.llm_message_id = chunk.id
                                db.commit()
                            first_chunk = False
                        
                        # If we have content, send it to frontend immediately
                        if content:
                            # Format as SSE event
                            event_data = {
                                "conversation_id": conversation_id,
                                "message": {
                                    "role": "assistant",
                                    "content": content
                                }
                            }
                            yield f"data: {json.dumps(event_data)}\n\n"
                            
                            # Accumulate content and update DB periodically
                            accumulated_content += content
                            now = datetime.utcnow()
                            if (now - last_db_update).total_seconds() >= 1.0:  # Update DB every second
                                db_message.content = accumulated_content
                                db.commit()
                                last_db_update = now
                    
                    # Final DB update with complete content
                    if accumulated_content:
                        db_message.content = accumulated_content
                        db.commit()
                        
                    # Update final message state
                    if hasattr(response, 'choices') and response.choices:
                        last_choice = response.choices[-1]
                        if hasattr(last_choice, 'finish_reason'):
                            db_message.finish_reason = last_choice.finish_reason
                            db.commit()
                            
                except Exception as e:
                    logger.error(f"Error in stream: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    
            return StreamingResponse(event_generator(), media_type="text/event-stream")
            
        else:
            # Non-streaming response
            response = response_handler._make_request(api_params)
            assistant_message = response.choices[0].message
            
            # Create message in DB
            db_message = Message(
                id=str(uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message.content,
                sequence=conversation.message_count + 1,
                created_at=datetime.utcnow(),
                llm_message_id=response.id,
                finish_reason=response.choices[0].finish_reason,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
            
            # Handle tool calls if present
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    db_tool_call = ToolCall(
                        id=str(uuid4()),
                        message_id=db_message.id,
                        tool_call_id=tool_call.id,
                        type=tool_call.type,
                        function_name=tool_call.function.name,
                        function_arguments=tool_call.function.arguments,
                        created_at=datetime.utcnow()
                    )
                    db.add(db_tool_call)
            
            db.add(db_message)
            conversation.message_count += 1
            db.commit()
            
            return ChatResponse(
                conversation_id=conversation_id,
                message=ChatMessage(
                    role="assistant",
                    content=assistant_message.content,
                    tool_calls=[{
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in assistant_message.tool_calls] if hasattr(assistant_message, 'tool_calls') else None
                )
            )
            
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """Get a specific conversation by ID"""
    try:
        ensure_chat_dirs()
        
        # If ID has hex suffix, it's an archived chat
        if '_' in conversation_id and len(conversation_id.split('_')[-1]) == 6:
            chat_history_path = config.ARCHIVE_DIR / f"{conversation_id}.json"
        else:
            chat_history_path = config.CHATS_DIR / f"{conversation_id}.json"
            
        logger.info(f"Loading chat from: {chat_history_path}")
        
        if not chat_history_path.exists():
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        chat_history = load_chat_history(str(chat_history_path))
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

@router.post("/advisor/{advisor_id}/new", response_model=ConversationHistory)
async def new_conversation(advisor_id: str, db: Session = Depends(get_db)):
    """Start a new conversation with an advisor"""
    try:
        # Create new conversation in database
        conversation = Conversation(
            id=str(uuid4()),
            advisor_id=advisor_id,
            status='active',
            message_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        
        # Return new chat info
        return ConversationHistory(
            id=conversation.id,  # Use the UUID here
            advisor_id=advisor_id,
            messages=[],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating new conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        # First check if this is a current chat
        current_path = config.CHATS_DIR / f"{conversation_id}.json"
        archive_path = config.ARCHIVE_DIR / f"{conversation_id}.json"
        
        if current_path.exists():
            current_path.unlink()
            return {"status": "deleted", "path": str(current_path)}
        elif archive_path.exists():
            archive_path.unlink()
            return {"status": "deleted", "path": str(archive_path)}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 