from http.server import BaseHTTPRequestHandler
import json
import urllib.request

API_ENDPOINT = "https://streamic.st"

# 1. Define the Stremio Manifest JSON structure
MANIFEST = {
    "id": "community.vercelsportsaddonpython",
    "version": "1.0.0",
    "name": "Live Sports Hub",
    "description": "Real-time live sports streams aggregated from Streamic API.",
    "resources": ["catalog", "stream"],
    "types": ["tv"],
    "catalogs": [
        {
            "type": "tv",
            "id": "live_sports_catalog",
            "name": "Live Matches"
        }
    ],
    "idPrefixes": ["live_sport:"]
}

def fetch_sports_events():
    try:
        req = urllib.request.Request(
            API_ENDPOINT, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return []

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Handle CORS preflight & routing headers
        path = self.path

        # 2. Serve Manifest JSON
        if path == "/manifest.json" or path == "/":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(MANIFEST).encode('utf-8'))
            return

        # 3. Serve Catalog JSON
        elif path.startswith("/catalog/tv/live_sports_catalog"):
            events = fetch_sports_events()
            metas = []
            
            for event in events:
                country = str(event.get("countryCode", "us")).upper()
                metas.append({
                    "id": f"live_sport:{event.get('id')}",
                    "type": "tv",
                    "name": f"{event.get('title')} ({event.get('league') or event.get('category') or 'Live'})",
                    "poster": f"https://flagsapi.com{country}/flat/64.png",
                    "description": f"Live match. Event ID: {event.get('id')}"
                })
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"metas": metas}).encode('utf-8'))
            return

        # 4. Serve Stream JSON
        elif "/stream/tv/" in path:
            # Extract stream id from path (e.g., /stream/tv/live_sport:123.json)
            try:
                stream_id = path.split("/stream/tv/")[-1].replace(".json", "")
                target_id = stream_id.replace("live_sport:", "")
            except:
                target_id = ""

            events = fetch_sports_events()
            matched_event = next((e for e in events if str(e.get("id")) == target_id), None)
            streams = []

            if matched_event and "_embeds" in matched_event:
                for embed_group in matched_event["_embeds"]:
                    lang = embed_group.get("language", "Unknown Language")
                    embeds_dict = embed_group.get("embeds", {})
                    
                    if isinstance(embeds_dict, dict):
                        for key, option in embeds_dict.items():
                            embed_url = option.get("embed", "")
                            if embed_url.startswith("//"):
                                embed_url = f"https:{embed_url}"
                                
                            streams.append({
                                "title": f"[{option.get('label', 'HD')}] {lang}",
                                "url": embed_url
                            })

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"streams": streams}).encode('utf-8'))
            return

        # Fallback 404
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Not Found")
