from http.server import BaseHTTPRequestHandler
import json
import urllib.request

API_ENDPOINT = "https://streamic.st/api/getEvents.php"

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
        path = self.path

        # 2. Serve Manifest JSON
        if path == "/manifest.json" or path == "/":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(MANIFEST).encode('utf-8'))
            return

        # 3. Serve Catalog JSON (With clean empty countryCode checks)
        elif path.startswith("/catalog/tv/live_sports_catalog"):
            events = fetch_sports_events()
            metas = []
            
            if isinstance(events, list):
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    
                    # Fix: If countryCode is missing or empty, apply a universal sports icon placeholder
                    raw_country = event.get("countryCode")
                    if raw_country and str(raw_country).strip():
                        poster_url = f"https://flagsapi.com{str(raw_country).strip().upper()}/flat/64.png"
                    else:
                        poster_url = "https://flaticon.com"

                    metas.append({
                        "id": f"live_sport:{event.get('id')}",
                        "type": "tv",
                        "name": f"{event.get('title')} ({event.get('league') or event.get('category') or 'Live'})",
                        "poster": poster_url,
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
            try:
                stream_id = path.split("/stream/tv/")[-1].replace(".json", "")
                target_id = stream_id.replace("live_sport:", "")
            except:
                target_id = ""

            events = fetch_sports_events()
            matched_event = None
            if isinstance(events, list):
                matched_event = next((e for e in events if isinstance(e, dict) and str(e.get("id")) == target_id), None)
                
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
