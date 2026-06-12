"""Debug script: check API response for v50215 to diagnose missing group data."""

import sys
sys.path.insert(0, "src")

from core.vndb_api import VNDBAPIClient

client = VNDBAPIClient()

# Fetch releases for v50215
import json

payload = {
    "filters": ["vn", "=", ["id", "=", "v50215"]],
    "fields": "id, title, alttitle, released, platforms, languages{lang}, producers{id, name, original, developer, publisher}",
    "results": 100,
}

data = client._post("release", payload)
results = data.get("results", [])

print(f"\nTotal releases found: {len(results)}")
print("=" * 80)

for i, r in enumerate(results):
    print(f"\n--- Release {i+1} ---")
    print(f"ID: {r.get('id')}")
    print(f"Title: {r.get('title')}")
    print(f"AltTitle: {r.get('alttitle')}")
    print(f"Released: {r.get('released')}")
    print(f"Platforms: {r.get('platforms')}")
    
    langs = [l.get('lang') for l in r.get('languages', []) if isinstance(l, dict)]
    print(f"Languages: {langs}")
    
    producers = r.get('producers', [])
    print(f"Producers ({len(producers)}):")
    for p in producers:
        if isinstance(p, dict):
            print(f"  - id={p.get('id')}, name={p.get('name')}, original={p.get('original')}, "
                  f"developer={p.get('developer')}, publisher={p.get('publisher')}")
    
    # Check if it's Chinese
    is_zh = any(lang in ("zh-Hans", "zh-Hant", "zh") for lang in langs)
    print(f"Is Chinese: {is_zh}")
    
    # Simulate the class methods
    if producers:
        for p in producers:
            if isinstance(p, dict) and p.get('developer'):
                print(f"  -> Developer: {p.get('original') or p.get('name')}")
                break
        else:
            if producers:
                print(f"  -> Fallback dev (first producer): {producers[0].get('original') or producers[0].get('name')}")
    
    if is_zh:
        print(f"  *** CHINESE RELEASE ***")