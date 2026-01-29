import httpx
import json

def search():
    url = "https://earth-search.aws.element84.com/v1/search"
    query = {
        "collections": ["sentinel-2-l2a"],
        "bbox": [88.8, 21.6, 89.3, 22.1], 
        "datetime": "2025-01-01T00:00:00Z/2026-01-27T23:59:59Z",
        "limit": 100,
        "query": { "eo:cloud_cover": {"lt": 5} }
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post(url, json=query)
        if response.status_code == 200:
            data = response.json()
            for feat in data['features']:
                if "45QXD" in feat['id']:
                    print(f"MATCH_FOUND_2026|{feat['id']}|{feat['assets']['red']['href']}|{feat['assets']['nir']['href']}|{feat['assets']['swir16']['href']}")
                    return
            print("NO_2026_TILE_MATCH_FOUND")
if __name__ == "__main__":
    search()
