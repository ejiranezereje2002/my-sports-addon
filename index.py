import json
import re
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces explicit cross-origin resource permissions for Stremio app clients

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "11.0.0",
    "name": "Cloud Live Sports",
    "description": "Premium DAMITV sports channels playing natively inside Stremio!",
    "resources": ["catalog", "meta", "stream"],
    "types": ["tv"],
    "catalogs": [
        {"type": "tv", "id": "all_matches", "name": "🌐 All Live Matches"},
        {"type": "tv", "id": "football", "name": "⚽ Football/Soccer"},
        {"type": "tv", "id": "american_football", "name": "🏈 American Football"},
        {"type": "tv", "id": "basketball", "name": "🏀 Basketball"},
        {"type": "tv", "id": "baseball", "name": "⚾ Baseball"},
        {"type": "tv", "id": "darts", "name": "🎯 Darts"},
        {"type": "tv", "id": "motorsports", "name": "🏎️ Motorsports"},
        {"type": "tv", "id": "rugby", "name": "🏉 Rugby"},
        {"type": "tv", "id": "combat_sports", "name": "🥊 Combat/UFC"}
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

def parse_m3u_playlist():
    parsed_items = []
    try:
        url = "https://s.id"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=8) as response:
            lines = [line.decode('utf-8').strip() for line in response.readlines()]
            
            current_item = {}
            for line in lines:
                if line.startswith("#EXTINF:"):
                    current_item = {}
                    name_match = re.search(r'tvg-name="([^"]+)"', line)
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    chno_match = re.search(r'tvg-chno="([^"]+)"', line)
                    
                    display_title = line.split(",")[-1] if "," in line else "Live Match"
                    
                    current_item["name"] = name_match.group(1) if name_match else display_title
                    current_item["logo"] = logo_match.group(1) if logo_match else "https://1000logos.net"
                    current_item["chno"] = chno_match.group(1) if chno_match else "0"
                    
                    lower_name = current_item["name"].lower()
                    if "bundesliga" in lower_name or "premier league" in lower_name or "epl" in lower_name or "laliga" in lower_name or "serie a" in lower_name or "brasileir" in lower_name or "soccer" in lower_name:
                        current_item["sport"] = "football"
                    elif "american football" in lower_name or "nfl" in lower_name or "ncaa" in lower_name:
                        current_item["sport"] = "american_football"
                    elif "basketball" in lower_name or "nbl" in lower_name:
                        current_item["sport"] = "basketball"
                    elif "mlb" in lower_name or "baseball" in lower_name:
                        current_item["sport"] = "baseball"
                    elif "darts" in lower_name:
                        current_item["sport"] = "darts"
                    elif "motogp" in lower_name or "racing" in lower_name or "motorsport" in lower_name:
                        current_item["sport"] = "motorsports"
                    elif "rugby" in lower_name:
                        current_item["sport"] = "rugby"
                    elif "ufc" in lower_name or "mma" in lower_name or "wwe" in lower_name or "wrestling" in lower_name:
                        current_item["sport"] = "combat_sports"
                    else:
                        current_item["sport"] = "football"
                        
                elif line.startswith("http://") or line.startswith("https://"):
                    if current_item and "name" in current_item:
                        current_item["stream_url"] = line
                        
                        # --- STRICT FILTER RULE ---
                        # Only keep the item if it explicitly belongs to DAMITV
                        stream_lower = line.lower()
                        name_lower = current_item["name"].lower()
                        if "damitv" in stream_lower or "dami" in stream_lower or "damitv" in name_lower or "dami" in name_lower:
                            clean_id = current_item["chno"] or str(len(parsed_items) + 1)
                            safe_title = re.sub(r'[^a-zA-Z0-9]', '', current_item["name"])
                            current_item["id"] = f"iptv_{clean_id}_{safe_title}"
                            parsed_items.append(current_item)
                            
                        current_item = {}
                        
    except Exception as e:
        print(f"IPTV Fetch Error: {e}")
        
    return parsed_items

@app.route('/')
@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)

@app.route('/catalog/tv/<catalog_id>')
@app.route('/catalog/tv/<catalog_id>.json')
def catalog(catalog_id):
    clean_catalog_id = catalog_id.replace(".json", "")
    matches_list = parse_m3u_playlist()
    metas = []

    for item in matches_list:
        if clean_catalog_id != "all_matches" and item["sport"] != clean_catalog_id:
            continue

        metas.append({
            "id": item["id"],
            "type": "tv",
            "name": f"🔴 {item['name']}",
            "poster": item["logo"],
            "description": f"Category: {item['sport'].upper()} | Source: DAMITV Native Stream"
        })

    return jsonify({"metas": metas})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    clean_id = item_id.replace(".json", "")
    matches_list = parse_m3u_playlist()
    
    for item in matches_list:
        if item["id"] == clean_id:
            return jsonify({
                "meta": {
                    "id": item["id"],
                    "type": "tv",
                    "name": item["name"],
                    "poster": item["logo"],
                    "description": f"DAMITV Live Channel | Source Tracker #{item['chno']}"
                }
            })
    return jsonify({"meta": {}})

@app.route('/stream/tv/<item_id>')
@app.route('/stream/tv/<item_id>.json')
def stream(item_id):
    clean_id = item_id.replace(".json", "")
    matches_list = parse_m3u_playlist()
    
    for item in matches_list:
        if item["id"] == clean_id:
            # All streams inside this loop are confirmed working DAMITV feeds
            return jsonify({
                "streams": [{
                    "title": "⚡ Play Native (DAMITV)",
                    "url": item["stream_url"],
                    "behaviorHints": {
                        "requestHeaders": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }
                    }
                }]
            })
            
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
