"""Test VNDB API interaction."""
import json
import requests

# Test 1: Fetch VN by ID
print("=== Test 1: Fetch VN v2622 ===")
r = requests.post("https://api.vndb.org/kana/vn", json={
    "filters": ["id", "=", "v2622"],
    "fields": "id, title, alttitle, titles{lang, title, latin}",
}, timeout=10)
data = r.json()
vn = data["results"][0]
print(f"ID: {vn['id']}")
print(f"Title: {vn['title']}")
print(f"AltTitle: {vn.get('alttitle', '')}")
print(f"Japanese title: {[t['title'] for t in vn.get('titles', []) if t.get('lang') == 'ja']}")

# Test 2: Fetch Releases
print("\n=== Test 2: Fetch Releases ===")
r2 = requests.post("https://api.vndb.org/kana/release", json={
    "filters": ["vn", "=", ["id", "=", "v2622"]],
    "fields": "id, title, alttitle, released, platforms, languages, producers{id, name, developer, publisher}",
    "results": 10,
}, timeout=10)
data2 = r2.json()
for i, rr in enumerate(data2.get("results", [])):
    devs = [p["name"] for p in rr.get("producers", []) if p.get("developer")]
    print(f"  [{i}] {rr['title']} | {rr.get('released', '')} | platforms={rr.get('platforms', [])} | dev={devs}")

print(f"\nTotal releases: {data2.get('count', len(data2.get('results', [])))}")