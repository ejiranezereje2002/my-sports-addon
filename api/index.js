const axios = require('axios');

const API_URL = 'https://lovable.app';

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
    // Force set headers to completely remove any CORS blocks or parsing friction
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');

    // Handle initial pre-flight check options safely
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // Safely extract the pathname as a pure string
    const fullUrl = req.url || '';
    const cleanPath = fullUrl.split('?')[0];

    // Manifest Endpoint - Catches all common root variations
    if (cleanPath === '/' || cleanPath === '/manifest.json' || cleanPath === '/api' || cleanPath === '/api/index') {
        return res.status(200).json(manifest);
    }

    try {
        const apiResponse = await axios.get(API_URL);
        const data = apiResponse.data || {};

        // Catalog Endpoint
        if (cleanPath.includes('/catalog/tv/')) {
            const catalogId = cleanPath.split('/catalog/tv/')[1].replace('.json', '');
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
                name: item.name || 'Unknown Event',
                poster: item.poster || '',
                banner: item.poster || '',
                genres: [item.category || 'Sports'],
                description: `Status: ${item.status || 'Active'}`
            }));

            return res.status(200).json({ metas });
        }

        // Meta Endpoint
        if (cleanPath.includes('/meta/tv/')) {
            const pathId = cleanPath.split('/meta/tv/')[1].replace('.json', '');
            const rawId = decodeURIComponent(pathId).replace('bintv:', '');
            
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
                name: item.name || 'Unknown Event',
                poster: item.poster || '',
                banner: item.poster || '',
                genres: [item.category || 'Sports'],
                description: `Watch live video coverage of ${item.name || 'this channel'}.`
            };

            return res.status(200).json({ meta });
        }

        // Stream Endpoint
        if (cleanPath.includes('/stream/tv/')) {
            const pathId = cleanPath.split('/stream/tv/')[1].replace('.json', '');
            const rawId = decodeURIComponent(pathId).replace('bintv:', '');
            
            const allItems = [
                ...(data['Live Events'] || []),
                ...(data['Upcoming Events'] || []),
                ...(data['24/7 Channels'] || [])
            ];
            
            const item = allItems.find(i => i.id === rawId);

            if (!item || !item.streams) {
                return res.status(200).json({ streams: [] });
            }

            const streams = item.streams.map(stream => {
                const streamObj = {
                    name: `BinTV\n${stream.name || 'Link'}`,
                    title: item.name || 'Stream'
                };

                const streamUrl = stream.url || '';
                if (streamUrl.includes('.m3u8') || streamUrl.includes('.mpd')) {
                    streamObj.url = streamUrl;
                } else {
                    streamObj.externalUrl = streamUrl;
                }

                return streamObj;
            });

            return res.status(200).json({ streams });
        }

        // Fallback catch-all error handling for unrecognized stream routes
        return res.status(404).json({ error: 'Endpoint path not matched' });

    } catch (error) {
        console.error('Addon Engine Crash Hook:', error.message);
        return res.status(200).json({ 
            metas: [], 
            streams: [], 
            note: 'Graceful crash recovery active. Check remote API target status.' 
        });
    }
};
