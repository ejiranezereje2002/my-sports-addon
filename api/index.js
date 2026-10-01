const https = require('https');

// Helper function to safely fetch the API data using standard Node.js HTTPS
function fetchLiveStreams() {
    return new Promise((resolve, reject) => {
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
        }).on('error', (e) => {
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
            type": "tv",
            name": "Live Sports Events"
        }
    ]
};

// 2. Main Serverless Export Handler
module.exports = async (req, res) => {
    // Setup clean CORS handling parameters immediately for Stremio cross-origin lookups
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');

    const urlPath = req.url || '';

    // Route A: Provide the Manifest profile cleanly
    if (urlPath === '/' || urlPath.includes('manifest.json')) {
        return res.status(200).json(MANIFEST);
    }

    // Route B: Handle the Homepage Dashboard rows displaying active games
    if (urlPath.includes('/catalog/')) {
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

            return res.status(200).json({ metas: metas });
        } catch (error) {
            return res.status(200).json({ metas: [] });
        }
    }

    // Route C: Handle the video playback link provider mapping
    if (urlPath.includes('/stream/')) {
        try {
            const match = urlPath.match(/live:(\d+)\.json/);
            if (!match) {
                return res.status(200).json({ streams: [] });
            }

            const streamId = parseInt(match[1], 10);
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

            // Return stream details back to Stremio interface engine
            return res.status(200).json({
                streams: [
                    {
                        title: `${foundStream.name}\nSource: ${foundStream.source_tag || 'Web Player'}`,
                        externalUrl: foundStream.iframe
                    }
                ]
            });
        } catch (error) {
            return res.status(200).json({ streams: [] });
        }
    }

    // Fallback response for unhandled endpoints
    return res.status(404).json({ error: "Not Found" });
};
