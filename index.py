import json
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Keeps communication completely open for Stremio cross-origin checks

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "3.0.0",
    "name": "Cloud Live Sports",
    "description": "Live multi-sport streams playing natively inside Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "football", "name": "⚽ Football/Soccer"},
        {"type": "tv", "id": "american_football", "name": "🏈 American Football"},
        {"type": "tv", "id": "basketball", "name": "🏀 Basketball"},
        {"type": "tv", "id": "baseball", "name": "⚾ Baseball"},
        {"type": "tv", "id": "darts", "name": "🎯 Darts"},
        {"type": "tv", "id": "motor_sports", "name": "🏎️ Motorsports"}
    ]
}

# Standardized mapping between your catalog keys and the incoming API strings
SPORT_MAPPING = {
    "football": "Football",
    "american_football": "american-football",
    "basketball": "Basketball",
    "baseball": "Baseball",
    "darts": "Darts",
    "motor_sports": "motor-sports"
}

def fetch_api_data():
    try:
        # Replaced with your new proxy API endpoint
        url = "https://tap4sport.st/api/events-proxy"
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

    # The new API houses items directly inside a "data" array list
    for item in api_data.get("data", []):
        is_live = item.get("_live", False)
        item_sport = item.get("sport", "")

        # Category Filter logic
        if clean_catalog_id == "live_now":
            if not is_live:
                continue
        else:
            mapped_sport = SPORT_MAPPING.get(clean_catalog_id)
            if item_sport != mapped_sport:
                continue

        status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
        if clean_catalog_id == "live_now":
            status_prefix = ""

        # Build neat description text using home and away team keys if available
        desc = f"League: {item.get('league', 'Sports Match')}"
        if item.get("away_team"):
            desc = f"{item['home_team']} vs {item['away_team']} | {desc}"

        metas.append({
            "id": f"sport_{item['id']}",
            "type": "tv",
            "name": f"{status_prefix}{item['title']}",
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
        if item["id"] == clean_id:
            return jsonify({
                "meta": {
                    "id": f"sport_{clean_id}",
                    "type": "tv",
                    "name": item["title"],
                    "poster": item.get("poster", ""),
                    "description": f"Sport: {item.get('sport')} | League: {item.get('league')}"
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
        if item["id"] == clean_id:
            # Loop through all embedded feeds/sources available for this match
            for idx, source in enumerate(item.get("sources", [])):
                source_name = source.get("source", f"Feed #{idx+1}").upper()
                
                # Constructing standard web-ready streaming URLs from the source IDs
                # Note: If these targets use raw m3u8 playlist files, they trigger native playback.
                stream_url = f"https://streamed.pk{source.get('id')}"
                
                response_streams.append({
                    "title": f"Watch Link ({source_name})",
                    "url": stream_url,
                    "behaviorHints": {
                        "notWebReady": True  # Forces Android/iOS to hand playback safely to an external app (VLC/MX)
                    }
                })
            return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
