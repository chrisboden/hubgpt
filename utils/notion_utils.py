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
        self.api_key = os.getenv('NOTION_API_KEY')
        if not self.api_key:
            raise ValueError("NOTION_API_KEY not found in environment variables")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"

    def fetch_block_children(self, block_id: str, start_cursor: Optional[str] = None) -> Dict:
        """Fetches children of a given block, handling pagination."""
        try:
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            response = requests.get(
                f"{self.base_url}/blocks/{block_id}/children",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            cprint(f"Error fetching block children: {str(e)}", "red")
            raise

    def get_page_content(self, page_id: str) -> str:
        """Fetches and formats the content of a Notion page."""
        try:
            all_blocks = []
            start_cursor = None

            while True:
                response = self.fetch_block_children(page_id, start_cursor)
                all_blocks.extend(response.get("results", []))
                if not response.get("has_more"):
                    break
                start_cursor = response.get("next_cursor")

            page_content = []
            for block in all_blocks:
                block_type = block.get("type", "")
                if block_type in ["paragraph", "bulleted_list_item", "numbered_list_item"]:
                    block_text = self._get_block_text(block, block_type)
                    if block_type == "bulleted_list_item":
                        page_content.append(f"* {block_text}")
                    elif block_type == "numbered_list_item":
                        page_content.append(f"1. {block_text}")
                    else:
                        page_content.append(block_text)

            return '\n'.join(page_content).strip()
        except Exception as e:
            cprint(f"Error getting page content: {str(e)}", "red")
            raise

    def create_page(self, parent_id: str, title: str, markdown_body: str) -> Dict:
        """Creates a new page in Notion with the given title and content."""
        try:
            notion_blocks = self._markdown_to_notion_blocks(markdown_body)
            data = {
                "parent": {"page_id": parent_id},
                "properties": {
                    "title": {"title": [{"type": "text", "text": {"content": title}}]}
                },
                "children": notion_blocks
            }

            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            cprint(f"Successfully created page: {title}", "green")
            return response.json()
        except requests.exceptions.RequestException as e:
            cprint(f"Error creating page: {str(e)}", "red")
            raise

    @staticmethod
    def _get_block_text(block: Dict, block_type: str) -> str:
        """Extracts text from a single block based on its type."""
        text_items = block.get(block_type, {}).get("rich_text", [])
        return ''.join(
            item['text']['content'] 
            for item in text_items 
            if item['type'] == 'text'
        )

    def _parse_markdown_table(self, table_text: str) -> List[Dict[str, Any]]:
        """Converts a markdown table to Notion table blocks."""
        # Clean up the table text and split into lines
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        if len(lines) < 2:
            return []

        # Parse header
        header_cells = [
            cell.strip().strip('|').strip() 
            for cell in lines[0].split('|') 
            if cell.strip()
        ]

        # Skip separator line and parse data rows
        data_rows = []
        for line in lines[2:]:  # Skip the separator line
            if '|' in line:  # Ensure it's a table row
                cells = [
                    cell.strip().strip('|').strip() 
                    for cell in line.split('|') 
                    if cell.strip()
                ]
                if cells:  # Only add non-empty rows
                    data_rows.append(cells)

        # Create table block
        table_block = {
            "type": "table",
            "table": {
                "table_width": len(header_cells),
                "has_column_header": True,
                "has_row_header": False,
                "children": []
            }
        }

        # Add header row
        header_row = {
            "type": "table_row",
            "table_row": {
                "cells": [[{"type": "text", "text": {"content": cell}}] for cell in header_cells]
            }
        }
        table_block["table"]["children"].append(header_row)

        # Add data rows
        for row in data_rows:
            # Ensure row has the same number of cells as header
            while len(row) < len(header_cells):
                row.append("")  # Pad with empty cells if necessary
            
            row_block = {
                "type": "table_row",
                "table_row": {
                    "cells": [[{"type": "text", "text": {"content": cell}}] for cell in row[:len(header_cells)]]
                }
            }
            table_block["table"]["children"].append(row_block)

        return [table_block]

    def _markdown_to_notion_blocks(self, markdown_text: str) -> List[Dict[str, Any]]:
        """Converts Markdown text to Notion blocks."""
        markdown_text = markdown_text.replace('\\n', '\n')
        blocks = []
        
        # Split content into sections
        sections = re.split(r'(\n\|[^\n]*\n\|[-|\s]*\n(?:\|[^\n]*\n)*)', markdown_text, flags=re.DOTALL)
        
        for section in sections:
            if not section.strip():
                continue
            
            # Check if this section is a table
            if section.strip().startswith('|') and '|' in section:
                table_blocks = self._parse_markdown_table(section)
                blocks.extend(table_blocks)
                continue

            # Handle non-table content
            lines = section.strip().split('\n')
            current_block = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Handle headings
                heading_match = re.match(r'^(#{1,3})\s+(.+)$', line)
                if heading_match:
                    level = len(heading_match.group(1))
                    content = heading_match.group(2).strip()
                    blocks.append({
                        "type": f"heading_{level}",
                        f"heading_{level}": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": content}
                            }]
                        }
                    })
                    continue

                # Handle regular paragraphs
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line}
                        }]
                    }
                })

        return blocks