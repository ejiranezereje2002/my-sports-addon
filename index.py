import json
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces open access rules for Stremio clients

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "2.2.0",
    "name": "Cloud Live Sports",
    "description": "Direct football streams playing natively in Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "football", "name": "⚽ Football/Soccer"}
    ]
}

def fetch_api_data():
    try:
        url = "https://www.futbol-x.xyz/api/football.json"
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
    api_data = fetch_api_data()
    metas = []

    # Loop through the API's main streams groupings
    for group in api_data.get("streams", []):
        for item in group.get("streams", []):
            
            # Use structural fallback checking to label ongoing games safely
            is_live_flag = item.get("always_live") == 1 or item.get("is_live") is True or item.get("live") == 1
            status_prefix = "🔴 LIVE: " if is_live_flag else "⏳ MATCH: "

            metas.append({
                "id": f"sport_{item['uri_name']}",
                "type": "tv",
                "name": f"{status_prefix}{item['name']}",
                "poster": item.get("poster", ""),
                "description": f"League/Tag: {item.get('tag', 'Match')} | Feeds: {len(item.get('streams', []))}"
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
                        "url": stream_source["url"],
                        # ⚠️ THIS FIXES THE MOBILE LOADING ERROR:
                        # It tells Stremio to open the stream link using an external player app on your phone
                        "behaviorHints": {
                            "notWebReady": True
                        }
                    })
                return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
