import json
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces explicit cross-origin resource permissions for Stremio app clients

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "3.3.0",
    "name": "Cloud Live Sports",
    "description": "Adaptive sports streams playing natively inside Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "live_now", "name": "🔴 Live Now"},
        {"type": "tv", "id": "all_matches", "name": "🌐 All Matches"}
    ]
}

def fetch_api_data():
    try:
        url = "https://tap4sport.st"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            raw_payload = json.loads(response.read().decode('utf-8'))
            
            # --- AGNOSTIC PAYLOAD LOOKUP ---
            # Automatically unpack array datasets regardless of the root key name
            if isinstance(raw_payload, list):
                return raw_payload
            if isinstance(raw_payload, dict):
                for key in ["data", "events", "streams", "matches"]:
                    if key in raw_payload and isinstance(raw_payload[key], list):
                        return raw_payload[key]
                # If no standard keys match, scan for any loose internal array
                for val in raw_payload.values():
                    if isinstance(val, list):
                        return val
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
    items_pool = fetch_api_data()
    metas = []

    for item in items_pool:
        if not isinstance(item, dict):
            continue

        # Extract standard unique index tracker elements
        match_id = item.get("id") or item.get("uri_name") or item.get("name")
        if not match_id:
            continue

        # Flexible live state assessment parameters
        is_live = item.get("_live") is True or item.get("is_live") is True or item.get("live") == 1
        
        # If browsing the Live Now view block, pass over anything not active
        if clean_catalog_id == "live_now" and not is_live:
            continue

        sport_label = str(item.get("sport", "Live Event")).upper()
        title_name = item.get("title") or item.get("name") or "Live Sports Event"
        
        # Structure clear descriptions matching home/away teams or generic tags
        league_text = item.get("league") or "Sports Match"
        if item.get("home_team") and item.get("away_team"):
            description_body = f"{item['home_team']} vs {item['away_team']} | Sport: {sport_label} ({league_text})"
        else:
            description_body = f"Sport: {sport_label} | League: {league_text}"

        status_tag = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
        if clean_catalog_id == "live_now":
            status_tag = ""

        metas.append({
            "id": f"sport_{match_id}",
            "type": "tv",
            "name": f"{status_tag}{title_name}",
            "poster": item.get("poster") or "https://streamed.pk",
            "description": description_body
        })

    return jsonify({"metas": metas})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    clean_id = item_id.replace(".json", "").replace("sport_", "")
    items_pool = fetch_api_data()
    
    for item in items_pool:
        if not isinstance(item, dict):
            continue
        match_id = item.get("id") or item.get("uri_name") or item.get("name")
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
    items_pool = fetch_api_data()
    response_streams = []
    
    for item in items_pool:
        if not isinstance(item, dict):
            continue
        match_id = item.get("id") or item.get("uri_name") or item.get("name")
        if str(match_id) == str(clean_id):
            
            # Map structural arrays representing links
            feeds_list = item.get("sources") or item.get("streams") or []
            for idx, source in enumerate(feeds_list):
                if not isinstance(source, dict):
                    continue
                
                label = str(source.get("source") or source.get("title") or f"Source Feed #{idx+1}").upper()
                target_url = source.get("url") or source.get("iframe")
                
                # If the item relies on internal index IDs, reconstruct the player path
                if not target_url and source.get("id"):
                    target_url = f"https://streamed.pk{source.get('id')}"
                
                if target_url:
                    response_streams.append({
                        "title": f"Play Link ({label})",
                        "url": target_url,
                        "behaviorHints": {
                            "notWebReady": True  # Instructs Stremio on phones/TVs to use VLC/MX Player safely
                        }
                    })
            return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
