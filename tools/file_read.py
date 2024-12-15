# tools/file_read.py

import os
import glob
import mimetypes
from PyPDF2 import PdfReader
import markdown
from bs4 import BeautifulSoup
from utils.file_utils import is_safe_path, sanitize_filename

def execute(filename):
    """
    Reads content from various file types including text, PDF, and Markdown.
    If exact filename is not found, tries to find files with matching wildcard pattern.
    Returns the content as a string, with appropriate formatting for Markdown files.
    """
    try:
        # Get the current working directory
        current_dir = os.getcwd()
        
        safe_filename = sanitize_filename(filename)
        filepath = os.path.join(current_dir, safe_filename)

        # If exact file doesn't exist, try wildcard search
        if not os.path.exists(filepath):
            # Create a wildcard pattern 
            wildcard_pattern = os.path.join(current_dir, f"{os.path.splitext(safe_filename)[0]}*{os.path.splitext(safe_filename)[1]}")
            matching_files = glob.glob(wildcard_pattern)
            
            if not matching_files:
                return f"Error: No file found matching {filename}"
            
            # Use the first matching file
            filepath = matching_files[0]

        if not is_safe_path(filepath, current_dir):
            return "Error: Cannot read files outside the current directory."

        # Get file extension and mime type
        file_ext = os.path.splitext(filepath)[1].lower()
        mime_type = mimetypes.guess_type(filepath)[0]

        # Handle different file types
        if file_ext == '.pdf':
            try:
                with open(filepath, 'rb') as file:
                    pdf_reader = PdfReader(file)
                    content = []
                    for page in pdf_reader.pages:
                        content.append(page.extract_text())
                return '\n'.join(content)
            except Exception as e:
                return f"Error reading PDF file: {str(e)}"

        elif file_ext == '.md':
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                    # Convert markdown to HTML
                    html = markdown.markdown(md_content)
                    # Convert HTML to plain text while preserving basic formatting
                    soup = BeautifulSoup(html, 'html.parser')
                    # Replace some HTML elements with text equivalents
                    for br in soup.find_all('br'):
                        br.replace_with('\n')
                    for hr in soup.find_all('hr'):
                        hr.replace_with('\n---\n')
                    # Get text while preserving some formatting
                    text = soup.get_text('\n', strip=True)
                    return text
            except Exception as e:
                return f"Error reading Markdown file: {str(e)}"

        elif mime_type and mime_type.startswith('text/') or file_ext in ['.txt', '.py', '.json', '.csv']:
            # Handle text-based files
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()

        else:
            return f"Error: Unsupported file type {file_ext}"

    except Exception as e:
        return f"Error reading file: {str(e)}"


TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "file_read",
        "description": (
            "Reads and returns the content of a specified file. "
            "Use this tool to access the contents of scripts, data files, or any text-based file, including pdf, md, txt. "
            "When the user's instruction is fuzzy, you should follow your curiosity to read files that could potentially help you learn more about the task. "
            "This is useful when you need to analyze existing code, extract information, or incorporate content into your responses or decision-making processes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": (
                        "Name of the file to read, including its extension. "
                        "Ensure the file exists and is accessible."
                    )
                }
            },
            "required": ["filename"]
        }
    }
}