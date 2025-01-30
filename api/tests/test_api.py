import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import shutil
from datetime import datetime
import base64
from typing import Generator
import glob
import os

from api.main import app
from api.models.advisors import AdvisorCreate
from api.models.chat import ChatRequest, ChatMessage
from api.models.files import FileContent, FileRename
from api.config import CHATS_DIR, ARCHIVE_DIR
from api import config

# Create test client
client = TestClient(app)

# Test data
TEST_ADVISOR = {
    "name": "test_advisor",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
    "tools": ["web_search", "file_reader"],
    "format": "json",
    "messages": [
        {
            "role": "system",
            "content": "You are a test advisor."
        }
    ],
    "stream": True,
    "gateway": "openrouter"
}

# Test advisor with file inclusion
TEST_ADVISOR_WITH_FILE = {
    "name": "test_advisor_with_file",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000,
    "messages": [
        {
            "role": "system",
            "content": "You are a test advisor with file inclusion.\n\nContext from file: <$files/test_context.txt$>"
        }
    ],
    "stream": False,
    "gateway": "openrouter"
}

# Test advisor with weather tool
TEST_ADVISOR_WITH_TOOL = {
    "name": "test_advisor_with_tool",
    "model": "openai/gpt-4o-mini",
    "temperature": 1,
    "max_output_tokens": 8092,
    "messages": [
        {
            "role": "system",
            "content": "You are a tool-calling LLM assistant. Your goal is to carefully process each user message and determine whether you need to respond naturally or make a tool call to assist the user effectively."
        }
    ],
    "tools": ["get_current_weather"],
    "stream": True,
    "gateway": "openrouter"
}

TEST_MESSAGE = {
    "message": "Hello, advisor!"
}

TEST_WEATHER_MESSAGE = {
    "message": "What's the weather like in Barcelona?"
}

TEST_FILE_CONTENT = {
    "content": "Test file content"
}

# Auth headers
def get_auth_headers() -> dict:
    """Get authentication headers for API requests"""
    credentials = base64.b64encode(
        f"{config.API_USERNAME}:{config.API_PASSWORD}".encode()
    ).decode()
    return {"Authorization": f"Basic {credentials}"}

@pytest.fixture
def auth_client() -> Generator[TestClient, None, None]:
    """Create a test client with authentication headers"""
    with TestClient(app) as test_client:
        test_client.headers.update(get_auth_headers())
        yield test_client

# Fixtures
@pytest.fixture(autouse=True)
def setup_and_cleanup():
    """Setup test environment and cleanup test files only"""
    # Setup - ensure directories exist but don't delete their contents
    CHATS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    Path("files").mkdir(parents=True, exist_ok=True)
    
    # Load tools from root tools directory
    tools_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tools")
    from api.api_utils.tool_utils import load_tools
    load_tools(tools_dir)
    
    # Clean only test files before starting
    for pattern in ["test_*.json", "test_*.md"]:
        for test_file in Path("advisors").glob(pattern):
            test_file.unlink()
        for test_file in CHATS_DIR.glob(pattern):
            test_file.unlink()
        for test_file in ARCHIVE_DIR.glob(pattern):
            test_file.unlink()
    
    yield
    
    # Cleanup - only remove test files
    for pattern in ["test_*.json", "test_*.md"]:
        for test_file in Path("advisors").glob(pattern):
            test_file.unlink()
        for test_file in CHATS_DIR.glob(pattern):
            test_file.unlink()
        for test_file in ARCHIVE_DIR.glob(pattern):
            test_file.unlink()
    
    # Clean test files from files directory
    for test_file in Path("files").glob("test_*"):
        if test_file.is_file():
            test_file.unlink()
        elif test_file.is_dir():
            shutil.rmtree(test_file)

# Advisor Tests
def test_list_advisors_empty(auth_client):
    """Test listing advisors"""
    # Get initial list
    response = auth_client.get("/advisors")
    assert response.status_code == 200
    initial_advisors = response.json()
    
    # Create test advisor
    auth_client.post("/advisors", json=TEST_ADVISOR)
    
    # Get updated list
    response = auth_client.get("/advisors")
    assert response.status_code == 200
    updated_advisors = response.json()
    
    # Verify our test advisor was added
    assert len(updated_advisors) == len(initial_advisors) + 1
    test_advisor = next((a for a in updated_advisors if a["name"] == TEST_ADVISOR["name"]), None)
    assert test_advisor is not None
    assert test_advisor["model"] == TEST_ADVISOR["model"]

def test_create_advisor(auth_client):
    """Test creating a new advisor"""
    response = auth_client.post("/advisors", json=TEST_ADVISOR)
    assert response.status_code == 200
    advisor = response.json()
    assert advisor["name"] == TEST_ADVISOR["name"]
    assert advisor["model"] == TEST_ADVISOR["model"]

def test_get_advisor(auth_client):
    """Test getting a specific advisor"""
    # First create an advisor
    auth_client.post("/advisors", json=TEST_ADVISOR)
    
    # Then get it
    response = auth_client.get(f"/advisors/{TEST_ADVISOR['name']}")
    assert response.status_code == 200
    advisor = response.json()
    assert advisor["name"] == TEST_ADVISOR["name"]

def test_update_advisor(auth_client):
    """Test updating an existing advisor"""
    # First create an advisor
    auth_client.post("/advisors", json=TEST_ADVISOR)
    
    # Update it
    updated_advisor = TEST_ADVISOR.copy()
    updated_advisor["temperature"] = 0.8
    response = auth_client.put(f"/advisors/{TEST_ADVISOR['name']}", json=updated_advisor)
    assert response.status_code == 200
    advisor = response.json()
    assert advisor["temperature"] == 0.8

# Chat Tests
def test_get_conversation_history_empty(auth_client):
    """Test getting conversation history when none exists"""
    response = auth_client.get(f"/chat/advisor/{TEST_ADVISOR['name']}/history")
    assert response.status_code == 200
    assert response.json() == []

def test_get_latest_conversation(auth_client):
    """Test getting latest conversation"""
    response = auth_client.get(f"/chat/advisor/{TEST_ADVISOR['name']}/latest")
    assert response.status_code == 200
    conversation = response.json()
    assert conversation["advisor_id"] == TEST_ADVISOR["name"]
    assert conversation["messages"] == []

def test_create_new_chat(auth_client):
    """Test creating a new chat"""
    response = auth_client.post(f"/chat/advisor/{TEST_ADVISOR['name']}/new")
    assert response.status_code == 200
    conversation = response.json()
    assert conversation["advisor_id"] == TEST_ADVISOR["name"]
    assert conversation["messages"] == []

def test_add_message(auth_client):
    """Test adding a message to a conversation"""
    # First create an advisor
    create_response = auth_client.post("/advisors", json=TEST_ADVISOR)
    assert create_response.status_code == 200
    assert create_response.json()["name"] == TEST_ADVISOR["name"]
    
    # Create a new chat
    chat_response = auth_client.post(f"/chat/advisor/{TEST_ADVISOR['name']}/new")
    assert chat_response.status_code == 200
    assert chat_response.json()["messages"] == []
    
    # Add a message and get streaming response
    with auth_client.stream(
        "POST",
        f"/chat/{TEST_ADVISOR['name']}/message",
        json=TEST_MESSAGE
    ) as message_response:
        assert message_response.status_code == 200
        assert message_response.headers["content-type"].startswith("text/event-stream")
        
        # Process SSE events
        assistant_response = ""
        for line in message_response.iter_lines():
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])  # Skip "data: " prefix
                    if "message" in data:
                        assistant_response += data["message"]["content"]
                except json.JSONDecodeError:
                    continue
    
    # Verify non-empty response was received
    assert len(assistant_response) > 0
    
    # Verify complete conversation
    conversation = auth_client.get(f"/chat/{TEST_ADVISOR['name']}").json()
    messages = conversation["messages"]
    assert len(messages) == 2  # User message + Assistant response
    
    # Verify user message
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == TEST_MESSAGE["message"]
    
    # Verify assistant response
    assert messages[1]["role"] == "assistant"
    assert isinstance(messages[1]["content"], str)
    assert len(messages[1]["content"]) > 0
    assert messages[1]["content"] == assistant_response

def test_add_message_non_streaming(auth_client):
    """Test adding a message with non-streaming response"""
    # Create a non-streaming advisor config
    non_streaming_advisor = TEST_ADVISOR.copy()
    non_streaming_advisor["name"] = "test_advisor_non_streaming"
    non_streaming_advisor["stream"] = False
    
    # Create the advisor
    create_response = auth_client.post("/advisors", json=non_streaming_advisor)
    assert create_response.status_code == 200
    assert create_response.json()["name"] == non_streaming_advisor["name"]
    
    # Create a new chat
    chat_response = auth_client.post(f"/chat/advisor/{non_streaming_advisor['name']}/new")
    assert chat_response.status_code == 200
    assert chat_response.json()["messages"] == []
    
    # Add a message and get non-streaming response
    message_response = auth_client.post(
        f"/chat/{non_streaming_advisor['name']}/message",
        json=TEST_MESSAGE
    )
    
    # Verify response
    assert message_response.status_code == 200
    assert message_response.headers["content-type"] == "application/json"
    
    response_data = message_response.json()
    assert "conversation_id" in response_data
    assert "message" in response_data
    assert "content" in response_data["message"]
    assert isinstance(response_data["message"]["content"], str)
    assert len(response_data["message"]["content"]) > 0
    
    # Verify complete conversation
    conversation = auth_client.get(f"/chat/{non_streaming_advisor['name']}").json()
    messages = conversation["messages"]
    assert len(messages) == 2  # User message + Assistant response
    
    # Verify user message
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == TEST_MESSAGE["message"]
    
    # Verify assistant response
    assert messages[1]["role"] == "assistant"
    assert isinstance(messages[1]["content"], str)
    assert len(messages[1]["content"]) > 0
    assert messages[1]["content"] == response_data["message"]["content"]

def test_delete_conversation(auth_client):
    """Test deleting a conversation"""
    # First create a chat
    auth_client.post(f"/chat/advisor/{TEST_ADVISOR['name']}/new")
    
    # Then delete it
    response = auth_client.delete(f"/chat/{TEST_ADVISOR['name']}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

# File Tests
def test_list_files_empty(auth_client):
    """Test listing files when none exist"""
    # Note: We can't guarantee an empty directory, so we just verify the structure
    response = auth_client.get("/files")
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) > 0
    # Verify at least the root directory exists
    root_dir = next((f for f in files if f["name"] == "" and f["is_dir"]), None)
    assert root_dir is not None
    assert root_dir["is_dir"] == True

def test_create_file(auth_client):
    """Test creating a new file"""
    test_filename = "test_create_file.txt"
    response = auth_client.post(f"/files/{test_filename}", json=TEST_FILE_CONTENT)
    assert response.status_code == 200
    
    # Verify file exists
    response = auth_client.get(f"/files/{test_filename}")
    assert response.status_code == 200
    assert response.text == TEST_FILE_CONTENT["content"]

def test_create_directory(auth_client):
    """Test creating a new directory"""
    test_dirname = "test_create_dir"
    response = auth_client.post(f"/files/{test_dirname}")
    assert response.status_code == 200
    
    # Verify directory exists
    response = auth_client.get("/files")
    files = response.json()["files"]
    assert any(f["name"] == test_dirname and f["is_dir"] for f in files)

def test_update_file(auth_client):
    """Test updating a file"""
    test_filename = "test_update_file.txt"
    # First create a file
    auth_client.post(f"/files/{test_filename}", json=TEST_FILE_CONTENT)
    
    # Update it
    new_content = {"content": "Updated content"}
    response = auth_client.put(f"/files/{test_filename}", json=new_content)
    assert response.status_code == 200
    
    # Verify update
    response = auth_client.get(f"/files/{test_filename}")
    assert response.status_code == 200
    assert response.text == new_content["content"]

def test_rename_file(auth_client):
    """Test renaming a file"""
    test_filename = "test_rename_source.txt"
    test_new_filename = "test_rename_target.txt"
    
    # First create a file
    auth_client.post(f"/files/{test_filename}", json=TEST_FILE_CONTENT)
    
    # Rename it
    response = auth_client.patch(f"/files/{test_filename}", json={"new_name": test_new_filename})
    assert response.status_code == 200
    
    # Verify rename
    response = auth_client.get(f"/files/{test_new_filename}")
    assert response.status_code == 200

def test_delete_file(auth_client):
    """Test deleting a file"""
    # First create a file
    auth_client.post("/files/test.txt", json=TEST_FILE_CONTENT)
    
    # Delete it
    response = auth_client.delete("/files/test.txt")
    assert response.status_code == 200
    
    # Verify deletion
    response = auth_client.get("/files/test.txt")
    assert response.status_code == 404

# Error Cases
def test_get_nonexistent_advisor(auth_client):
    """Test getting an advisor that doesn't exist"""
    response = auth_client.get("/advisors/nonexistent")
    assert response.status_code == 404

def test_get_nonexistent_conversation(auth_client):
    """Test getting a conversation that doesn't exist"""
    response = auth_client.get("/chat/nonexistent")
    assert response.status_code == 404

def test_get_nonexistent_file(auth_client):
    """Test getting a file that doesn't exist"""
    response = auth_client.get("/files/nonexistent.txt")
    assert response.status_code == 404

def test_file_inclusion_in_prompt(auth_client):
    """Test that files are correctly included in prompts"""
    # Create a test context file in the files directory
    test_context = "This is test context that should be included in the prompt."
    auth_client.post("/files/test_context.txt", json={"content": test_context})
    
    # Create advisor with file inclusion
    create_response = auth_client.post("/advisors", json=TEST_ADVISOR_WITH_FILE)
    assert create_response.status_code == 200
    advisor_data = create_response.json()
    assert advisor_data["name"] == TEST_ADVISOR_WITH_FILE["name"]
    
    # Create a new chat
    chat_response = auth_client.post(f"/chat/advisor/{TEST_ADVISOR_WITH_FILE['name']}/new")
    assert chat_response.status_code == 200
    
    # Send a message that should trigger a response using the included file content
    message_response = auth_client.post(
        f"/chat/{TEST_ADVISOR_WITH_FILE['name']}/message",
        json={"message": "What context do you have?"}
    )
    
    # Verify response
    assert message_response.status_code == 200
    response_data = message_response.json()
    assert "message" in response_data
    assert "content" in response_data["message"]
    
    # Get the full conversation to check the system message
    conversation = auth_client.get(f"/chat/{TEST_ADVISOR_WITH_FILE['name']}").json()
    system_message = conversation["messages"][0]["content"]
    assert test_context in system_message

def test_tool_calling_flow(auth_client):
    """Test the complete tool calling flow with weather tool"""
    # Create advisor with weather tool
    create_response = auth_client.post("/advisors", json=TEST_ADVISOR_WITH_TOOL)
    assert create_response.status_code == 200
    
    # Create a new chat
    chat_response = auth_client.post(f"/chat/advisor/{TEST_ADVISOR_WITH_TOOL['name']}/new")
    assert chat_response.status_code == 200
    
    # Send message asking about weather
    with auth_client.stream(
        "POST",
        f"/chat/{TEST_ADVISOR_WITH_TOOL['name']}/message",
        json={"message": "What's the weather like in Barcelona?"}
    ) as message_response:
        assert message_response.status_code == 200
        assert message_response.headers["content-type"].startswith("text/event-stream")
        
        # Process SSE events
        assistant_response = ""
        for line in message_response.iter_lines():
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])  # Skip "data: " prefix
                    if "message" in data and "content" in data["message"]:
                        assistant_response += data["message"]["content"]
                except json.JSONDecodeError:
                    continue
    
    # Get conversation to verify the flow worked
    conversation = auth_client.get(f"/chat/{TEST_ADVISOR_WITH_TOOL['name']}").json()
    messages = conversation["messages"]
    print("\nMessages:", json.dumps(messages, indent=2))
    
    # Verify we have all messages in the flow
    assert len(messages) == 4  # user -> assistant tool call -> tool response -> assistant final
    
    # Verify tool call was made
    assert messages[1]["role"] == "assistant"
    assert messages[1]["tool_calls"] is not None
    assert messages[1]["tool_calls"][0]["function"]["name"] == "get_current_weather"
    
    # Verify tool response
    assert messages[2]["role"] == "tool"
    assert messages[2]["tool_call_id"] == messages[1]["tool_calls"][0]["id"]
    tool_response = json.loads(messages[2]["content"])
    assert "result" in tool_response
    assert "temperature" in tool_response["result"]
    
    # Verify final response
    assert messages[3]["role"] == "assistant"
    final_response = messages[3]["content"].lower()
    assert "barcelona" in final_response
    assert any(term in final_response for term in ["weather", "temperature", "celsius", "fahrenheit"]) 