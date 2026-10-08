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

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const rawUrl = req.url || '';
    // Safely extract path string before any query parameters
    const cleanPath = rawUrl.split('?')[0]; 

    // 1. Manifest Endpoint
    if (cleanPath === '/' || cleanPath === '/manifest.json' || cleanPath.endsWith('/api') || cleanPath.endsWith('/api/index')) {
        return res.status(200).json(manifest);
    }

    // Initialize data storage safely
    let data = {};
    try {
        const apiResponse = await axios.get(API_URL, { timeout: 8000 });
        data = apiResponse.data || {};
    } catch (apiErr) {
        console.error('Failed to fetch sports API payload:', apiErr.message);
        // If external API times out, return empty structures quickly to prevent Stremio stalling
        if (cleanPath.includes('/catalog/')) return res.status(200).json({ metas: [] });
        if (cleanPath.includes('/stream/')) return res.status(200).json({ streams: [] });
        if (cleanPath.includes('/meta/')) return res.status(200).json({ meta: {} });
        return res.status(200).json(manifest);
    }

    // 2. Catalog Endpoint
    if (cleanPath.includes('/catalog/tv/')) {
        try {
            const parts = cleanPath.split('/catalog/tv/');
            const catalogFileName = parts[parts.length - 1] || '';
            const catalogId = catalogFileName.replace('.json', '');
            
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
                name: String(item.name || 'Unknown Event'),
                poster: String(item.poster || ''),
                banner: String(item.poster || ''),
                genres: [String(item.category || 'Sports')],
                description: `Status: ${String(item.status || 'Active')}`
            }));

            return res.status(200).json({ metas });
        } catch (err) {
            console.error('Catalog serialization crashed:', err.message);
            return res.status(200).json({ metas: [] });
        }
    }

    // 3. Meta Endpoint
    if (cleanPath.includes('/meta/tv/')) {
        try {
            const parts = cleanPath.split('/meta/tv/');
            const metaFileName = parts[parts.length - 1] || '';
            const rawId = decodeURIComponent(metaFileName.replace('.json', '')).replace('bintv:', '');
            
            const allItems = [
                ...(data['Live Events'] || []),
                ...(data['Upcoming Events'] || []),
                ...(data['24/7 Channels'] || [])
            ];
            
            const item = allItems.find(i => String(i.id) === String(rawId));
            if (!item) return res.status(200).json({ meta: {} });

            const meta = {
                id: `bintv:${item.id}`,
                type: 'tv',
                name: String(item.name || 'Unknown Event'),
                poster: String(item.poster || ''),
                banner: String(item.poster || ''),
                genres: [String(item.category || 'Sports')],
                description: `Watch live video coverage of ${String(item.name || 'this channel')}.`
            };

            return res.status(200).json({ meta });
        } catch (err) {
            console.error('Meta parser crashed:', err.message);
            return res.status(200).json({ meta: {} });
        }
    }

    // 4. Stream Endpoint
    if (cleanPath.includes('/stream/tv/')) {
        try {
            const parts = cleanPath.split('/stream/tv/');
            const streamFileName = parts[parts.length - 1] || '';
            const rawId = decodeURIComponent(streamFileName.replace('.json', '')).replace('bintv:', '');
            
            const allItems = [
                ...(data['Live Events'] || []),
                ...(data['Upcoming Events'] || []),
                ...(data['24/7 Channels'] || [])
            ];
            
            const item = allItems.find(i => String(i.id) === String(rawId));
            if (!item || !item.streams) return res.status(200).json({ streams: [] });

            const streams = item.streams.map(stream => {
                const streamObj = {
                    name: `BinTV\n${String(stream.name || 'Link')}`,
                    title: String(item.name || 'Stream')
                };

                const streamUrl = String(stream.url || '');
                if (streamUrl.includes('.m3u8') || streamUrl.includes('.mpd')) {
                    streamObj.url = streamUrl;
                } else {
                    streamObj.externalUrl = streamUrl;
                }

                return streamObj;
            });

            return res.status(200).json({ streams });
        } catch (err) {
            console.error('Stream processing crashed:', err.message);
            return res.status(200).json({ streams: [] });
        }
    }

    return res.status(404).json({ error: 'Endpoint path not matched' });
};
