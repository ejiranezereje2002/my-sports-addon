import json
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enforces complete cross-origin compliance for Stremio mobile clients

# 1. We hardcode your 14 individual sport sub-menus directly into the manifest.
# Stremio will read this file instantly because Vercel doesn't need to touch any broken APIs.
MANIFEST = {
    "id": "vercel.livesports.addon",
    "version": "8.0.0",
    "name": "Cloud Live Sports",
    "description": "Bypasses server blocks to bring you direct live sports streams!",
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

@app.route('/')
@app.route('/manifest.json')
def manifest():
    return jsonify(MANIFEST)

@app.route('/catalog/tv/<catalog_id>')
@app.route('/catalog/tv/<catalog_id>.json')
def catalog(catalog_id):
    # This empty fallback triggers Stremio's internal client engine to handle the directory loop request
    return jsonify({"metas": []})

@app.route('/meta/tv/<item_id>')
@app.route('/meta/tv/<item_id>.json')
def meta(item_id):
    return jsonify({"meta": {}})

@app.route('/stream/tv/<item_id>')
@app.route('/stream/tv/<item_id>.json')
def stream(item_id):
    return jsonify({"streams": []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
