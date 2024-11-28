# multi_agent.py
import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any
from openai import OpenAI
from agent_framework import Agent, AgentManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    base_url=os.getenv('API_BASE_URL'),
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Agent definitions
manager_agent = Agent(
    name="Manager",
    model="openai/gpt-4o-mini",
    system_prompt="""You are a workflow manager responsible for orchestrating text analysis.
    Your job is to:
    1. First get a summary using the summarizer agent
    2. Then get a detailed analysis using the analyzer agent
    3. Finally, get recommendations using the advisor agent
    4. Determine if the task is complete or needs additional analysis
    
    After each step, evaluate the results and decide the next step.
    When all necessary information has been gathered, compile a final report.""",
    tools=[]
)

summarizer_agent = Agent(
    name="Summarizer",
    model="openai/gpt-4o-mini",
    system_prompt="You are a summarizer. Create a concise, clear summary of the provided text.",
    tools=[]
)

analyzer_agent = Agent(
    name="Analyzer",
    model="openai/gpt-4o-mini",
    system_prompt="You are an analyst. Provide detailed insights about the text's main points, implications, and significance.",
    tools=[]
)

advisor_agent = Agent(
    name="Advisor",
    model="openai/gpt-4o-mini",
    system_prompt="You are an advisor. Based on the analysis, provide specific, actionable recommendations.",
    tools=[]
)

def run_orchestrated_pipeline(text: str):
    """Run a pipeline with automated handoffs between agents."""
    logger.info("Starting orchestrated pipeline")
    manager = AgentManager(client)
    context = {
        "original_text": text,
        "summary": "",
        "analysis": "",
        "recommendations": "",
        "status": "starting"
    }
    
    try:
        while context["status"] != "complete":
            if context["status"] == "starting":
                # Step 1: Get summary
                print("\n📝 Getting summary...")
                messages = [{
                    "role": "user",
                    "content": f"Please summarize this text: {text}"
                }]
                
                response_stream = manager.run(summarizer_agent, messages)
                for chunk in response_stream:
                    if chunk.get("type") == "content":
                        context["summary"] += chunk["content"]
                        print(chunk["content"], end="", flush=True)
                
                context["status"] = "need_analysis"
                
            elif context["status"] == "need_analysis":
                # Step 2: Get analysis
                print("\n\n🔍 Generating analysis...")
                messages = [{
                    "role": "user",
                    "content": f"Based on this summary: {context['summary']}\n\nPlease provide a detailed analysis of the original text: {text}"
                }]
                
                response_stream = manager.run(analyzer_agent, messages)
                for chunk in response_stream:
                    if chunk.get("type") == "content":
                        context["analysis"] += chunk["content"]
                        print(chunk["content"], end="", flush=True)
                
                context["status"] = "need_recommendations"
                
            elif context["status"] == "need_recommendations":
                # Step 3: Get recommendations
                print("\n\n💡 Generating recommendations...")
                messages = [{
                    "role": "user",
                    "content": f"Based on this analysis: {context['analysis']}\n\nPlease provide specific recommendations."
                }]
                
                response_stream = manager.run(advisor_agent, messages)
                for chunk in response_stream:
                    if chunk.get("type") == "content":
                        context["recommendations"] += chunk["content"]
                        print(chunk["content"], end="", flush=True)
                
                context["status"] = "need_final_review"
                
            elif context["status"] == "need_final_review":
                # Step 4: Final review by manager
                print("\n\n✅ Generating final report...")
                messages = [{
                    "role": "user",
                    "content": f"""Please review all components and provide a final report:
                    Summary: {context['summary']}
                    Analysis: {context['analysis']}
                    Recommendations: {context['recommendations']}
                    
                    Is this analysis complete? If so, provide a final synthesis. If not, what additional analysis is needed?"""
                }]
                
                response_stream = manager.run(manager_agent, messages)
                for chunk in response_stream:
                    if chunk.get("type") == "content":
                        print(chunk["content"], end="", flush=True)
                
                context["status"] = "complete"

        print("\n\n✨ Analysis pipeline complete!")

    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    sample_text = input("Enter some text to analyze: ")
    run_orchestrated_pipeline(sample_text)