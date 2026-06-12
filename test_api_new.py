"""Test the new VNDB API (kana) endpoints."""
import requests

# Test 1: VN endpoint
print("=== VN Test ===")
r = requests.post("https://api.vndb.org/kana/vn", json={
    "filters": ["id", "=", "v2622"],
    "fields": "id, title, alttitle, titles{lang, title, latin}, image{url,dims,sexual,violence,votecount}",
}, timeout=15)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    vn = d["results"][0]
    print(f"  title: {vn.get('title')}")
    print(f"  image: {vn.get('image')}")

# Test 2: Release endpoint
print("\n=== Release Test ===")
r2 = requests.post("https://api.vndb.org/kana/release", json={
    "filters": ["vn", "=", ["id", "=", "v2622"]],
    "fields": "id, title, alttitle, released, platforms, languages{lang}, producers{id, name, developer, publisher}, media{medium, qty}",
    "results": 10,
}, timeout=15)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    d2 = r2.json()
    print(f"  more: {d2.get('more')}")
    for rr in d2.get("results", []):
        langs = [l["lang"] for l in rr.get("languages", [])]
        devs = [p["name"] for p in rr.get("producers", []) if p.get("developer")]
        print(f"  {rr['id']}: {rr['title']} | {rr.get('released')} | langs={langs} | dev={devs}")
else:
    print(f"  Error: {r2.text}")

# Test 3: Search by title
print("\n=== Search Test ===")
r3 = requests.post("https://api.vndb.org/kana/vn", json={
    "filters": ["search", "=", "Clannad"],
    "fields": "id, title, alttitle",
    "results": 5,
}, timeout=15)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    d3 = r3.json()
    for vn in d3.get("results", []):
        print(f"  {vn['id']}: {vn['title']}")

# Test 4: Producer endpoint
print("\n=== Producer Test ===")
r4 = requests.post("https://api.vndb.org/kana/producer", json={
    "filters": ["id", "=", "p129"],
    "fields": "id, name, alias, lang, type, description",
}, timeout=15)
print(f"Status: {r4.status_code}")
if r4.status_code == 200:
    d4 = r4.json()
    for p in d4.get("results", []):
        print(f"  {p['id']}: {p['name']} | lang={p.get('lang')} | type={p.get('type')}")