# tools/make_podcast.py

import os
from dotenv import load_dotenv
from pyht import Client, TTSOptions

load_dotenv()

def execute(llm_client=None, raw_content=None):
    """
    Generate a podcast from raw content. This function uses the provided LLM client to generate a script
    and PlayHT to convert the script into audio.

    Parameters:
    - llm_client: An LLM client instance to generate the podcast script.
    - raw_content (str): Raw input content for the podcast, provided by the LLM.

    Returns:
    - dict: A dictionary containing the podcast script and audio URL.
    """
    if not raw_content:
        raise ValueError("Raw content must be provided.")
    if not llm_client:
        raise ValueError("LLM client must be provided.")

    # Step 1: Generate the podcast script
    try:
        print("Generating podcast script using LLM...")
        script_response = llm_client.chat.completions.create(
            model="google/gemini-flash-1.5-8b",
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    Based on the following raw content, create a podcast script with an engaging introduction, 
                    discussions of key points, and a closing call to action. Maintain a friendly and professional tone.

                    Raw content: {raw_content}
                    """
                }
            ],
            max_tokens=2000,
            temperature=1
        )

        podcast_script = script_response.choices[0].message.content.strip()
        print(f"Generated Podcast Script:\n{podcast_script}")
        if not podcast_script:
            raise RuntimeError("Failed to generate a podcast script.")
    except Exception as e:
        raise RuntimeError(f"Error during script generation: {e}")

    # Step 2: Generate the audio
    try:
        print("Initializing PlayHT client...")
        playht_user_id = os.getenv("PLAY_HT_USER_ID")
        playht_api_key = os.getenv("PLAY_HT_API_KEY")
        playht_voice_id = os.getenv("PLAY_HT_VOICE_ID")

        if not playht_user_id or not playht_api_key or not playht_voice_id:
            raise RuntimeError("PlayHT API credentials or voice ID are missing in the environment variables.")

        client = Client(user_id=playht_user_id, api_key=playht_api_key)

        print("Generating audio using PlayHT...")
        options = TTSOptions(voice=playht_voice_id)
        audio_file_path = f"podcast_{os.getpid()}.mp3"

        with open(audio_file_path, "wb") as audio_file:
            for chunk in client.tts(podcast_script, options):
                if chunk:  # Skip empty chunks
                    audio_file.write(chunk)
                else:
                    print("Received empty chunk (ignored).")

        audio_url = f"file://{os.path.abspath(audio_file_path)}"
        print(f"Audio saved to: {audio_url}")

    except Exception as e:
        raise RuntimeError(f"Error during audio generation: {e}")

    finally:
        try:
            client.close()
        except Exception as e:
            print(f"Warning: Failed to close PlayHT client: {e}")

    # Return the result
    return {
        "podcast_script": podcast_script,
        "audio_url": audio_url
    }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "make_podcast",
        "description": "Generate a podcast from raw content using LLM and text-to-speech capabilities.",
        "parameters": {
            "type": "object",
            "properties": {
                "raw_content": {
                    "type": "string",
                    "description": "The raw content to base the podcast script on."
                }
            },
            "required": ["raw_content"]
        }
    }
}
