#notepads.py

import os
import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard
import google.generativeai as genai
from google.generativeai import types
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv
import tempfile
import json
import uuid
import shutil
import datetime
import mimetypes
from pathlib import Path
import shortuuid  # Install via pip install shortuuid
from utils.prompt_utils import load_prompt
from utils.message_utils import save_snippet, display_messages
import time  # Added for wait_for_files_active

load_dotenv()
os.getenv("GEMINI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def wait_for_files_active(files, timeout=300, check_interval=10):
    """
    Waits until all provided Gemini files are in the 'ACTIVE' state.

    Args:
        files (list): List of Gemini file objects to check.
        timeout (int): Maximum time to wait in seconds (default: 300).
        check_interval (int): Time between status checks in seconds (default: 10).

    Raises:
        Exception: If any file does not become active within the timeout period.
    """
    start_time = time.time()
    for file in files:
        print(f"Checking status of file: {file.name}")
        while True:
            current_file = genai.get_file(name=file.name)
            status = current_file.state.name
            print(f"Current status of '{file.name}': {status}")
            if status == "ACTIVE":
                print(f"File '{file.name}' is ACTIVE.")
                break
            elif status == "FAILED":
                raise Exception(f"File '{file.name}' failed to process.")
            elif time.time() - start_time > timeout:
                raise Exception(f"Timeout while waiting for file '{file.name}' to become ACTIVE.")
            else:
                print(f"Waiting for file '{file.name}' to become ACTIVE...")
                time.sleep(check_interval)
    print("All files are ACTIVE and ready for use.")

def clear_chat_history():
    st.session_state.messages = []
    # Clear chat history in index.json
    selected_notepad_dir = Path(f'notepads/{st.session_state.selected_notepad_id}')
    index_file = selected_notepad_dir / 'index.json'
    if index_file.exists():
        with open(index_file, 'r') as f:
            index_data = json.load(f)

        index_data['chat'] = []

        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=4)

def rename_notepad(notepad_id, new_name):
    notepad_dir = Path(f'notepads/{notepad_id}')
    index_file = notepad_dir / 'index.json'
    if index_file.exists():
        with open(index_file, 'r') as f:
            index_data = json.load(f)
        index_data['name'] = new_name
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=4)
    else:
        st.error("Notepad index file not found.")

@st.dialog("Rename Notepad")
def rename_notepad_dialog():
    selected_notepad_id = st.session_state.selected_notepad_id
    if not selected_notepad_id:
        st.error("No notepad selected.")
        return

    selected_notepad_dir = Path(f'notepads/{selected_notepad_id}')
    index_file = selected_notepad_dir / 'index.json'
    if not index_file.exists():
        st.error("Notepad index file not found.")
        return

    with open(index_file, 'r') as f:
        index_data = json.load(f)
    current_name = index_data['name']

    new_notepad_name = st.text_input("New Notepad Name", value=current_name)

    existing_notepads = load_notepads()
    existing_names = {notepad['name'] for notepad in existing_notepads}

    if st.button("Save"):
        if new_notepad_name.strip() == "":
            st.warning("Notepad name cannot be empty.")
        elif new_notepad_name.strip() in existing_names and new_notepad_name.strip() != current_name:
            st.warning("A notepad with this name already exists.")
        else:
            rename_notepad(selected_notepad_id, new_notepad_name.strip())
            st.rerun()  # Close the dialog and refresh the app

def load_notepads():
    notepads_dir = Path('notepads')
    notepads_dir.mkdir(exist_ok=True)
    notepad_paths = [p for p in notepads_dir.iterdir() if p.is_dir()]
    notepads = []
    for path in notepad_paths:
        index_file = path / 'index.json'
        if index_file.exists():
            with open(index_file, 'r') as f:
                data = json.load(f)
                notepads.append({'id': data['id'], 'name': data['name']})
    return notepads

def create_default_notepad():
    default_notepad_dir = Path('notepads/default')
    default_notepad_dir.mkdir(parents=True, exist_ok=True)
    (default_notepad_dir / 'files').mkdir(exist_ok=True)
    default_index_file = default_notepad_dir / 'index.json'
    if not default_index_file.exists():
        default_index = {
            "id": "default",
            "name": "Default Notepad",
            "created": str(datetime.datetime.now()),
            "files": [],
            "chat": []
        }
        with open(default_index_file, 'w') as f:
            json.dump(default_index, f, indent=4)

def create_new_notepad():
    # First clear ALL state except current_tab
    current_tab = st.session_state.current_tab  # Preserve tab state
    
    keys_to_reset = [
        'messages',
        'uploaded_files',
        'uploaded_file_names', 
        'cloud_files',
        'cloud_file_names',
        'notepad_loaded',
        'selected_notepad_id'
    ]

    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

    # Restore tab state
    st.session_state.current_tab = current_tab

    # Create new notepad
    new_id = shortuuid.ShortUUID().random(length=5)
    new_notepad_dir = Path(f'notepads/{new_id}')
    new_notepad_dir.mkdir(parents=True, exist_ok=True)
    (new_notepad_dir / 'files').mkdir(exist_ok=True)

    index_data = {
        "id": new_id,
        "name": "Untitled Notepad",
        "created": str(datetime.datetime.now()),
        "files": [],
        "chat": []
    }
    with open(new_notepad_dir / 'index.json', 'w') as f:
        json.dump(index_data, f, indent=4)

    # Set new notepad ID
    st.session_state.selected_notepad_id = new_id
    
    # Force reload
    st.rerun()

def handle_file_upload(uploaded_files):
    selected_notepad_dir = Path(f'notepads/{st.session_state.selected_notepad_id}')
    files_dir = selected_notepad_dir / 'files'
    files_dir.mkdir(exist_ok=True)

    index_file = selected_notepad_dir / 'index.json'
    with open(index_file, 'r') as f:
        index_data = json.load(f)

    uploaded_gemini_files = []  # Collect uploaded Gemini file objects

    for uploaded_file in uploaded_files:
        local_file_path = files_dir / uploaded_file.name
        with open(local_file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        mime_type = uploaded_file.type

        # Upload to Gemini
        with st.spinner(f"Uploading {uploaded_file.name} to Gemini..."):
            try:
                gemini_file = genai.upload_file(
                    str(local_file_path),
                    mime_type=mime_type,
                    display_name=uploaded_file.name
                )
                uploaded_gemini_files.append(gemini_file)
                print(f"Uploaded file '{gemini_file.name}' successfully.")
            except Exception as e:
                st.error(f"Failed to upload {uploaded_file.name}: {str(e)}")
                print(f"Error uploading {uploaded_file.name}: {str(e)}")
                continue  # Skip to the next file

        # Update index.json
        index_data['files'].append({
            "local_name": str(local_file_path.relative_to(selected_notepad_dir)),
            "cloud_name": gemini_file.name
        })

        # Update session state
        st.session_state.uploaded_files.append({
            "name": uploaded_file.name,
            "gemini_file": gemini_file,
            "selected": True
        })
        st.session_state.uploaded_file_names.add(uploaded_file.name)

        # Update cloud files in session state
        st.session_state.cloud_files.append(gemini_file)
        st.session_state.cloud_file_names.add(gemini_file.name)

    # Save the updated index.json
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=4)

    # Wait for all uploaded files to become ACTIVE
    if uploaded_gemini_files:
        try:
            wait_for_files_active(uploaded_gemini_files)
            st.success("Files uploaded, processed, and saved locally.")
        except Exception as e:
            st.error(str(e))
            print(str(e))

def sync_notepad_files(notepad_id):
    selected_notepad_dir = Path(f'notepads/{notepad_id}')
    index_file = selected_notepad_dir / 'index.json'
    with open(index_file, 'r') as f:
        index_data = json.load(f)

    # Use cloud files from session state
    cloud_file_names = st.session_state.cloud_file_names

    files_updated = False
    reuploaded_files = []  # Collect re-uploaded Gemini file objects

    for file_info in index_data['files']:
        cloud_name = file_info.get('cloud_name')
        local_name = file_info['local_name']

        # Ensure we're using the correct path relative to the notepad's files directory
        local_file_path = selected_notepad_dir / local_name

        if local_file_path.exists():  # Only proceed if file exists
            if not cloud_name or cloud_name not in cloud_file_names:
                # Re-upload the file
                mime_type = mimetypes.guess_type(local_file_path)[0] or 'application/octet-stream'
                with st.spinner(f"Re-uploading {local_file_path.name} to Gemini..."):
                    try:
                        gemini_file = genai.upload_file(
                            str(local_file_path),
                            mime_type=mime_type,
                            display_name=local_file_path.name
                        )
                        reuploaded_files.append(gemini_file)
                        print(f"Re-uploaded file '{gemini_file.name}' successfully.")
                    except Exception as e:
                        st.warning(f"Failed to upload {local_file_path.name}: {str(e)}")
                        print(f"Error uploading {local_file_path.name}: {str(e)}")
                        continue  # Skip to the next file

                # Update cloud_name
                file_info['cloud_name'] = gemini_file.name
                files_updated = True

                # Update cloud files in session state
                st.session_state.cloud_files.append(gemini_file)
                st.session_state.cloud_file_names.add(gemini_file.name)
        else:
            st.warning(f"File not found: {local_file_path}")

    if files_updated:
        # Save the updated index.json
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=4)
        st.success("Local and cloud files are synced.")

        # Wait for re-uploaded files to become ACTIVE
        if reuploaded_files:
            try:
                wait_for_files_active(reuploaded_files)
                st.success("Re-uploaded files are active and synced.")
            except Exception as e:
                st.error(str(e))
                print(str(e))


def user_input(user_question):
    print("\n=== DEBUG: CHAT HISTORY AND MESSAGE STRUCTURE ===")
    print("Current session messages:")
    print(json.dumps(st.session_state.messages, indent=2))
    
    selected_files = []
    for file_info in st.session_state.uploaded_files:
        if file_info["selected"]:
            selected_files.append(file_info["gemini_file"])
    
    print("\nSelected files:")
    for file in selected_files:
        print(f"- {file.name} ({file.display_name})")

    # Load prompt configuration
    with open('notepads/notepad_prompt.json', 'r') as f:
        prompt_config = json.load(f)

    # Get configuration values
    model_name = prompt_config.get("model", "gemini-1.5-pro-002")
    temperature = prompt_config.get("temperature", 0.7)
    max_tokens = prompt_config.get("max_tokens", 8092)
    
    # Extract system prompt from messages array
    system_prompt = next(
        (msg["content"] for msg in prompt_config.get("messages", []) 
         if msg["role"] == "system"), 
        ""
    )

    print("\nSystem Prompt:")
    print(system_prompt)

    # Create generation config
    generation_config = types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    # Initialize model with system prompt
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=system_prompt,
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )

    # Convert session messages to chat history format
    history = []
    for msg in st.session_state.messages[:-1]:  # Exclude latest user message
        history.append({
            "role": msg["role"],
            "parts": [msg["content"]]
        })

    print("\nConverted Chat History being sent to Gemini:")
    print(json.dumps(history, indent=2))

    # Start chat session with history
    chat = model.start_chat(history=history)

    # Create file list string and enhanced question
    file_list = "\n".join([f"- {file.display_name}" for file in selected_files])
    
    enhanced_question = f"""User question: {user_question}

IMPORTANT: Note that the user has provided these specific documents 
for you to analyse and use in your response:

{file_list}

Please ensure you use ALL of the available documents for your response."""

    # Prepare the current message with files and enhanced question
    message_parts = selected_files + [enhanced_question]

    print("\nCurrent Message Parts:")
    print(f"- Files: {[f.display_name for f in selected_files]}")
    print(f"- Enhanced Question: {enhanced_question}")
    print("===============================================\n")

    # Send message and get response
    try:
        response = chat.send_message(message_parts)
        return response
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        print(f"Error details: {str(e)}")
        return None

def save_notepad_snippet(message_content):
    snippets_dir = os.path.join("snippets")
    source_type = "notepad"
    source_name = st.session_state.selected_notepad_id  # Or use the notepad's name
    save_snippet(message_content, source_type, source_name, snippets_dir)
    st.success("✅")

def delete_notepad_message(index):
    # Remove the message from session state
    st.session_state.messages.pop(index)
    # Update the chat history in index.json
    selected_notepad_dir = Path(f'notepads/{st.session_state.selected_notepad_id}')
    index_file = selected_notepad_dir / 'index.json'
    with open(index_file, 'r') as f:
        index_data = json.load(f)
    index_data['chat'] = st.session_state.messages
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=4)
    st.rerun()

def main():
    # Initialize session state for selected notepad
    if 'selected_notepad_id' not in st.session_state:
        st.session_state.selected_notepad_id = None

    # Load available notepads
    notepads = load_notepads()

    # Handle cold start
    if not notepads:
        # Create default notepad
        create_default_notepad()
        notepads = load_notepads()

    # Sidebar for notepad selection
    with st.sidebar:
        notepad_names = [notepad['name'] for notepad in notepads]

        # Determine the current notepad name and index
        if st.session_state.selected_notepad_id is None:
            selected_notepad_name = st.selectbox("Choose a notepad", notepad_names)
        else:
            # Get current notepad name
            current_notepad = next((n for n in notepads if n['id'] == st.session_state.selected_notepad_id), None)
            current_notepad_name = current_notepad['name'] if current_notepad else ''
            selected_notepad_name = st.selectbox("Choose a notepad", notepad_names, index=notepad_names.index(current_notepad_name))

        # Get the selected notepad ID
        selected_notepad = next((n for n in notepads if n['name'] == selected_notepad_name), None)
        if selected_notepad:
            if st.session_state.selected_notepad_id != selected_notepad['id']:
                st.session_state.selected_notepad_id = selected_notepad['id']
                st.session_state.messages = []
                st.session_state.uploaded_files = []
                st.session_state.uploaded_file_names = set()
                st.session_state.cloud_files = []
                st.session_state.cloud_file_names = set()
        else:
            st.session_state.selected_notepad_id = None

        # Create a two-column layout for the buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("New Notepad"):
                create_new_notepad()
        with col2:
            if st.button("Rename"):
                rename_notepad_dialog()

    if st.session_state.selected_notepad_id:
        # Load chat history and uploaded files before syncing
        selected_notepad_dir = Path(f'notepads/{st.session_state.selected_notepad_id}')
        index_file = selected_notepad_dir / 'index.json'
        with open(index_file, 'r') as f:
            index_data = json.load(f)

        if "messages" not in st.session_state or st.session_state.get('notepad_loaded') != st.session_state.selected_notepad_id:
            st.session_state.messages = index_data.get('chat', [])
            st.session_state.notepad_loaded = st.session_state.selected_notepad_id

        # Initialize uploaded_files and cloud_files in session state
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = []
            st.session_state.uploaded_file_names = set()
            st.session_state.cloud_files = []
            st.session_state.cloud_file_names = set()

        # Load uploaded files from index.json
        st.session_state.uploaded_files = []
        st.session_state.uploaded_file_names = set()
        st.session_state.cloud_files = []
        st.session_state.cloud_file_names = set()

        uploaded_gemini_files = []  # Collect files to wait for activation

        for file_info in index_data['files']:
            try:
                gemini_file = genai.get_file(name=file_info["cloud_name"])
                st.session_state.uploaded_files.append({
                    "name": Path(file_info["local_name"]).name,
                    "gemini_file": gemini_file,
                    "selected": True
                })
                st.session_state.uploaded_file_names.add(Path(file_info["local_name"]).name)
                st.session_state.cloud_files.append(gemini_file)
                st.session_state.cloud_file_names.add(gemini_file.name)
                uploaded_gemini_files.append(gemini_file)
            except Exception as e:
                st.warning(f"Failed to load file {file_info['local_name']}: {str(e)}")

        # Now call sync_notepad_files
        sync_notepad_files(st.session_state.selected_notepad_id)

        # Wait for all loaded files to become ACTIVE
        if uploaded_gemini_files:
            try:
                wait_for_files_active(uploaded_gemini_files)
                st.success("All loaded files are ACTIVE and ready.")
            except Exception as e:
                st.error(str(e))
                print(str(e))

        # Sidebar for uploading files
        with st.sidebar:
            # File uploader
            uploaded_docs = st.file_uploader(
                "", accept_multiple_files=True)

            if uploaded_docs:
                handle_file_upload(uploaded_docs)

            # Now display the list of uploaded files with checkboxes
            if st.session_state.uploaded_files:
                st.write("Select files to include in the prompt:")
                for idx, file_info in enumerate(st.session_state.uploaded_files):
                    key = f"{st.session_state.selected_notepad_id}_{file_info['name']}_{idx}"
                    file_info["selected"] = st.checkbox(
                        file_info["name"], value=file_info.get("selected", True), key=key)

            st.button('Clear Chat History', on_click=clear_chat_history)

    else:
        st.error("No notepad selected.")
        st.stop()

    # Main content area for displaying chat messages
    st.write("Welcome to the chat!")

    display_messages(
        messages=st.session_state.messages,
        save_callback=save_notepad_snippet,
        delete_callback=delete_notepad_message,
        context_id=st.session_state.selected_notepad_id
    )

    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Display chat messages and bot response
        if st.session_state.uploaded_files:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = user_input(prompt)
                    full_response = response.text
                    st.write(full_response)
            if response is not None:
                message = {"role": "assistant", "content": full_response}
                st.session_state.messages.append(message)

                # Save the updated chat history to index.json
                index_data['chat'] = st.session_state.messages
                with open(index_file, 'w') as f:
                    json.dump(index_data, f, indent=4)
        else:
            st.warning("Please upload and select at least one file before asking a question.")

if __name__ == "__main__":
    main()
