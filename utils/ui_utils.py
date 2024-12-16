# utils/ui_utils.py

import streamlit as st


def update_spinner_status(message):
    """
    Update the spinner status message dynamically
    
    Args:
        message (str): Status message to display
    
    Purpose:
    - Provides flexible mechanism for updating UI spinner status
    - Handles multiple fallback methods for status updates
    - Ensures visibility of current processing state
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
