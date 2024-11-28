# main.py

import os
import logging
import streamlit as st
from dotenv import load_dotenv
import advisors
import notepads
import teams

# Remove any existing handlers to prevent conflicts
#for handler in logging.root.handlers[:]:
    #logging.root.removeHandler(handler)

# Configure logging
#logging.basicConfig(
    #level=logging.INFO,
    #format='%(asctime)s %(levelname)s:%(message)s',
    #handlers=[
        #logging.FileHandler("logs/app.log"),
        #logging.StreamHandler()
    #]
#)

# Load environment variables
load_dotenv()

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

col3.button(
    "🧑‍🤝‍🧑",
    key="teams_btn",
    type="primary" if st.session_state.current_tab == "Teams" else "secondary",
    on_click=lambda: setattr(st.session_state, 'current_tab', 'Teams'),
    use_container_width=True
)

# Load content in main area based on selected tab
if st.session_state.current_tab == "Advisors":
    advisors.main()
elif st.session_state.current_tab == "Notepads":
    notepads.main()
elif st.session_state.current_tab == "Teams":
    teams.main()
