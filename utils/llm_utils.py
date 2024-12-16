# utils/llm_utils.py

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import streamlit as st
from openai.types.chat import ChatCompletion
from utils.tool_utils import execute_tool, TOOL_METADATA_REGISTRY
from utils.chat_utils import save_chat_history

# Configure logging
LOGGING_ENABLED = True

def get_default_llm_params() -> Dict[str, Any]:
    """Default parameters for LLM API calls"""
    return {
        'model': 'gpt-4o-mini',
        'temperature': 1.0,
        'max_tokens': 8092,
        'top_p': 1,
        'frequency_penalty': 0,
        'presence_penalty': 0,
        'stream': True
    }

def prepare_api_params(messages: List[Dict[str, Any]], tools: List[str], tool_choice: str, **overrides) -> Dict[str, Any]:
    """Prepare API parameters for LLM call"""
    api_params = {**get_default_llm_params()}
    
    # Add overrides
    for key, value in overrides.items():
        if key not in ['spinner_placeholder', 'status_placeholder']:
            api_params[key] = value
    
    # Add messages and tools
    api_params['messages'] = messages
    if tools:
        api_params['tools'] = resolve_tools(tools)
        api_params['tool_choice'] = tool_choice
    
    if LOGGING_ENABLED:
        logging.info(f"Prepared API parameters: {api_params}")
    
    return api_params

def process_tool_call(
    delta: Any, 
    accumulated_args: str
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]], str]:
    """Process a tool call from the LLM response"""
    tool_name = None
    tool_id = None
    function_data = None
    
    if hasattr(delta, 'tool_calls') and delta.tool_calls:
        tool_call = delta.tool_calls[0]
        
        if hasattr(tool_call.function, 'name') and tool_call.function.name:
            tool_name = tool_call.function.name
            if LOGGING_ENABLED:
                logging.info(f"Tool name detected: {tool_name}")
        
        if hasattr(tool_call, 'id'):
            tool_id = tool_call.id
        
        if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
            accumulated_args += tool_call.function.arguments
            try:
                function_data = json.loads(accumulated_args)
                if LOGGING_ENABLED:
                    logging.info(f"Complete tool call data: {function_data}")
            except json.JSONDecodeError:
                if LOGGING_ENABLED:
                    logging.debug(f"Partial arguments received: {accumulated_args}")
    
    return tool_name, tool_id, function_data, accumulated_args

def handle_tool_execution(
    tool_name: str,
    function_data: Dict[str, Any],
    client: Any,
    chat_history: List[Dict[str, Any]],
    chat_history_path: str,
    response_placeholder: Any,
    status_placeholder: Any
) -> None:
    """Handle tool execution and response processing"""
    if LOGGING_ENABLED:
        logging.info(f"Executing tool '{tool_name}' with arguments: {function_data}")
    
    status_placeholder.markdown(f"*🔧 Executing tool: {tool_name}*")
    
    tool_response_data = execute_tool(
        tool_name, 
        function_data,
        llm_client=client
    )
    
    if LOGGING_ENABLED:
        logging.info(f"Tool response received: {tool_response_data}")
    
    if tool_response_data:
        if tool_response_data.get('direct_stream', False):
            stream = tool_response_data.get('result', '')
            status_placeholder.empty()
            
            follow_on = tool_response_data.get('follow_on_instructions')
            
            process_direct_stream(
                stream,
                chat_history,
                tool_name,
                response_placeholder,
                chat_history_path,
                follow_on
            )
            
            if follow_on:
                if LOGGING_ENABLED:
                    logging.info("Triggering rerun for follow-on instructions")
                st.rerun()

def resolve_tools(tools: List[str]) -> List[Dict[str, Any]]:
    """Resolve tool names to their metadata"""
    resolved_tools = []
    for tool_name in tools:
        metadata = TOOL_METADATA_REGISTRY.get(tool_name)
        if metadata:
            resolved_tools.append(metadata)
        else:
            logging.warning(f"Tool '{tool_name}' metadata not found. Skipping tool.")
    return resolved_tools

def handle_tool_call(delta: Any, tool_call_args: str) -> Optional[Dict[str, Any]]:
    """Handle tool calls from LLM response"""
    if not hasattr(delta, 'tool_calls') or not delta.tool_calls:
        return None
    
    tool_call = delta.tool_calls[0]
    
    if hasattr(tool_call, 'id') and tool_call.id:
        st.session_state.last_tool_call_id = tool_call.id
    
    if hasattr(tool_call.function, 'name') and tool_call.function.name:
        st.session_state.last_tool_name = tool_call.function.name
    
    if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
        try:
            # Try to parse the complete arguments
            return json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            # If parsing fails, accumulate partial arguments
            return None
    
    return None

def process_direct_stream(
    stream: Any,
    chat_history: List[Dict[str, Any]],
    tool_name: str,
    response_placeholder: Any,
    chat_history_path: str,
    follow_on_instructions: Optional[Union[str, List[str]]] = None
) -> str:
    """Process direct stream response from tool and handle follow-on instructions"""
    full_response = ""
    for chunk in stream:
        if not chunk.choices:
            continue
        
        delta = chunk.choices[0].delta
        chunk_text = delta.content or ""
        full_response += chunk_text
        response_placeholder.markdown(full_response)
    
    if full_response.strip():
        chat_history.append({
            "role": "assistant",
            "content": full_response,
            "tool_name": tool_name
        })
    
    # Handle follow-on instructions
    if follow_on_instructions:
        if isinstance(follow_on_instructions, str):
            follow_on_instructions = [follow_on_instructions]
        
        for instruction in follow_on_instructions:
            if LOGGING_ENABLED:
                logging.info(f"Adding follow-on instruction to chat history: {instruction}")
            chat_history.append({"role": "user", "content": instruction})
            save_chat_history(chat_history, chat_history_path)
            
            # Set a session state flag to process the follow-on instruction
            st.session_state.process_follow_on = True
            st.session_state.follow_on_instruction = instruction
    
    return full_response

def process_follow_on_instructions(
    client: Any,
    messages: List[Dict[str, Any]],
    initial_messages: List[Dict[str, Any]],
    chat_history: List[Dict[str, Any]],
    chat_history_path: str,
    advisor_data: Dict[str, Any],
    selected_advisor: str,
    tools: List[str],
    tool_choice: str,
    follow_on_instructions: Union[str, List[str]],
    **overrides
) -> None:
    """Process follow-on instructions after tool execution"""
    if isinstance(follow_on_instructions, str):
        follow_on_instructions = [follow_on_instructions]
    
    for instruction in follow_on_instructions:
        # Add instruction to chat history
        chat_history.append({"role": "user", "content": instruction})
        save_chat_history(chat_history, chat_history_path)
        
        # Process the follow-on instruction
        st.rerun()

def get_llm_response(
    client: Any,
    messages: List[Dict[str, Any]],
    initial_messages: List[Dict[str, Any]],
    chat_history: List[Dict[str, Any]],
    chat_history_path: str,
    advisor_data: Dict[str, Any],
    selected_advisor: str,
    tools: List[str] = [],
    tool_choice: str = 'auto',
    **overrides
) -> List[Dict[str, Any]]:
    """Main function to handle LLM responses and tool execution"""
    try:
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            response_placeholder = st.empty()
            
            with st.spinner(f"{selected_advisor} is thinking..."):
                # Prepare API parameters
                api_params = prepare_api_params(messages, tools, tool_choice, **overrides)
                
                try:
                    # Initialize tracking variables
                    accumulated_args = ""
                    current_tool_name = None
                    function_call_data = None
                    full_response = ""
                    
                    # Get LLM response stream
                    stream = client.chat.completions.create(**api_params)
                    
                    # Process stream
                    for chunk in stream:
                        if not chunk.choices:
                            continue
                        
                        delta = chunk.choices[0].delta
                        
                        # Handle tool calls
                        tool_name, tool_id, function_data, accumulated_args = process_tool_call(
                            delta, accumulated_args)
                        
                        if tool_name:
                            current_tool_name = tool_name
                        if function_data:
                            function_call_data = function_data
                        
                        # Handle content
                        if hasattr(delta, 'content') and delta.content:
                            chunk_text = delta.content
                            full_response += chunk_text
                            response_placeholder.markdown(full_response)
                    
                    # Important: Add the response to chat history BEFORE executing tools
                    if full_response.strip():
                        chat_history.append({
                            "role": "assistant",
                            "content": full_response
                        })
                        save_chat_history(chat_history, chat_history_path)
                    
                    # Execute tool if we have complete data
                    if current_tool_name and function_call_data:
                        handle_tool_execution(
                            current_tool_name,
                            function_call_data,
                            client,
                            chat_history,
                            chat_history_path,
                            response_placeholder,
                            status_placeholder
                        )
                
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    logging.error(f"LLM Response Error: {e}")
                    logging.exception(e)
                
                finally:
                    status_placeholder.empty()
    
    except Exception as main_e:
        st.error(f"An unexpected error occurred: {main_e}")
        logging.error(f"Unexpected error in get_llm_response: {main_e}")
        logging.exception(main_e)
    
    save_chat_history(chat_history, chat_history_path)
    return chat_history