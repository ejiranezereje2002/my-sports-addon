from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import base64

# FIX: Added the missing /api/getEvents.php path
API_ENDPOINT = "https://streamic.st/api/getEvents.php"

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
        with urllib.request.urlopen(req, timeout=8) as response:
            raw_data = response.read()
            
            # Decode the base64 dynamic stream payload structure
            try:
                decoded_bytes = base64.b64decode(raw_data.strip())
                decoded_str = decoded_bytes.decode('utf-8-sig').strip()
                return json.loads(decoded_str)
            except Exception as decode_err:
                print(f"Direct JSON reading active: {decode_err}")
                return json.loads(raw_data.decode('utf-8-sig'))
                
    except Exception as e:
        print(f"Error fetching API data: {e}")
        return []

class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_cors_headers(200)

    def do_GET(self):
        path = self.path

        # Catch Manifest Routing
        if "manifest.json" in path or path == "/":
            self.send_cors_headers(200)
            self.wfile.write(json.dumps(MANIFEST).encode('utf-8'))
            return

        # Catch Catalog Rows
        elif "live_sports_catalog" in path:
            events = fetch_sports_events()
            metas = []
            
            if isinstance(events, list):
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    
                    event_id = str(event.get("id", ""))
                    if not event_id:
                        continue

                    raw_country = event.get("countryCode")
                    if raw_country and str(raw_country).strip():
                        poster_url = f"https://flagsapi.com{str(raw_country).strip().upper()}/flat/64.png"
                    else:
                        poster_url = "https://flaticon.com"

                    metas.append({
                        "id": f"live_sport:{event_id}",
                        "type": "tv",
                        "name": f"{event.get('title', 'Live Match')} ({event.get('league') or event.get('category') or 'Sports'})",
                        "poster": poster_url,
                        "description": f"Live sports stream. Event ID: {event_id}"
                    })
                
            self.send_cors_headers(200)
            self.wfile.write(json.dumps({"metas": metas}).encode('utf-8'))
            return

        # Catch Video Feeds
        elif "/stream/" in path:
            try:
                clean_path = path.split("/stream/tv/")[-1].replace(".json", "")
                if "?" in clean_path:
                    clean_path = clean_path.split("?")[0]
                target_id = clean_path.replace("live_sport:", "")
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

            self.send_cors_headers(200)
            self.wfile.write(json.dumps({"streams": streams}).encode('utf-8'))
            return

        # Fallback structural response container
        self.send_cors_headers(200)
        self.wfile.write(json.dumps({"metas": []}).encode('utf-8'))
