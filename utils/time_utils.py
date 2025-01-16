from datetime import datetime
import pytz
from termcolor import colored

def get_time_context():
    """
    Returns a natural language string with current time across key timezones,
    centered around Brisbane/Noosa time.
    
    Returns:
        str: A formatted string with current time across timezones
    """
    try:
        # Define timezones
        brisbane_tz = pytz.timezone('Australia/Brisbane')
        ny_tz = pytz.timezone('America/New_York')
        sf_tz = pytz.timezone('America/Los_Angeles')
        london_tz = pytz.timezone('Europe/London')
        beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # Get current time in Brisbane
        brisbane_time = datetime.now(brisbane_tz)
        
        # Convert to other timezones
        ny_time = brisbane_time.astimezone(ny_tz)
        sf_time = brisbane_time.astimezone(sf_tz)
        london_time = brisbane_time.astimezone(london_tz)
        beijing_time = brisbane_time.astimezone(beijing_tz)
        
        # Format the output string
        time_context = (
            f"Keep in mind it is {brisbane_time.strftime('%-I:%M %p')} on {brisbane_time.strftime('%A, %B %-d, %Y')} "
            f"where Chris is in Noosa and\n"
            f"{ny_time.strftime('%-I:%M %p')} on {ny_time.strftime('%A, %B %-d')} in New York\n"
            f"{sf_time.strftime('%-I:%M %p')} on {sf_time.strftime('%A, %B %-d')} in San Francisco\n"
            f"{london_time.strftime('%-I:%M %p')} on {london_time.strftime('%A, %B %-d')} in London\n"
            f"{beijing_time.strftime('%-I:%M %p')} on {beijing_time.strftime('%A, %B %-d')} in Beijing"
        )
        
        return time_context
        
    except Exception as e:
        print(colored(f"Error getting time context: {str(e)}", "red"))
        return "Error: Unable to generate time context"

def get_current_time(timezone='Australia/Brisbane'):
    """
    Get current time in specified timezone.
    
    Args:
        timezone (str): Timezone name (default: 'Australia/Brisbane')
    
    Returns:
        datetime: Current time in specified timezone
    """
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz)
    except Exception as e:
        print(colored(f"Error getting current time: {str(e)}", "red"))
        return None

if __name__ == "__main__":
    print("\nCurrent time context:")
    print(get_time_context()) 