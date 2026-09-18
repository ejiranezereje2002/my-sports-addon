import json
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces open cross-origin access policies for Stremio players

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "3.2.0",
    "name": "Cloud Live Sports",
    "description": "Dynamic multi-sport proxy streams playing natively in Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "sports_streams", "name": "⚽ Sports Streams"}
    ]
}

def fetch_api_data():
    try:
        url = "https://tap4sport.st"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            raw_data = json.loads(response.read().decode('utf-8'))
            
            # --- STRUCTURE-PROOF EXTRACTION ---
            # 1. If the API returns a direct raw list
            if isinstance(raw_data, list):
                return raw_data
            # 2. If it is wrapped in an object wrapper envelope
            if isinstance(raw_data, dict):
                if "data" in raw_data and isinstance(raw_data["data"], list):
                    return raw_data["data"]
                if "events" in raw_data and isinstance(raw_data["events"], list):
                    return raw_data["events"]
                if "streams" in raw_data and isinstance(raw_data["streams"], list):
                    return raw_data["streams"]
            return []
    except Exception:
        return []

@app.route('/')
@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)

@app.route('/catalog/tv/<catalog_id>')
@app.route('/catalog/tv/<catalog_id>.json')
def catalog(catalog_id):
    clean_catalog_id = catalog_id.replace(".json", "")
    events_list = fetch_api_data()
    metas = []

    for item in events_list:
        if not isinstance(item, dict):
            continue

        # Extract event identifiers with safety fallbacks
        match_id = item.get("id") or item.get("uri_name")
        if not match_id:
            continue
            
        is_live = item.get("_live") or item.get("is_live") or item.get("live") == 1
        sport_type = str(item.get("sport", "Live Event")).upper()
        title_name = item.get("title") or item.get("name") or "Live Sports Event"

        # Apply strict category safety filtering parameters
        if clean_catalog_id == "live_now" and not is_live:
            continue

        status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
        if clean_catalog_id == "live_now":
            status_prefix = ""

        # Construct clean metadata layout tags
        desc = f"Sport: {sport_type} | League: {item.get('league', 'Match')}"
        if item.get("home_team") and item.get("away_team"):
            desc = f"{item['home_team']} vs {item['away_team']} | {desc}"

        metas.append({
            "id": f"sport_{match_id}",
            "type": "tv",
            "name": f"{status_prefix}{title_name}",
            "poster": item.get("poster") or "https://streamed.pk",
            "description": desc
        })

    return jsonify({"metas": metas})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    clean_id = item_id.replace(".json", "").replace("sport_", "")
    events_list = fetch_api_data()
    
    for item in events_list:
        if not isinstance(item, dict):
            continue
        match_id = item.get("id") or item.get("uri_name")
        if str(match_id) == str(clean_id):
            return jsonify({
                "meta": {
                    "id": f"sport_{clean_id}",
                    "type": "tv",
                    "name": item.get("title") or item.get("name") or "Live Match",
                    "poster": item.get("poster") or "https://streamed.pk",
                    "description": f"Sport: {item.get('sport')} | League: {item.get('league', 'Match')}"
                }
            })
    return jsonify({"meta": {}})

@app.route('/stream/tv/<item_id>')
@app.route('/stream/tv/<item_id>.json')
def stream(item_id):
    clean_id = item_id.replace(".json", "").replace("sport_", "")
    events_list = fetch_api_data()
    response_streams = []
    
    for item in events_list:
        if not isinstance(item, dict):
            continue
        match_id = item.get("id") or item.get("uri_name")
        if str(match_id) == str(clean_id):
            
            # Extract stream links dynamically from the sources matrix array configuration
            sources = item.get("sources") or item.get("streams") or []
            for idx, source in enumerate(sources):
                if not isinstance(source, dict):
                    continue
                
                source_label = str(source.get("source") or source.get("title") or f"Feed #{idx+1}").upper()
                
                # Check for either a direct URL or an ID to format into the streamed.pk API route
                stream_url = source.get("url") or source.get("iframe")
                if not stream_url and source.get("id"):
                    stream_url = f"https://streamed.pk{source.get('id')}"
                
                if stream_url:
                    response_streams.append({
                        "title": f"Play Link ({source_label})",
                        "url": stream_url,
                        "behaviorHints": {
                            "notWebReady": True  # Seamless player handover rule for mobile players
                        }
                    })
            return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
