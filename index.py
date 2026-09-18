import json
import time
import urllib.request
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "2.0.0",
    "name": "Cloud Live Sports",
    "description": "Direct m3u8 football streams playing natively in Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "football", "name": "⚽ Football/Soccer"}
    ]
}

def fetch_api_data():
    try:
        # Replaced with your new direct video stream API endpoint
        url = "https://www.futbol-x.xyz/api/football.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return {"streams": []}

def is_event_live(starts_at_str, ends_at_str, always_live_val):
    if always_live_val == 1:
        return True
    try:
        # Parse the new ISO time strings (e.g. 2026-09-18T21:30:00) into a Unix timestamp
        start_ts = int(datetime.fromisoformat(starts_at_str).timestamp())
        end_ts = int(datetime.fromisoformat(ends_at_str).timestamp())
        current_ts = int(time.time())
        
        # Generous 1-hour pre-buffer and post-buffer padding for timezones
        return (start_ts - 3600) <= current_ts <= (end_ts + 3600)
    except Exception:
        return True # Fallback to true if date parsing fails so games don't disappear

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

    for group in api_data.get("streams", []):
        category = group.get("category", "Football")
        
        for item in group.get("streams", []):
            starts = item.get("starts_at", "")
            ends = item.get("ends_at", "")
            always_live = item.get("always_live", 0)

            # Check if the current match is broadcasting right now
            is_live = is_event_live(starts, ends, always_live)

            # If browsing the Live Now section, strictly hide non-live events
            if clean_catalog_id == "live_now" and not is_live:
                continue

            status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
            if clean_catalog_id == "live_now" or always_live == 1:
                status_prefix = ""

            metas.append({
                # We use uri_name as a unique tracking key string (e.g., sport_b4v1u8)
                "id": f"sport_{item['uri_name']}",
                "type": "tv",
                "name": f"{status_prefix}{item['name']}",
                "poster": item.get("poster", ""),
                "description": f"League/Tag: {item.get('tag', 'Match')} | Total Sources: {len(item.get('streams', []))}"
            })

    return jsonify({"metas": metas})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    clean_uri_name = item_id.replace(".json", "").replace("sport_", "")
    api_data = fetch_api_data()
    
    for group in api_data.get("streams", []):
        for item in group.get("streams", []):
            if item["uri_name"] == clean_uri_name:
                return jsonify({
                    "meta": {
                        "id": f"sport_{clean_uri_name}",
                        "type": "tv",
                        "name": item["name"],
                        "poster": item.get("poster", ""),
                        "description": f"League: {item.get('tag', 'Match')}"
                    }
                })
    return jsonify({"meta": {}})

@app.route('/stream/tv/<item_id>')
@app.route('/stream/tv/<item_id>.json')
def stream(item_id):
    clean_uri_name = item_id.replace(".json", "").replace("sport_", "")
    api_data = fetch_api_data()
    response_streams = []
    
    for group in api_data.get("streams", []):
        for item in group.get("streams", []):
            if item["uri_name"] == clean_uri_name:
                # Loop through all embedded feeds available for this specific match
                for idx, stream_source in enumerate(item.get("streams", [])):
                    response_streams.append({
                        "title": stream_source.get("title", f"Source Feed #{idx+1}"),
                        # Passing a direct .m3u8 URL triggers Stremio's default hardware media player window
                        "url": stream_source["url"]
                    })
                return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
