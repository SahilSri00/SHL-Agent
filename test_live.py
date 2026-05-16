import requests
import json
import time

# Your live Render URL
LIVE_URL = "https://shl-agent-4om5.onrender.com"

print("1. Testing /health endpoint...")
health_res = requests.get(f"{LIVE_URL}/health")
try:
    print(f"Status: {health_res.status_code} | Body: {health_res.json()}\n")
except Exception:
    print(f"Status: {health_res.status_code} | Body: {health_res.text}\n")

print("2. Testing /chat endpoint with a specific query...")
start = time.time()
chat_res = requests.post(
    f"{LIVE_URL}/chat",
    json={
        "messages": [
            {"role": "user", "content": "I'm hiring a senior Java developer. Please recommend some assessments."}
        ]
    },
    timeout=60
)
elapsed = time.time() - start

print(f"Response received in {elapsed:.1f} seconds (Status: {chat_res.status_code})")
try:
    print("Response JSON:")
    print(json.dumps(chat_res.json(), indent=2))
except Exception:
    print(f"Raw Response: {chat_res.text}")
