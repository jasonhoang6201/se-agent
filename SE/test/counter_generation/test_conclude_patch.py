#!/usr/bin/env python
"""
Test the Claude API request functionality in conclude_patch.py
"""

import os
import sys
import json
from pathlib import Path
import pytest

# Get the directory of the current script
current_dir = Path(__file__).parent
# Ensure the claude module can be imported
sys.path.insert(0, str(current_dir))

# Import the modules to test
from conclude_patch import (
    analyze_patch_with_claude,
    ClaudeAPI,
    extract_content,
    load_filtered_predictions,
    save_predictions
)

def test_claude_api_request_simple():
    """
    Simple test of Claude API request functionality, only verifying successful connection without checking detailed fields
    """
    # Test Claude API key
    test_api_key = "api_key"

    # Create Claude API client
    claude_api = ClaudeAPI(test_api_key)

    # Send simple request
    response = claude_api.send_message(
        message="Hello, Claude! Please respond with a simple JSON: {\"test\": \"success\"}",
        model="claude-3-7-sonnet-20250219",
        temperature=0.3,
        max_tokens=100
    )
    
    # Verify response was received
    assert response is not None, "No API response received"
    assert "content" in response, "Response format error"

    # Extract content
    content = extract_content(response)
    print(f"API response content: {content[:100]}...")

    # Verify content contains "success"
    assert "success" in content.lower(), "Response content does not match expected"

    print("Claude API connection test successful!")

def test_claude_analysis_function():
    """
    Test the basic functionality of the analyze_patch_with_claude function
    """
    # Test Claude API key
    test_api_key = "api_key"

    # Create Claude API client
    claude_api = ClaudeAPI(test_api_key)

    # Test data
    test_problem = """
    Issue: The function `calculate_sum` does not handle negative numbers correctly.
    Expected behavior: The function should return the sum of all numbers, including negative ones.
    """
    
    test_patch = """
    def calculate_sum(numbers):
        return sum([n for n in numbers if n > 0])  # Only calculate positive numbers
    """
    
    test_instance_id = "test_instance_001"
    
    # Call the analysis function
    result = analyze_patch_with_claude(
        problem_statement=test_problem,
        model_patch=test_patch,
        instance_id=test_instance_id,
        claude_api=claude_api
    )
    
    # Only verify basic structure, don't check specific fields
    assert isinstance(result, dict), "Return result should be a dictionary type"
    print(f"Fields in analysis result: {list(result.keys())}")

    # Should have at least some fields
    assert len(result) > 0, "Return result is an empty dictionary"

    # Check for errors
    assert "error" not in result, f"API request failed: {result.get('error', '')}"

    print("Claude analysis function test successful!")

def test_claude_api_integration():
    """
    Test the integration of Claude API with file processing

    This test will:
    1. Create a test conclusion.json file
    2. Use the Claude API to analyze patches
    3. Verify results are correctly saved to file
    """
    # Test Claude API key
    test_api_key = "api_key"

    # Create Claude API client
    claude_api = ClaudeAPI(test_api_key)

    # Create test conclusion.json file
    test_data = {
        "test_instance_001": {
            "problem_statement": "Issue: The function `calculate_sum` does not handle negative numbers correctly.",
            "model_patch": "def calculate_sum(numbers):\n    return sum([n for n in numbers if n > 0])  # Only calculate positive numbers"
        }
    }
    
    # Save test data
    test_file = "test_conclusion.json"
    save_predictions(test_data, test_file)
    
    try:
        # Load test data
        predictions = load_filtered_predictions(test_file)
        
        # Process test data
        instance_id = "test_instance_001"
        instance_data = predictions[instance_id]
        
        # Call the analysis function
        analysis = analyze_patch_with_claude(
            problem_statement=instance_data["problem_statement"],
            model_patch=instance_data["model_patch"],
            instance_id=instance_id,
            claude_api=claude_api
        )
        
        # Add analysis results to the data
        predictions[instance_id]["claude_analysis"] = analysis
        
        # Save updated data
        save_predictions(predictions, test_file)
        
        # Verify the file was correctly updated
        updated_predictions = load_filtered_predictions(test_file)
        assert "claude_analysis" in updated_predictions[instance_id], "Analysis results were not correctly saved to file"
        
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
            
    print("Claude API and file processing integration test successful!")

if __name__ == "__main__":
    test_claude_api_request_simple()
    test_claude_analysis_function()
    test_claude_api_integration()
    print("All tests passed!") 