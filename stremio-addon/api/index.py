import json
import time
import urllib.request
from http.server import BaseHTTPRequestHandler

MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "1.2.0",
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

class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        # Crucial security headers needed by Stremio
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        # Handle browser preflight checks
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        path = self.path
        api_data = fetch_api_data()
        current_time = int(time.time())

        # Route 1: Manifest
        if path.endswith("/manifest.json"):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(MANIFEST).encode('utf-8'))
            return

        # Route 2: Catalog Filtering
        elif "/catalog/tv/" in path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()

            catalog_id = path.split("/")[-1].replace(".json", "")
            metas = []

            for group in api_data.get("streams", []):
                category = group.get("category", "Sports")
                if catalog_id != "live_now" and category != CATEGORY_MAPPING.get(catalog_id):
                    continue

                for item in group.get("streams", []):
                    starts = item.get("starts_at", 0)
                    ends = item.get("ends_at", 0)
                    is_always_live = item.get("always_live", 0) == 1 or group.get("always_live") is True
                    is_live = is_always_live or (starts <= current_time <= ends)

                    if catalog_id == "live_now" and not is_live:
                        continue

                    status_prefix = "🔴 LIVE: " if is_live else "⏳ UPCOMING: "
                    if catalog_id == "live_now":
                        status_prefix = ""

                    metas.append({
                        "id": f"sport_{item['id']}",
                        "type": "tv",
                        "name": f"{status_prefix}{item['name']}",
                        "poster": item.get("poster", ""),
                        "description": f"Sport: {category} | Source: {item.get('source_tag', 'Live')}"
                    })
            self.wfile.write(json.dumps({"metas": metas}).encode('utf-8'))
            return

        # Route 3: Meta Layout
        elif "/meta/tv/" in path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()

            item_id = path.split("/")[-1].replace(".json", "")
            clean_id = int(item_id.replace("sport_", ""))
            
            for group in api_data.get("streams", []):
                for item in group.get("streams", []):
                    if item["id"] == clean_id:
                        meta_obj = {
                            "meta": {
                                "id": item_id,
                                "type": "tv",
                                "name": item["name"],
                                "poster": item.get("poster", ""),
                                "description": f"Source: {item.get('source_tag')}"
                            }
                        }
                        self.wfile.write(json.dumps(meta_obj).encode('utf-8'))
                        return
            self.wfile.write(json.dumps({"meta": {}}).encode('utf-8'))
            return

        # Route 4: Streams Linking
        elif "/stream/tv/" in path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()

            item_id = path.split("/")[-1].replace(".json", "")
            clean_id = int(item_id.replace("sport_", ""))
            
            for group in api_data.get("streams", []):
                for item in group.get("streams", []):
                    if item["id"] == clean_id:
                        stream_obj = {
                            "streams": [{
                                "title": f"Watch on {item.get('source_tag', 'Web Player')}",
                                "externalUrl": item["iframe"]
                            }]
                        }
                        self.wfile.write(json.dumps(stream_obj).encode('utf-8'))
                        return
            self.wfile.write(json.dumps({"streams": []}).encode('utf-8'))
            return

        # Generic Fallback Error Response
        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))
