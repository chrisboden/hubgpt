# utils/ui_utils.py

import streamlit as st


def update_spinner_status(status: str):
    """Update the spinner status message in the UI"""
    if 'spinner_placeholder' in st.session_state:
        st.session_state.spinner_placeholder.markdown(f"*{status}*")
