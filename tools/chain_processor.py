# tools/chain_processor.py

from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class ChainStepType(Enum):
    CATEGORIZE = "categorize"
    ANALYZE = "analyze"
    SUMMARIZE = "summarize"
    CUSTOM = "custom"

@dataclass
class ChainStep:
    """Defines a single step in the processing chain"""
    step_type: ChainStepType
    prompt_template: str
    required_fields: List[str]  # Fields needed from previous steps
    output_key: str  # Key under which to store this step's output

class ChainProcessor:
    """Handles sequential processing of data through LLM chain steps"""
    
    def __init__(self):
        self.steps: List[ChainStep] = []
        self.results: Dict[str, Any] = {}
    
    def add_step(self, step: ChainStep) -> None:
        """Add a processing step to the chain"""
        self.steps.append(step)
    
    def _validate_required_fields(self, step: ChainStep) -> bool:
        """Check if all required fields from previous steps exist"""
        return all(field in self.results for field in step.required_fields)
    
    def _format_prompt(self, step: ChainStep, input_data: Dict) -> str:
        """Format the prompt template with available data"""
        context = {
            "input": input_data,
            "previous_results": self.results
        }
        return step.prompt_template.format(**context)
    
    async def process_chain(self, llm_client, input_data: Dict) -> Dict:
        """
        Process input data through all chain steps
        """
        self.results = {}  # Reset results for new processing
        
        try:
            for step in self.steps:
                if not self._validate_required_fields(step):
                    raise ValueError(f"Missing required fields for step {step.step_type}")
                
                prompt = self._format_prompt(step, input_data)
                
                response = llm_client.chat.completions.create(
                    model='openai/gpt-4o-mini',
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Store result under specified key
                try:
                    # Attempt to parse as JSON first
                    self.results[step.output_key] = json.loads(
                        response.choices[0].message.content
                    )
                except json.JSONDecodeError:
                    # If not JSON, store raw string
                    self.results[step.output_key] = response.choices[0].message.content
            
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "chain_results": self.results
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

def execute(llm_client=None, input_data: Dict = None) -> Dict:
    """
    Main tool execution function
    
    Args:
        llm_client: OpenAI client instance
        input_data: Data to be processed through the chain
    """
    if not llm_client or not input_data:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": "Both llm_client and input_data are required"
        }
    
    # Initialize processor
    processor = ChainProcessor()
    
    # Example: Add some basic chain steps
    processor.add_step(ChainStep(
        step_type=ChainStepType.CATEGORIZE,
        prompt_template="Categorize this data into main themes:\n{input}",
        required_fields=[],  # First step has no requirements
        output_key="categories"
    ))
    
    processor.add_step(ChainStep(
        step_type=ChainStepType.ANALYZE,
        prompt_template="""Analyze these categories for patterns:
        Categories: {previous_results[categories]}
        Data: {input}""",
        required_fields=["categories"],
        output_key="analysis"
    ))
    
    processor.add_step(ChainStep(
        step_type=ChainStepType.SUMMARIZE,
        prompt_template="""Provide a summary based on:
        Categories: {previous_results[categories]}
        Analysis: {previous_results[analysis]}""",
        required_fields=["categories", "analysis"],
        output_key="summary"
    ))
    
    # Process the chain
    return processor.process_chain(llm_client, input_data)

# Tool metadata
TOOL_METADATA = {
    "type": "function",
    "function": {
        "name": "chain_processor",
        "description": "Process data through a chain of LLM operations",
        "parameters": {
            "type": "object",
            "properties": {
                "input_data": {
                    "type": "object",
                    "description": "Data to be processed through the chain"
                }
            },
            "required": ["input_data"]
        }
    }
}