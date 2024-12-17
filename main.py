# main.py

import os
import sys
import logging
import streamlit as st
from dotenv import load_dotenv
import advisors
import notepads
#import teams

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Ensure the logs directory exists
logs_dir = os.path.join(project_root, "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Remove any existing handlers to prevent conflicts
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "app.log")),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

HORIZONTAL_HUB = "static/logo_full.png"
ICON_HUB = "static/logo.png"
sidebar_logo = HORIZONTAL_HUB
main_body_logo = ICON_HUB
st.logo(sidebar_logo, icon_image=main_body_logo)


# Initialize session state for tab selection if not exists
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "Advisors"


with open('./static/style.css') as f:
    css = f.read()

st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

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

#col3.button(
#    "🧑‍🤝‍🧑",
#    key="teams_btn",
#    type="primary" if st.session_state.current_tab == "Teams" else "secondary",
#    on_click=lambda: setattr(st.session_state, 'current_tab', 'Teams'),
#    use_container_width=True
#)

# Load content in main area based on selected tab
if st.session_state.current_tab == "Advisors":
    advisors.main()
elif st.session_state.current_tab == "Notepads":
    notepads.main()
#elif st.session_state.current_tab == "Teams":
#    teams.main()
