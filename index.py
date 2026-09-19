import json
import time
import re
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces open access compliance rules for Stremio mobile clients

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "6.2.0",
    "name": "Cloud Live Sports NATIVE",
    "description": "Auto-sniffed direct m3u8 sports playing perfectly inside Stremio!",
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
        url = "https://ppv.st"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return {"streams": []}

def extract_hidden_m3u8(embed_url):
    """
    Automated background link sniffer. Reads the target HTML page 
    and extracts hidden .m3u8 video streaming configurations instantly.
    """
    try:
        req = urllib.request.Request(embed_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=4) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
            
            # Locate all potential streaming configurations inside the page layout
            found_urls = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html_content)
            if found_urls:
                # FIXED TYPO BUG: Added proper bracket indexing notation to extract the string element
                first_url = found_urls[0]
                clean_url = first_url.replace('\\/', '/')
                return clean_url
    except Exception:
        pass
    return None

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
        if clean_catalog_id != "live_now" and category != CATEGORY_MAPPING.get(clean_catalog_id):
            continue

        for item in group.get("streams", []):
            starts = item.get("starts_at", 0)
            ends = item.get("ends_at", 0)
            is_always_live = item.get("always_live", 0) == 1 or group.get("always_live") is True
            is_live = is_always_live or (starts <= current_time <= ends)

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
                
                # Run background sniffing routine
                iframe_url = item.get("iframe", "")
                if iframe_url:
                    sniffed_video_url = extract_hidden_m3u8(iframe_url)
                    if sniffed_video_url:
                        response_streams.append({
                            "title": f"⚡ Play Native ({item.get('source_tag', 'Main Feed')})",
                            "url": sniffed_video_url
                        })
                
                # Bulletproof Fallback: Keeps streams active if scraping hits a restriction block
                response_streams.append({
                    "title": f"🌐 Web Player Fallback ({item.get('source_tag', 'Embed Frame')})",
                    "url": iframe_url,
                    "behaviorHints": {"notWebReady": True}
                })
                
                # Check for alternative substation channels
                for idx, sub in enumerate(item.get("substreams", [])):
                    sub_url = sub.get("iframe", "")
                    if sub_url:
                        sub_label = sub.get("source_tag") or sub.get("locale", "").upper() or f"Feed #{idx+2}"
                        sniffed_sub_url = extract_hidden_m3u8(sub_url)
                        if sniffed_sub_url:
                            response_streams.append({
                                "title": f"⚡ Play Native ({sub_label})",
                                "url": sniffed_sub_url
                            })
                        response_streams.append({
                            "title": f"🌐 Web Player Fallback ({sub_label})",
                            "url": sub_url,
                            "behaviorHints": {"notWebReady": True}
                        })
                        
                return jsonify({"streams": response_streams})
                
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
