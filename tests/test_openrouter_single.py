# tests/test_openrouter_single.py
import os
import requests

api_key = os.environ.get("OPENROUTER_API_KEY")
print(f"Key set: {bool(api_key)}")

response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model":  "inclusionai/ling-3.0-tiny:free",
        "messages": [{"role": "user", "content": "Say hello in one sentence."}]
    },
    timeout=20,
)

print(f"HTTP Status: {response.status_code}")
print(response.json())