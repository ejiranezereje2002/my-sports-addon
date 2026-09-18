import json
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces complete cross-origin compliance for Stremio mobile clients

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "3.1.0",
    "name": "Cloud Live Sports",
    "description": "Live multi-sport streams playing natively inside Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "football", "name": "⚽ Sports Streams"}
    ]
}

def fetch_api_data():
    try:
        url = "https://tap4sport.st"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return {"data": []}

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

    for item in api_data.get("data", []):
        # Fallback values to prevent extraction errors if fields are missing
        match_id = item.get("id", "")
        if not match_id:
            continue
            
        is_live = item.get("_live", False)
        sport_type = item.get("sport", "Live Event").upper()
        title_name = item.get("title", "Live Match")

        # Force label string tags cleanly on the card layout
        status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
        if clean_catalog_id == "live_now":
            status_prefix = ""

        # Build clean visual row details
        desc = f"Sport: {sport_type} | League: {item.get('league', 'Sports Match')}"
        if item.get("home_team") and item.get("away_team"):
            desc = f"{item['home_team']} vs {item['away_team']} | {desc}"

        metas.append({
            "id": f"sport_{match_id}",
            "type": "tv",
            "name": f"{status_prefix}{title_name}",
            "poster": item.get("poster", "https://streamed.pk"),
            "description": desc
        })

    return jsonify({"metas": metas})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    clean_id = item_id.replace(".json", "").replace("sport_", "")
    api_data = fetch_api_data()
    
    for item in api_data.get("data", []):
        if str(item.get("id")) == str(clean_id):
            return jsonify({
                "meta": {
                    "id": f"sport_{clean_id}",
                    "type": "tv",
                    "name": item.get("title", "Live Match"),
                    "poster": item.get("poster", "https://streamed.pk"),
                    "description": f"Sport: {item.get('sport')} | League: {item.get('league', 'Match')}"
                }
            })
    return jsonify({"meta": {}})

@app.route('/stream/tv/<item_id>')
@app.route('/stream/tv/<item_id>.json')
def stream(item_id):
    clean_id = item_id.replace(".json", "").replace("sport_", "")
    api_data = fetch_api_data()
    response_streams = []
    
    for item in api_data.get("data", []):
        if str(item.get("id")) == str(clean_id):
            # Extrapolate alternative feeds natively from sources matrix array
            for idx, source in enumerate(item.get("sources", [])):
                source_label = source.get("source", f"Feed #{idx+1}").upper()
                source_id = source.get("id", "")
                
                if source_id:
                    # Construct valid native web player stream paths
                    stream_url = f"https://streamed.pk{source_id}"
                    
                    response_streams.append({
                        "title": f"Play Link ({source_label})",
                        "url": stream_url,
                        "behaviorHints": {
                            "notWebReady": True  # Forces smooth handover to phone apps like VLC
                        }
                    })
            return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
