from app.catalog import Catalog
from app.retriever import Retriever

c = Catalog()
print(f"OK: {len(c.items)} items")

opq = c.get_by_name("Occupational Personality Questionnaire OPQ32r")
print(f"OPQ32r found: {opq is not None}")
if opq:
    print(f"  test_type_code: {opq.test_type_code}")
    print(f"  link: {opq.link}")

gplus = c.get_by_name("SHL Verify Interactive G+")
print(f"Verify G+ found: {gplus is not None}")

# Test retriever
r = Retriever(c)
msgs = [{"role": "user", "content": "I'm hiring a Java developer"}]
candidates = r.retrieve(msgs, top_k=10)
print(f"\nRetrieved {len(candidates)} candidates for 'Java developer':")
for item in candidates[:5]:
    print(f"  - {item.name} ({item.test_type_code})")

print("\nAll tests passed!")
