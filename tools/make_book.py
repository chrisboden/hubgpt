# tools/make_book.py

import json
from termcolor import colored
import asyncio
from typing import Dict, List
import os
from datetime import datetime
from utils.ui_utils import update_spinner_status  # Add spinner status import

# Configuration constants for API request management
SLEEP_BETWEEN_REQUESTS = 1  # Seconds to wait between API calls to prevent rate limiting
MAX_PARALLEL_REQUESTS = 5  # Maximum number of concurrent API requests to manage resource usage

# Define the base directory for storing book generation artifacts
ARTIFACTS_DIR = "data/books"

def save_artifact(book_id: str, stage: str, data: dict):
    """
    Save intermediate book generation artifacts to disk for tracking and debugging.
    
    Args:
        book_id (str): Unique identifier for the book being generated
        stage (str): Current stage of book generation (e.g., 'outline', 'research')
        data (dict): Data to be saved as a JSON artifact
    
    Purpose:
    - Creates a structured directory for each book's artifacts
    - Saves timestamped JSON files for each generation stage
    - Provides visibility into the book generation process
    """
    try:
        # Create artifacts directory structure
        book_dir = os.path.join(ARTIFACTS_DIR, book_id)
        os.makedirs(book_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        filename = f"{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(book_dir, filename)
        
        # Write artifact data to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        print(colored(f"✅ Saved {stage} artifact to {filepath}", "green"))
        update_spinner_status(f"Saved {stage} artifact to {filepath}")
        
    except Exception as e:
        print(colored(f"⚠️ Failed to save {stage} artifact: {str(e)}", "yellow"))
        update_spinner_status(f"Failed to save {stage} artifact: {str(e)}")

async def get_book_outline(llm_client, topic: str) -> Dict:
    """
    Generate a comprehensive book outline using a language model.
    
    Args:
        llm_client: Language model client for generating outline
        topic (str): Main subject of the book
    
    Returns:
        Dict: Structured book outline with chapters and research questions
    
    Key Steps:
    - Uses a specialized prompt to generate a JSON-formatted book outline
    - Ensures consistent structure for further processing
    """
    print(colored("🎯 Generating detailed book outline...", "cyan"))
    update_spinner_status(f"Generating book outline for topic: {topic}")
    
    response = llm_client.chat.completions.create(
        model="x-ai/grok-2-1212",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional book outline creator. Create a detailed book outline with "
                    "chapters and research questions for each chapter. Return as JSON with format: "
                    "{'title': str, 'chapters': [{'title': str, 'description': str, "
                    "'research_questions': [str]}]}"
                )
            },
            {"role": "user", "content": f"Create a detailed book outline about: {topic}"}
        ]
    )
    
    # Parse and return the generated outline
    outline = json.loads(response.choices[0].message.content)
    print(colored("✅ Book outline generated!", "green"))
    update_spinner_status(f"Book outline generated with {len(outline.get('chapters', [])) or 0} chapters")
    return outline

async def research_chapter(llm_client, chapter: Dict) -> Dict:
    """
    Conduct research for a specific book chapter.
    
    Args:
        llm_client: Language model client for research
        chapter (Dict): Chapter details including title and research questions
    
    Returns:
        Dict: Researched information for the chapter
    
    Purpose:
    - Aggregate research for each chapter using targeted research questions
    - Provides context for subsequent chapter writing
    """
    print(colored(f"🔍 Researching chapter: {chapter['title']}", "yellow"))
    update_spinner_status(f"Researching chapter: {chapter['title']}")
    
    # Combine research questions into a single research prompt
    questions = " ".join(chapter["research_questions"])
    response = llm_client.chat.completions.create(
        model="perplexity/llama-3.1-sonar-huge-128k-online",
        messages=[
            {
                "role": "system", 
                "content": "You are a thorough researcher. Provide detailed, factual answers."
            },
            {
                "role": "user",
                "content": f"Research and provide detailed information for: {questions}"
            }
        ]
    )
    
    update_spinner_status(f"Research completed for chapter: {chapter['title']}")
    return {
        "title": chapter["title"],
        "research_data": response.choices[0].message.content
    }

async def write_chapter(llm_client, chapter_title: str, research_data: str) -> str:
    """
    Write a book chapter using research data and language model.
    
    Args:
        llm_client: Language model client for writing
        chapter_title (str): Title of the chapter
        research_data (str): Researched information to inform chapter writing
    
    Returns:
        str: Generated chapter content
    
    Purpose:
    - Transform research into a coherent, engaging chapter
    - Leverage research context for more accurate content generation
    """
    print(colored(f"✍️ Writing chapter: {chapter_title}", "magenta"))
    update_spinner_status(f"Writing chapter: {chapter_title}")
    
    response = llm_client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a professional book writer. Write an engaging and informative chapter."
            },
            {
                "role": "user",
                "content": f"Write a chapter titled '{chapter_title}' based on this research:\n{research_data}"
            }
        ]
    )
    
    update_spinner_status(f"Chapter writing completed: {chapter_title}")
    return response.choices[0].message.content

async def process_chapters_in_batches(llm_client, chapters: List[Dict]) -> List[Dict]:
    """
    Process book chapters in parallel batches to manage API resources.
    
    Args:
        llm_client: Language model client
        chapters (List[Dict]): List of chapters to process
    
    Returns:
        List[Dict]: Researched chapters
    
    Key Features:
    - Implements controlled parallel processing
    - Prevents overwhelming API with too many simultaneous requests
    - Adds small delay between batches to respect rate limits
    """
    results = []
    for i in range(0, len(chapters), MAX_PARALLEL_REQUESTS):
        batch = chapters[i:i + MAX_PARALLEL_REQUESTS]
        update_spinner_status(f"Processing chapter batch {i//MAX_PARALLEL_REQUESTS + 1}")
        batch_results = await asyncio.gather(
            *(research_chapter(llm_client, chapter) for chapter in batch)
        )
        results.extend(batch_results)
        await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)
    return results

def format_book_content(title: str, chapters: List[Dict]) -> str:
    """
    Format book chapters into a markdown document.
    
    Args:
        title (str): Book title
        chapters (List[Dict]): List of processed chapters
    
    Returns:
        str: Formatted markdown book content
    
    Purpose:
    - Create a structured, readable markdown document
    - Number chapters sequentially
    - Prepare content for file output
    """
    update_spinner_status(f"Formatting book content: {title}")
    content = f"# {title}\n\n"
    for idx, chapter in enumerate(chapters, 1):
        content += f"## Chapter {idx}: {chapter['title']}\n\n"
        content += f"{chapter['content']}\n\n"
    return content

async def generate_book(llm_client, topic: str, output_file: str) -> Dict:
    """
    Orchestrate the entire book generation process.
    
    Args:
        llm_client: Language model client
        topic (str): Book topic
        output_file (str): Path to save generated book
    
    Returns:
        Dict: Book generation results and metadata
    
    Workflow:
    1. Generate book outline
    2. Research chapters in parallel
    3. Write chapters using research
    4. Format and save book
    5. Save artifacts for tracking
    """
    try:
        # Create unique book ID for artifact tracking
        book_id = f"{topic.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        update_spinner_status(f"Starting book generation: {topic}")
        
        # Generate outline
        print(colored("🎯 Generating detailed book outline...", "cyan"))
        outline = await get_book_outline(llm_client, topic)
        save_artifact(book_id, "outline", outline)
        
        # Research chapters
        print(colored("📚 Starting parallel research for chapters...", "blue"))
        update_spinner_status(f"Researching {len(outline['chapters'])} chapters")
        researched_chapters = await process_chapters_in_batches(llm_client, outline["chapters"])
        save_artifact(book_id, "research", {
            "title": outline["title"],
            "chapters": researched_chapters
        })
        
        # Write chapters
        written_chapters = []
        for idx, research in enumerate(researched_chapters, 1):
            update_spinner_status(f"Writing chapter {idx} of {len(researched_chapters)}")
            chapter_content = await write_chapter(
                llm_client,
                research["title"],
                research["research_data"]
            )
            written_chapters.append({
                "title": research["title"],
                "content": chapter_content
            })
            # Save each chapter as it's completed
            save_artifact(book_id, f"chapter_{idx}", {
                "title": research["title"],
                "content": chapter_content
            })
        
        # Format and save final book
        update_spinner_status("Formatting final book content")
        book_content = format_book_content(outline["title"], written_chapters)
        
        # Save book to specified output file
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(book_content)
            
        # Save complete book data
        final_data = {
            "title": outline["title"],
            "file_path": output_file,
            "num_chapters": len(written_chapters),
            "outline": outline,
            "research": researched_chapters,
            "chapters": written_chapters
        }
        save_artifact(book_id, "final", final_data)
        
        update_spinner_status(f"Book generation completed: {outline['title']}")
            
        return {
            "title": outline["title"],
            "file_path": output_file,
            "num_chapters": len(written_chapters),
            "content": book_content,
            "artifacts_dir": os.path.join(ARTIFACTS_DIR, book_id)
        }
        
    except Exception as e:
        print(colored(f"❌ Error generating book: {str(e)}", "red"))
        update_spinner_status(f"Book generation failed: {str(e)}")
        raise

def execute(llm_client=None, topic=None, output_file="book.md", **kwargs):
    """
    Execute the book generation tool with error handling.
    
    Args:
        llm_client: Language model client (required)
        topic (str): Book topic (required)
        output_file (str): Path to save generated book
    
    Returns:
        Dict: Book generation result or error information
    
    Key Features:
    - Validates input requirements
    - Manages async event loop
    - Provides structured error and success responses
    """
    if not topic:
        update_spinner_status("Error: Topic is required")
        return {"error": "Topic is required"}
        
    if not llm_client:
        update_spinner_status("Error: LLM client is required")
        return {"error": "LLM client is required"}
    
    try:
        # Create event loop and run async function
        update_spinner_status("Initializing book generation process")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_book(llm_client, topic, output_file))
        loop.close()
        
        update_spinner_status(f"Book generated successfully: {result['title']}")
        return {
            "result": f"Book generated successfully: {result['title']}",
            "file_path": result["file_path"],
            "num_chapters": result["num_chapters"],
            "content": result["content"]
        }
        
    except Exception as e:
        update_spinner_status(f"Book generation failed: {str(e)}")
        return {"error": f"Failed to generate book: {str(e)}"}
    
# Metadata for tool registration and discovery
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "make_book",
        "description": "Generate a complete book with multiple chapters on any topic using AI. The tool handles research, writing, and formatting.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The main topic or subject for the book"
                },
                "output_file": {
                    "type": "string",
                    "description": "Optional: The output file path for the generated book (default: book.md)"
                }
            },
            "required": ["topic"]
        }
    }
}
