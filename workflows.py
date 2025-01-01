# workflows.py

import streamlit as st
from workflow_manager import WorkflowManager
from utils.llm_utils import get_llm_response
import openai
import os

def main():
    st.title("Autonomous Workflows")
    
    # Initialize OpenAI client
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    
    # Get workflow goal from user
    goal = st.text_area("Enter workflow goal:", height=100)
    
    if st.button("Start Workflow"):
        if not goal:
            st.error("Please enter a workflow goal")
            return
            
        # Initialize and execute workflow
        workflow = WorkflowManager(client, goal)
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Execute workflow with UI updates
        with st.spinner("Workflow in progress..."):
            result = workflow.execute_workflow()
            
            # Display results
            if result["success"]:
                st.success("Workflow completed successfully!")
            else:
                st.error(f"Workflow failed: {result.get('error', 'Unknown error')}")
            
            # Show step details
            st.subheader("Workflow Steps")
            for i, step in enumerate(result["steps"]):
                with st.expander(f"Step {i+1}: {step.advisor}"):
                    st.write("Messages:")
                    st.json(step.messages)
                    if step.error:
                        st.error(f"Error: {step.error}")
                    else:
                        st.write("Result:")
                        st.write(step.result)

if __name__ == "__main__":
    main()