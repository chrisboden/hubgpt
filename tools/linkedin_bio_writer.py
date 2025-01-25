# tools/linkedin_bio_writer.py

import os
import json
import logging
from termcolor import colored
from typing import Dict, Any
import requests
from utils.log_utils import log_llm_request, log_llm_response
from utils.prompt_utils import process_inclusions

class LinkedInBioWriter:
    def __init__(self, llm_client):
        self.api_key = os.getenv('RAPIDAPI_KEY')
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable is not set")
        
        self.llm_client = llm_client
        self.api_endpoints = [
            "https://linkedin-data-api.p.rapidapi.com",
            "https://linkedin-api8.p.rapidapi.com"
        ]
        self.current_api_index = 0
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_endpoints[0].replace('https://', '')
        }

    def _update_api_endpoint(self):
        """Switch to alternate API endpoint and update headers"""
        self.current_api_index = (self.current_api_index + 1) % len(self.api_endpoints)
        new_host = self.api_endpoints[self.current_api_index].replace('https://', '')
        self.headers["x-rapidapi-host"] = new_host
        print(colored(f"Switching to alternate API endpoint: {self.api_endpoints[self.current_api_index]}", "yellow"))

    def _make_api_request(self, endpoint_path: str, params: dict) -> Dict:
        """Make API request with automatic fallback on rate limit"""
        for attempt in range(len(self.api_endpoints)):
            current_base = self.api_endpoints[self.current_api_index]
            # Add trailing slash to base URL and remove leading slash from endpoint path if present
            full_url = f"{current_base.rstrip('/')}/{endpoint_path.lstrip('/')}"
            
            try:
                print(colored(f"Making API request to: {full_url}", "cyan"))
                print(f"Request params:\n{params}")
                
                response = requests.get(
                    full_url.rstrip('/'),  # Ensure no trailing slash
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit exceeded
                    print(colored(f"Rate limit exceeded on {current_base}", "yellow"))
                    self._update_api_endpoint()
                    continue
                else:
                    raise Exception(f"API request failed with status {response.status_code}")
                    
            except Exception as e:
                print(colored(f"Error with endpoint {current_base}: {str(e)}", "red"))
                if attempt < len(self.api_endpoints) - 1:
                    self._update_api_endpoint()
                else:
                    raise Exception(f"All API endpoints failed. Last error: {str(e)}")


    def _extract_linkedin_username(self, profile_url: str) -> str:
        """Extract username from LinkedIn profile URL."""
        try:
            if '/in/' not in profile_url:
                raise ValueError("Invalid LinkedIn profile URL format")
            
            clean_url = profile_url.rstrip('/')
            username = clean_url.split('/in/')[-1].split('?')[0]
            
            print(colored(f"Extracted username: {username}", "green"))
            return username
            
        except Exception as e:
            print(colored(f"Error extracting username: {str(e)}", "red"))
            raise

    def _get_profile_data(self, username: str) -> Dict:
        """Get profile data from LinkedIn API with fallback."""
        try:
            print(colored(f"Fetching profile data for: {username}", "yellow"))
            # Changed to use empty string instead of "profile" endpoint
            return self._make_api_request("", {"username": username})
            
        except Exception as e:
            print(colored(f"Error fetching profile data: {str(e)}", "red"))
            raise

    def generate_bio(self, profile_data: Dict) -> str:
        """Generate bio using LLM."""
        try:
            print(colored("Generating bio with LLM...", "yellow"))
            
            # System message with file inclusion
            system_message = """

ABOUT YOU:
You are a professional bio writer for the Peregian Digital Hub, crafting concise and compelling bios for mentors contributing to the Tokenizer program. 

ABOUT TOKENIZER:
<$files/me/about_tokenizer_short.md$>

YOUR TASK::
Your goal is to highlight each mentor’s expertise, relevant achievements, and the reason they will make valuable  contributions to the Tokenizer program. 

### **Guidelines**
1. **Tone:** 
   - Professional yet approachable, reflecting the innovative and collaborative ethos of the Hub.
   - Focused on showcasing the mentor’s unique skills and value to the Tokenizer program.

2. **Structure:**
   - **Opening:** Start with the mentor’s professional background (e.g., their role, expertise, and industry experience).
   - **Middle:** Highlight their key achievements or projects, focusing on those relevant to AI, technology, or problem-solving.
   - **Closing:** Emphasise their contribution to the Tokenizer program and its significance.

3. **Length:** 
   - The bio must STRICTLY be one paragraph, approximately 120 words. Remove fluff, keep it information dense.

4. **Focus Areas for the Tokenizer Program:** 
   - AI, generative technologies, robotics, education, and innovation.
   - Highlight their role in areas like prompting, mentorship, or program development.

### **Input Requirements**
For each bio, you will be provided with:
   - Mentor’s name.
   - LinkedIn profile link.
   - Area of contribution to the Tokenizer program.


Guidelines:
- Write in third person
- Focus on career narrative and achievements
- Highlight key expertise and industry impact
- Include relevant metrics and accomplishments
- Maintain professional yet engaging tone
- Length: 2-3 paragraphs
"""

            # Process any file inclusions
            processed_system_message = process_inclusions(system_message, depth=5)
            
            messages = [
                {
                    "role": "system",
                    "content": processed_system_message
                },
                {
                    "role": "user",
                    "content": f"Please write a professional biography based on this LinkedIn profile data:\n\n{json.dumps(profile_data, indent=2)}"
                }
            ]

            api_params = {
                "model": "openai/gpt-4o-mini",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": True
            }

            # Log the request
            log_llm_request(api_params)
            
            # Get streaming response
            stream = self.llm_client.chat.completions.create(**api_params)
            
            print(colored("Successfully received stream response", "green"))
            logging.info("\n" + "="*50 + "\nDIRECT STREAM RESPONSE:\n" + "="*50 + 
                        "\nReturning stream object for bio generation\n" + "="*50)

            return {
                "result": stream,
                "direct_stream": True
            }

        except Exception as e:
            print(colored(f"Error generating bio: {str(e)}", "red"))
            raise

def execute(llm_client=None, profile_url=None):
    """Execute LinkedIn bio generation."""
    if not llm_client or not profile_url:
        raise ValueError("Both llm_client and profile_url are required")

    try:
        print(colored("Starting LinkedIn bio generation...", "cyan"))
        
        # Initialize tool
        tool = LinkedInBioWriter(llm_client)
        
        # Get LinkedIn username
        username = tool._extract_linkedin_username(profile_url)
        
        try:
            # Get profile data
            profile_data = tool._get_profile_data(username)
            
            # Generate bio
            return tool.generate_bio(profile_data)
            
        except requests.exceptions.HTTPError as http_err:
            error_msg = f"Failed to fetch LinkedIn profile: {str(http_err)}"
            print(colored(error_msg, "red"))
            
            # Create an error message stream
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant explaining LinkedIn profile access issues."
                },
                {
                    "role": "user",
                    "content": f"Please explain this error in user-friendly terms: {error_msg}"
                }
            ]
            
            # Get streaming response for error
            stream = llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=150,
                stream=True
            )
            
            return {
                "result": stream,
                "direct_stream": True,
                "error": error_msg
            }

    except Exception as e:
        error_msg = f"Failed to generate LinkedIn bio: {str(e)}"
        print(colored(error_msg, "red"))
        logging.error(error_msg)
        
        try:
            # Create a stream for the error message
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant explaining technical errors."
                },
                {
                    "role": "user",
                    "content": f"Please explain this error in user-friendly terms: {error_msg}"
                }
            ]
            
            # Get streaming response for error
            stream = llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=150,
                stream=True
            )
            
            return {
                "result": stream,
                "direct_stream": True,
                "error": error_msg
            }
            
        except Exception as llm_err:
            # If even the error streaming fails, return a basic error response
            return {
                "result": "I apologize, but I encountered an error while trying to access the LinkedIn profile. Please verify the profile URL and try again.",
                "direct_stream": False,
                "error": error_msg
            }

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "linkedin_bio_writer",
        "description": "Generate a professional biography from a LinkedIn profile",
        "parameters": {
            "type": "object",
            "properties": {
                "profile_url": {
                    "type": "string",
                    "description": "LinkedIn profile URL (format: https://www.linkedin.com/in/username)"
                }
            },
            "required": ["profile_url"]
        }
    },
    "direct_stream": True
}