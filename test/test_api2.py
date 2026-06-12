"""Debug VNDB release API - fix languager field."""
import requests

# languages needs sub-fields, e.g. languages{lang}
r2 = requests.post("https://api.vndb.org/kana/release", json={
    "filters": ["vn", "=", ["id", "=", "v2622"]],
    "fields": "id, title, alttitle, released, platforms, languages{lang}, producers{id, name, developer, publisher}",
    "results": 10,
}, timeout=10)

print(f"Status: {r2.status_code}")
print(f"Body (first 3000): {r2.text[:3000]}")