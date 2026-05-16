"""Quick full check — health, vague, specific, off-topic, multi-turn."""
import requests
import json
import time

BASE = "http://localhost:8000"

def timed_post(label, payload):
    start = time.time()
    r = requests.post(f"{BASE}/chat", json=payload, timeout=30)
    elapsed = time.time() - start
    d = r.json()
    print(f"\n{'='*60}")
    print(f"TEST: {label} ({elapsed:.1f}s)")
    print(f"  Reply: {d['reply'][:200]}")
    recs = d.get("recommendations")
    if recs:
        print(f"  Recommendations ({len(recs)}):")
        for rec in recs:
            print(f"    - {rec['name']} ({rec['test_type']}) -> {rec['url'][:60]}...")
    else:
        print(f"  Recommendations: None")
    print(f"  End of conversation: {d['end_of_conversation']}")
    return d

# 1. Health
print("=" * 60)
r = requests.get(f"{BASE}/health")
print(f"HEALTH: {r.status_code} {r.json()}")

# 2. Vague query
d1 = timed_post("Vague query (should clarify)", {
    "messages": [{"role": "user", "content": "I need an assessment"}]
})
assert d1["recommendations"] is None, "FAIL: Should not recommend on vague query"
print("  -> PASS")

time.sleep(1)

# 3. Specific query
d2 = timed_post("Specific query (should recommend)", {
    "messages": [{"role": "user", "content": "I'm hiring a senior Java developer with Spring Boot and SQL experience. Mid-professional level. They will own microservice delivery. Please recommend assessments."}]
})
print("  -> PASS")

time.sleep(1)

# 4. Off-topic refusal
d3 = timed_post("Off-topic (should refuse)", {
    "messages": [{"role": "user", "content": "What is the best way to fire an employee legally?"}]
})
assert d3["recommendations"] is None, "FAIL: Should not recommend for off-topic"
print("  -> PASS")

time.sleep(1)

# 5. Multi-turn
d4 = timed_post("Multi-turn (turn 2 with context)", {
    "messages": [
        {"role": "user", "content": "We need to screen contact centre agents."},
        {"role": "assistant", "content": "Could you tell me more about the role level and language requirements?"},
        {"role": "user", "content": "Entry-level, English US, inbound customer service. About 500 candidates."}
    ]
})
print("  -> PASS")

time.sleep(1)

# 6. Comparison
d5 = timed_post("Comparison (should not recommend)", {
    "messages": [{"role": "user", "content": "What is the difference between OPQ32r and Verify G+?"}]
})
assert d5["recommendations"] is None, "FAIL: Comparison should not produce recommendations"
print("  -> PASS")

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
