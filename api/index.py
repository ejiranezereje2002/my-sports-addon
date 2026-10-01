from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request

# 1. Define the Stremio Addon Profile (Manifest) with Catalog Support
MANIFEST = {
    "id": "org.ppvstreams.python.addon",
    "version": "1.1.0",
    "name": "Live PPV Sports Streams",
    "description": "Watch live sports events mapped directly via Python serverless routing",
    "resources": ["catalog", "stream"],
    "types": ["tv", "movie"],
    "idPrefixes": ["live:"],
    "catalogs": [
        {
            "id": "live_sports_catalog",
            "type": "tv",
            "name": "Live Sports Events"
        }
    ]
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url_path = self.path

        # Setup standard CORS response routing parameters immediately
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        # Clean the route safely by isolating everything before a '?' parameter symbol
        path_main = url_path.split('?')[0]
        cleaned_path = path_main.strip('/')

        # Route A: Match manifest lookups cleanly
        if cleaned_path == "" or cleaned_path == "api" or "manifest.json" in cleaned_path:
            response_data = json.dumps(MANIFEST)
            self.wfile.write(response_data.encode('utf-8'))
            return

        # Route B: Handle the Homepage Dashboard Catalog row display
        if 'catalog' in cleaned_path:
            try:
                req = urllib.request.Request('https://ppv.st')
                req.add_header('Origin', 'https://embedindia.st')
                req.add_header('Referer', 'https://embedindia.st')
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36')
                
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))

                metas = []
                if data and data.get("success") and "streams" in data:
                    for category in data["streams"]:
                        cat_name = category.get("category", "Live Stream")
                        for stream_obj in category.get("streams", []):
                            metas.append({
                                "id": f"live:{stream_obj.get('id')}",
                                "type": "tv",
                                "name": stream_obj.get("name"),
                                "poster": stream_obj.get("poster"),
                                "description": f"Category: {cat_name} | Source: {stream_obj.get('source_tag')}",
                                "banner": stream_obj.get("poster")
                            })

                self.wfile.write(json.dumps({"metas": metas}).encode('utf-8'))
                return
            except Exception:
                self.wfile.write(json.dumps({"metas": []}).encode('utf-8'))
                return

        # Route C: Handle player request playback source mapping
        if 'stream' in cleaned_path:
            try:
                match = re.search(r'live:(\d+)\.json', url_path)
                if not match:
                    self.wfile.write(json.dumps({"streams": []}).encode('utf-8'))
                    return
                
                stream_id = int(match.group(1))

                req = urllib.request.Request('https://ppv.st')
                req.add_header('Origin', 'https://embedindia.st')
                req.add_header('Referer', 'https://embedindia.st')
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36')
                
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))

                found_stream = None
                if data and data.get("success") and "streams" in data:
                    for category in data["streams"]:
                        for stream_obj in category.get("streams", []):
                            if stream_obj.get("id") == stream_id:
                                found_stream = stream_obj
                                break
                        if found_stream:
                            break

                if not found_stream:
                    self.wfile.write(json.dumps({"streams": []}).encode('utf-8'))
                    return

                stream_response = {
                    "streams": [
                        {
                            "title": f"{found_stream.get('name')}\nSource: {found_stream.get('source_tag')}",
                            "externalUrl": found_stream.get("iframe")
                        }
                    ]
                }
                
                self.wfile.write(json.dumps(stream_response).encode('utf-8'))
                return
            except Exception:
                self.wfile.write(json.dumps({"streams": []}).encode('utf-8'))
                return

        # Fallback response ensuring valid JSON dictionary data is returned 
        self.wfile.write(json.dumps({"error": f"Path {url_path} not found"}).encode('utf-8'))
        return
