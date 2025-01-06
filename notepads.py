# notepads.py

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
import shortuuid
from utils.prompt_utils import load_prompt
from utils.message_utils import save_snippet, display_messages
from utils.ui_utils import update_spinner_status
import time

load_dotenv()

os.getenv("GEMINI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class NotepadFileManager:
    @staticmethod
    def wait_for_files_active(files, timeout=300, check_interval=10):
        """
        Waits until all provided Gemini files are in the 'ACTIVE' state.
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

    @staticmethod
    def handle_file_upload(uploaded_files):
        selected_notepad_dir = Path(f'notepads/{st.session_state.selected_notepad_id}')
        files_dir = selected_notepad_dir / 'files'
        files_dir.mkdir(exist_ok=True)

        index_file = selected_notepad_dir / 'index.json'
        with open(index_file, 'r') as f:
            index_data = json.load(f)

        uploaded_gemini_files = []  # Collect uploaded Gemini file objects

        for uploaded_file in uploaded_files:
            # Check if file is already uploaded
            if uploaded_file.name in st.session_state.uploaded_file_names:
                print(f"File {uploaded_file.name} already uploaded. Skipping.")
                continue

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
                NotepadFileManager.wait_for_files_active(uploaded_gemini_files)
                st.success("Files uploaded, processed, and saved locally.")
            except Exception as e:
                st.error(str(e))
                print(str(e))

    @staticmethod
    def sync_notepad_files(notepad_id):
        selected_notepad_dir = Path(f'notepads/{notepad_id}')
        index_file = selected_notepad_dir / 'index.json'
        
        # Reset file-related session state
        st.session_state.uploaded_files = []
        st.session_state.uploaded_file_names = set()
        st.session_state.cloud_files = []
        st.session_state.cloud_file_names = set()

        # Ensure the index file exists
        if not index_file.exists():
            st.warning(f"No index file found for notepad {notepad_id}")
            return

        try:
            with open(index_file, 'r') as f:
                index_data = json.load(f)

            # Track if we need to update the index file
            index_needs_update = False

            # Create a placeholder in sidebar for upload status
            with st.sidebar:
                status_container = st.empty()
                progress_container = st.empty()
                
                # Show initial status
                status_container.info("Checking notepad files...")
                
                # Create progress bar
                total_files = len(index_data.get('files', []))
                if total_files > 0:
                    progress_bar = progress_container.progress(0)

            # Process files from index
            for file_idx, file_info in enumerate(index_data.get('files', [])):
                local_name = file_info.get('local_name')
                cloud_name = file_info.get('cloud_name')

                if not local_name:
                    continue

                local_file_path = selected_notepad_dir / local_name

                # Update status
                status_container.info(f"Processing: {local_file_path.name}")
                if total_files > 0:
                    progress_bar.progress((file_idx) / total_files)

                # Verify local file exists
                if not local_file_path.exists():
                    status_container.warning(f"Local file missing: {local_name}")
                    continue

                try:
                    # Try to get the Gemini file
                    try:
                        gemini_file = genai.get_file(name=cloud_name) if cloud_name else None
                        if gemini_file and gemini_file.state.name == "ACTIVE":
                            # File exists and is active, no need to re-upload
                            status_container.success(f"File available: {local_file_path.name}")
                    except Exception as cloud_err:
                        # Any cloud error (404, 403, etc) should trigger re-upload attempt
                        print(f"Cloud file error {cloud_name}: {cloud_err}")
                        gemini_file = None

                    # If no cloud file or error occurred, attempt to re-upload
                    if not gemini_file:
                        status_container.warning(f"Re-uploading: {local_file_path.name}")
                        try:
                            # Determine mime type
                            mime_type = mimetypes.guess_type(local_file_path)[0]
                            if not mime_type:
                                mime_type = 'application/octet-stream'
                            
                            # Upload to Gemini
                            gemini_file = genai.upload_file(
                                str(local_file_path),
                                mime_type=mime_type,
                                display_name=local_file_path.name
                            )
                            
                            # Update cloud name in file info
                            file_info['cloud_name'] = gemini_file.name
                            index_needs_update = True
                            
                            status_container.info(f"Waiting for {local_file_path.name} to be ready...")
                            
                            # Wait for file to become active
                            NotepadFileManager.wait_for_files_active([gemini_file])
                            
                            status_container.success(f"Re-uploaded: {local_file_path.name}")
                            
                        except Exception as upload_err:
                            status_container.error(f"Failed to re-upload {local_name}: {str(upload_err)}")
                            print(f"Error re-uploading {local_name}: {str(upload_err)}")
                            continue  # Skip adding to session state only if upload fails

                    # If we have a valid file (either existing or re-uploaded), add to session state
                    if gemini_file:
                        file_entry = {
                            "name": local_file_path.name,
                            "gemini_file": gemini_file,
                            "selected": True
                        }
                        
                        # Prevent duplicates
                        if local_file_path.name not in st.session_state.uploaded_file_names:
                            st.session_state.uploaded_files.append(file_entry)
                            st.session_state.uploaded_file_names.add(local_file_path.name)
                            st.session_state.cloud_files.append(gemini_file)
                            st.session_state.cloud_file_names.add(gemini_file.name)

                except Exception as e:
                    status_container.warning(f"Error processing file {local_name}: {str(e)}")

            # Update progress to completion
            if total_files > 0:
                progress_bar.progress(1.0)

            # Update index.json if needed
            if index_needs_update:
                status_container.info("Updating notepad index...")
                with open(index_file, 'w') as f:
                    json.dump(index_data, f, indent=4)

            # Clear status indicators after short delay
            time.sleep(1)
            status_container.empty()
            progress_container.empty()

            # Display files in sidebar
            with st.sidebar:
                if st.session_state.uploaded_files:
                    for idx, file in enumerate(st.session_state.uploaded_files):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(file['name'])
                        with col2:
                            # Checkbox to select/deselect file without label
                            file['selected'] = st.checkbox(
                                "", # Removed "Use" text
                                value=file.get('selected', True), 
                                key=f"file_select_{idx}"
                            )
                else:
                    st.write("No files uploaded")

        except Exception as e:
            st.error(f"Error syncing notepad files: {str(e)}")

class NotepadManager:
    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def create_new_notepad():
        # Existing create_new_notepad method implementation
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

    @staticmethod
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

class NotepadChatManager:
    @staticmethod
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

    @staticmethod
    def save_notepad_snippet(message_content):
        snippets_dir = os.path.join("snippets")
        source_type = "notepad"
        source_name = st.session_state.selected_notepad_id
        save_snippet(message_content, source_type, source_name, snippets_dir)
        st.success("✅")

    @staticmethod
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

def user_input():
    """
    Handle user input for chat interactions using Gemini AI.
    """
    print("\n=== DEBUG: CHAT HISTORY AND MESSAGE STRUCTURE ===")
    print("Current session messages:")
    print(json.dumps(st.session_state.messages, indent=2))
    
    # Add the user's message to the session state messages
    st.session_state.messages.append({
        "role": "user", 
        "content": st.session_state.get('prompt', '')
    })

    # Prepare the selected files for context
    selected_files = [
        file['gemini_file'] for file in st.session_state.uploaded_files 
        if file.get('selected', False)
    ]

    print("\nSelected files:")
    for file in selected_files:
        print(f"- {file.name} ({file.display_name})")

    try:
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

        # Configure safety settings
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE
        }

        # Initialize model with system prompt
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=system_prompt,
            safety_settings=safety_settings
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
        
        enhanced_question = f"""User question: {st.session_state.messages[-1]['content']}

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
        response = chat.send_message(message_parts)

        # Add the AI's response to the messages
        ai_response = {
            "role": "assistant", 
            "content": response.text
        }
        st.session_state.messages.append(ai_response)

        # Update the chat history in the notepad's index.json
        selected_notepad_dir = Path(f'notepads/{st.session_state.selected_notepad_id}')
        index_file = selected_notepad_dir / 'index.json'
        
        with open(index_file, 'r') as f:
            index_data = json.load(f)
        
        index_data['chat'] = st.session_state.messages
        
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=4)

    except Exception as e:
        error_message = {
            "role": "assistant", 
            "content": f"Sorry, an error occurred: {str(e)}"
        }
        st.session_state.messages.append(error_message)
        st.error(f"An error occurred: {str(e)}")
        print(f"Error details: {str(e)}")

def main():
    # Initialize default notepad if not exists
    NotepadManager.create_default_notepad()

    # Initialize session state variables if not already set
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 'chat'

    if 'selected_notepad_id' not in st.session_state:
        st.session_state.selected_notepad_id = 'default'

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

    if 'uploaded_file_names' not in st.session_state:
        st.session_state.uploaded_file_names = set()

    if 'cloud_files' not in st.session_state:
        st.session_state.cloud_files = []

    if 'cloud_file_names' not in st.session_state:
        st.session_state.cloud_file_names = set()

    # Load existing notepads
    notepads = NotepadManager.load_notepads()

    # Sidebar for notepad management
    with st.sidebar:

        # Notepad selection dropdown
        notepad_names = [np['name'] for np in notepads]
        selected_notepad_name = st.selectbox(
            "Select Notepad", 
            notepad_names, 
            index=0 if notepad_names else None
        )

        # Find the selected notepad's ID
        selected_notepad_id = next(
            (np['id'] for np in notepads if np['name'] == selected_notepad_name), 
            'default'
        )

        # If notepad selection changed, reset messages
        if st.session_state.selected_notepad_id != selected_notepad_id:
            st.session_state.selected_notepad_id = selected_notepad_id
            # Load chat history from index.json
            selected_notepad_dir = Path(f'notepads/{selected_notepad_id}')
            index_file = selected_notepad_dir / 'index.json'
            with open(index_file, 'r') as f:
                index_data = json.load(f)
                st.session_state.messages = index_data.get('chat', [])

        # Buttons for notepad management
        col1, col2 = st.columns(2)
        with col1:
            if st.button("New Notepad"):
                NotepadManager.create_new_notepad()

        with col2:
            if st.button("Clear Chat"):
                NotepadChatManager.clear_chat_history()

        # File upload section
        uploaded_files = st.file_uploader(
            "Upload Files", 
            accept_multiple_files=True
        )
        if uploaded_files:
            NotepadFileManager.handle_file_upload(uploaded_files)

        # Sync files for the selected notepad
        st.markdown("Select Files for Chat")
        NotepadFileManager.sync_notepad_files(selected_notepad_id)

    # Display existing messages with save and delete callbacks
    display_messages(
        messages=st.session_state.messages,
        save_callback=NotepadChatManager.save_notepad_snippet,
        delete_callback=NotepadChatManager.delete_notepad_message
    )

    # Chat input
    if prompt := st.chat_input("Enter your message"):
        st.session_state['prompt'] = prompt
        
        # Display user message immediately
        with st.chat_message("user"):
            st.write(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                user_input()

if __name__ == "__main__":
    main()