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
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');

    // FIX: Safely parse out the true clean string pathname without queries
    const cleanPath = req.url.split('?')[0];

    // Manifest Endpoint
    if (cleanPath === '/' || cleanPath === '/manifest.json') {
        return res.status(200).json(manifest);
    }

    try {
        const apiResponse = await axios.get(API_URL);
        const data = apiResponse.data;

        // Catalog Endpoint
        if (cleanPath.startsWith('/catalog/tv/')) {
            const catalogId = cleanPath.replace('/catalog/tv/', '').replace('.json', '');
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
                description: `Status: ${item.status || 'Active'}`
            }));

            return res.status(200).json({ metas });
        }

        // Meta Endpoint
        if (cleanPath.startsWith('/meta/tv/')) {
            // FIX: Using decodeURIComponent to handle special characters or dashes in IDs safely
            const rawId = decodeURIComponent(cleanPath.replace('/meta/tv/', '').replace('.json', '').replace('bintv:', ''));
            
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
        if (cleanPath.startsWith('/stream/tv/')) {
            const rawId = decodeURIComponent(cleanPath.replace('/stream/tv/', '').replace('.json', '').replace('bintv:', ''));
            
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
                    name: `BinTV\n${stream.name}`,
                    title: item.name
                };

                if (stream.url.includes('.m3u8') || stream.url.includes('.mpd')) {
                    streamObj.url = stream.url;
                } else {
                    streamObj.externalUrl = stream.url;
                }

                return streamObj;
            });

            return res.status(200).json({ streams });
        }

        return res.status(404).json({ error: 'Endpoint path not matched' });

    } catch (error) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error processing payload infrastructure' });
    }
};
