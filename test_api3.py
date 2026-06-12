"""Test VNDB release API with fixed languages field."""
import requests, json

r = requests.post("https://api.vndb.org/kana/release", json={
    "filters": ["vn", "=", ["id", "=", "v2622"]],
    "fields": "id, title, alttitle, released, platforms, languages{lang}, producers{id, name, developer, publisher}",
    "results": 5,
}, timeout=10)

print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Count: {data.get('count', '?')}")
    for i, rr in enumerate(data.get("results", [])):
        devs = [p["name"] for p in rr.get("producers", []) if p.get("developer")]
        langs = [l.get("lang") for l in rr.get("languages", [])]
        print(f"  [{i}] {rr['title']} | {rr.get('released', '')} | platforms={rr.get('platforms', [])} | langs={langs} | dev={devs}")
else:
    print(f"Error: {r.text}")