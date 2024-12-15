# tools/file_write.py

import os
import json
import mimetypes
from fpdf import FPDF
import markdown
import tempfile
from pathlib import Path
import re
import json
from utils.file_utils import sanitize_path, is_safe_path

def count_words(content):
    """
    Count words in the given content.
    
    Args:
        content (str): The content to count words in
    
    Returns:
        int: Number of words
    """
    # Remove markdown/HTML tags if content is markdown
    if isinstance(content, str):
        # Remove markdown/HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'[*_`#\[\]()]', '', content)
        
        # Split by whitespace and filter out empty strings
        words = content.split()
        return len(words)
    return 0

def add_word_count_to_filename(filename, word_count):
    """
    Append word count to filename before the extension.
    
    Args:
        filename (str): Original filename
        word_count (int): Number of words in the content
    
    Returns:
        str: Filename with word count appended
    """
    # Split filename into base and extension
    base, ext = os.path.splitext(filename)
    
    # Remove any existing word count tag if present
    base = re.sub(r'\[wc_\d+\]$', '', base)
    
    # Append word count tag
    return f"{base}[wc_{word_count}]{ext}"

def execute(filename, content, create_dirs=False):
    """
    Writes content to a file, supporting multiple file types and optional directory creation.
    Calculates and appends word count to filename.
    
    Args:
        filename (str): Name of the file to write, including path and extension
        content (str): Content to write to the file
        create_dirs (bool): Whether to create intermediate directories if they don't exist
        
    Returns:
        str: Success or error message with updated filename
    """
    try:
        # Calculate word count before writing
        word_count = count_words(content)
        
        # Modify filename to include word count
        filename_with_wc = add_word_count_to_filename(filename, word_count)
        
        # Get the current working directory
        current_dir = os.getcwd()
        
        # Handle potential directory creation
        dir_path = os.path.dirname(filename_with_wc)
        if dir_path:
            full_dir_path = os.path.join(current_dir, sanitize_path(dir_path))
            if create_dirs:
                if not is_safe_path(full_dir_path, current_dir):
                    return "Error: Cannot create directories outside the current directory."
                os.makedirs(full_dir_path, exist_ok=True)
            elif not os.path.exists(full_dir_path):
                return f"Error: Directory '{dir_path}' does not exist. Set create_dirs=true to create it."

        safe_filename = os.path.join(sanitize_path(dir_path) if dir_path else "", 
                                   os.path.basename(filename_with_wc))
        filepath = os.path.join(current_dir, safe_filename)

        if not is_safe_path(filepath, current_dir):
            return "Error: Cannot write files outside the current directory."

        # Get file extension and mime type
        file_ext = os.path.splitext(filename_with_wc)[1].lower()
        mime_type = mimetypes.guess_type(filename_with_wc)[0]

        # Handle different file types with consistent word count appending
        if file_ext == '.pdf':
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                # Split content into lines and write to PDF
                max_line_length = 80  # Approximate characters per line
                lines = []
                current_line = ""
                
                words = content.split()
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_line_length:
                        current_line += word + " "
                    else:
                        lines.append(current_line)
                        current_line = word + " "
                if current_line:
                    lines.append(current_line)

                # Write lines to PDF
                for line in lines:
                    pdf.cell(0, 10, txt=line, ln=True)
                
                pdf.output(filepath)
                return f"PDF file '{safe_filename}' created successfully (Word count: {word_count})."
            except Exception as e:
                return f"Error creating PDF file: {str(e)}"

        elif file_ext == '.md':
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Markdown file '{safe_filename}' created successfully (Word count: {word_count})."
            except Exception as e:
                return f"Error writing Markdown file: {str(e)}"

        elif file_ext == '.json':
            try:
                # Ensure content is valid JSON
                if isinstance(content, str):
                    try:
                        json_content = json.loads(content)
                    except json.JSONDecodeError:
                        json_content = content
                else:
                    json_content = content

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(json_content, f, indent=2)
                return f"JSON file '{safe_filename}' created successfully (Word count: {word_count})."
            except Exception as e:
                return f"Error writing JSON file: {str(e)}"

        elif mime_type and mime_type.startswith('text/') or file_ext in ['.txt', '.py', '.csv']:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Text file '{safe_filename}' created successfully (Word count: {word_count})."
            except Exception as e:
                return f"Error writing text file: {str(e)}"

        else:
            return f"Error: Unsupported file type {file_ext}"

    except Exception as e:
        return f"Error writing file: {str(e)}"



TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "file_write",
        "description": (
            "Writes content to a file, supporting multiple file types (txt, pdf, md, json, py, csv) "
            "and optional directory creation. Use this tool to create or update files "
            "with specific content. Can create directories if they don't exist."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": (
                        "Name of the file to write, including path and extension. "
                        "Can include subdirectories, e.g., 'docs/report.pdf'"
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Content to write to the file. For PDFs, this will be formatted as text. "
                        "For JSON files, this should be valid JSON string or object."
                    )
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": (
                        "Whether to create intermediate directories if they don't exist. "
                        "Default is false."
                    ),
                    "default": False
                }
            },
            "required": ["filename", "content"]
        }
    }
}