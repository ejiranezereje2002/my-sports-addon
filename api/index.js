const axios = require('axios');

const API_URL = 'https://bintvjson.lovable.app/api/public/bintvjson';

// Define the Stremio Addon Manifest
const manifest = {
    id: 'org.stremio.bintvsports',
    version: '1.0.0',
    name: 'BinTV Sports & Live TV',
    description: 'Watch live sports events, upcoming matches, and 24/7 channels.',
    resources: ['catalog', 'meta', 'stream'],
    types: ['tv'],
    catalogs: [
        {
            type: 'tv',
            id: 'bintv_live',
            name: '🔴 Live Events'
        },
        {
            type: 'tv',
            id: 'bintv_upcoming',
            name: '📅 Upcoming Events'
        },
        {
            type: 'tv',
            id: 'bintv_channels',
            name: '📺 24/7 Channels'
        }
    ],
    idPrefixes: ['bintv:']
};

module.exports = async (req, res) => {
    // Add CORS headers explicitly for Stremio client compatibility
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');

    const urlPath = req.url.split('?')[0];

    // Manifest Endpoint
    if (urlPath === '/' || urlPath === '/manifest.json') {
        return res.status(200).json(manifest);
    }

    try {
        // Fetch fresh payload array data from raw Lovable source
        const apiResponse = await axios.get(API_URL);
        const data = apiResponse.data;

        // Catalog Endpoint
        if (urlPath.startsWith('/catalog/tv/')) {
            const catalogId = urlPath.split('/')[3].replace('.json', '');
            let items = [];

            if (catalogId === 'bintv_live' && data['Live Events']) {
                items = data['Live Events'];
            } else if (catalogId === 'bintv_upcoming' && data['Upcoming Events']) {
                items = data['Upcoming Events'];
            } else if (catalogId === 'bintv_channels' && data['24/7 Channels']) {
                items = data['24/7 Channels'];
            }

            const metas = items.map(item => ({
                id: `bintv:${item.id}`,
                type: 'tv',
                name: item.name,
                poster: item.poster,
                banner: item.poster,
                genres: [item.category || 'Sports'],
                description: `Status: ${item.status}. Stream options: ${item.streams ? item.streams.map(s => s.name).join(', ') : 'None'}`
            }));

            return res.status(200).json({ metas });
        }

        // Meta Endpoint
        if (urlPath.startsWith('/meta/tv/')) {
            const rawId = urlPath.split('/')[3].replace('.json', '').replace('bintv:', '');
            
            // Search all arrays for the item definition
            const allItems = [
                ...(data['Live Events'] || []),
                ...(data['Upcoming Events'] || []),
                ...(data['24/7 Channels'] || [])
            ];
            
            const item = allItems.find(i => i.id === rawId);

            if (!item) return res.status(404).json({ error: 'Item not found' });

            const meta = {
                id: `bintv:${item.id}`,
                type: 'tv',
                name: item.name,
                poster: item.poster,
                banner: item.poster,
                genres: [item.category || 'Sports'],
                description: `Watch live video coverage of ${item.name}.`
            };

            return res.status(200).json({ meta });
        }

        // Stream Endpoint
        if (urlPath.startsWith('/stream/tv/')) {
            const rawId = urlPath.split('/')[3].replace('.json', '').replace('bintv:', '');
            
            const allItems = [
                ...(data['Live Events'] || []),
                ...(data['Upcoming Events'] || []),
                ...(data['24/7 Channels'] || [])
            ];
            
            const item = allItems.find(i => i.id === rawId);

            if (!item || !item.streams) {
                return res.status(200).json({ streams: [] });
            }

            // Map standard web URLs/M3U8 links to Stremio Engine structure
            const streams = item.streams.map(stream => ({
                name: `BinTV\n${stream.name}`,
                title: item.name,
                url: stream.url // Stremio external player / web view fallback link
            }));

            return res.status(200).json({ streams });
        }

        return res.status(404).json({ error: 'Endpoint path not matched' });

    } catch (error) {
        console.error(error);
        return res.status(500).json({ error: 'Internal pipeline broken fetching remote sports JSON content' });
    }
};
