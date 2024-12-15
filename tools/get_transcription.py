# tools/get_transcription.py

import traceback
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from termcolor import cprint

def download_transcript(video_url):
    """
    Download transcript from a YouTube video
    
    Args:
        video_url (str): URL of the YouTube video
    
    Returns:
        str: Markdown-formatted transcript
    """
    try:
        cprint("Starting transcript download process...", "blue")
        
        # Extract video ID from URL
        video_id = YouTube(video_url).video_id
        cprint(f"Extracted Video ID: {video_id}", "green")
        
        # Attempt to get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        cprint(f"Successfully retrieved transcript with {len(transcript)} entries", "green")
        
        # Convert transcript to readable markdown
        transcript_text = "### Transcript:\n\n"
        for entry in transcript:
            transcript_text += f"[{entry['start']:.2f}s] {entry['text']}\n"
        
        # Debug: Print first few lines of transcript
        cprint("First few lines of transcript:", "cyan")
        cprint(transcript_text[:500], "white")
        
        return transcript_text
    
    except Exception as e:
        cprint(f"Transcript Download Error: {e}", "red")
        cprint(f"Error Type: {type(e).__name__}", "red")
        traceback.print_exc()
        return f"### Transcript:\n\n*Error downloading transcript: {e}*"


def download_captions(video_url):
    """
    Download captions from a YouTube video
    
    Args:
        video_url (str): URL of the YouTube video
    
    Returns:
        str: Markdown-formatted captions
    """
    try:
        cprint("Starting caption download process...", "blue")
        
        yt = YouTube(video_url)
        cprint(f"Successfully loaded YouTube video: {video_url}", "green")
        
        # Get all available captions
        captions = yt.captions
        cprint(f"Total captions found: {len(captions)}", "cyan")
        
        # Try to find English captions
        english_caption = None
        for lang, caption in captions.items():
            cprint(f"Checking caption language: {lang}", "magenta")
            if 'en' in lang.lower():
                english_caption = caption
                cprint(f"Found English caption for language: {lang}", "green")
                break
        
        if english_caption:
            cprint("Generating SRT captions...", "blue")
            srt_captions = english_caption.generate_srt_captions()
            cprint("SRT captions generated successfully", "green")
            return f"### Captions:\n\n```\n{srt_captions}\n```"
        
        cprint("No English captions found", "yellow")
        return "### Captions:\n\n*No captions available in English.*"
    
    except Exception as e:
        cprint(f"Detailed Caption Download Error: {e}", "red")
        cprint(f"Error Type: {type(e).__name__}", "red")
        traceback.print_exc()
        return f"### Captions:\n\n*Error downloading captions: {e}*"

def summarize_transcript(transcript_text, llm_client):
    """
    Comprehensive diagnostic summarization with extensive error handling
    """
    try:
        print("\n🔍 DIAGNOSTIC: Entering summarize_transcript")
        print(f"🔢 Transcript Length: {len(transcript_text)} characters")
        
        # Validate inputs
        if not transcript_text:
            print("❌ ERROR: Empty transcript text")
            return {
                "error": "Empty transcript text",
                "direct_stream": False
            }
        
        if not llm_client:
            print("❌ ERROR: No LLM client provided")
            return {
                "error": "No LLM client provided",
                "direct_stream": False
            }
        
        # Diagnostic: Check LLM client capabilities
        try:
            print("🕵️ Checking LLM Client Configuration")
            print(f"Client Type: {type(llm_client)}")
            print(f"Available Methods: {dir(llm_client)}")
            print(f"Chat Attribute Exists: {'chat' in dir(llm_client)}")
        except Exception as config_error:
            print(f"❌ LLM Client Configuration Error: {config_error}")
        
        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": "You are an expert content processor. Clean and structure the given transcript, removing any irrelevant information, ads, or boilerplate text. Your cleaned output should be an information-dense, faithful, detailed and comprehensive summary that loses none of the key information. Your output will be used as context by an AI agent "
            },
            {
                "role": "user",
                "content": f"Here is the transcript:\n\n{transcript_text}"
            }
        ]
        
        # Diagnostic: Message preparation
        print("📝 Prepared Messages:")
        for msg in messages:
            print(f"  {msg['role']}: {msg['content'][:200]}...")
        
        # Attempt streaming completion with comprehensive error handling
        try:
            print("🚀 Attempting Streaming Completion")
            
            # Diagnostic: Verify chat.completions method
            if not hasattr(llm_client, 'chat') or not hasattr(llm_client.chat, 'completions'):
                print("❌ ERROR: Invalid LLM Client Structure")
                return {
                    "error": "Invalid LLM Client - Missing chat.completions method",
                    "direct_stream": False
                }
            
            # Attempt streaming using the same model as get_advice.py
            stream = llm_client.chat.completions.create(
                model="google/gemini-flash-1.5-8b",  # Changed to match get_advice.py
                messages=messages,
                temperature=0.7,
                max_tokens=3024,
                stream=True
            )
            
            print("✅ Streaming Completion Created Successfully")
            
            return {
                "result": stream,
                "direct_stream": True
            }
        
        except AttributeError as attr_error:
            print(f"❌ Attribute Error: {attr_error}")
            print(f"Client Attributes: {dir(llm_client)}")
            return {
                "error": f"Attribute Error in LLM Client: {attr_error}",
                "direct_stream": False
            }
        except Exception as stream_error:
            print(f"❌ Streaming Completion Error: {stream_error}")
            import traceback
            traceback.print_exc()
            
            return {
                "error": f"Failed to create streaming completion: {str(stream_error)}",
                "direct_stream": False
            }
    
    except Exception as e:
        print(f"❌ CRITICAL Summarization Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "error": f"Unexpected error in summarization: {str(e)}",
            "direct_stream": False
        }


def execute(video_url=None, llm_client=None):
    """
    Enhanced diagnostic transcript processing
    """
    print("\n🎬 DIAGNOSTIC: Entering Transcription Execute")
    print(f"🔗 Video URL: {video_url}")
    print(f"🤖 LLM Client: {'Provided' if llm_client else 'Not Provided'}")

    if not video_url:
        raise ValueError("A YouTube video URL is required.")
    
    # Initialize result dictionary
    result = {
        "video_url": video_url,
        "captions_markdown": None,
        "transcript_markdown": None,
        "summary_stream": None,
        "direct_stream": True
    }
    
    # Fetch captions and transcript
    captions_result = download_captions(video_url)
    result["captions_markdown"] = captions_result
    
    transcript_result = download_transcript(video_url)
    result["transcript_markdown"] = transcript_result
    
    # Diagnostic logging
    print(f"📄 Captions Length: {len(captions_result)}")
    print(f"📜 Transcript Length: {len(transcript_result)}")

    # Summarization with extensive error handling
    if llm_client:
        try:
            # Remove markdown header for summarization
            transcript_text = result["transcript_markdown"].replace("### Transcript:\n\n", "")
            
            print("🔍 Preparing Transcript Summarization")
            summary_result = summarize_transcript(transcript_text, llm_client)
            
            # Detailed diagnostic of summary result
            print("📋 Summary Result Diagnostics:")
            print(f"  Direct Stream: {summary_result.get('direct_stream')}")
            print(f"  Error (if any): {summary_result.get('error', 'None')}")
            print(f"  Stream Object Present: {summary_result.get('result') is not None}")
            
            # Return the summary result directly if it's a stream
            if summary_result.get('direct_stream') and summary_result.get('result'):
                print("🔄 Returning direct stream result")
                return summary_result
            
            # Otherwise store in result dictionary
            result["summary_stream"] = summary_result.get('result')
            result["direct_stream"] = summary_result.get('direct_stream', False)
        
        except Exception as summarization_error:
            print(f"❌ Summarization Process Error: {summarization_error}")
            import traceback
            traceback.print_exc()
            result["summary_stream"] = None
            result["direct_stream"] = False

    return result
# Tool metadata
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
    "direct_stream": True  # Ensure this matches the result's direct_stream flag
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