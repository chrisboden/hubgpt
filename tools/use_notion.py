# tools/use_notion.py

from utils.notion_utils import NotionClient
from typing import Optional, Dict, Any
from utils.ui_utils import update_spinner_status

def execute(llm_client=None, operation: str = None, page_id: str = None, title: str = None, content: str = None) -> str:
    """
    Interact with Notion pages - create new pages or fetch content from existing pages.

    Parameters:
    - operation (str): The operation to perform ("create_page" or "fetch_content")
    - page_id (str): The Notion page ID (parent ID for creation, target ID for fetching)
    - title (str): The title for the new page (only for create_page operation)
    - content (str): The markdown content for the new page (only for create_page operation)
    - llm_client (optional): An LLM client for generating additional context if needed

    Returns:
    - str: A user-friendly message describing the result of the operation
    """
    try:
        update_spinner_status("Using the Notion tool")
        notion = NotionClient()

        if operation == "create_page":
            if not all([page_id, title, content]):
                return "The page was not created because page_id, title, and content are all required"
            
            update_spinner_status("Creating new page in Notion...")
            response = notion.create_page(
                parent_id=page_id,
                title=title,
                markdown_body=content
            )
            page_url = response.get("url", "URL not available")
            update_spinner_status(f"Successfully created page: {title}")
            return f"The page was successfully created with a title of '{title}' and can be viewed here: {page_url}"

        elif operation == "fetch_content":
            if not page_id:
                return "The page was not fetched because page_id is required"
            
            update_spinner_status("Fetching content from Notion page...")
            content = notion.get_page_content(page_id)
            update_spinner_status("Successfully fetched page content")
            return f"The page was successfully fetched. The contents is as follows:\n\n{content}"

        else:
            return f"The operation failed because '{operation}' is not a valid operation. Use 'create_page' or 'fetch_content'."

    except Exception as e:
        error_msg = str(e)
        update_spinner_status(f"Error: {error_msg}")
        if operation == "create_page":
            return f"The page was not created because: {error_msg}"
        else:
            return f"The page was not fetched due to the following error: {error_msg}"

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_notion",
        "description": "The use_notion tool allows you to interact with Notion by either creating new pages or fetching existing page content.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Specify the action to perform: 'create_page' to add a new page or 'fetch_content' to retrieve content from an existing page.",
                    "enum": ["create_page", "fetch_content"]
                },
                "page_id": {
                    "type": "string",
                    "description": "The unique identifier for the Notion page. Required for both creating and fetching content. Use the default if not specified: '6aa23cc62c2e4a3cbda8d8e7cfc9b5ca' for notes, '15ecd0ff08558020a58cd4b48a9b4d34' for advice.",
                    "enum": [
                        "15ecd0ff08558020a58cd4b48a9b4d34", "6aa23cc62c2e4a3cbda8d8e7cfc9b5ca"
                    ],
                    "default": "15ecd0ff08558020a58cd4b48a9b4d34"
                },
                "title": {
                    "type": "string",
                    "description": "The title for the new page. Required when creating a new page. Generate a title based on the content to be added."
                },
                "content": {
                    "type": "string",
                    "description": "The markdown content for the new page. Required when creating a new page. Create content based on the user's instructions."
                }
            },
            "required": ["operation", "page_id"]
        }
    },
    "direct_stream": True
}