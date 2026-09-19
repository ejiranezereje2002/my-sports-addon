from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import re

# Update: Switched base endpoint to the new M3U playlist path
API_ENDPOINT = "https://axsp.pages.dev/playlist.txt"

MANIFEST = {
    "id": "community.vercelsportsaddonpython",
    "version": "1.0.0",
    "name": "Live Sports Hub",
    "description": "Real-time live sports streams aggregated from AXSP M3U playlist.",
    "resources": ["catalog", "meta", "stream"], 
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

def parse_m3u_playlist():
    try:
        req = urllib.request.Request(
            API_ENDPOINT, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            
        events = []
        current_item = None
        
        # Parse M3U playlist rows sequentially
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("#EXTINF:"):
                # Reset item tracker
                current_item = {"headers": {}}
                
                # Regex parsing arrays to map properties cleanly out of line configurations
                tvg_id_match = re.search(r'tvg-id="([^"]+)"', line)
                logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                
                # Capture titles located behind commas
                title = line.split(",")[-1].strip() if "," in line else "Live Match"
                
                current_item["id"] = tvg_id_match.group(1) if tvg_id_match else "unknown"
                current_item["title"] = title
                current_item["logo"] = logo_match.group(1) if logo_match else "https://flaticon.com"
                
            elif line.startswith("#EXTVLCOPT:"):
                # Store dynamic stream injection arguments (User-Agents and HTTP Referrers)
                if current_item:
                    if "http-user-agent=" in line:
                        current_item["headers"]["User-Agent"] = line.split("http-user-agent=")[-1].strip()
                    elif "http-referrer=" in line:
                        current_item["headers"]["Referer"] = line.split("http-referrer=")[-1].strip()
                        
            elif line.startswith("http://") or line.startswith("https://"):
                if current_item and current_item.get("id") != "unknown":
                    current_item["url"] = line
                    events.append(current_item)
                    current_item = None
                    
        return events
    except Exception as e:
        print(f"Error parsing dynamic M3U data stream: {e}")
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
        path = urllib.request.urlsplit(self.path).path
        path = urllib.request.unquote(path)

        # 1. Manifest Output Link
        if "manifest.json" in path or path == "/":
            self.send_cors_headers(200)
            self.wfile.write(json.dumps(MANIFEST).encode('utf-8'))
            return

        # 2. Catalogs Data Link
        elif "live_sports_catalog" in path:
            events = parse_m3u_playlist()
            metas = []
            seen_ids = set()
            
            for event in events:
                event_id = event["id"]
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                metas.append({
                    "id": f"live_sport:{event_id}",
                    "type": "tv",
                    "name": event["title"].split(" - ")[0], # Cleans server names from general cards grid view
                    "poster": event["logo"],
                    "description": f"Live sports stream. Channel ID: {event_id}"
                })
                
            self.send_cors_headers(200)
            self.wfile.write(json.dumps({"metas": metas}).encode('utf-8'))
            return

        # 3. Meta Mapping Details Link
        elif "/meta/tv/" in path or ("live_sport:" in path and "/stream/" not in path):
            events = parse_m3u_playlist()
            matched_event = None
            
            for event in events:
                if f"live_sport:{event['id']}" in path:
                    matched_event = event
                    break

            meta_data = {"meta": {}}
            if matched_event:
                meta_data["meta"] = {
                    "id": f"live_sport:{matched_event['id']}",
                    "type": "tv",
                    "name": matched_event["title"].split(" - ")[0],
                    "poster": matched_event["logo"],
                    "background": matched_event["logo"],
                    "description": f"Streaming Options Available: {matched_event['title']}"
                }

            self.send_cors_headers(200)
            self.wfile.write(json.dumps(meta_data).encode('utf-8'))
            return

        # 4. Active Player Streams Feeds Links Interception (Groups variations under one title grid card)
        elif "/stream/" in path:
            events = parse_m3u_playlist()
            streams = []

            for event in events:
                if f"live_sport:{event['id']}" in path:
                    # Clean up server labels inside selectors panels menu list dynamically
                    title_label = "Live Feed Server"
                    if "[" in event["title"] and "]" in event["title"]:
                        title_label = event["title"].split("[")[-1].replace("]", "").strip()
                    elif "-" in event["title"]:
                        title_label = event["title"].split("-")[-1].strip()

                    streams.append({
                        "title": f"[{title_label}] Dynamic M3U Link",
                        "url": event["url"],
                        "behaviorHints": {
                            "notout": True,
                            "proxyHeaders": {
                                "request": event["headers"]
                            }
                        }
                    })

            self.send_cors_headers(200)
            self.wfile.write(json.dumps({"streams": streams}).encode('utf-8'))
            return

        # Global layout container fallback
        self.send_cors_headers(200)
        self.wfile.write(json.dumps({"metas": []}).encode('utf-8'))
