const express = require('express');
const https = require('https');
const app = express();

// Helper function to safely pull layout data using native Node.js
function fetchLiveStreams() {
    return new Promise((resolve) => {
        const options = {
            hostname: 'api.ppv.st',
            path: '/api/streams',
            method: 'GET',
            headers: {
                'Origin': 'https://embedindia.st',
                'Referer': 'https://embedindia.st',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36'
            }
        };

        https.get(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    resolve(null);
                }
            });
        }).on('error', () => {
            resolve(null);
        });
    });
}

// 1. Define the Stremio Addon Profile (Manifest) with Catalog Support
const MANIFEST = {
    "id": "org.ppvstreams.js.addon",
    "version": "1.3.3",
    "name": "Live PPV Sports",
    "description": "Watch live sports matches directly inside Stremio via Node.js serverless architecture",
    "resources": ["catalog", "stream"],
    "types": ["movie"],
    "idPrefixes": ["live:"],
    "catalogs": [
        {
            "id": "live_sports_catalog",
            "type": "movie",
            "name": "Live Sports Events"
        }
    ]
};

// Global CORS Middleware rule block for Stremio client support
app.use((req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');
    next();
});

// Route A: Base / Manifest endpoints lookup mapping
app.get(['/', '/manifest.json', '/api', '/api/manifest.json'], (req, res) => {
    res.status(200).json(MANIFEST);
});

// Route B: Homepage Grid Rows Catalog Handler (Nested Parsing)
app.get(['/catalog/:type/:id', '/catalog/:type/:id.json'], async (req, res) => {
    try {
        const rawData = await fetchLiveStreams();
        const metas = [];

        // Navigate your actual nested layout structure: data.streams -> category -> streams array
        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            rawData.streams.forEach(categoryObj => {
                const catName = categoryObj.category || "Live Match";
                
                if (Array.isArray(categoryObj.streams)) {
                    categoryObj.streams.forEach(streamObj => {
                        if (streamObj && (streamObj.id || streamObj.uri_name)) {
                            const uniqueId = streamObj.id || streamObj.uri_name;
                            const titleName = streamObj.name || uniqueId.toString().toUpperCase();
                            
                            metas.push({
                                "id": `live:${uniqueId}`,
                                "type": "movie",
                                "name": titleName,
                                "poster": streamObj.poster || "https://placehold.co",
                                "description": `Sport: ${catName} | Viewers: ${streamObj.viewers || '0'}`,
                                "banner": streamObj.poster || ""
                            });
                        }
                    });
                }
            });
        }

        res.status(200).json({ "metas": metas });
    } catch (error) {
        res.status(200).json({ "metas": [] });
    }
});

// Route C: Dynamic Player Playback Source link mapping provider
app.get(['/stream/:type/:id', '/stream/:type/:id.json'], async (req, res) => {
    try {
        const idParam = req.params.id || '';
        const cleanId = idParam.replace('live:', '').replace('.json', '');
        
        const rawData = await fetchLiveStreams();
        let foundStream = null;

        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            for (const categoryObj of rawData.streams) {
                if (Array.isArray(categoryObj.streams)) {
                    foundStream = categoryObj.streams.find(s => 
                        String(s.id) === String(cleanId) || 
                        String(s.uri_name) === String(cleanId)
                    );
                    if (foundStream) break;
                }
            }
        }

        if (!foundStream || !foundStream.iframe) {
            return res.status(200).json({ "streams": [] });
        }

        res.status(200).json({
            "streams": [
                {
                    "title": `✨ Play Stream on Web Player\nSource: ${foundStream.category_name || 'Live TV'}`,
                    "externalUrl": foundStream.iframe
                }
            ]
        });
    } catch (error) {
        res.status(200).json({ "streams": [] });
    }
});

// Export app deployment execution loop modules
module.exports = app;
