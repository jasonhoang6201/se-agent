#!/usr/bin/env python3
"""
Trajectory Summarizer
Dedicated prompt system for generating trajectory summaries for the trajectory pool
"""

import json
from typing import Dict, Any, Optional
from core.utils.se_logger import get_se_logger


class TrajSummarizer:
    """Trajectory summarizer that generates trajectory analysis prompts and parses responses"""
    
    def __init__(self):
        self.logger = get_se_logger("traj_summarizer", emoji="📊")
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt

        Returns:
            System prompt string
        """
        return """You are an AI assistant specialized in analyzing software engineering trajectories. Your task is to analyze execution trajectories from SWE-agent runs and provide structured insights about the solution approach.

You will be provided with:
1. A trajectory file (.tra) in JSON format containing the agent's step-by-step execution
2. A prediction file (.pred) containing the final result

Your goal is to extract and summarize the core solution strategy, techniques, and approaches used in this trajectory.

Return your analysis in JSON format with the following fields:
- approach_summary: A concise summary of the main approach used in this solution
- modified_files: List of files that were modified during execution  
- key_changes: Description of the most important code changes made
- strategy: The core solution strategy at an abstract level
- specific_techniques: Specific techniques or methods used in this solution
- tools_used: Tools and commands heavily utilized during execution
- reasoning_pattern: The problem-solving pattern observed in the trajectory
- assumptions_made: Key assumptions made during the solution process
- components_touched: Main components, functions, or modules that were modified

Focus on extracting actionable insights about the solution methodology rather than implementation details."""

    def get_user_prompt_template(self) -> str:
        """
        Get the user prompt template

        Returns:
            User prompt template string
        """
        return """Please analyze the following SWE-agent trajectory and provide insights about the solution approach.

Trajectory Data (.tra file):
{trajectory_content}

Prediction Result (.patch/.pred file):
{patch_content}

Please provide your analysis in the JSON format specified in the system prompt."""

    def format_user_prompt(self, trajectory_content: str, patch_content: str) -> str:
        """
        Format the user prompt

        Args:
            trajectory_content: Trajectory file content
            patch_content: Prediction file content (.patch/.pred)

        Returns:
            Formatted user prompt
        """
        template = self.get_user_prompt_template()
        return template.format(
            trajectory_content=trajectory_content,
            patch_content=patch_content
        )
    
    def parse_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse LLM response content

        Args:
            response_content: Raw content of the LLM response

        Returns:
            Parsed JSON data, or error information if parsing fails
        """
        try:
            # Try to parse JSON directly
            if response_content.strip().startswith('{'):
                return json.loads(response_content.strip())
            
            # If not direct JSON, try to extract the JSON portion
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_content = response_content[start_idx:end_idx]
                return json.loads(json_content)
            else:
                self.logger.warning("Unable to find JSON formatted content in response")
                return {
                    "error": "Unable to parse JSON",
                    "raw_content": response_content[:500] + "..." if len(response_content) > 500 else response_content
                }
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {e}")
            return {
                "error": "JSON parsing error", 
                "details": str(e),
                "raw_content": response_content[:500] + "..." if len(response_content) > 500 else response_content
            }
    
    def validate_response_format(self, response_data: Dict[str, Any]) -> bool:
        """
        Validate whether the response format meets expectations

        Args:
            response_data: Parsed response data

        Returns:
            Whether the format meets expectations
        """
        required_fields = [
            "approach_summary",
            "modified_files", 
            "key_changes",
            "strategy",
            "specific_techniques",
            "tools_used",
            "reasoning_pattern",
            "assumptions_made",
            "components_touched"
        ]
        
        # Check if there is an error field
        if "error" in response_data:
            return False
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in response_data]
        if missing_fields:
            self.logger.warning(f"Response is missing required fields: {missing_fields}")
            return False
        
        return True
    
    def create_fallback_summary(self, trajectory_content: str, patch_content: str, iteration: int) -> Dict[str, Any]:
        """
        Create a fallback summary (used when LLM call fails)

        Args:
            trajectory_content: Trajectory content
            patch_content: Prediction content (.patch/.pred)
            iteration: Iteration number

        Returns:
            Fallback summary data
        """
        # Simple fallback analysis
        trajectory_length = len(trajectory_content.split('\n')) if trajectory_content else 0
        patch_length = len(patch_content) if patch_content else 0
        
        return {
            "approach_summary": f"Iteration {iteration} execution with {trajectory_length} trajectory steps",
            "modified_files": ["unknown"],
            "key_changes": "Unable to analyze - LLM summarization failed",
            "strategy": f"iteration_{iteration}_strategy",
            "specific_techniques": ["automated_execution"],
            "tools_used": ["swe_agent"],
            "reasoning_pattern": "step_by_step_execution", 
            "assumptions_made": ["standard_swe_agent_assumptions"],
            "components_touched": ["unknown_components"],
            "meta": {
                "is_fallback": True,
                "trajectory_length": trajectory_length,
                "patch_length": patch_length,
                "iteration": iteration
            }
        }