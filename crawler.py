# crawler.py

import os
import json
from typing import Dict, Any
import dotenv
import logging
from swarm import Agent, Swarm
from requests import Response  # Ensure this is imported if swarm.run returns Response objects

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env file
dotenv.load_dotenv()

# Initialize the Swarm framework with OpenRouter configurations
swarm = Swarm()

# Define agent functions

def gather_preferences(context_variables: Dict[str, Any]) -> str:
    """
    Concierge Agent gathers user preferences for the trip.
    """
    try:
        # Gather real user input (replace with simulated data if necessary)
        destination = input("Where would you like to travel? ").strip()
        while not destination:
            destination = input("Please enter a valid destination: ").strip()
        
        travel_dates = input("Enter your travel dates (e.g., 2023-12-20 to 2023-12-30): ").strip()
        while not travel_dates:
            travel_dates = input("Please enter valid travel dates: ").strip()
        
        budget = input("What is your budget? ").strip()
        while not budget:
            budget = input("Please enter a valid budget: ").strip()
        
        interests_input = input("What are your interests? (comma-separated, e.g., culture,food,history): ").strip()
        interests = [interest.strip() for interest in interests_input.split(',') if interest.strip()]
        while not interests:
            interests_input = input("Please enter at least one interest: ").strip()
            interests = [interest.strip() for interest in interests_input.split(',') if interest.strip()]
        
        preferences = {
            "destination_preference": destination,
            "travel_dates": travel_dates,
            "budget": budget,
            "interests": interests
        }
        logging.info(f"Gathered preferences: {preferences}")
        return json.dumps(preferences)
    except Exception as e:
        logging.error(f"Error gathering preferences: {e}")
        return json.dumps({})

def suggest_destinations(preferences_json: str) -> str:
    """
    Destination Expert Agent suggests destinations based on preferences.
    """
    try:
        preferences = json.loads(preferences_json)
        # Simulate destination suggestions (replace with API calls if necessary)
        destination_pref = preferences.get("destination_preference", "Italy")
        if destination_pref.lower() == "italy":
            suggested_destinations = ["Rome", "Florence", "Venice"]
        elif destination_pref.lower() == "peru":
            suggested_destinations = ["Cusco", "Lima", "Arequipa"]
        else:
            suggested_destinations = ["Paris", "Berlin", "Amsterdam"]
        logging.info(f"Suggested Destinations: {suggested_destinations}")
        return json.dumps({"suggested_destinations": suggested_destinations})
    except Exception as e:
        logging.error(f"Error suggesting destinations: {e}")
        return json.dumps({"suggested_destinations": []})

def create_itinerary(context_variables_json: str) -> str:
    """
    Itinerary Planner Agent creates an itinerary for the selected destination.
    """
    try:
        context_variables = json.loads(context_variables_json)
        selected_destination = context_variables.get("selected_destination", "Rome")
        interests = context_variables.get("interests", ["culture", "food", "history"])
        
        # Create a prompt for the OpenAI API to generate an itinerary
        prompt = f"Create a 10-day itinerary for {selected_destination} focusing on {', '.join(interests)}."
        response = swarm.client.chat.completions.create(
            model=swarm.default_model,
            messages=[
                {"role": "system", "content": "You are an itinerary planner."},
                {"role": "user", "content": prompt}
            ]
        )
        itinerary = response['choices'][0]['message']['content'].strip()
        logging.info(f"Created Itinerary: {itinerary}")
        return json.dumps({"itinerary": itinerary})
    except Exception as e:
        logging.error(f"Error creating itinerary: {e}")
        return json.dumps({"itinerary": ""})

def recommend_accommodations(context_variables_json: str) -> str:
    """
    Accommodation Specialist Agent recommends accommodations based on itinerary and budget.
    """
    try:
        context_variables = json.loads(context_variables_json)
        itinerary = context_variables.get("itinerary", "")
        budget = context_variables.get("budget", "$3000")
        
        # Simulate accommodation recommendations (replace with API calls if necessary)
        # For example, based on budget, select different accommodations
        if int(budget.replace('$', '')) >= 3000:
            accommodations = [
                {"name": "Luxury Hotel Roma", "price": "$300/night", "location": "City Center"},
                {"name": "Premium Stay Florence", "price": "$250/night", "location": "Historic District"}
            ]
        else:
            accommodations = [
                {"name": "Hotel Roma", "price": "$150/night", "location": "City Center"},
                {"name": "Budget Stay Florence", "price": "$80/night", "location": "Near Train Station"}
            ]
        logging.info(f"Recommended Accommodations: {accommodations}")
        return json.dumps({"accommodations": accommodations})
    except Exception as e:
        logging.error(f"Error recommending accommodations: {e}")
        return json.dumps({"accommodations": []})

# Define handoff functions

def handoff_to_destination_expert(preferences_json: str) -> Agent:
    """Delegate task to Destination Expert Agent."""
    return destination_expert_agent

def handoff_to_itinerary_planner(context_variables_json: str) -> Agent:
    """Delegate task to Itinerary Planner Agent."""
    return itinerary_planner_agent

def handoff_to_accommodation_specialist(context_variables_json: str) -> Agent:
    """Delegate task to Accommodation Specialist Agent."""
    return accommodation_specialist_agent

# Define Agents

# Concierge Agent: Gathers user preferences
concierge_agent = Agent(
    name="Concierge Agent",
    instructions="You gather user preferences for their trip and delegate tasks to specialized agents.",
    functions=[gather_preferences, handoff_to_destination_expert],
)

# Destination Expert Agent: Suggests destinations
destination_expert_agent = Agent(
    name="Destination Expert Agent",
    instructions="You suggest travel destinations based on user preferences.",
    functions=[suggest_destinations, handoff_to_itinerary_planner],
)

# Itinerary Planner Agent: Creates itinerary
itinerary_planner_agent = Agent(
    name="Itinerary Planner Agent",
    instructions="You create a detailed itinerary for the selected destination.",
    functions=[create_itinerary, handoff_to_accommodation_specialist],
)

# Accommodation Specialist Agent: Recommends accommodations
accommodation_specialist_agent = Agent(
    name="Accommodation Specialist Agent",
    instructions="You recommend accommodations based on the itinerary and budget.",
    functions=[recommend_accommodations],
)

# Autonomous Workflow Function

def autonomous_travel_planning():
    """
    Orchestrates the autonomous travel planning workflow.
    """
    # Step 1: Concierge Agent gathers preferences
    preferences_response = swarm.run(
        agent=concierge_agent,
        messages=[],  # No initial messages; concierge initiates
        context_variables={}
    )
    
    # Check if preferences_response is a Response object
    if isinstance(preferences_response, Response):
        preferences = preferences_response.json()
    else:
        preferences = json.loads(preferences_response)
    
    if not preferences:
        print("[Coordinator] No preferences gathered. Aborting workflow.")
        return

    # Step 2: Concierge delegates to Destination Expert Agent
    destination_response = swarm.run(
        agent=destination_expert_agent,
        messages=[],  # No messages needed; using context_variables
        context_variables=preferences
    )
    
    if isinstance(destination_response, Response):
        destination_data = destination_response.json()
    else:
        destination_data = json.loads(destination_response)
    
    suggested_destinations = destination_data.get("suggested_destinations", [])

    if not suggested_destinations:
        print("[Coordinator] No destinations suggested. Aborting workflow.")
        return

    # Select the first suggested destination for simplicity
    selected_destination = suggested_destinations[0]

    # Step 3: Destination Expert delegates to Itinerary Planner Agent
    itinerary_response = swarm.run(
        agent=itinerary_planner_agent,
        messages=[],  # No messages needed; using context_variables
        context_variables={"selected_destination": selected_destination, **preferences}
    )
    
    if isinstance(itinerary_response, Response):
        itinerary_data = itinerary_response.json()
    else:
        itinerary_data = json.loads(itinerary_response)
    
    itinerary = itinerary_data.get("itinerary", "")

    if not itinerary:
        print("[Coordinator] Itinerary creation failed. Aborting workflow.")
        return

    # Step 4: Itinerary Planner delegates to Accommodation Specialist Agent
    accommodation_response = swarm.run(
        agent=accommodation_specialist_agent,
        messages=[],  # No messages needed; using context_variables
        context_variables={"itinerary": itinerary, **preferences}
    )
    
    if isinstance(accommodation_response, Response):
        accommodation_data = accommodation_response.json()
    else:
        accommodation_data = json.loads(accommodation_response)
    
    accommodations = accommodation_data.get("accommodations", [])

    if not accommodations:
        print("[Coordinator] Accommodation recommendations failed. Aborting workflow.")
        return

    # Final Output
    print("\n=== Travel Plan ===")
    print(f"Destination: {selected_destination}")
    print(f"Itinerary: {itinerary}")
    print(f"Accommodations: {json.dumps(accommodations, indent=2)}")

# Run the autonomous workflow
if __name__ == "__main__":
    print("Starting Autonomous Travel Planning Agent Swarm...\n")
    autonomous_travel_planning()
    print("\nAutonomous Travel Planning Completed.")
