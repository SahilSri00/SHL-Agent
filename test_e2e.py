"""End-to-end test: hit /health then /chat with a real conversation."""
import requests
import json
import sys

BASE = "http://localhost:8000"

# 1. Health check
print("=== Health Check ===")
r = requests.get(f"{BASE}/health")
print(f"Status: {r.status_code} | Body: {r.json()}")
assert r.status_code == 200
assert r.json() == {"status": "ok"}
print("PASS\n")

# 2. Simple chat - vague query (should clarify, NOT recommend)
print("=== Test: Vague query should clarify ===")
r = requests.post(f"{BASE}/chat", json={
    "messages": [
        {"role": "user", "content": "I need an assessment"}
    ]
}, timeout=30)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Reply: {data['reply'][:200]}")
print(f"Recommendations: {data['recommendations']}")
print(f"End of conversation: {data['end_of_conversation']}")
assert r.status_code == 200
assert data["recommendations"] is None, "Should NOT recommend on vague query!"
assert data["end_of_conversation"] == False
print("PASS\n")

# 3. Specific query (should recommend)
print("=== Test: Specific query should recommend ===")
r = requests.post(f"{BASE}/chat", json={
    "messages": [
        {"role": "user", "content": "I'm hiring a senior Java developer with Spring and SQL experience. They need to own microservice delivery. What assessments should I use?"}
    ]
}, timeout=30)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Reply: {data['reply'][:200]}")
if data["recommendations"]:
    print(f"Recommendations ({len(data['recommendations'])}):")
    for rec in data["recommendations"]:
        print(f"  - {rec['name']} ({rec['test_type']}) -> {rec['url']}")
else:
    print("Recommendations: None (agent may want to clarify more)")
print(f"End of conversation: {data['end_of_conversation']}")
assert r.status_code == 200
print("PASS\n")

# 4. Off-topic refusal
print("=== Test: Off-topic refusal ===")
r = requests.post(f"{BASE}/chat", json={
    "messages": [
        {"role": "user", "content": "What's the best way to fire an employee legally?"}
    ]
}, timeout=30)
data = r.json()
print(f"Reply: {data['reply'][:200]}")
print(f"Recommendations: {data['recommendations']}")
assert data["recommendations"] is None, "Should NOT recommend for off-topic!"
print("PASS\n")

print("=== ALL TESTS PASSED ===")
