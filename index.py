import json
import time
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces explicit cross-origin permissions for Stremio app clients

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "5.0.0",
    "name": "Cloud Live Sports",
    "description": "Multi-sport live streaming streams playing natively inside Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "american_football", "name": "🏈 American Football"},
        {"type": "tv", "id": "australian_football", "name": "🦘 Australian Football"},
        {"type": "tv", "id": "baseball", "name": "⚾ Baseball"},
        {"type": "tv", "id": "basketball", "name": "🏀 Basketball"},
        {"type": "tv", "id": "combat_sports", "name": "🥊 Combat Sports"},
        {"type": "tv", "id": "cricket", "name": "🏏 Cricket"},
        {"type": "tv", "id": "football", "name": "⚽ Football/Soccer"},
        {"type": "tv", "id": "golf", "name": "⛳ Golf"},
        {"type": "tv", "id": "ice_hockey", "name": "🏒 Ice Hockey"},
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
    "combat_sports": "Combat Sports",
    "cricket": "Cricket",
    "football": "Football",
    "golf": "Golf",
    "ice_hockey": "Ice Hockey",
    "motorsports": "Motorsports",
    "rugby": "Rugby",
    "wrestling": "Wrestling",
    "streams_247": "24/7 Streams"
}

def fetch_api_data():
    try:
        url = "https://api.ppv.st/api/streams"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return {"streams": []}

@app.route('/')
@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)

@app.route('/catalog/tv/<catalog_id>')
@app.route('/catalog/tv/<catalog_id>.json')
def catalog(catalog_id):
    clean_catalog_id = catalog_id.replace(".json", "")
    api_data = fetch_api_data()
    metas = []
    current_time = int(time.time())

    for group in api_data.get("streams", []):
        category = group.get("category", "Sports")
        
        # Verify requested target catalog mapping parameter rules
        if clean_catalog_id != "live_now" and category != CATEGORY_MAPPING.get(clean_catalog_id):
            continue

        for item in group.get("streams", []):
            starts = item.get("starts_at", 0)
            ends = item.get("ends_at", 0)
            is_always_live = item.get("always_live", 0) == 1 or group.get("always_live") is True
            
            # Live state window checks
            is_live = is_always_live or (starts <= current_time <= ends)
            
            # If browsing the 'Live Now' view row block, strictly bypass non-live events
            if clean_catalog_id == "live_now" and not is_live:
                continue

            status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
            if clean_catalog_id == "live_now" or is_always_live:
                status_prefix = ""

            metas.append({
                "id": f"sport_{item['id']}",
                "type": "tv",
                "name": f"{status_prefix}{item['name']}",
                "poster": item.get("poster", ""),
                "description": f"Sport: {category} | Source: {item.get('source_tag', 'Live Broadcast')}"
            })

    return jsonify({"metas": metas})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    try:
        clean_id = int(item_id.replace(".json", "").replace("sport_", ""))
    except Exception:
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
                        "description": f"Source Tag: {item.get('source_tag')}"
                    }
                })
    return jsonify({"meta": {}})

@app.route('/stream/tv/<item_id>')
@app.route('/stream/tv/<item_id>.json')
def stream(item_id):
    try:
        clean_id = int(item_id.replace(".json", "").replace("sport_", ""))
    except Exception:
        return jsonify({"streams": []})
        
    api_data = fetch_api_data()
    response_streams = []
    
    for group in api_data.get("streams", []):
        for item in group.get("streams", []):
            if item["id"] == clean_id:
                # Main Feed Route Setup - Forces internal iframe layout rendering inside Stremio's window
                response_streams.append({
                    "title": f"Play inside {item.get('source_tag', 'Stremio Player')}",
                    "url": item["iframe"],
                    "behaviorHints": {
                        "notWebReady": True  # Crucial hint parameter to prevent player format crashes
                    }
                })
                
                # Substreams Route Setup
                for idx, sub in enumerate(item.get("substreams", [])):
                    sub_label = sub.get("source_tag") or sub.get("locale", "").upper() or f"Feed #{idx+2}"
                    response_streams.append({
                        "title": f"Play inside {sub_label}",
                        "url": sub["iframe"],
                        "behaviorHints": {
                            "notWebReady": True
                        }
                    })
                    
                return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
