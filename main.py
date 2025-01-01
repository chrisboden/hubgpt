# main.py

import os
import sys
import streamlit as st
from dotenv import load_dotenv
import advisors
import notepads
from utils.log_utils import setup_logging

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Setup logging
logger = setup_logging(project_root)

# Load environment variables
@st.cache_resource
def load_environment():
    """Cache environment loading"""
    load_dotenv()
    return True

@st.cache_resource
def load_css():
    """Cache CSS loading"""
    with open('./static/css/style.css') as f:
        base_css = f.read()
    with open('./static/css/advisors.css') as f:
        advisors_css = f.read()
    return base_css, advisors_css

def main():
    # Load environment once
    load_environment()
    
    # Load CSS first - before any content rendering
    base_css, advisors_css = load_css()
    st.markdown(f'<style>{base_css}</style>', unsafe_allow_html=True)
    st.markdown(f'<style>{advisors_css}</style>', unsafe_allow_html=True)

    # Logo configuration
    HORIZONTAL_HUB = "static/images/logo_full.png"
    ICON_HUB = "static/images/logo.png"
    sidebar_logo = HORIZONTAL_HUB
    main_body_logo = ICON_HUB
    st.logo(sidebar_logo, icon_image=main_body_logo)

    # Initialize session state for tab selection if not exists
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Advisors"

    # Create sidebar with navigation buttons
    col1, col2, col3 = st.sidebar.columns(3)

    # Place buttons in columns with active states
    col1.button(
        "🧑🏻‍💻",
        key="advisors_btn",
        type="primary" if st.session_state.current_tab == "Advisors" else "secondary",
        on_click=lambda: setattr(st.session_state, 'current_tab', 'Advisors'),
        use_container_width=True
    )

    col2.button(
        "📝",
        key="notepads_btn", 
        type="primary" if st.session_state.current_tab == "Notepads" else "secondary",
        on_click=lambda: setattr(st.session_state, 'current_tab', 'Notepads'),
        use_container_width=True
    )

    # Load content in main area based on selected tab
    if st.session_state.current_tab == "Advisors":
        advisors.main()
    elif st.session_state.current_tab == "Notepads":
        notepads.main()

if __name__ == "__main__":
    main()