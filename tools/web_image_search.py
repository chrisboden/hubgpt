# tools/web_image_search.py

import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import base64
import io
from io import BytesIO
import os
from termcolor import cprint
import json
from typing import List, Dict
from dotenv import load_dotenv
import uuid
import pathlib

# Load environment variables
load_dotenv()

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/images/search"

# Ensure temp/images directory exists
TEMP_DIR = pathlib.Path("temp/images")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def create_session_dirs(session_id: str) -> tuple[pathlib.Path, pathlib.Path]:
    """Create and return paths for temporary and permanent storage"""
    # Create temp working directory
    temp_dir = pathlib.Path("temp/images") / session_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create permanent storage directory
    data_dir = pathlib.Path("data/images")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return temp_dir, data_dir

def save_final_image(image_url: str, session_id: str, data_dir: pathlib.Path) -> str:
    """Download and save the final selected image to permanent storage"""
    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        
        # Determine file extension from the image format
        format_to_ext = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'WEBM': '.webm',
            'GIF': '.gif'
        }
        ext = format_to_ext.get(image.format, '.jpg')
        
        # Save to permanent location
        output_path = data_dir / f"{session_id}{ext}"
        image.save(output_path, format=image.format)
        
        # Return relative path from app root
        return str(pathlib.Path('data/images') / f"{session_id}{ext}")
        
    except Exception as e:
        cprint(f"Error saving final image: {str(e)}", "red")
        return None

def fetch_images(query: str, count: int = 12) -> List[Dict]:
    """Fetch images from Brave Search API with better error handling"""
    try:
        if not BRAVE_API_KEY:
            raise ValueError("BRAVE_API_KEY environment variable not set")

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        
        params = {
            "q": query,
            "count": min(count, 20),
            "safesearch": "strict",
            "search_lang": "en",
            "country": "us"
        }
        
        cprint(f"Fetching images for query: {query}", "blue")
        response = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params)
        
        print(f"Search results (raw):\n\n{response}")

        # Better error handling
        if response.status_code != 200:
            cprint(f"API Error: Status {response.status_code}", "red")
            cprint(f"Response: {response.text}", "red")
            return []
            
        data = response.json()
        if "results" not in data:
            cprint("No 'results' field in API response", "yellow")
            cprint(f"Response data: {data}", "yellow")
            return []
            
        return data["results"]
        
    except requests.RequestException as e:
        cprint(f"Request error: {str(e)}", "red")
        return []
    except json.JSONDecodeError as e:
        cprint(f"JSON decode error: {str(e)}", "red")
        return []
    except Exception as e:
        cprint(f"Unexpected error: {str(e)}", "red")
        return []

def generate_short_uuid() -> str:
    """Generate a short 5-character UUID"""
    return str(uuid.uuid4())[:5]

def download_image_with_size(thumbnail_url: str, full_url: str = None) -> tuple[Image.Image, tuple]:
    """Download an image from URL and return PIL Image object and its size. 
    Try thumbnail first, fallback to full URL if needed."""
    try:
        # Try thumbnail URL first
        response = requests.get(thumbnail_url, timeout=10)
        
        # If thumbnail fails, try full URL if provided
        if response.status_code == 404 and full_url:
            cprint(f"Thumbnail 404, trying full URL: {full_url}", "yellow")
            response = requests.get(full_url, timeout=10)
        
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        return img, img.size
        
    except requests.RequestException as e:
        cprint(f"Error downloading image: {str(e)}", "red")
        return None, None
    except Exception as e:
        cprint(f"Error processing image: {str(e)}", "red")
        return None, None

def save_search_results(images: List[Dict], session_id: str, temp_dir: pathlib.Path) -> List[Dict]:
    """Save search results as JSON with image sizes and thumbnails"""
    processed_results = []
    
    for img in images:
        # Download image with fallback to full URL
        image, size = download_image_with_size(
            thumbnail_url=img["thumbnail"]["src"],
            full_url=img["properties"]["url"]
        )
        size_str = f"{size[0]}x{size[1]}" if size else "unknown"
        
        processed_results.append({
            "url": img["properties"]["url"],
            "thumbnail": img["thumbnail"]["src"],
            "title": img["title"],
            "uuid": generate_short_uuid(),
            "size": size_str
        })
    
    # Save to session directory
    filename = temp_dir / f"{session_id}.json"
    with open(filename, 'w') as f:
        json.dump(processed_results, f, indent=4)
    
    return processed_results

def add_caption_to_image(image: Image.Image, caption: str) -> Image.Image:
    """Add caption below the image"""
    # Create new image with space for caption
    caption_height = 30
    new_img = Image.new('RGB', (image.width, image.height + caption_height), 'white')
    new_img.paste(image, (0, 0))
    
    # Add caption
    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype("Arial", 20)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text_width = draw.textlength(caption, font=font)
    x = (image.width - text_width) // 2
    y = image.height + 5
    
    draw.text((x, y), caption, fill='black', font=font)
    return new_img

def create_image_grid(processed_results: List[Dict], cols: int = 4) -> Image.Image:
    """Create a composite grid image from the list of image URLs with captions"""
    try:
        if not processed_results:
            return None

        # Download all images and add captions
        pil_images = []
        for img_data in processed_results:
            pil_img, _ = download_image_with_size(img_data["url"])
            if pil_img:
                if pil_img.mode in ('RGBA', 'P'):
                    pil_img = pil_img.convert('RGB')
                # Add caption with UUID
                caption = f"{img_data['uuid']} ({img_data['size']})"
                pil_img = add_caption_to_image(pil_img, caption)
                pil_images.append(pil_img)

        if not pil_images:
            return None

        # Calculate rows needed
        n_images = len(pil_images)
        rows = (n_images + cols - 1) // cols

        # Get max dimensions
        max_width = max(img.width for img in pil_images)
        max_height = max(img.height for img in pil_images)

        # Create the composite image
        grid_width = cols * max_width
        grid_height = rows * max_height
        grid_img = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))

        # Paste images into grid
        for idx, img in enumerate(pil_images):
            row = idx // cols
            col = idx % cols
            x = col * max_width + (max_width - img.width) // 2
            y = row * max_height + (max_height - img.height) // 2
            grid_img.paste(img, (x, y))

        return grid_img

    except Exception as e:
        cprint(f"Error creating image grid: {str(e)}", "red")
        return None

def get_llm_image_selection(grid_image_path: str, query: str, client) -> str:
    """Get LLM to select best image from grid"""
    try:
        cprint("Asking LLM to select best image...", "blue")
        
        # Extract session_id from grid_image_path
        # Path format is temp/images/session_id/session_id_grid.jpg
        session_id = pathlib.Path(grid_image_path).parent.name
        
        # Construct path to json results file
        json_path = pathlib.Path(grid_image_path).parent / f"{session_id}.json"
        
        # Read and encode the image
        with open(grid_image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        # Read the JSON results file
        with open(json_path) as f:
            json_results = f.read()
        
        # Construct the messages with base64 image
        messages = [
            {
                "role": "system",
                "content": "You are an expert image selector. You are given a grid of images to select from and an image brief. Below each image in the grid is a uuid. You select the image which best meets the brief by replying with the uuid of that image.\n\nYou must strictly reply with the following json format: {\n \"uuid\": \"the uuid of the image you have selected\",\n \"rationale\": \"your rationale for choosing this image over the others and why you think it best meets the brief\",\n \"caption\": \"a suggested caption to accompany the image\"\n}"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"The brief is: {query}.\n\nI have provided the grid of images for you to choose from. Here is the json version which includes caption, fyi {json_results}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    }
                ]
            }
        ]
        
        # Log the request
        cprint(f"Sending request to LLM with query: {query}", "blue")
        
        llm_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        # Log the raw response
        cprint(f"Raw LLM response: {llm_response}", "yellow")
        
        if not llm_response or not llm_response.choices:
            cprint("No valid response from LLM", "red")
            return None
            
        # Parse the JSON response
        response_content = json.loads(llm_response.choices[0].message.content)
        selected_uuid = response_content.get("uuid")
        rationale = response_content.get("rationale")
        caption = response_content.get("caption")
        
        cprint(f"Selected UUID: {selected_uuid}", "green")
        cprint(f"Rationale: {rationale}", "green")
        cprint(f"Caption: {caption}", "green")
        
        return response_content
        
    except Exception as e:
        cprint(f"Error in LLM image selection: {str(e)}", "red")
        cprint(f"Full error details: {repr(e)}", "red")
        return None

def execute(query: str = None, count: int = 12, llm_client=None, **kwargs) -> dict:
    """Execute image search and return markdown formatted results"""
    try:
        # Handle nested function data structure
        if isinstance(query, dict) and 'arguments' in query:
            args = query['arguments']
            if isinstance(args, dict):
                query = args.get('query')
                count = args.get('count', count)
        
        if not query:
            return {"result": "No query provided"}

        # Create session ID and directories
        session_id = str(uuid.uuid4())[:5]
        temp_dir, data_dir = create_session_dirs(session_id)
        cprint(f"Created session {session_id}", "blue")

        cprint(f"Processing query: {query} with count: {count}", "green")
        images = fetch_images(query, count)
        
        if not images:
            return {"result": "No images found for the given query."}

        # Save search results with session ID and temp_dir
        processed_results = save_search_results(images, session_id, temp_dir)
        results_path = temp_dir / f"{session_id}.json"
        
        # Create the composite grid image
        grid_image = create_image_grid(processed_results)
        
        if grid_image:
            # Save the grid image with session ID
            grid_path = temp_dir / f"{session_id}_grid.jpg"
            grid_image.save(grid_path, "JPEG")
            cprint(f"Saved grid image to {grid_path}", "green")
            
            # Create initial markdown output
            markdown = f"### Image Search Results for '{query}'\n\n"
            markdown += f"![Grid Image]({grid_path})\n\n"
            
            # Return early if no LLM client
            if not llm_client:
                cprint("No LLM client provided, skipping image selection", "yellow")
                return {
                    "result": markdown,
                    "grid_path": str(grid_path),
                    "processed_results": processed_results,
                    "direct_stream": False
                }
            
            try:
                selected = get_llm_image_selection(grid_path, query, llm_client)
                cprint(f"Selected image UUID: {selected}", "green")
                
                if selected:
                    # Find and highlight the selected image
                    selected_image = next((img for img in processed_results if img["uuid"] == selected["uuid"]), None)
                    if selected_image:
                        # Download and save final image
                        final_image_path = save_final_image(selected_image['url'], session_id, data_dir)
                        if final_image_path:
                            # Create simplified result message
                            result = (
                                f"The image selected is: {selected_image['url']}\n"  # Use cloud URL
                                f"Caption for the image is: {selected['caption']}\n"
                                f"Rationale for selection is: {selected['rationale']}\n"
                                f"Metadata stored at: temp/images/{session_id}"
                            )
                            
                            return {
                                "result": result,
                                "direct_stream": False
                            }
                        
                    return {"result": "Failed to save selected image"}
                
                return {"result": "No image was selected"}
            
            except Exception as llm_error:
                cprint(f"Error in LLM selection: {str(llm_error)}", "red")
                return {"result": f"Error in image selection: {str(llm_error)}"}
        
        return {"result": "Failed to create image grid"}
        
    except Exception as e:
        error_msg = f"Error in execute: {str(e)}"
        cprint(error_msg, "red")
        return {"result": error_msg}

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "web_image_search",
        "description": "Perform an image search to find the best matching image for a given user request",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for images. Make sure to take a deep breath and think carefully about what the user is trying to achieve with their brief, thenthink step by step about what image search query is likely to generate the most useful results"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of images to return (use default 10, max 20)"
                }
            },
            "required": ["query"]
        }
    }
}