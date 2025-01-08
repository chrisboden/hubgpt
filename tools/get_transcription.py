# tools/get_transcription.py

import traceback
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from termcolor import cprint
from yt_dlp import YoutubeDL
import json
import duckdb
from pathlib import Path
from halo import Halo

def init_db():
    """Initialize the DuckDB database and create the transcripts table if it doesn't exist"""
    try:
        # Ensure the data directory exists
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Connect to DuckDB database
        db_path = data_dir / "transcripts.db"
        conn = duckdb.connect(str(db_path))
        
        # Create table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                video_id VARCHAR PRIMARY KEY,
                raw_transcript TEXT NOT NULL,
                summary TEXT,
                metadata JSON,  -- Added metadata column
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Debug: Print table schema
        cprint("DEBUG - Table Schema:", "blue")
        schema = conn.execute("DESCRIBE transcripts").fetchall()
        for col in schema:
            cprint(f"Column: {col}", "blue")
        
        return conn
    except Exception as e:
        cprint(f"Database initialization error: {e}", "red")
        traceback.print_exc()
        raise

def get_video_metadata(video_url, spinner):
    """Extract metadata from YouTube video"""
    try:
        spinner.text = "Extracting video metadata..."
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
        metadata = {
            "id": info.get("id"),
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "uploader_id": info.get("uploader_id"),
            "upload_date": info.get("upload_date"),
            "duration": info.get("duration"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "description": info.get("description"),
            "categories": info.get("categories"),
            "tags": info.get("tags"),
            "thumbnail": info.get("thumbnail"),
            "channel_url": info.get("channel_url"),
            "webpage_url": info.get("webpage_url")
        }
        
        cprint(f"Successfully extracted metadata for video: {metadata['title']}", "green")
        return metadata
        
    except Exception as e:
        cprint(f"Metadata extraction error: {e}", "red")
        traceback.print_exc()
        return None

def store_transcript(conn, video_id, raw_transcript, summary=None, metadata=None):
    """Store transcript, summary, and metadata in cache"""
    try:
        # Debug print before storage
        cprint(f"Storing data for video ID: {video_id}", "blue")
        cprint(f"Summary value being stored: {repr(summary)}", "blue")
        cprint(f"New metadata being stored: {bool(metadata)}", "blue")
        
        if metadata:
            # If new metadata is provided, store it
            conn.execute("""
                INSERT INTO transcripts (video_id, raw_transcript, summary, metadata)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (video_id) DO UPDATE 
                SET raw_transcript = EXCLUDED.raw_transcript,
                    summary = EXCLUDED.summary,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
            """, [video_id, raw_transcript, summary, json.dumps(metadata)])
        else:
            # If no new metadata, preserve existing metadata
            conn.execute("""
                INSERT INTO transcripts (video_id, raw_transcript, summary, metadata)
                VALUES (?, ?, ?, NULL)
                ON CONFLICT (video_id) DO UPDATE 
                SET raw_transcript = EXCLUDED.raw_transcript,
                    summary = EXCLUDED.summary,
                    created_at = NOW()
            """, [video_id, raw_transcript, summary])
        
        # Verify what was stored
        result = conn.execute("""
            SELECT metadata FROM transcripts WHERE video_id = ?
        """, [video_id]).fetchone()
        cprint(f"Verified metadata in database: {bool(result[0])}", "green")
        
        cprint(f"Stored transcript and metadata for video ID: {video_id}", "green")
    except Exception as e:
        cprint(f"Cache storage error: {e}", "red")
        traceback.print_exc()


def get_cached_transcript(conn, video_id, spinner):
    """Check if transcript exists in cache and return it"""
    try:
        spinner.text = f"Checking cache for video ID: {video_id}"
        result = conn.execute("""
            SELECT raw_transcript, summary, metadata 
            FROM transcripts 
            WHERE video_id = ?
        """, [video_id]).fetchone()
        
        if result:
            cprint(f"Cache hit for video ID: {video_id}", "green")
            return {
                "raw_transcript": result[0],
                "summary": result[1],
                "metadata": json.loads(result[2]) if result[2] else None
            }
        return None
    except Exception as e:
        cprint(f"Cache retrieval error: {e}", "red")
        traceback.print_exc()
        return None

def download_transcript(video_url, conn, spinner):
    """Download transcript from a YouTube video with caching"""
    try:
        spinner.text = "Starting transcript download process..."
        
        # Extract video ID from URL
        video_id = YouTube(video_url).video_id
        spinner.text = f"Extracted Video ID: {video_id}"
        
        # Check cache first
        cached_data = get_cached_transcript(conn, video_id, spinner)
        if cached_data and cached_data["raw_transcript"]:
            cprint("Retrieved transcript from cache", "green")
            return cached_data["raw_transcript"]
        
        # Get metadata
        metadata = get_video_metadata(video_url, spinner)
        
        # If not in cache, download transcript
        spinner.text = "Downloading transcript..."
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        cprint(f"Successfully retrieved transcript with {len(transcript)} entries", "green")
        
        # Convert transcript to readable markdown
        transcript_text = "### Transcript:\n\n"
        for entry in transcript:
            transcript_text += f"[{entry['start']:.2f}s] {entry['text']}\n"
        
        # Store in cache with metadata
        store_transcript(conn, video_id, transcript_text, None, metadata)
        
        return transcript_text
    
    except Exception as e:
        cprint(f"Transcript Download Error: {e}", "red")
        traceback.print_exc()
        return f"### Transcript:\n\n*Error downloading transcript: {e}*"


def summarize_transcript(transcript_text, llm_client, video_id, conn, spinner):
    """Summarize transcript with caching"""
    try:
        spinner.text = "Starting transcript summarization..."
        
        # Check cache first
        cached_data = get_cached_transcript(conn, video_id, spinner)
        if cached_data and cached_data.get("summary"):
            cprint("Retrieved valid summary from cache", "green")
            
            # Create a generator that yields the cached content in chunk format
            def cached_stream():
                yield type('ChunkResponse', (), {
                    'choices': [type('Choice', (), {
                        'delta': type('Delta', (), {
                            'content': cached_data["summary"]
                        })
                    })]
                })
            
            return {
                "result": cached_stream(),
                "direct_stream": True,  # We're still streaming, just from cache
                "cached": True
            }
        
        cprint("No valid summary in cache. Generating new summary...", "yellow")
        
        # Validate inputs
        if not transcript_text:
            cprint("Empty transcript text", "red")
            return {
                "error": "Empty transcript text",
                "direct_stream": False
            }
        
        if not llm_client:
            cprint("No LLM client provided", "red")
            return {
                "error": "No LLM client provided",
                "direct_stream": False
            }

        # Get metadata from cache if available
        metadata = cached_data.get("metadata") if cached_data else None
        
        # Prepare metadata text
        video_title = metadata.get("title", "Not provided") if metadata else "Not provided"
        
        cprint(f"Using metadata - Title: {video_title}", "blue")
        
        # Prepare metadata text
        video_title = metadata.get("title", "Not provided") if metadata else "Not provided"
        video_uploader = metadata.get("uploader", "Not provided") if metadata else "Not provided"
        video_description = metadata.get("description", "Not provided") if metadata else "Not provided"
        video_duration = metadata.get("duration", "Not provided") if metadata else "Not provided"
                

        # Create the stream - EXACTLY as in working version
        spinner.text = "Generating summary..."
        stream = llm_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert content processor. Your job is to generate perfect transcriptions for youtube videos by stitching together and cleaning the messy timestamped captions for a given video. \n\nNOTES:\n\n1. You do not summarise. 2. You have no editorial permission to interpret or add your own take on the content - you faithfully transcribe what is said in the video. 3. You can remove obvious adverts and boilerplate. 4. You should correct caption errors with your transcript. For example, often the youtube speech to text system mis-hears or mis-interprets the audio in the video and as a result produces an incorrect caption - mis-spelled or just wrong. You can correct this where you are very sure of the mistake, eg where the captions refer to a name that you know is incorrect because the title/description/uploader mentions the correct name. Similarly, a caption may contain a total non-sequitir which you can detect because you have read the entire transcript up until that point, and with an understanding of the context, can correct the wrongly-heard word.\n5.The videos you work with will often be podcast-style chats, panels or interviews with guests with a lot of back and forth q&a. Where possible try to denote questions and answers, eg by using linebreaks or colons. If it is obvious who the asker is and who the answerer is, then show their names \n6. Your cleaned output should be delivered in markdown format. "
                },
                {
                    "role": "user",
                    "content": f"""Here is the data for you to process:

                    Video Title: {video_title}
                    Uploaded by: {video_uploader}
                    Duration: {video_duration} seconds
                    Description: {video_description}

                    The video transcript is as follows:

                    {transcript_text}"""
                }
            ],
            temperature=0.7,
            max_tokens=16000,
            stream=True
        )
        
        # Create a simple accumulator for the DB
        def accumulate_and_save():
            full_response = ""
            for chunk in stream:
                if hasattr(chunk.choices[0].delta, 'content'):
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                if chunk.choices[0].finish_reason == "stop":
                    store_transcript(conn, video_id, transcript_text, full_response, None)
                yield chunk
        
        return {
            "result": accumulate_and_save(),
            "direct_stream": True,
            "cached": False
        }
            
    except Exception as e:
        cprint(f"Summarization Error: {e}", "red")
        traceback.print_exc()
        return {
            "error": f"Unexpected error in summarization: {str(e)}"
        }

def execute(video_url=None, llm_client=None):
    """Main execution function with caching"""
    try:
        spinner = Halo(text="Starting execution process...", spinner="dots")
        spinner.start()
        
        if not video_url:
            raise ValueError("A YouTube video URL is required.")
        
        # Initialize database connection
        conn = init_db()
        
        # Extract video ID
        video_id = YouTube(video_url).video_id
        
        # Get transcript
        transcript_markdown = download_transcript(video_url, conn, spinner)
        
        # Get summary if LLM client is provided
        if llm_client:
            # Remove markdown header from transcript
            transcript_text = transcript_markdown.replace("### Transcript:\n\n", "")
            
            spinner.text = "Preparing Transcript Summarization"
            summary_result = summarize_transcript(transcript_text, llm_client, video_id, conn, spinner)
            
            # Handle both streaming and cached responses
            if summary_result.get("direct_stream"):
                spinner.text = "Returning direct stream result"
                spinner.succeed()
                return summary_result
            elif summary_result.get("cached"):
                spinner.text = "Returning cached summary"
                spinner.succeed()
                # Format cached summary as an assistant message
                return {
                    "result": summary_result["result"],
                    "direct_stream": False
                }
        
        spinner.succeed()
        return {
            "transcript": transcript_markdown,
            "summary": None,
            "direct_stream": False
        }
        
    except Exception as e:
        spinner.fail(f"Execution Error: {e}")
        traceback.print_exc()
        return {
            "error": str(e),
            "transcript": None,
            "summary": None
        }

TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_transcription",
        "description": "Download captions and transcript from a YouTube video, with optional AI-powered summarization",
        "parameters": {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "The URL of the YouTube video to transcribe"
                }
            },
            "required": ["video_url"]
        }
    },
    "direct_stream": True
}


if __name__ == "__main__":
    # Example usage
    video_url = input("Enter the YouTube video URL: ")
    result = execute(video_url=video_url)
    
    # Display captions, transcript, and summary
    print("\n--- Captions (Markdown) ---\n")
    print(result["captions_markdown"])
    print("\n--- Transcript (Markdown) ---\n")
    print(result["transcript_markdown"])
    
    # Only print summary if available
    if result.get("summary_markdown"):
        print("\n--- Summary (Markdown) ---\n")
        print(result["summary_markdown"])

    # Optionally save to a markdown file
    with open("video_captions_transcript.md", "w") as f:
        f.write(result["captions_markdown"])
        f.write("\n\n")
        f.write(result["transcript_markdown"])
        if result.get("summary_markdown"):
            f.write("\n\n")
            f.write(result["summary_markdown"])