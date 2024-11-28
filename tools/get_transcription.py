# tools/get_transcription.py

from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi

def execute(video_url=None):
    """
    Download captions and transcript from a YouTube video in markdown format.
    
    Parameters:
    - video_url (str): The YouTube video URL specified by the user.
    
    Returns:
    - dict: A dictionary with caption and transcript information formatted as markdown.
    """
    if not video_url:
        raise ValueError("A YouTube video URL is required.")
    
    # Initialize result dictionary
    result = {
        "video_url": video_url,
        "captions_markdown": None,
        "transcript_markdown": None
    }
    
    # Helper functions for downloading captions and transcript
    def download_captions(video_url):
        yt = YouTube(video_url)
        captions = yt.captions.get_by_language_code('en')
        if captions:
            return f"### Captions:\n\n```\n{captions.generate_srt_captions()}\n```"
        return "### Captions:\n\n*No captions available in English.*"

    def download_transcript(video_url):
        video_id = YouTube(video_url).video_id
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            transcript_text = "\n".join([f"- {entry['text']}" for entry in transcript])
            return f"### Transcript:\n\n{transcript_text}"
        except Exception as e:
            return f"### Transcript:\n\n*An error occurred: {e}*"

    # Fetch captions in markdown format
    result["captions_markdown"] = download_captions(video_url)
    # Fetch transcript in markdown format
    result["transcript_markdown"] = download_transcript(video_url)

    return result

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_transcription",
        "description": "Download captions from a YouTube video URL and intelligently format into a readable transcript, in markdown format. Diarise where possible.",
        "parameters": {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "The URL of the YouTube video"
                }
            },
            "required": ["video_url"]
        }
    }
}

if __name__ == "__main__":
    # Example usage
    video_url = input("Enter the YouTube video URL: ")
    result = execute(video_url=video_url)
    
    # Display captions and transcript in markdown format
    print("\n--- Captions (Markdown) ---\n")
    print(result["captions_markdown"])
    print("\n--- Transcript (Markdown) ---\n")
    print(result["transcript_markdown"])

    # Optionally save to a markdown file
    with open("video_captions_transcript.md", "w") as f:
        f.write(result["captions_markdown"])
        f.write("\n\n")
        f.write(result["transcript_markdown"])
