# tools/make_book.py

import json
from termcolor import colored
import asyncio
from typing import Dict, List
import os
from datetime import datetime

SLEEP_BETWEEN_REQUESTS = 1  # Seconds to wait between API calls
MAX_PARALLEL_REQUESTS = 5  # Adjusted for API limits

# Add at top with other constants
ARTIFACTS_DIR = "data/books"

def save_artifact(book_id: str, stage: str, data: dict):
    """Save intermediate artifact to disk."""
    try:
        # Create artifacts directory structure
        book_dir = os.path.join(ARTIFACTS_DIR, book_id)
        os.makedirs(book_dir, exist_ok=True)
        
        # Save artifact with timestamp
        filename = f"{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(book_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        print(colored(f"✅ Saved {stage} artifact to {filepath}", "green"))
        
    except Exception as e:
        print(colored(f"⚠️ Failed to save {stage} artifact: {str(e)}", "yellow"))

async def get_book_outline(llm_client, topic: str) -> Dict:
    """Get detailed book outline using LLM."""
    print(colored("🎯 Generating detailed book outline...", "cyan"))
    
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
    
    outline = json.loads(response.choices[0].message.content)
    print(colored("✅ Book outline generated!", "green"))
    return outline

async def research_chapter(llm_client, chapter: Dict) -> Dict:
    """Research a single chapter using LLM."""
    print(colored(f"🔍 Researching chapter: {chapter['title']}", "yellow"))
    
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
    
    return {
        "title": chapter["title"],
        "research_data": response.choices[0].message.content
    }

async def write_chapter(llm_client, chapter_title: str, research_data: str) -> str:
    """Write a chapter using LLM with research context."""
    print(colored(f"✍️ Writing chapter: {chapter_title}", "magenta"))
    
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
    
    return response.choices[0].message.content

async def process_chapters_in_batches(llm_client, chapters: List[Dict]) -> List[Dict]:
    """Process chapters in parallel batches."""
    results = []
    for i in range(0, len(chapters), MAX_PARALLEL_REQUESTS):
        batch = chapters[i:i + MAX_PARALLEL_REQUESTS]
        batch_results = await asyncio.gather(
            *(research_chapter(llm_client, chapter) for chapter in batch)
        )
        results.extend(batch_results)
        await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)
    return results

def format_book_content(title: str, chapters: List[Dict]) -> str:
    """Format the book content with markdown."""
    content = f"# {title}\n\n"
    for idx, chapter in enumerate(chapters, 1):
        content += f"## Chapter {idx}: {chapter['title']}\n\n"
        content += f"{chapter['content']}\n\n"
    return content

# Modify generate_book function
async def generate_book(llm_client, topic: str, output_file: str) -> Dict:
    """Main function to create the book."""
    try:
        # Create unique book ID
        book_id = f"{topic.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate outline
        outline = await get_book_outline(llm_client, topic)
        save_artifact(book_id, "outline", outline)
        
        # Research chapters
        print(colored("📚 Starting parallel research for chapters...", "blue"))
        researched_chapters = await process_chapters_in_batches(llm_client, outline["chapters"])
        save_artifact(book_id, "research", {
            "title": outline["title"],
            "chapters": researched_chapters
        })
        
        # Write chapters
        written_chapters = []
        for research in researched_chapters:
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
            save_artifact(book_id, f"chapter_{len(written_chapters)}", {
                "title": research["title"],
                "content": chapter_content
            })
        
        # Format and save final book
        book_content = format_book_content(outline["title"], written_chapters)
        
        # Save final version
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
            
        return {
            "title": outline["title"],
            "file_path": output_file,
            "num_chapters": len(written_chapters),
            "content": book_content,
            "artifacts_dir": os.path.join(ARTIFACTS_DIR, book_id)
        }
        
    except Exception as e:
        print(colored(f"❌ Error generating book: {str(e)}", "red"))
        raise

def execute(llm_client=None, topic=None, output_file="book.md", **kwargs):
    """Execute the make_book tool."""
    if not topic:
        return {"error": "Topic is required"}
        
    if not llm_client:
        return {"error": "LLM client is required"}
    
    try:
        # Create event loop and run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_book(llm_client, topic, output_file))
        loop.close()
        
        return {
            "result": f"Book generated successfully: {result['title']}",
            "file_path": result["file_path"],
            "num_chapters": result["num_chapters"],
            "content": result["content"]
        }
        
    except Exception as e:
        return {"error": f"Failed to generate book: {str(e)}"}

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