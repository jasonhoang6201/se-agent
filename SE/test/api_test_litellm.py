#!/usr/bin/env python3
"""
Test deepseek model connection using LiteLLM
"""

import litellm
import requests

# Test API connection
API_BASE = "http://publicshare.a.pinggy.link"
API_KEY = "EMPTY"  # Use the same key as the original test

def test_api_endpoint():
    """Test API endpoint connection"""
    print("Testing API endpoint connection...")
    try:
        response = requests.get(API_BASE)
        print(f"API endpoint status: {response.status_code}")
        print(f"Response content: {response.text[:100]}...")  # Only print first 100 characters
    except Exception as e:
        print(f"Failed to connect to API endpoint: {e}")

def test_different_providers():
    """Try different provider prefixes"""
    # Try different provider prefixes
    providers = [
        "vllm/deepseek-chat",
        "openai/deepseek-chat",
        "deepseek-chat",
        "custom/deepseek-chat",
        "deepseek/deepseek-chat"
    ]

    for model_name in providers:
        print(f"\nTrying model name: {model_name}")
        try:
            # Simplest request
            response = litellm.completion(
                model=model_name,
                messages=[{"role": "user", "content": "Hi"}],
                api_base=API_BASE,
                api_key=API_KEY,
                max_tokens=10  # Limit response length to speed up testing
            )

            print("Success!")
            print(f"Model: {response.model}")
            print(f"Content: {response.choices[0].message.content}")
            return model_name  # Return the valid model name

        except Exception as e:
            print(f"Failed: {e}")

    return None  # All attempts failed

def try_custom_completion_with_provider(working_model=None):
    """Test completion with custom parameters"""
    model_name = working_model or "custom/deepseek-chat"
    print(f"\nTrying custom parameters with model {model_name}...")

    try:
        # Enable litellm debug mode
        litellm.set_verbose = True

        print("Calling LiteLLM...")
        response = litellm.completion(
            model=model_name,
            messages=[{"role": "user", "content": "Who are you?"}],
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.6,
        )

        print("\n=== Response ===")
        print(f"Model: {response.model}")
        print(f"Content: {response.choices[0].message.content}")
        print(f"Tokens used: {response.usage.total_tokens if response.usage else 'unknown'}")

    except Exception as e:
        print(f"Call failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    # First test API endpoint connection
    test_api_endpoint()

    # Then try different providers
    working_model = test_different_providers()

    # If a valid model name is found, try using it
    try_custom_completion_with_provider(working_model)
