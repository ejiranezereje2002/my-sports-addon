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

// Route A: Base / Manifest endpoint - DYNAMICALLY BUILDS YOUR DROP-DOWNS FROM THE API
app.get(['/', '/manifest.json', '/api', '/api/manifest.json'], async (req, res) => {
    // Default fallback options if the API lookup fails or is empty
    let dynamicGenres = ["Live Now", "Today"];
    
    try {
        const rawData = await fetchLiveStreams();
        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            rawData.streams.forEach(categoryObj => {
                if (categoryObj && categoryObj.category) {
                    const catName = categoryObj.category.trim();
                    // Avoid duplicating genres in our drop-down list array
                    if (catName && !dynamicGenres.includes(catName)) {
                        dynamicGenres.push(catName);
                    }
                }
            });
        }
    } catch (e) {
        // Safe fallback preservation
        dynamicGenres = ["Live Now", "Today", "American Football", "Basketball", "Football", "Hockey", "Baseball", "Darts", "Rugby"];
    }

    const manifest = {
        "id": "org.ppvstreams.js.addon",
        "version": "1.6.0",
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
                        "options": dynamicGenres // Dynamically inserted sport array elements
                    }
                ]
            }
        ]
    };

    res.status(200).json(manifest);
});

// Route B: Homepage Grid Rows Catalog Handler with Multi-Genre Filter Mapping
app.get(['/catalog/:type/:id', '/catalog/:type/:id.json'], async (req, res) => {
    try {
        const rawData = await fetchLiveStreams();
        const metas = [];

        // Parse optional Stremio genre filters from route parameter strings (e.g., genre=Basketball)
        const urlParams = req.url.split('?')[1] || '';
        const genreMatch = urlParams.match(/genre=([^&]+)/);
        let targetGenre = genreMatch ? decodeURIComponent(genreMatch[1]) : 'Live Now';

        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            rawData.streams.forEach(categoryObj => {
                const catName = categoryObj.category || "Live Match";
                
                // Dropdown structural alignment logic filtering module
                if (targetGenre !== "Live Now" && targetGenre !== "Today") {
                    if (catName.toLowerCase().trim() !== targetGenre.toLowerCase().trim()) {
                        return; // Skip streaming items that do not match selected dropdown parameter fields
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

// Route C: Unified Multi-Type Playback Handler covering Movie, TV, and Sport lookups
app.get(['/stream/:type/:id', '/stream/:type/:id.json'], async (req, res) => {
    try {
        const idParam = req.params.id || '';
        
        // Handle variations of incoming ID characters cleanly
        let cleanId = idParam.replace('live:', '').replace('streamed:', '').replace('.json', '');
        if (cleanId.includes('%')) {
            cleanId = decodeURIComponent(cleanId);
        }
        
        const rawData = await fetchLiveStreams();
        let foundStream = null;

        if (rawData && rawData.success && Array.isArray(rawData.streams)) {
            for (const categoryObj of rawData.streams) {
                if (Array.isArray(categoryObj.streams)) {
                    foundStream = categoryObj.streams.find(s => 
                        String(s.id) === String(cleanId) || 
                        String(s.uri_name) === String(cleanId) ||
                        slugify(s.name) === slugify(cleanId)
                    );
                    if (foundStream) break;
                }
            }
        }

        if (!foundStream || !foundStream.iframe) {
            return res.status(200).json({ "streams": [] });
        }

        // Return a clean stream array layout compatible with both TV and Mobile app architectures
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
