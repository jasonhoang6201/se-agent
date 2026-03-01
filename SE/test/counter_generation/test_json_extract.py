#!/usr/bin/env python
"""
Test JSON extraction functionality
"""

import sys
import json
from pathlib import Path
import re

# Get the directory of the current script
current_dir = Path(__file__).parent
# Ensure the claude module can be imported
sys.path.insert(0, str(current_dir))

# Import the API to test
from claude import ClaudeAPI, extract_content

def test_json_extraction():
    """Test extracting JSON content from Claude API responses"""

    # Simulate Claude API response with JSON code block format
    sample_response_with_code_block = {
        "id": "msg_01NLR3UDjC4qWJVnYBC4bK1v",
        "type": "message",
        "role": "assistant",
        "model": "claude-3-7-sonnet-20250219",
        "content": [
            {
                "type": "text",
                "text": "```json\n{\n  \"approach_summary\": \"Initialize variables\",\n  \"modified_files\": [\"file1.py\", \"file2.py\"],\n  \"key_changes\": \"Added initialization code\"\n}\n```"
            }
        ],
        "stop_reason": "end_turn"
    }

    # Simulate pure JSON format response
    sample_response_pure_json = {
        "id": "msg_01NLR3UDjC4qWJVnYBC4bK1v",
        "type": "message",
        "role": "assistant",
        "model": "claude-3-7-sonnet-20250219",
        "content": [
            {
                "type": "text",
                "text": "{\"approach_summary\": \"Initialize variables\", \"modified_files\": [\"file1.py\", \"file2.py\"], \"key_changes\": \"Added initialization code\"}"
            }
        ],
        "stop_reason": "end_turn"
    }

    # Test extracting JSON from code block
    print("Testing JSON extraction from code block:")
    content = extract_content(sample_response_with_code_block)
    print(f"Extracted content: {content}")

    # Try to extract JSON
    json_pattern = r"```json\s*([\s\S]*?)\s*```"
    json_match = re.search(json_pattern, content)

    if json_match:
        json_content = json_match.group(1)
        parsed_json = json.loads(json_content)
        print(f"Parsed JSON: {parsed_json}")
    else:
        print("No JSON code block found")

        # Try to extract generic JSON
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_content = content[start_idx:end_idx]
            parsed_json = json.loads(json_content)
            print(f"Parsed generic JSON: {parsed_json}")
        else:
            print("No JSON content found")

    # Test extracting JSON from plain text
    print("\nTesting JSON extraction from plain text:")
    content = extract_content(sample_response_pure_json)
    print(f"Extracted content: {content}")

    # Try to extract JSON
    json_pattern = r"```json\s*([\s\S]*?)\s*```"
    json_match = re.search(json_pattern, content)

    if json_match:
        json_content = json_match.group(1)
        parsed_json = json.loads(json_content)
        print(f"Parsed JSON: {parsed_json}")
    else:
        print("No JSON code block found")

        # Try to extract generic JSON
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_content = content[start_idx:end_idx]
            parsed_json = json.loads(json_content)
            print(f"Parsed generic JSON: {parsed_json}")
        else:
            print("No JSON content found")

if __name__ == "__main__":
    test_json_extraction()
