const express = require('express');
const https = require('https');
const app = express();

// Helper function to safely stream remote data layouts using native Node.js
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
    id: "org.ppvstreams.js.addon",
    version: "1.2.0",
    name: "Live PPV Sports",
    description: "Watch live sports matches directly inside Stremio via Node.js serverless architecture",
    resources: ["catalog", "stream"],
    types: ["tv", "movie"],
    idPrefixes: ["live:"],
    catalogs: [
        {
            id: "live_sports_catalog",
            type: "tv",
            name": "Live Sports Events"
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

// Route B: Homepage Grid Rows Catalog Handler
app.get(['/catalog/:type/:id', '/catalog/:type/:id.json'], async (req, res) => {
    try {
        const data = await fetchLiveStreams();
        const metas = [];

        if (data && data.success && data.streams) {
            data.streams.forEach(category => {
                const catName = category.category || "Live Match";
                if (category.streams) {
                    category.streams.forEach(streamObj => {
                        metas.push({
                            id: `live:${streamObj.id}`,
                            type: "tv",
                            name: streamObj.name,
                            poster: streamObj.poster,
                            description: `Sport: ${catName} | Source: ${streamObj.source_tag || 'Live Link'}`,
                            banner: streamObj.poster
                        });
                    });
                }
            });
        }
        res.status(200).json({ metas: metas });
    } catch (error) {
        res.status(200).json({ metas: [] });
    }
});

// Route C: Dynamic Player Playback Source link mapping provider
app.get(['/stream/:type/:id', '/stream/:type/:id.json'], async (req, res) => {
    try {
        const idParam = req.params.id || '';
        const streamIdMatch = idParam.match(/live:(\d+)/);
        if (!streamIdMatch) {
            return res.status(200).json({ streams: [] });
        }

        const streamId = parseInt(streamIdMatch[1], 10);
        const data = await fetchLiveStreams();
        let foundStream = null;

        if (data && data.success && data.streams) {
            for (const category of data.streams) {
                if (category.streams) {
                    foundStream = category.streams.find(s => s.id === streamId);
                    if (foundStream) break;
                }
            }
        }

        if (!foundStream) {
            return res.status(200).json({ streams: [] });
        }

        res.status(200).json({
            streams: [
                {
                    title: `${foundStream.name}\nSource: ${foundStream.source_tag || 'Web Player'}`,
                    externalUrl: foundStream.iframe
                }
            ]
        });
    } catch (error) {
        res.status(200).json({ streams: [] });
    }
});

// Export app deployment execution loop modules
module.exports = app;
