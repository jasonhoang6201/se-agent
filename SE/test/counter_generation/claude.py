#!/usr/bin/env python
"""
Claude API Client
Provides a simple interface for interacting with the Anthropic Claude API
Uses the official anthropic Python library
"""

import json
import time
from typing import Dict, Any, List, Optional, Union

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic library not found, please install with: pip install anthropic")

class ClaudeAPI:
    """Claude API client class"""

    def __init__(self, api_key: str):
        """
        Initialize the Claude API client

        Args:
            api_key: Claude API key
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic library not installed. Please install with: pip install anthropic")

        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)

    def send_message(
        self,
        message: str,
        model: str = "claude-3-7-sonnet-20250219",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system: Optional[str] = None,
        max_retries: int = 3,  # Additional application-level retries
        timeout: int = 60  # Timeout setting in seconds
    ) -> Dict[str, Any]:
        """
        Send a message to the Claude API

        Args:
            message: User message content
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            system: System prompt
            max_retries: Number of additional retries
            timeout: Request timeout in seconds

        Returns:
            API response
        """
        # Use application-level retry mechanism
        for attempt in range(max_retries + 1):
            try:
                kwargs = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": message
                        }
                    ]
                }

                if system:
                    kwargs["system"] = system

                # Call Anthropic client
                message_response = self.client.messages.create(**kwargs, timeout=timeout)

                # Convert to unified format
                return {
                    "id": message_response.id,
                    "model": message_response.model,
                    "content": message_response.content
                }

            except Exception as e:
                print(f"API request failed (attempt {attempt+1}/{max_retries+1}): {e}")

                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    return {"error": str(e)}

def extract_content(response: Dict[str, Any]) -> str:
    """
    Extract text content from a Claude API response

    Args:
        response: Claude API response

    Returns:
        Extracted text content
    """
    if "error" in response:
        return f"Error: {response['error']}"

    if "content" not in response:
        return "Error: content field not found in response"

    content_blocks = response["content"]

    if not content_blocks:
        return ""

    # Process content blocks
    extracted_text = ""
    for block in content_blocks:
        # If it's a TextBlock object (anthropic library response format)
        if hasattr(block, 'text'):
            extracted_text += block.text
        # If it's a dictionary (our own converted format)
        elif isinstance(block, dict) and block.get("type") == "text":
            extracted_text += block.get("text", "")

    return extracted_text
