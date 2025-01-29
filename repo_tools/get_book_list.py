#!/usr/bin/env python3

import json
import os
from pathlib import Path
from termcolor import colored

def get_book_list():
    try:
        # Get the absolute path to the files directory
        files_dir = Path(__file__).parent.parent / 'files'
        book_list = []
        
        # Recursively iterate through all files in the directory and subdirectories
        for file_path in files_dir.rglob('*.json'):
            try:
                print(colored(f"Processing {file_path.relative_to(files_dir)}...", "cyan"))
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        
                        # Handle both array and object structures
                        if isinstance(data, list) and len(data) > 0:
                            data = data[0]  # Get first object in array
                        
                        # Check if the data contains the required fields
                        if isinstance(data, dict) and 'author' in data and 'title' in data:
                            book_info = {
                                'author': data['author'],
                                'title': data['title']
                            }
                            book_list.append(book_info)
                            print(colored(f"Added: {book_info['title']} by {book_info['author']}", "green"))
                    except json.JSONDecodeError:
                        print(colored(f"Error: Could not parse JSON in {file_path.relative_to(files_dir)}", "red"))
                        continue
                    
            except Exception as e:
                print(colored(f"Error processing {file_path.relative_to(files_dir)}: {str(e)}", "red"))
                continue
        
        # Write the results to book_list.json
        output_path = Path(__file__).parent / 'book_list.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(book_list, f, indent=2)
        
        print(colored(f"\nProcessing complete! Results written to {output_path}", "green"))
        return book_list
        
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))
        return []

if __name__ == "__main__":
    get_book_list() 