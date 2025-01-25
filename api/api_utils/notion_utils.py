# utils/notion_utils.py

import os
import re
from typing import List, Dict, Optional, Any
import requests
from dotenv import load_dotenv
from termcolor import cprint

# Load environment variables
load_dotenv()

class NotionClient:
    """A client for interacting with the Notion API."""
    
    def __init__(self):
        # Retrieve the NOTION_API_KEY from environment variables
        self.api_key = os.getenv('NOTION_API_KEY')
        # Raise an error if the API key is not found
        if not self.api_key:
            raise ValueError("NOTION_API_KEY not found in environment variables")
        
        # Set up the headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        # Define the base URL for the Notion API
        self.base_url = "https://api.notion.com/v1"

    def fetch_block_children(self, block_id: str, start_cursor: Optional[str] = None) -> Dict:
        """
        Fetches children of a given block, handling pagination.

        :param block_id: The ID of the block whose children are to be fetched.
        :param start_cursor: The cursor to start fetching from, used for pagination.
        :return: A dictionary containing the block children.
        """
        try:
            # Set up the parameters for the API request
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            # Make the GET request to fetch block children
            response = requests.get(
                f"{self.base_url}/blocks/{block_id}/children",
                headers=self.headers,
                params=params
            )
            # Raise an exception if the request was unsuccessful
            response.raise_for_status()
            # Return the JSON response
            return response.json()
        except requests.exceptions.RequestException as e:
            # Print an error message if an exception occurs
            cprint(f"Error fetching block children: {str(e)}", "red")
            raise

    def get_page_content(self, page_id: str) -> str:
        """
        Fetches and formats the content of a Notion page.

        :param page_id: The ID of the page to fetch content from.
        :return: A string containing the formatted page content.
        """
        try:
            # Initialize a list to store all blocks and a cursor for pagination
            all_blocks = []
            start_cursor = None

            # Loop to fetch all blocks, handling pagination
            while True:
                # Fetch block children using the fetch_block_children method
                response = self.fetch_block_children(page_id, start_cursor)
                # Extend the list of all blocks with the fetched results
                all_blocks.extend(response.get("results", []))
                # Check if there are more blocks to fetch
                if not response.get("has_more"):
                    break
                # Update the cursor for the next page of results
                start_cursor = response.get("next_cursor")

            # Initialize a list to store the formatted page content
            page_content = []
            # Loop through each block to extract and format text
            for block in all_blocks:
                # Get the type of the block
                block_type = block.get("type", "")
                # Check if the block is a paragraph, bulleted list item, or numbered list item
                if block_type in ["paragraph", "bulleted_list_item", "numbered_list_item"]:
                    # Extract text from the block
                    block_text = self._get_block_text(block, block_type)
                    # Format the text based on the block type and add to page content
                    if block_type == "bulleted_list_item":
                        page_content.append(f"* {block_text}")
                    elif block_type == "numbered_list_item":
                        page_content.append(f"1. {block_text}")
                    else:
                        page_content.append(block_text)

            # Join the page content into a single string and return it
            return '\n'.join(page_content).strip()
        except Exception as e:
            # Print an error message if an exception occurs
            cprint(f"Error getting page content: {str(e)}", "red")
            raise

    def create_page(self, parent_id: str, title: str, markdown_body: str) -> Dict:
        """
        Creates a new page in Notion with the given title and content.

        :param parent_id: The ID of the parent page where the new page will be created.
        :param title: The title of the new page.
        :param markdown_body: The content of the new page in Markdown format.
        :return: A dictionary containing the response from the Notion API.
        """
        try:
            # Convert the Markdown content to Notion blocks
            notion_blocks = self._markdown_to_notion_blocks(markdown_body)
            # Set up the data payload for the API request
            data = {
                "parent": {"page_id": parent_id},
                "properties": {
                    "title": {"title": [{"type": "text", "text": {"content": title}}]}
                },
                "children": notion_blocks
            }

            # Make the POST request to create a new page
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=data
            )
            # Raise an exception if the request was unsuccessful
            response.raise_for_status()
            # Print a success message
            cprint(f"Successfully created page: {title}", "green")
            # Return the JSON response
            return response.json()
        except requests.exceptions.RequestException as e:
            # Print an error message if an exception occurs
            cprint(f"Error creating page: {str(e)}", "red")
            raise

    @staticmethod
    def _get_block_text(block: Dict, block_type: str) -> str:
        """
        Extracts text from a single block based on its type.

        :param block: The block from which to extract text.
        :param block_type: The type of the block.
        :return: A string containing the extracted text.
        """
        # Retrieve the rich text items from the block
        text_items = block.get(block_type, {}).get("rich_text", [])
        # Join the text content of the items and return it
        return ''.join(
            item['text']['content'] 
            for item in text_items 
            if item['type'] == 'text'
        )

    def _parse_markdown_table(self, table_text: str) -> List[Dict[str, Any]]:
        """
        Converts a markdown table to Notion table blocks.

        :param table_text: The markdown text representing the table.
        :return: A list of dictionaries representing the Notion table blocks.
        """
        # Clean up the table text and split into lines
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        # Return an empty list if there are fewer than 2 lines
        if len(lines) < 2:
            return []

        # Parse the header cells from the first line
        header_cells = [
            cell.strip().strip('|').strip() 
            for cell in lines[0].split('|') 
            if cell.strip()
        ]

        # Initialize a list to store data rows
        data_rows = []
        # Loop through the lines starting from the third line (skipping the separator line)
        for line in lines[2:]:  # Skip the separator line
            # Ensure the line contains a table row
            if '|' in line:
                # Split the line into cells and strip whitespace
                cells = [
                    cell.strip().strip('|').strip() 
                    for cell in line.split('|') 
                    if cell.strip()
                ]
                # Add the row to data rows if it's not empty
                if cells:
                    data_rows.append(cells)

        # Create a dictionary to represent the table block
        table_block = {
            "type": "table",
            "table": {
                "table_width": len(header_cells),
                "has_column_header": True,
                "has_row_header": False,
                "children": []
            }
        }

        # Create a dictionary to represent the header row
        header_row = {
            "type": "table_row",
            "table_row": {
                "cells": [[{"type": "text", "text": {"content": cell}}] for cell in header_cells]
            }
        }
        # Add the header row to the table block
        table_block["table"]["children"].append(header_row)

        # Loop through each data row to create table row blocks
        for row in data_rows:
            # Ensure the row has the same number of cells as the header
            while len(row) < len(header_cells):
                row.append("")  # Pad with empty cells if necessary
            
            # Create a dictionary to represent the data row
            row_block = {
                "type": "table_row",
                "table_row": {
                    "cells": [[{"type": "text", "text": {"content": cell}}] for cell in row[:len(header_cells)]]
                }
            }
            # Add the data row to the table block
            table_block["table"]["children"].append(row_block)

        # Return the table block as a list
        return [table_block]

    def _markdown_to_notion_blocks(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        Converts Markdown text to Notion blocks.

        :param markdown_text: The Markdown text to convert.
        :return: A list of dictionaries representing the Notion blocks.
        """
        # Replace escaped newlines with actual newlines
        markdown_text = markdown_text.replace('\\n', '\n')
        # Initialize a list to store the Notion blocks
        blocks = []
        
        # Split the Markdown text into sections, separating tables
        sections = re.split(r'(\n\|[^\n]*\n\|[-|\s]*\n(?:\|[^\n]*\n)*)', markdown_text, flags=re.DOTALL)
        
        # Loop through each section
        for section in sections:
            # Skip empty sections
            if not section.strip():
                continue
            
            # Check if the section is a table
            if section.strip().startswith('|') and '|' in section:
                # Convert the table section to Notion blocks
                table_blocks = self._parse_markdown_table(section)
                # Extend the blocks list with the table blocks
                blocks.extend(table_blocks)
                continue

            # Handle non-table content
            lines = section.strip().split('\n')
            current_block = None
            
            # Loop through each line in the section
            for line in lines:
                line = line.strip()
                # Skip empty lines
                if not line:
                    continue

                # Check if the line is a heading
                heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
                if heading_match:
                    # Determine the heading level and content
                    level = len(heading_match.group(1))
                    content = heading_match.group(2).strip()
                    if level <= 3:
                        # Create a dictionary to represent the heading block
                        blocks.append({
                            "type": f"heading_{level}",
                            f"heading_{level}": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": content}
                                }]
                            }
                        })
                    else:
                        # Convert h4 to bold text in a paragraph
                        blocks.append({
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": content},
                                    "annotations": {"bold": True}
                                }]
                            }
                        })
                    continue

                # Handle regular paragraphs
                # Create a dictionary to represent the paragraph block

                def process_text_with_bold(text):
                    # Split text by bold markers
                    parts = re.split(r'(\*\*.*?\*\*)', text)
                    rich_text = []
                    
                    for part in parts:
                        if part.startswith('**') and part.endswith('**'):
                            # Handle bold text
                            content = part[2:-2]  # Remove ** markers
                            rich_text.append({
                                "type": "text",
                                "text": {"content": content},
                                "annotations": {"bold": True}
                            })
                        elif part.strip():
                            # Handle regular text
                            rich_text.append({
                                "type": "text",
                                "text": {"content": part}
                            })
                    
                    return rich_text
                
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": process_text_with_bold(line)
                    }
                })

                return blocks

        # Return the list of Notion blocks
        return blocks