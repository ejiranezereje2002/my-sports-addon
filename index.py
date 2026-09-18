import json
import time
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces global CORS rules so Stremio never gets empty responses

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "1.4.0",
    "name": "Cloud Live Sports",
    "description": "Live sports sorted by category and live status!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "american_football", "name": "🏈 American Football"},
        {"type": "tv", "id": "australian_football", "name": "🦘 Australian Football"},
        {"type": "tv", "id": "baseball", "name": "⚾ Baseball"},
        {"type": "tv", "id": "basketball", "name": "🏀 Basketball"},
        {"type": "tv", "id": "cricket", "name": "🏏 Cricket"},
        {"type": "tv", "id": "darts", "name": "🎯 Darts"},
        {"type": "tv", "id": "football", "name": "⚽ Football/Soccer"},
        {"type": "tv", "id": "motorsports", "name": "🏎️ Motorsports"},
        {"type": "tv", "id": "rugby", "name": "🏉 Rugby"},
        {"type": "tv", "id": "wrestling", "name": "🤼 Wrestling"},
        {"type": "tv", "id": "streams_247", "name": "📺 24/7 Streams"}
    ]
}

CATEGORY_MAPPING = {
    "american_football": "American Football",
    "australian_football": "Australian Football",
    "baseball": "Baseball",
    "basketball": "Basketball",
    "cricket": "Cricket",
    "darts": "Darts",
    "football": "Football",
    "motorsports": "Motorsports",
    "rugby": "Rugby",
    "wrestling": "Wrestling",
    "streams_247": "24/7 Streams"
}

def fetch_api_data():
    try:
        url = "https://ppv.st"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return {"streams": []}

# Catch-all base routes for the manifest file
@app.route('/')
@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)

# Explicit string parameters to bypass catalog string extraction bugs
@app.route('/catalog/tv/<catalog_id>')
@app.route('/catalog/tv/<catalog_id>.json')
def catalog(catalog_id):
    # Remove any trailing extension artifacts injected by Stremio clients
    clean_catalog_id = catalog_id.replace(".json", "")
    
    api_data = fetch_api_data()
    metas = []
    current_time = int(time.time())

    for group in api_data.get("streams", []):
        category = group.get("category", "Sports")
        
        # Verify the requested catalog matches the group category mapping
        if clean_catalog_id != "live_now" and category != CATEGORY_MAPPING.get(clean_catalog_id):
            continue

        for item in group.get("streams", []):
            starts = item.get("starts_at", 0)
            ends = item.get("ends_at", 0)
            is_always_live = item.get("always_live", 0) == 1 or group.get("always_live") is True
            is_live = is_always_live or (starts <= current_time <= ends)

            # Filter out non-live listings strictly if looking inside the "Live Now" view block
            if clean_catalog_id == "live_now" and not is_live:
                continue

            status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
            if clean_catalog_id == "live_now":
                status_prefix = ""

            metas.append({
                "id": f"sport_{item['id']}",
                "type": "tv",
                "name": f"{status_prefix}{item['name']}",
                "poster": item.get("poster", ""),
                "description": f"Sport: {category} | Source: {item.get('source_tag', 'Live')}"
            })
    return jsonify({"metas": metas})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    clean_id_str = item_id.replace(".json", "").replace("sport_", "")
    try:
        clean_id = int(clean_id_str)
    except ValueError:
        return jsonify({"meta": {}})
        
    api_data = fetch_api_data()
    for group in api_data.get("streams", []):
        for item in group.get("streams", []):
            if item["id"] == clean_id:
                return jsonify({
                    "meta": {
                        "id": f"sport_{clean_id}",
                        "type": "tv",
                        "name": item["name"],
                        "poster": item.get("poster", ""),
                        "description": f"Source: {item.get('source_tag')}"
                    }
                })
    return jsonify({"meta": {}})

@app.route('/stream/tv/<item_id>')
@app.route('/stream/tv/<item_id>.json')
def stream(item_id):
    clean_id_str = item_id.replace(".json", "").replace("sport_", "")
    try:
        clean_id = int(clean_id_str)
    except ValueError:
        return jsonify({"streams": []})
        
    api_data = fetch_api_data()
    for group in api_data.get("streams", []):
        for item in group.get("streams", []):
            if item["id"] == clean_id:
                return jsonify({
                    "streams": [{
                        "title": f"Watch on {item.get('source_tag', 'Web Player')}",
                        "externalUrl": item["iframe"]
                    }]
                })
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
