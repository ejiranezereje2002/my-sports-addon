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

    // Isolate path parts by stripping query items and splitting by slashes
    const rawUrl = req.url || '';
    const pathString = rawUrl.split('?')[0];
    const pathParts = pathString.split('/').filter(Boolean);

    // 1. Manifest Endpoint handler (Handles /, /manifest.json, /api, /api/manifest.json)
    if (pathParts.length === 0 || pathParts[pathParts.length - 1] === 'manifest.json' || pathParts[pathParts.length - 1] === 'api') {
        return res.status(200).json(manifest);
    }

    // Load API payload data
    let data = {};
    try {
        const apiResponse = await axios.get(API_URL, { timeout: 8000 });
        data = apiResponse.data || {};
    } catch (apiErr) {
        console.error('Failed to fetch sports API payload:', apiErr.message);
        if (pathString.includes('/catalog/')) return res.status(200).json({ metas: [] });
        if (pathString.includes('/stream/')) return res.status(200).json({ streams: [] });
        if (pathString.includes('/meta/')) return res.status(200).json({ meta: {} });
        return res.status(200).json(manifest);
    }

    // 2. Catalog Endpoint handler
    if (pathString.includes('/catalog/')) {
        try {
            // Stremio path structure template: /catalog/{type}/{id}.json
            const jsonFile = pathParts[pathParts.length - 1] || '';
            const catalogId = jsonFile.replace('.json', '');
            
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

    // 3. Meta Endpoint handler
    if (pathString.includes('/meta/')) {
        try {
            // Stremio path structure template: /meta/{type}/{id}.json
            const jsonFile = pathParts[pathParts.length - 1] || '';
            const rawId = decodeURIComponent(jsonFile.replace('.json', '')).replace('bintv:', '');
            
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

    // 4. Stream Endpoint handler
    if (pathString.includes('/stream/')) {
        try {
            // Stremio path structure template: /stream/{type}/{id}.json
            const jsonFile = pathParts[pathParts.length - 1] || '';
            const rawId = decodeURIComponent(jsonFile.replace('.json', '')).replace('bintv:', '');
            
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
