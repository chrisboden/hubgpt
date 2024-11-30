# utils/llm_utils.py

import json
import logging
import streamlit as st
from utils.tool_utils import execute_tool, TOOL_METADATA_REGISTRY
from utils.chat_utils import save_chat_history
from typing import Dict, Any


def update_spinner_status(message):
    """
    Update the spinner status message dynamically
    
    Args:
        message (str): Status message to display
    """
    try:
        # Check if there's an active spinner in session state or Streamlit
        if hasattr(st.session_state, 'active_spinner'):
            try:
                # Attempt to update the spinner directly
                st.session_state.active_spinner.text = message
                return
            except Exception:
                pass
        
        # Fallback to session state storage
        st.session_state.spinner_status = message
        
        # Optional fallback: use placeholder if available
        if hasattr(st.session_state, 'spinner_placeholder'):
            try:
                st.session_state.spinner_placeholder.markdown(f"*{message}*")
            except Exception:
                pass
        
        # Console debug
        print(f"Spinner Status: {message}")
    
    except Exception as e:
        print(f"Error updating spinner status: {e}")


def get_default_llm_params():
    return {
        'model': 'gpt-4o-mini',
        'temperature': 1.0,
        'max_tokens': 8092,
        'top_p': 1,
        'frequency_penalty': 0,
        'presence_penalty': 0,
        'stream': True  # Renamed 'stream_mode' to 'stream' to match API parameter
    }

def get_llm_response(
    client,
    messages,
    initial_messages,
    chat_history,
    chat_history_path,
    advisor_data,
    selected_advisor,
    tools=[],
    tool_choice='auto',
    **overrides
):
    """
    Get response from LLM with support for streaming, tool calls, and dynamic status updates.
    """
    try:
        with st.chat_message("assistant"):
            # Create a placeholder for dynamic status updates
            status_placeholder = st.empty()
            
            # Create a container for the spinner and response
            with st.spinner(f"{selected_advisor} is thinking..."):
                # Get default parameters
                default_params = get_default_llm_params()
                
                # Merge overrides from advisor_data but exclude non-API parameters
                api_params = {**default_params}
                for key, value in overrides.items():
                    if key not in ['spinner_placeholder', 'status_placeholder']:  # Exclude UI elements
                        api_params[key] = value
                
                # Remove 'tools' and 'tool_choice' from api_params
                api_params.pop('tools', None)
                api_params.pop('tool_choice', None)
                
                # Resolve tool names to their metadata
                resolved_tools = []
                for tool_name in tools:
                    metadata = TOOL_METADATA_REGISTRY.get(tool_name)
                    if metadata:
                        resolved_tools.append(metadata)
                    else:
                        logging.warning(f"Tool '{tool_name}' metadata not found. Skipping tool.")
                
                # Initialize variables
                function_call_data = None
                st.session_state.tool_call_args = ""
                st.session_state.last_tool_call_id = ""
                st.session_state.last_tool_name = ""
                
                response_placeholder = st.empty()
                full_response = ""
                
                try:
                    # Set messages in API parameters
                    api_params['messages'] = messages
                    
                    # Add resolved tools to API parameters if applicable
                    if resolved_tools:
                        api_params['tools'] = resolved_tools
                        api_params['tool_choice'] = tool_choice
                    
                    # Stream the response
                    stream = client.chat.completions.create(**api_params)
                    for chunk in stream:
                        if not chunk.choices:
                            continue
                        
                        delta = chunk.choices[0].delta
                        
                        # Handle tool calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            tool_call = delta.tool_calls[0]
                            
                            if hasattr(tool_call, 'id') and tool_call.id:
                                st.session_state.last_tool_call_id = tool_call.id
                            
                            if hasattr(tool_call.function, 'name') and tool_call.function.name:
                                st.session_state.last_tool_name = tool_call.function.name
                                status_placeholder.markdown(f"*🔧 Using tool: {tool_call.function.name}*")
                            
                            if tool_call.function.arguments:
                                st.session_state.tool_call_args += tool_call.function.arguments
                            
                            try:
                                function_call_data = json.loads(st.session_state.tool_call_args)
                                st.session_state.tool_call_args = ""
                            except json.JSONDecodeError:
                                continue
                        
                        # Handle normal content streaming
                        chunk_text = delta.content or ""
                        full_response += chunk_text
                        response_placeholder.markdown(full_response)
                    
                    # Process completed response
                    if full_response.strip():
                        chat_history.append({"role": "assistant", "content": full_response})
                    
                    # Execute tool calls if detected
                    if function_call_data:
                        tool_name = st.session_state.last_tool_name
                        status_placeholder.markdown(f"*🔧 Executing tool: {tool_name}*")
                        
                        tool_response_data = execute_tool(tool_name, function_call_data, llm_client=client)

                        # Check if direct streaming is enabled
                        if tool_response_data.get('direct_stream', False):
                            # Get the stream from the tool response
                            stream = tool_response_data.get('result', '')
                            
                            # Clear status placeholder
                            status_placeholder.empty()
                            
                            # Create a new placeholder for streaming response
                            response_placeholder = st.empty()
                            full_response = ""
                            
                            # Handle OpenAI stream
                            for chunk in stream:
                                if not chunk.choices:
                                    continue
                                
                                delta = chunk.choices[0].delta
                                chunk_text = delta.content or ""
                                full_response += chunk_text
                                response_placeholder.markdown(full_response)
                            
                            # Add to chat history as an assistant message
                            chat_history.append({
                                "role": "assistant", 
                                "content": full_response,
                                "tool_name": tool_name
                            })
                            
                            # Save chat history
                            save_chat_history(chat_history, chat_history_path)
                            return chat_history



                        if tool_response_data:
                            # Add tool messages to chat history
                            assistant_tool_message = {
                                "role": "assistant",
                                "content": "null",
                                "tool_calls": [{
                                    "id": st.session_state.last_tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json.dumps(function_call_data)
                                    }
                                }]
                            }
                            chat_history.append(assistant_tool_message)
                            
                            tool_message = {
                                "role": "tool",
                                "name": tool_name,
                                "tool_call_id": st.session_state.last_tool_call_id,
                                "content": json.dumps(tool_response_data, indent=2)
                            }
                            chat_history.append(tool_message)
                            
                            # Process tool response
                            status_placeholder.markdown("*💭 Processing tool response...*")
                            
                            full_history = initial_messages + chat_history
                            api_params['messages'] = full_history
                            
                            final_stream = client.chat.completions.create(**api_params)
                            final_response_placeholder = st.empty()
                            final_response_text = ""
                            
                            for chunk in final_stream:
                                delta = chunk.choices[0].delta
                                if hasattr(delta, "content") and delta.content:
                                    chunk_text = delta.content
                                    final_response_text += chunk_text
                                    final_response_placeholder.markdown(final_response_text)
                            
                            if final_response_text.strip():
                                chat_history.append({"role": "assistant", "content": final_response_text})
                
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    logging.error(f"LLM Response Error: {e}")
                
                finally:
                    # Clean up status placeholder
                    status_placeholder.empty()
    
    except Exception as main_e:
        st.error(f"An unexpected error occurred: {main_e}")
        logging.error(f"Unexpected error in get_llm_response: {main_e}")

    # Save chat history
    save_chat_history(chat_history, chat_history_path)
    return chat_history