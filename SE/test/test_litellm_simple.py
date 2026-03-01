#!/usr/bin/env python3
"""
Simplest LiteLLM test - send "Hello" and print the response
"""

import litellm

def test_simple_litellm():
    """Test basic LiteLLM call"""
    print("Starting LiteLLM test...")

    # Configuration parameters
    model_name = "openai/deepseek-chat"
    api_base = "http://publicshare.a.pinggy.link"
    api_key = "EMPTY"

    print(f"Using model: {model_name}")
    print(f"API endpoint: {api_base}")

    # Build messages
    messages = [
        {"role": "user", "content": "Hello"}
    ]

    try:
        print("Calling LiteLLM...")

        # Call LiteLLM
        response = litellm.completion(
            model=model_name,
            messages=messages,
            api_base=api_base,
            api_key=api_key,
            temperature=0.7,
            max_tokens=100
        )

        print("\n=== Response ===")
        print(f"Model: {response.model}")
        print(f"Content: {response.choices[0].message.content}")
        print(f"Tokens used: {response.usage.total_tokens if response.usage else 'unknown'}")
    except Exception as e:
        print(f"Call failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_simple_litellm()
