# tools/make_artifact.py
import os
import json
import uuid
import streamlit as st
from termcolor import cprint
import html

def execute(html_content):
    try:
        cprint("Starting artifact generation...", "blue")
        
        # Generate unique widget ID
        artifact_id = f"widget_{uuid.uuid4().hex[:8]}"
        
        # Parse the html_content from the arguments if it's a JSON string
        if isinstance(html_content, str) and html_content.startswith('{'):
            try:
                content_dict = json.loads(html_content)
                html_content = content_dict.get('html_content', '')
            except json.JSONDecodeError:
                pass
        
        # Don't escape the HTML - it's meant to be rendered
        complete_html = html_content  # Remove html.escape()
        
        # Create artifacts directory and save logic...
        
        return {
            "result": "Artifact generated successfully",
            "artifact_id": artifact_id,
            "artifact_html": complete_html
        }
    
    except Exception as e:
        cprint(f"Error in artifact generation: {str(e)}", "red")
        return {
            "error": f"Artifact generation failed: {str(e)}"
        }

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "make_artifact",
        "description": "Generate self-contained HTML artifacts (widgets) with embedded JavaScript and CSS",
        "parameters": {
            "type": "object",
            "properties": {
                "html_content": {
                    "type": "string",
                    "description": "The HTML content of the artifact"
                }
            },
            "required": ["html_content"]
        }
    }
}