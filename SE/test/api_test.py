from openai import OpenAI
import requests

"""
API Test Script - Fixed Version

Note: Testing revealed that basic requests work, but extra parameters (such as chat_template_kwargs)
cause a server error: "name 'base_url' is not defined"
"""

# API configuration
openai_api_key = "EMPTY"
openai_api_base = "http://publicshare.a.pinggy.link"

# Test API connection
print("Testing basic API connection...")
try:
    response = requests.get(openai_api_base)
    print(f"API endpoint status: {response.status_code}")
    print(f"Response content: {response.text[:100]}...")  # Only print first 100 characters
except Exception as e:
    print(f"Failed to connect to API endpoint: {e}")

# Initialize client
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

# Try basic API request (working method)
try:
    print("\nAttempting basic API request...")
    chat_response = client.chat.completions.create(
        model="openai/deepseek-chat",
        messages=[
            {"role": "user", "content": "Who you are?"}
        ],
        temperature=0.6,
    )
    print("Response successful!")
    print(f"Model: {chat_response.model}")
    print(f"Content: {chat_response.choices[0].message.content}")
    print(f"Tokens used: {chat_response.usage.total_tokens}")
except Exception as e:
    print(f"Request failed: {e}")

# Note: The request below causes a server error, so it has been commented out
"""
try:
    print("\nAttempting request with extra parameters (may fail)...")
    chat_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "Who you are?"},
        ],
        temperature=0.6,
        top_p=0.95,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": True},  # This parameter causes a server error
        }, 
    )
    print("Response successful:", chat_response)
except Exception as e:
    print(f"Expected error: {e}")
"""