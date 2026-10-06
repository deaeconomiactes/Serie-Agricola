/* Adapter for published MCBA detail. No source aliases are applied in the browser. */
(function (root) {
    'use strict';
    const MCBA = 'Mercado Central de Buenos Aires';
    const BASE = 'data/magyp/dashboard/mcba/';
    const REQUIRED = ['date', 'type', 'product_normalized', 'variety_normalized',
        'origin_normalized', 'package_normalized', 'quality', 'size', 'grade', 'price',
        'currency', 'price_unit', 'observation_level', 'observation_id', 'raw_sha256',
        'capture_id', 'capture_timestamp', 'source_url', 'product_raw', 'variety_raw',
        'origin_raw', 'package_raw', 'kg_raw', 'volume', 'data_source', 'source_status', 'last_update'];

    // RFC4180, including quoted newlines and UTF-8 BOM. Invalid shapes fail closed.
    function parseCSV(text, required = REQUIRED) {
        text = text.replace(/^\uFEFF/, '');
        const rows = []; let cells = [], cell = '', quoted = false;
        for (let i = 0; i < text.length; i++) {
            const c = text[i];
            if (c === '"') {
                if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
                else if (quoted || cell === '') quoted = !quoted;
                else throw new Error('Comillas CSV inválidas');
            } else if (!quoted && (c === ',' || c === '\n')) {
                cells.push(cell.replace(/\r$/, '')); cell = '';
                if (c === '\n') { rows.push(cells); cells = []; }
            } else cell += c;
        }
        if (quoted) throw new Error('CSV incompleto');
        if (cell || cells.length) { cells.push(cell.replace(/\r$/, '')); rows.push(cells); }
        const headers = rows.shift() || [];
        if (new Set(headers).size !== headers.length || required.some(k => !headers.includes(k)))
            throw new Error('Contrato MCBA cambiado');
        return rows.filter(r => r.some(Boolean)).map(r => {
            if (r.length !== headers.length) throw new Error('Fila CSV incompleta');
            return Object.fromEntries(headers.map((h, i) => [h, r[i]]));
        });
    }
    function validate(rows, summary) {
        if (!rows.length || !summary || Number(summary.valid_rows) !== rows.length ||
            summary.dashboard_schema_version !== 'mcba-dashboard-v3') throw new Error('Captura vacía o incompleta');
        const ids = new Set();
        for (const r of rows) {
            const d = new Date(r.date + 'T00:00:00Z');
            if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date) || !Number.isFinite(d.valueOf()) ||
                d.toISOString().slice(0, 10) !== r.date || !(Number(r.price) > 0) ||
                !Number.isFinite(Number(r.price)) || !r.product_normalized || r.currency !== 'ARS' ||
                r.price_unit !== 'kg' || !['detail', 'species_summary'].includes(r.observation_level) ||
                !/^[a-f0-9]{64}$/.test(r.raw_sha256) || !r.capture_id || !r.observation_id ||
                !Number.isFinite(Date.parse(r.capture_timestamp)) || r.volume ||
                r.source_url !== 'https://ssma.magyp.gob.ar/frutas.precios.aspx' ||
                r.data_source !== 'MAGYP' || r.source_status !== 'MAGYP' ||
                (r.observation_level === 'detail' && r.variety_normalized === 'PROM.ESP.') || ids.has(r.observation_id))
                throw new Error('Observación MCBA inválida');
            ids.add(r.observation_id);
        }
        if (Number(summary.detail_rows) !== rows.filter(r => r.observation_level === 'detail').length)
            throw new Error('Conteo detail inconsistente');
        return rows;
    }
    function adapt(rows, months, status = 'MAGYP', label = value => value || '') {
        return rows.filter(r => r.observation_level === 'detail').map(r => ({
            ...r, fecha: r.date, year: Number(r.date.slice(0, 4)), month: Number(r.date.slice(5, 7)),
            mes: months[Number(r.date.slice(5, 7)) - 1], fechaPrecision: 'diaria',
            rubro: /HORTAL/i.test(r.type) ? 'Hortalizas' : /FRUT/i.test(r.type) ? 'Frutas' : r.type,
            especie: label(r.product_normalized), variedad: label(r.variety_normalized),
            mercado: MCBA, procedencia: label(r.origin_normalized), unidad: '$/kg', envase: label(r.package_normalized),
            calidadMCBA: r.quality, tamanoMCBA: r.size, gradoMCBA: r.grade,
            precio: Number(r.price), precioObservado: Number(r.price), precioKgEstimado: Number(r.price),
            precioPromedio: Number(r.price), precioMin: null, precioMax: null, kgBulto: null,
            unidadPrecioObservado: '$/kg', metodoConversion: 'Precio publicado por kg', confianzaConversion: 'Alta',
            calidad: '', fuente: r.source_url, source_status: status,
            product_normalized: r.product_normalized, variety_normalized: r.variety_normalized
        }));
    }
    function route(legacy, magyp, frequency, coverageKnown = true) {
        const daily = frequency === 'diaria';
        // Coverage is decided before product/origin filters: never fill a missing dimension with legacy.
        const covered = new Set(magyp.map(r => r.fecha));
        const historical = legacy.filter(r => r.mercado !== MCBA ||
            (!daily || (coverageKnown && String(r.fechaPrecision).toLowerCase() !== 'mensual' && !covered.has(r.fecha))));
        return daily ? historical.concat(magyp) : historical;
    }
    async function hash(text) {
        const bytes = new TextEncoder().encode(text);
        return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
            .map(n => n.toString(16).padStart(2, '0')).join('');
    }
    function parseSummary(text) {
        const rows = parseCSV(text, ['valid_rows', 'detail_rows', 'dashboard_schema_version', 'updated_at']);
        if (rows.length !== 1) throw new Error('Resumen inválido');
        return rows[0];
    }
    async function verifyBundle(bundle) {
        const { daily, summary, marker } = bundle;
        if (await hash(daily) !== marker.files?.['MCBA_MAGYP_DAILY.csv'] ||
            await hash(summary) !== marker.files?.['MCBA_MAGYP_SUMMARY.csv']) throw new Error('Publicación incompleta');
        const info = parseSummary(summary);
        const rows = validate(parseCSV(daily), info);
        if (Number(marker.record_count) !== rows.length) throw new Error('Manifest inconsistente');
        return { rows, info };
    }
    async function cache(mode, bundle) {
        if (typeof indexedDB === 'undefined') return null;
        return new Promise(resolve => {
            const request = indexedDB.open('serie-agricola-mcba', 1);
            request.onupgradeneeded = () => request.result.createObjectStore('published');
            request.onerror = () => resolve(null);
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction('published', mode === 'write' ? 'readwrite' : 'readonly');
                const op = mode === 'write' ? tx.objectStore('published').put(bundle, 'last-valid-v3')
                    : tx.objectStore('published').get('last-valid-v3');
                let value = null;
                op.onsuccess = () => { value = op.result; };
                tx.oncomplete = () => { db.close(); resolve(value); };
                tx.onerror = () => { db.close(); resolve(null); };
                tx.onabort = () => { db.close(); resolve(null); };
            };
        });
    }
    async function load() {
        try {
            const get = async name => {
                const response = await fetch(BASE + name, { cache: 'no-store' });
                if (!response.ok) throw new Error('Publicación MCBA no disponible');
                return response.text();
            };
            const [daily, summary, markerText, updateText] = await Promise.all([
                get('MCBA_MAGYP_DAILY.csv'), get('MCBA_MAGYP_SUMMARY.csv'), get('_SUCCESS.json'),
                get('MCBA_MAGYP_UPDATE_STATUS.json').catch(() => '{}')]);
            const bundle = { daily, summary, marker: JSON.parse(markerText) };
            const result = await verifyBundle(bundle);
            await cache('write', bundle);
            const lastValid = JSON.parse(updateText).source_status === 'MAGYP_LAST_VALID';
            return { ...result, status: lastValid ? 'MAGYP_LAST_VALID' : 'MAGYP',
                warning: lastValid ? 'Falló la última actualización; se conserva la última salida MAGyP válida.' : '' };
        } catch (error) {
            const previous = await cache('read');
            if (previous) {
                try { return { ...await verifyBundle(previous), status: 'MAGYP_LAST_VALID',
                    warning: 'Actualización MAGyP no disponible; se conserva la última versión válida.' }; }
                catch (_) { /* Corrupt cache is not used. */ }
            }
            return { rows: [], info: null, status: 'LEGACY',
                warning: 'MAGyP no disponible y sin copia válida local. No se puede verificar cobertura diaria; el respaldo legacy sigue disponible en frecuencia mensual.' };
        }
    }
    const api = { MCBA, BASE, parseCSV, validate, adapt, route, verifyBundle, load };
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.MCBAPrices = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
