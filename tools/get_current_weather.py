# tools/get_current_weather.py

def execute(llm_client=None, location=None, unit="celsius"):
    """
    Provide the current weather for a given location. This function can optionally use an LLM client to generate additional context.

    Parameters:
    - location (str): The city and state specified by the user, e.g., "San Francisco, CA".
    - unit (str): The temperature unit, either "celsius" (default) or "fahrenheit".
    - llm_client (optional): An LLM client for generating additional information, if needed.

    Returns:
    - dict: A dictionary with weather information, including location, temperature, unit, forecast, and optionally, a description.
    """
    # Example logic to get the current weather
    # In a real implementation, you'd call a weather API
    weather_info = {
        "location": location or "Unknown",
        "temperature": "18",
        "unit": unit,
        "forecast": ["cloudy", "rainy"]
    }

    return weather_info

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Provide the current weather for a given location when asked by a user",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state that the user mentions, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "description": "The temperature units to use. Note always use celsius as a default.",
                    "enum": [
                        "celsius",
                        "fahrenheit"
                    ]
                }
            },
            "required": [
                "location"
            ]
        }
    }
}
