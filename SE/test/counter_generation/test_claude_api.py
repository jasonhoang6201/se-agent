#!/usr/bin/env python
"""
Test the enhanced Claude API client
"""

import sys
import json
from pathlib import Path

# Get the directory of the current script
current_dir = Path(__file__).parent
# Ensure the claude module can be imported
sys.path.insert(0, str(current_dir))

# Import the API to test
from claude import ClaudeAPI, extract_content

def test_claude_api_with_retry():
    """Test the Claude API client with retry mechanism"""

    # Test Claude API key
    test_api_key = "api_key"

    # Create Claude API client
    print("Initializing Claude API client...")
    claude_api = ClaudeAPI(test_api_key)

    # Test simple request
    print("\nSending simple request to test connection...")
    message = "Hello, please respond with a very short greeting."
    
    try:
        # Use shorter timeout and more retries for testing
        response = claude_api.send_message(
            message=message,
            model="claude-3-7-sonnet-20250219",
            temperature=0.7,
            max_tokens=100,
            max_retries=3,
            timeout=30
        )
        
        # Check for errors
        if "error" in response:
            print(f"Request returned error: {response['error']}")
            return False

        # Extract content
        content = extract_content(response)
        print(f"Response content: {content}")

        print("API request successful!")
        return True

    except Exception as e:
        print(f"Error occurred during test: {e}")
        return False

if __name__ == "__main__":
    success = test_claude_api_with_retry()
    if success:
        print("\nTest passed: API is working properly")
    else:
        print("\nTest failed: API connection issue") 