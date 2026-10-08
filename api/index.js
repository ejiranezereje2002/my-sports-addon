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
    // Inject correct headers for cross-origin handshakes
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // Safely parse the incoming path using standard string cleaning
    const rawUrl = req.url || '';
    const cleanPath = rawUrl.split('?')[0]; 

    // 1. Manifest Endpoint Routing
    if (cleanPath === '/' || cleanPath === '/manifest.json' || cleanPath.endsWith('/api') || cleanPath.endsWith('/api/index')) {
        return res.status(200).json(manifest);
    }

    try {
        const apiResponse = await axios.get(API_URL);
        const data = apiResponse.data || {};

        // 2. Catalog Endpoint Routing
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

        // 3. Meta Endpoint Routing
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

        // 4. Stream Endpoint Routing
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

        return res.status(404).json({ error: 'Endpoint path not matched' });

    } catch (error) {
        console.error('Addon Engine Exception Context:', error.message);
        
        // Dynamically return clean responses corresponding strictly to the endpoint type
        if (cleanPath.includes('/catalog/')) {
            return res.status(200).json({ metas: [] });
        }
        if (cleanPath.includes('/stream/')) {
            return res.status(200).json({ streams: [] });
        }
        if (cleanPath.includes('/meta/')) {
            return res.status(200).json({ meta: {} });
        }
        
        return res.status(200).json(manifest);
    }
};
