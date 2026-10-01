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

// Helper utility to safely convert standard text strings into URL-safe layout slugs
function slugify(text) {
    return text.toString().toLowerCase().trim()
        .replace(/\s+/g, '-')
        .replace(/[^\w\-]+/g, '')
        .replace(/\-\-+/g, '-');
}

// Global CORS Middleware rule block for Stremio client support
app.use((req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');
    next();
});

// Route A: Base / Manifest endpoint
app.get(['/', '/manifest.json', '/api', '/api/manifest.json'], async (req, res) => {
    let dynamicGenres = ["Live Now", "Today"];
    let sortingPool = [];
    
    try {
        const rawData = await fetchLiveStreams();
        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            rawData.streams.forEach(categoryObj => {
                if (categoryObj && categoryObj.category) {
                    const catName = categoryObj.category.trim();
                    if (!catName) return;

                    let totalCategoryViewers = 0;
                    if (Array.isArray(categoryObj.streams)) {
                        categoryObj.streams.forEach(s => {
                            totalCategoryViewers += parseInt(s.viewers || 0, 10);
                        });
                    }

                    sortingPool.push({ name: catName, viewers: totalCategoryViewers });
                }
            });

            sortingPool.sort((a, b) => b.viewers - a.viewers);
            sortingPool.forEach(item => {
                if (!dynamicGenres.includes(item.name)) {
                    dynamicGenres.push(item.name);
                }
            });
        }
    } catch (e) {
        dynamicGenres = ["Live Now", "Today", "American Football", "Basketball", "Football", "Hockey", "Baseball", "Darts", "Rugby"];
    }

    const manifest = {
        "id": "org.ppvstreams.js.addon",
        "version": "1.6.2",
        "name": "Live PPV Sports",
        "description": "Watch live sports matches directly inside Stremio via Node.js serverless architecture",
        "resources": ["catalog", "stream"],
        "types": ["sport", "movie", "tv"],
        "idPrefixes": ["live:", "streamed:"],
        "catalogs": [
            {
                "id": "live_sports_catalog",
                "type": "sport",
                "name": "Live Now",
                "extra": [
                    {
                        "name": "genre",
                        "isRequired": false,
                        "options": dynamicGenres
                    }
                ]
            }
        ]
    };

    res.status(200).json(manifest);
});

// Route B: Homepage Grid Rows Catalog Handler
app.get(['/catalog/:type/:id', '/catalog/:type/:id.json'], async (req, res) => {
    try {
        const rawData = await fetchLiveStreams();
        const metas = [];

        let targetGenre = 'Live Now';
        if (req.url.includes('?')) {
            const queryString = req.url.substring(req.url.indexOf('?'));
            const urlParams = new URLSearchParams(queryString);
            if (urlParams.has('genre')) {
                targetGenre = urlParams.get('genre');
            }
        }

        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            rawData.streams.forEach(categoryObj => {
                const catName = categoryObj.category || "Live Match";
                
                if (targetGenre !== "Live Now" && targetGenre !== "Today") {
                    if (catName.toLowerCase().trim() !== targetGenre.toLowerCase().trim()) {
                        return; 
                    }
                }

                if (Array.isArray(categoryObj.streams)) {
                    categoryObj.streams.forEach(streamObj => {
                        if (streamObj && (streamObj.id || streamObj.uri_name)) {
                            const uniqueId = streamObj.id || streamObj.uri_name;
                            const titleName = streamObj.name || uniqueId.toString().toUpperCase();
                            
                            metas.push({
                                "id": `live:${uniqueId}`,
                                "type": "sport",
                                "name": titleName,
                                "poster": streamObj.poster || "https://placehold.co",
                                "description": `LIVE NOW Popular match Sources: Admin\nCategory: ${catName}`,
                                "genres": [catName, streamObj.source_tag || "Live TV"],
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

// Route C: BULLETPROOF STREAM ID PARSING
app.get('/stream/:type/:id*', async (req, res) => {
    try {
        // Isolate the ID parameter from either path variables or raw request pathing structures
        let rawId = req.params.id || '';
        
        // Fallback fallback selector parser if Express slices off trailing wildcard values
        if (!rawId || rawId === 'sport' || rawId === 'movie' || rawId === 'tv') {
            const urlParts = req.url.split('/');
            rawId = urlParts[urlParts.length - 1] || '';
        }

        // Strip prefixes and format extensions completely
        let cleanId = rawId.replace('live:', '').replace('streamed:', '').replace('.json', '');
        cleanId = decodeURIComponent(cleanId).trim();

        const rawData = await fetchLiveStreams();
        let foundStream = null;

        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            for (const categoryObj of rawData.streams) {
                if (Array.isArray(categoryObj.streams)) {
                    foundStream = categoryObj.streams.find(s => 
                        String(s.id) === String(cleanId) || 
                        String(s.uri_name) === String(cleanId) ||
                        slugify(s.name) === slugify(cleanId) ||
                        slugify(s.uri_name) === slugify(cleanId)
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
                    "name": foundStream.source_tag || "Leaf (4K)",
                    "title": `${foundStream.name || 'Live Event'}\n1920x1080 · Stereo · Live Feed`,
                    "externalUrl": foundStream.iframe
                }
            ]
        });
    } catch (error) {
        res.status(200).json({ "streams": [] });
    }
});

module.exports = app;
