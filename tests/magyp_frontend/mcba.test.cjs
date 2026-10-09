const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { webcrypto } = require('node:crypto');
global.crypto = webcrypto;
const mcba = require('../../mcba-prices.js');
const folder = path.join(__dirname, '../../data/magyp/dashboard/mcba');
const bundle = () => ({
    daily: fs.readFileSync(path.join(folder, 'MCBA_MAGYP_DAILY.csv'), 'utf8'),
    summary: fs.readFileSync(path.join(folder, 'MCBA_MAGYP_SUMMARY.csv'), 'utf8'),
    marker: JSON.parse(fs.readFileSync(path.join(folder, '_SUCCESS.json'), 'utf8'))
});
const fixture = () => mcba.parseCSV(bundle().daily).slice(0, 1);
const summary = rows => ({ valid_rows: rows.length,
    detail_rows: rows.filter(r => r.observation_level === 'detail').length, dashboard_schema_version: 'mcba-dashboard-v3' });

test('public bundle hashes, shape and counts are valid', async () => {
    const result = await mcba.verifyBundle(bundle());
    assert.ok(result.rows.length > 0);
    const detail = mcba.adapt(result.rows, ['Enero']);
    assert.ok(detail.every(r => r.observation_level === 'detail' && r.volume === '' && r.kgBulto === null));
    assert.equal(detail.length, Number(result.info.detail_rows));
});
test('corrupt/empty publication is rejected', async () => {
    const b = bundle(); b.daily += '\n';
    await assert.rejects(mcba.verifyBundle(b), /Publicación incompleta/);
    assert.throws(() => mcba.validate([], summary([])), /vacía/);
});
test('missing column, invalid date/price/currency/volume and exact duplicates fail closed', () => {
    assert.throws(() => mcba.parseCSV('date,price\n2026-08-24,2\n'), /Contrato/);
    for (const [field, value] of [['price','bad'], ['date','2026-02-31'], ['currency','USD'],
        ['price_unit','tn'], ['raw_sha256','bad'], ['volume','0']]) {
        const rows = fixture(); rows[0][field] = value;
        assert.throws(() => mcba.validate(rows, summary(rows)), /inválida/);
    }
    const rows = fixture().concat(fixture());
    assert.throws(() => mcba.validate(rows, summary(rows)), /inválida/);
});
test('RFC4180 quoted fields and newlines are parsed without label corrections', () => {
    const rows = mcba.parseCSV('a,b\n"ESPA¥A, x","line1\nline2"\n', ['a','b']);
    assert.deepEqual(rows, [{a:'ESPA¥A, x', b:'line1\nline2'}]);
});
test('daily MCBA priority is decided by date before product filtering', () => {
    const legacy = [
        {mercado:mcba.MCBA, fecha:'2026-08-24', especie:'Missing',fechaPrecision:'diaria'},
        {mercado:mcba.MCBA, fecha:'2026-08-25', especie:'Other',fechaPrecision:'diaria'},
        {mercado:mcba.MCBA, fecha:'2025-10-01',fechaPrecision:'Mensual'},
        {mercado:'Mercado de Corrientes',fecha:'2026-08-24',fechaPrecision:'diaria'}
    ];
    const modern = [{mercado:mcba.MCBA,fecha:'2026-08-24',especie:'Manzana'}];
    const daily = mcba.route(legacy, modern, 'diaria');
    assert.equal(daily.length, 3);
    assert.ok(!daily.some(r => r.especie === 'Missing'));
    assert.strictEqual(daily.find(r => r.mercado === 'Mercado de Corrientes'), legacy[3]);
});
test('monthly and annual preserve legacy and never derive official monthly from daily', () => {
    const legacy = [{mercado:mcba.MCBA,fechaPrecision:'mensual'}];
    assert.deepEqual(mcba.route(legacy, [{mercado:mcba.MCBA}], 'mensual'), legacy);
    assert.deepEqual(mcba.route(legacy, [{mercado:mcba.MCBA}], 'anual'), legacy);
});
test('unknown MAGyP coverage does not authorize daily legacy replacement', () => {
    const legacy = [{mercado:mcba.MCBA,fecha:'2026-08-24',fechaPrecision:'diaria'},
        {mercado:'Mercado de Corrientes',fecha:'2026-08-24',fechaPrecision:'diaria'}];
    assert.deepEqual(mcba.route(legacy, [], 'diaria', false), [legacy[1]]);
    assert.deepEqual(mcba.route(legacy, [], 'mensual', false), legacy);
});
test('frontend keeps raw/normalized labels and excludes species summaries', () => {
    const rows = fixture();
    rows[0].observation_level = 'detail';
    rows[0].product_raw = 'ESPA¥A'; rows[0].product_normalized = 'ESPA¥A';
    const adapted = mcba.adapt(rows.concat({...rows[0],observation_level:'species_summary'}), ['Enero'], 'MAGYP_LAST_VALID');
    assert.equal(adapted.length, 1);
    assert.equal(adapted[0].product_raw, 'ESPA¥A');
    assert.equal(adapted[0].source_status, 'MAGYP_LAST_VALID');
    assert.equal(adapted[0].precioObservado, Number(rows[0].price));
});
test('network failure with no validated browser cache is explicit legacy', async () => {
    const previous = global.fetch;
    global.fetch = async () => { throw Error('offline'); };
    try {
        const result = await mcba.load();
        assert.equal(result.status, 'LEGACY');
        assert.match(result.warning, /sin copia válida/);
    } finally { global.fetch = previous; }
});
test('publisher failure status uses last valid MAGyP instead of legacy', async () => {
    const previous = global.fetch;
    const b = bundle();
    global.fetch = async url => ({ok:true, text:async () =>
        url.endsWith('DAILY.csv') ? b.daily : url.endsWith('SUMMARY.csv') ? b.summary :
        url.endsWith('_SUCCESS.json') ? JSON.stringify(b.marker) : '{"source_status":"MAGYP_LAST_VALID"}'});
    try {
        const result = await mcba.load();
        assert.equal(result.status, 'MAGYP_LAST_VALID');
        assert.ok(result.rows.length);
        assert.match(result.warning, /última salida/);
    } finally { global.fetch = previous; }
});
