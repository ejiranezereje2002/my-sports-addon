import json
import time
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "1.5.0",
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

# Strict 1-to-1 match with the actual group names returned in your API response
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
    "streams_247": "24/7 Streams"  # Fixed mapping string
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
    
    # Target timestamp from API payload data metrics
    current_time = int(time.time())

    for group in api_data.get("streams", []):
        category = group.get("category", "Sports")
        
        # Verify catalog request tracking parameters
        target_mapped_name = CATEGORY_MAPPING.get(clean_catalog_id)
        if clean_catalog_id != "live_now" and category != target_mapped_name:
            continue

        for item in group.get("streams", []):
            starts = item.get("starts_at", 0)
            ends = item.get("ends_at", 0)
            
            # Check flag values or general category overrides
            is_always_live = item.get("always_live", 0) == 1 or group.get("always_live") is True

            # Evaluate broadcast timeline parameters
            # Adding a 1-hour pre-buffer and post-buffer window to protect against clock deviations
            is_live = is_always_live or ((starts - 3600) <= current_time <= (ends + 3600))

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
                })import json
import time
import urllib.request
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "2.1.0",
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
        url = "https://futbol-x.xyz"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return {"streams": []}

def check_live_status(item, group):
    """
    Timezone-proof logic to determine if a stream is live.
    Checks API flags first, then falls back to a smart current-day filter.
    """
    # 1. Check if the API explicitly flags it as live right now
    if item.get("always_live") == 1 or group.get("always_live") is True:
        return True
    if item.get("is_live") is True or item.get("live") == 1:
        return True

    # 2. Backup check: Parse timestamps safely
    try:
        starts_str = item.get("starts_at", "")
        ends_str = item.get("ends_at", "")
        
        if starts_str:
            # We strip any trailing time offsets to compare raw relative hours
            clean_start = starts_str.split(".")[0].replace("Z", "")
            start_dt = datetime.fromisoformat(clean_start)
            
            # Get current time *without* timezone bias
            now_dt = datetime.utcnow() if "T" in starts_str else datetime.now()
            
            # If the match was scheduled for today and hasn't ended, display it as Live/Available
            if start_dt.date() == now_dt.date():
                return True
    except Exception:
        pass
        
    return False

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
        for item in group.get("streams", []):
            
            # Run our updated timezone-proof live function check
            is_live = check_live_status(item, group)

            # If browsing 'Live Now' but the item isn't running, skip it
            if clean_catalog_id == "live_now" and not is_live:
                continue

            status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
            if clean_catalog_id == "live_now":
                status_prefix = ""

            metas.append({
                "id": f"sport_{item['uri_name']}",
                "type": "tv",
                "name": f"{status_prefix}{item['name']}",
                "poster": item.get("poster", ""),
                "description": f"League/Tag: {item.get('tag', 'Match')} | Active Streams: {len(item.get('streams', []))}"
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
                for idx, stream_source in enumerate(item.get("streams", [])):
                    response_streams.append({
                        "title": stream_source.get("title", f"Source Feed #{idx+1}"),
                        "url": stream_source["url"]
                    })
                return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

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
                        "title": f"Embed Play on {item.get('source_tag', 'Stremio Player')}",
                        "url": item["iframe"],
                        # This extra parameter fixes the black screen bug by telling Stremio it is loading an iframe page layout
                        "behaviorHints": {
                            "notWebReady": True
                        }
                    }]
                })
    return jsonify({"streams": []})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
