#!/usr/bin/env python3
"""
LLM Client Module
Provides a unified LLM calling interface for the SE framework
"""

from openai import OpenAI
from typing import Dict, Any, Optional, List
from core.utils.se_logger import get_se_logger


class LLMClient:
    """LLM client supporting multiple models and API endpoints"""
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        Initialize the LLM client

        Args:
            model_config: Model configuration dictionary containing name, api_base, api_key, etc.
        """
        self.config = model_config
        self.logger = get_se_logger("llm_client", emoji="🤖")
        
        # Validate required configuration parameters
        required_keys = ["name", "api_base", "api_key"]
        missing_keys = [key for key in required_keys if key not in model_config]
        if missing_keys:
            raise ValueError(f"Missing required configuration parameters: {missing_keys}")
        
        # Strip litellm provider prefix (e.g. "openai/DeepSeek-V3.1" -> "DeepSeek-V3.1")
        # The raw OpenAI SDK doesn't understand litellm provider prefixes
        self._model_name = self.config["name"]
        if "/" in self._model_name:
            self._model_name = self._model_name.split("/", 1)[1]
        
        # Initialize OpenAI client, following the working pattern from api_test.py
        self.client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["api_base"],
        )
        
        self.logger.info(f"Initialized LLM client: {self.config['name']} (model: {self._model_name})")
    
    def call_llm(self, messages: List[Dict[str, str]], 
                 temperature: float = 0.3, 
                 max_tokens: Optional[int] = None) -> str:
        """
        Call the LLM and return the response content

        Args:
            messages: List of messages, each containing role and content
            temperature: Temperature parameter controlling output randomness
            max_tokens: Maximum output token count, None uses the configured default

        Returns:
            Text content of the LLM response

        Raises:
            Exception: Raised when the LLM call fails
        """
        try:
            # Use max_output_tokens from config as default
            if max_tokens is None:
                max_tokens = self.config.get("max_output_tokens", 4000)
            
            self.logger.debug(f"Calling LLM: {len(messages)} messages, temp={temperature}, max_tokens={max_tokens}")
            
            # Use basic OpenAI client call, following the working pattern from api_test.py
            # Do not use extra parameters to avoid server errors
            response = self.client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=temperature,
            )
            
            # Extract response content
            content = response.choices[0].message.content
            
            # Log usage information
            if response.usage:
                self.logger.debug(f"Token usage: input={response.usage.prompt_tokens}, "
                                f"output={response.usage.completion_tokens}, "
                                f"total={response.usage.total_tokens}")
            
            return content
            
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise
    
    def call_with_system_prompt(self, system_prompt: str, user_prompt: str, 
                               temperature: float = 0.3, 
                               max_tokens: Optional[int] = None) -> str:
        """
        Call the LLM with a system prompt and user prompt

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature parameter
            max_tokens: Maximum output token count

        Returns:
            Text content of the LLM response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.call_llm(messages, temperature, max_tokens)
    
    @classmethod
    def from_se_config(cls, se_config: Dict[str, Any], use_operator_model: bool = False) -> "LLMClient":
        """
        Create an LLM client from SE framework configuration

        Args:
            se_config: SE framework configuration dictionary
            use_operator_model: Whether to use operator_models config instead of the main model config

        Returns:
            LLM client instance
        """
        if use_operator_model and "operator_models" in se_config:
            model_config = se_config["operator_models"]
        else:
            model_config = se_config["model"]
        
        return cls(model_config)


class TrajectorySummarizer:
    """LLM client wrapper specifically for trajectory summarization"""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the trajectory summarizer

        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
        self.logger = get_se_logger("traj_summarizer", emoji="📊")
    
    def summarize_trajectory(self, trajectory_content: str, patch_content: str, 
                           iteration: int) -> Dict[str, Any]:
        """
        Summarize trajectory content using LLM

        Args:
            trajectory_content: .tra file content
            patch_content: .patch/.pred file content (prediction result)
            iteration: Iteration number

        Returns:
            Trajectory summary dictionary
        """
        from .traj_summarizer import TrajSummarizer
        
        summarizer = TrajSummarizer()
        
        try:
            # Get prompts
            system_prompt = summarizer.get_system_prompt()
            user_prompt = summarizer.format_user_prompt(trajectory_content, patch_content)
            
            self.logger.info(f"Starting LLM trajectory summarization (iteration {iteration})")
            
            # Call the LLM
            response = self.llm_client.call_with_system_prompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse the response
            summary = summarizer.parse_response(response)
            
            # Validate response format
            if summarizer.validate_response_format(summary):
                self.logger.info(f"LLM trajectory summarization succeeded (iteration {iteration})")
                return summary
            else:
                self.logger.warning(f"LLM response format does not meet expectations, using fallback summary (iteration {iteration})")
                return summarizer.create_fallback_summary(trajectory_content, patch_content, iteration)
                
        except Exception as e:
            self.logger.error(f"LLM trajectory summarization failed: {e}")
            # Return fallback summary
            return summarizer.create_fallback_summary(trajectory_content, patch_content, iteration)