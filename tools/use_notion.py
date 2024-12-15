# tools/use_notion.py

from utils.notion_utils import NotionClient
from typing import Optional, Dict, Any

def execute(llm_client=None, operation: str = None, page_id: str = None, title: str = None, content: str = None) -> Dict[str, Any]:
    """
    Interact with Notion pages - create new pages or fetch content from existing pages.

    Parameters:
    - operation (str): The operation to perform ("create_page" or "fetch_content")
    - page_id (str): The Notion page ID (parent ID for creation, target ID for fetching)
    - title (str): The title for the new page (only for create_page operation)
    - content (str): The markdown content for the new page (only for create_page operation)
    - llm_client (optional): An LLM client for generating additional context if needed

    Returns:
    - dict: A dictionary with the operation results and relevant information
    """
    try:
        print("Using the Notion tool")
        notion = NotionClient()
        result = {
            "operation": operation,
            "success": False,
            "message": ""
        }

        if operation == "create_page":
            if not all([page_id, title, content]):
                raise ValueError("page_id, title, and content are required for create_page operation")
            
            response = notion.create_page(
                parent_id=page_id,
                title=title,
                markdown_body=content
            )
            result.update({
                "success": True,
                "message": f"Successfully created page: {title}",
                "page_data": response
            })

        elif operation == "fetch_content":
            if not page_id:
                raise ValueError("page_id is required for fetch_content operation")
            
            content = notion.get_page_content(page_id)
            result.update({
                "success": True,
                "message": "Successfully fetched page content",
                "content": content
            })

        else:
            raise ValueError(f"Unsupported operation: {operation}")

        return result

    except Exception as e:
        return {
            "operation": operation,
            "success": False,
            "message": f"Error: {str(e)}"
        }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "use_notion",
        "description": "This tool enables you to create pages in Notion using content you generate. It also allows you to fetch page content from Notion.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation is the action you wish to perform with Notion to either fetch Notion page content or create page content",
                    "enum": ["create_page", "fetch_content"]
                },
                "page_id": {
                    "type": "string",
                    "description": "The Notion page ID identifies the page that is either being fetched or having content appended to it (parent ID for creation, target ID for fetching)"
                },
                "title": {
                    "type": "string",
                    "description": "The title for the new page you are creating (only for create_page operation)"
                },
                "content": {
                    "type": "string",
                    "description": "The markdown content to be added for the new page (only for create_page operation)"
                }
            },
            "required": ["operation", "page_id"]
        }
    }
}