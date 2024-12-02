HOW_MANY_RESEARCH_STEPS = 3
QUESTION_MULTIPLIER = 3 # WE START WITH 1 QUESTION AND THEN MULTIPLY IT BY THIS NUMBER FOR EACH RESEARCH STEP

take these steps one by one:

1- check if you have researcher(queries: list) function in tools.py file(if not create the function in the file)
2- if not create it using this perpelxity api call:
---------
from openai import AsyncOpenAI
import os
import asyncio
from termcolor import colored

YOUR_API_KEY = os.getenv("PERPLEXITY_API_KEY")

async def researcher(queries: list) -> list:
    try:
        print(colored("Starting parallel research queries...", "cyan"))
        
        async def process_query(query: str) -> str:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a versatile research assistant with expertise in both academic and general web research. "
                        "Your task is to provide comprehensive, accurate, and well-structured responses that: "
                        "1) Draw from both academic sources and reliable web resources "
                        "2) Break down topics into clear, accessible explanations "
                        "3) Include relevant data, statistics, and expert insights from various sources "
                        "4) Consider multiple perspectives and fact-check information "
                        "5) Distinguish between academic research and general web content "
                        "6) Provide a mix of scholarly citations and credible web references "
                        "7) Evaluate the reliability of web sources and identify potential biases "
                        "8) Incorporate recent developments and real-world applications "
                        "Please balance academic rigor with practical, real-world relevance. "
                        "When using web sources, prioritize authoritative websites, industry experts, and verified information. "
                        "If uncertain about any information, clearly indicate this and provide both academic and web-based resources for further research."
                    ),
                },
                {   
                    "role": "user",
                    "content": query,
                },
            ]

            try:
                client = AsyncOpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")
                print(colored(f"Processing query: {query[:50]}...", "yellow"))
                
                response = await client.chat.completions.create(
                    model="llama-3.1-sonar-large-128k-online",
                    messages=messages,
                )
                return response.choices[0].message.content
            except Exception as e:
                print(colored(f"Error processing query: {str(e)}", "red"))
                return f"Error processing query: {str(e)}"

        # Create tasks for all queries
        tasks = [process_query(query) for query in queries]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        print(results)
        
        print(colored("All research queries completed successfully!", "green"))
        return results
        
    except Exception as e:
        print(colored(f"Error in researcher function: {str(e)}", "red"))
        return [str(e)] * len(queries)
    
you will run this function for each research step as a terminal command only with "python -c from tools import researcher; researcher(queries)"
    
3- next folow HOW_MANY_RESEARCH_STEPS steps AS FOLLOWS:
    1- ask a basic but comprehensive question about the topic or question user is interested in
    2- run the researcher function with that question
    3- create a research.md file with general skeleton structure with general information about that topic based on the researches output
    4- multiply the question by QUESTION_MULTIPLIER and run the researcher function again with the new more in depth questions
    5- update the research.md file with the new information including charts, graphs, tables, etc. make sure it is as beautiful as it is accurate and informative. we belive in you!!
    6- repeat step 4 and 5 HOW_MANY_RESEARCH_STEPS times
    7- when you are done create a summary.txt file with a very consice summary of the research.


