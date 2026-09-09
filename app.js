/* ======================================================================
   Dashboard Agrícola – Corrientes 2025  |  app.js
   ====================================================================== */

// ─── Constants ──────────────────────────────────────────────────────────
const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
const MONTHS_FULL = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const CSV_PATH = 'REGISTRO 2025 INTEGRADO.csv';
const PRICE_CSV_PATH = 'PRECIOS_MAYORISTAS_INTEGRADO.csv';
const PRICE_CSV_FALLBACK_PATH = 'PRECIOS_MAYORISTAS_2026_INTEGRADO.csv';
const COMMODITY_SOURCE_CONFIG = {
    sio: {
        label: 'SIO Granos — operaciones informadas',
        subtitle: 'Fuente SIO Granos — operaciones informadas',
        path: 'data/commodities_sio/dashboard/',
        files: { diario: 'COMMODITIES_SIO_DASHBOARD_DIARIO.csv', mensual: 'COMMODITIES_SIO_DASHBOARD_MENSUAL.csv', ultimos: 'COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv', resumen: 'COMMODITIES_SIO_DASHBOARD_RESUMEN.csv', semaforo: 'COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv' },
        monthlyOnly: false,
        operationsLabel: 'Operaciones con precio',
        operationsUnit: 'precios positivos',
        note: 'Fuente: SIO Granos. Operaciones informadas. Los precios cero se excluyen de las series. ARS y USD se analizan por separado.'
    },
    local_mensual: {
        label: 'Histórico local mensual — precios internos',
        subtitle: 'Histórico local mensual — precios internos',
        path: 'data/commodities_local_mensual/dashboard/',
        files: { diario: null, mensual: 'COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv', ultimos: 'COMMODITIES_LOCAL_MENSUAL_DASHBOARD_ULTIMOS.csv', resumen: 'COMMODITIES_LOCAL_MENSUAL_DASHBOARD_RESUMEN.csv', semaforo: 'COMMODITIES_LOCAL_MENSUAL_DASHBOARD_SEMAFORO.csv' },
        monthlyOnly: true,
        operationsLabel: 'Observaciones con precio',
        operationsUnit: 'precios positivos por plaza',
        note: 'Fuente: Secretaría de Agricultura / Mercados Agropecuarios. Serie mensual de precios internos de principales granos en pesos por tonelada. No equivale a operaciones SIO, precios FOB/FAS ni precios de pizarra BCR.'
    }
};

// Canonical names used by filters, aggregations and chart data. The keys are
// compact location keys so accents, punctuation and spacing cannot create
// duplicate locations.
const LOCATION_EQUIVALENCES = {
    BUENOSAIRES: 'Buenos Aires', BSAS: 'Buenos Aires',
    CABA: 'Ciudad Autónoma de Buenos Aires',
    CAPITALFEDERAL: 'Ciudad Autónoma de Buenos Aires',
    CIUDADAUTONOMADEBUENOSAIRES: 'Ciudad Autónoma de Buenos Aires',
    MDPLAT: 'Mar del Plata', MDP: 'Mar del Plata', MARDELPLATA: 'Mar del Plata',
    PTORICO: 'Puerto Rico', PUERTORICO: 'Puerto Rico',
    SBSAS: 'Buenos Aires',
    CORDOBA: 'Córdoba', CBA: 'Córdoba',
    ERIOS: 'Entre Ríos', ENTRERIOS: 'Entre Ríos',
    GRLBELG: 'General Belgrano', GRALBELGRANO: 'General Belgrano', GENERALBELGRANO: 'General Belgrano',
    SPEDRO: 'San Pedro', SANPEDRO: 'San Pedro',
    CATAMARC: 'Catamarca', RNEGRO: 'Río Negro',
    NEUQUEN: 'Neuquén', TUCUMAN: 'Tucumán', MEXICO: 'México', PERU: 'Perú',
    SGODELESTERO: 'Santiago del Estero', SGOEST: 'Santiago del Estero', SANTIAGODELESTERO: 'Santiago del Estero',
    STACRUZ: 'Santa Cruz',
    LARIOJA: 'La Rioja', LAPAMPA: 'La Pampa', JUJUY: 'Jujuy', SALTA: 'Salta', MENDOZA: 'Mendoza',
    MISIONES: 'Misiones', FORMOSA: 'Formosa', CHUBUT: 'Chubut', CHACO: 'Chaco', CORRIENTES: 'Corrientes',
    SANJUAN: 'San Juan', SANLUIS: 'San Luis', SANTAFE: 'Santa Fe', TIERRADELFUEGO: 'Tierra del Fuego',
    CHILE: 'Chile', CHINA: 'China', COLOMBIA: 'Colombia', ECUADOR: 'Ecuador', ESPANA: 'España',
    GRECIA: 'Grecia', ITALIA: 'Italia', PARAGUAY: 'Paraguay', PORTUGAL: 'Portugal', URUGUAY: 'Uruguay',
    BRASIL: 'Brasil'
};

// Chart.js color palette
const PALETTE = [
    '#34d399', '#60a5fa', '#fb923c', '#a78bfa', '#fb7185',
    '#22d3ee', '#fbbf24', '#f472b6', '#4ade80', '#818cf8',
    '#f87171', '#38bdf8', '#facc15', '#c084fc', '#2dd4bf'
];

const PALETTE_ALPHA = PALETTE.map(c => c + '33');

// ─── Variety normalization map ──────────────────────────────────────────
// ─── Species normalization map ──────────────────────────────────────────
const SPECIES_MAP = {
    'CEB.VERDEO': 'CEBOLLA DE VERDEO',
    'CILANDRO': 'CILANTRO',
    'DURAZONO': 'DURAZNO',
    'HOR.PRO.VS': 'HORTALIZAS VARIAS',
    'REP.BRUSEL': 'REPOLLITOS DE BRUSELAS',
    'RESTO FRU': 'RESTO FRUTAS',
    'RTO.HORTAL': 'RESTO HORTALIZAS',
    'SIA.GRANEL': 'FRUTAS A GRANEL'
};

function normalizeEspecie(especie) {
    if (SPECIES_MAP[especie] !== undefined) {
        return SPECIES_MAP[especie];
    }
    const equivalent = Object.entries(SPECIES_MAP).find(([key]) => normalizeText(key) === normalizeText(especie));
    if (equivalent) return equivalent[1];
    return especie;
}

// Key: "ESPECIE|VARIEDAD" (raw) → normalized variedad
// When the CORRIENTES market uses "TOMATE CHERRY" as variedad for especie TOMATE,
// we normalize it to just "CHERRY" to match the BSAS format.
const VARIETY_MAP = {
    // TOMATE
    'TOMATE|TOMATE CHERRY': 'CHERRY',
    'TOMATE|TOMATE PERITA': 'PERITA',
    'TOMATE|TOMATE REDONDO': 'REDONDO',
    'TOMATE|TOMATE': 'SIN VARIEDAD',
    'TOMATE|LARGA VIDA': 'LARGA VIDA',

    // PIMIENTO
    'PIMIENTO|PIMIENTO MORRON ROJO': 'MORRON ROJO',
    'PIMIENTO|PIMIENTO MORRON VERDE': 'MORRON VERDE',
    'PIMIENTO|PIMIENTO MORRON AMARILLO': 'MORRON AMARILLO',
    'PIMIENTO|PIMIENTO AJI VINAGRE': 'VINAGRE',
    'PIMIENTO|AJI PICANTE': 'PICANTE',
    'PIMIENTO|MORRON': 'MORRÓN',

    // NARANJA
    'NARANJA|NARANJA VALENCIA': 'VALENCIA',
    'NARANJA|NARANJA VALENCIA LATE': 'VALENCIA LATE',
    'NARANJA|NARANJA VALENCIA SEEDLES': 'VALENCIA SEEDLESS',
    'NARANJA|NARANJA SALUSTIANA': 'SALUSTIANA',
    'NARANJA|NARANJA OMBLIGO': 'OMBLIGO',
    'NARANJA|NARANJA NAVELINA': 'NAVELINA',
    'NARANJA|MIDK NIGTH': 'MIDKNIGHT',
    'NARANJA|VAL. FROST': 'VALENCIA FROST',
    'NARANJA|R. NAVEL': 'WASHINGTON NAVEL',
    'NARANJA|NAVEL LATE': 'LANE LATE',
    'NARANJA|VAL.SEEDLE': 'VALENCIA SEEDLESS',
    'NARANJA|VALEN.FROS': 'VALENCIA FROST',
    'NARANJA|VALEN.LATE': 'VALENCIA LATE',

    // LIMON
    'LIMON|LIMON': 'SIN VARIEDAD',
    'LIMON|LIMON COMERCIAL': 'SIN VARIEDAD',
    'LIMON|LIMON ELEGIDO': 'ELEGIDO',
    'LIMON|LIMONEIRA': 'EUREKA',

    // MANDARINA
    'MANDARINA|MANDARINA OKITSU': 'OKITSU',
    'MANDARINA|AFURE': 'AFOURER',
    'MANDARINA|W.MURCOT': 'W. MURCOTT',

    // POMELO
    'POMELO|POMELO ROSADO': 'ROSADO',
    'POMELO|MARSH.SEED': 'MARSH SEEDLESS',

    // SANDIA
    'SANDIA|SANDIA': 'SIN VARIEDAD',
    'SANDIA|SANDIA REDONDA RAYADA': 'REDONDA RAYADA',

    // FRUTILLA
    'FRUTILLA|FRUTILLA': 'SIN VARIEDAD',

    // PALTA
    'PALTA|PALTA': 'SIN VARIEDAD',

    // MELON
    'MELON|MELON CRIOLLO': 'CRIOLLO',
    'MELON|MELON ROCIO DE MIEL': 'ROCIO DE MIEL',
    'MELON|ROCIO MIEL': 'ROCIO DE MIEL',
    'MELON|SWEET HEAR': 'SWEET HEART',

    // BATATA
    'BATATA|BATATA BLANCA': 'BLANCA',
    'BATATA|BATATA COLORADA': 'COLORADA',

    // BERENJENA
    'BERENJENA|BERENJENA': 'SIN VARIEDAD',
    'BERENJENA|BCA.MED.LA': 'VIOLETA MEDIA LARGA',
    'BERENJENA|VTA.LARGA': 'VIOLETA MEDIA LARGA',
    'BERENJENA|VTA.MED.LA': 'VIOLETA MEDIA LARGA',

    // PEPINO
    'PEPINO|PEPINO': 'SIN VARIEDAD',

    // ZAPALLITO
    'ZAPALLITO|ZAPALLITO TRONCO': 'TRONCO',
    'ZAPALLITO|ZAPALLITO ZUCHINI': 'ZUCCHINI',
    'ZAPALLITO|ZAPALLITO': 'SIN VARIEDAD',

    // ZAPALLO
    'ZAPALLO|ZAPALLO COREANO': 'COREANO',
    'ZAPALLO|ZAPALLO INGLES': 'INGLES',
    'ZAPALLO|ZAPALLO PLOMO': 'PLOMO',
    'ZAPALLO|ZAPALLO TETSUKABUTO': 'TETSUKABUTO',
    'ZAPALLO|TETSUKAB.': 'TETSUKABUTO',
    'ZAPALLO|COQUENA': 'ANQUITO',

    // REPOLLO
    'REPOLLO|REPOLLO BLANCO': 'BLANCO',
    'REPOLLO|REPOLLO COLORADO': 'COLORADO',

    // CHAUCHA
    'CHAUCHA|CHAUCHA MUSICA': 'MUSICA',
    'CHAUCHA|CHAUCHA POR METRO': 'POR METRO',
    'CHAUCHA|CHAUCHA ROLLIZA': 'ROLLIZA',
    'CHAUCHA|CONTRANCHA': 'SIN VARIEDAD',

    // LECHUGA
    'LECHUGA|LECHUGA CRESPA': 'CRESPA',
    'LECHUGA|LECHUGA MANTECOSA': 'MANTECOSA',
    'LECHUGA|LECHUGA REPOLLADA': 'REPOLLADA',

    // CHOCLO
    'CHOCLO|CHOCLO AMARILLO': 'AMARILLO',
    'CHOCLO|CHOCLO CREMA': 'CREMA',
    'CHOCLO|CHOCLO CRIOLLO': 'CRIOLLO',

    // ACELGA
    'ACELGA|ACELGA': 'SIN VARIEDAD',

    // CEBOLLA DE VERDEO
    'CEBOLLA DE VERDEO|CEBOLLITA DE VERDEO': 'SIN VARIEDAD',

    // ALBAHACA
    'ALBAHACA|ALBAHACA': 'SIN VARIEDAD',

    // PEREJIL
    'PEREJIL|PEREJIL': 'SIN VARIEDAD',

    // RUCULA
    'RUCULA|RUCULA': 'SIN VARIEDAD',

    // ESPINACA
    'ESPINACA|ESPINACA': 'SIN VARIEDAD',

    // BROCOLI
    'BROCOLI|BROCOLI': 'SIN VARIEDAD',

    // MANDIOCA
    'MANDIOCA|MANDIOCA': 'SIN VARIEDAD',
    'MANDIOCA|MANDIOCA CORRIENTES': 'SIN VARIEDAD',

    // ACHICORIA
    'ACHICORIA|ACHICORIA': 'SIN VARIEDAD',

    // APIO
    'APIO|APIO DE HOJA': 'SIN VARIEDAD',

    // ARVEJA
    'ARVEJA|ARVEJA': 'SIN VARIEDAD',

    // REMOLACHA
    'REMOLACHA|REMOLACHA': 'SIN VARIEDAD',

    // RABANITO
    'RABANITO|RABANITO': 'SIN VARIEDAD',

    // PUERRO
    'PUERRO|PUERRO': 'SIN VARIEDAD',

    // CILANTRO
    'CILANTRO|CILANTRO': 'SIN VARIEDAD',

    // MENTA
    'MENTA|MENTA': 'SIN VARIEDAD',

    // COLIFLOR
    'COLIFLOR|COLIFLOR': 'SIN VARIEDAD',

    // KINOTO
    'KINOTO|KINOTO': 'SIN VARIEDAD',

    // POROTO
    'POROTO|POROTO SEÑORITA': 'SEÑORITA',

    // AROMATICAS
    'AROMATICAS|OREGANO': 'ORÉGANO',
    'AROMATICAS|LAUREL': 'LAUREL',

    // PAPA
    'PAPA|PAPA BLANCA': 'BLANCA',

    // BANANA
    'BANANA|BANANA BRASILEÑA': 'BRASILEÑA',
    'BANANA|BANANA PARAGUAYA': 'PARAGUAYA',

    // DURAZNO
    'DURAZNO|DURAZNO 1633': '1633',

    // PERA
    'PERA|PERA PACKAMS  COMERCIAL': "PACKHAM'S",
    'PERA|PERA PACKAMS ELEGIGA': "PACKHAM'S",

    // MANGO
    'MANGO|TOMMY ATKI': 'TOMMY ATKINS',
};

function normalizeVariedad(especie, variedad) {
    const key = especie + '|' + variedad;
    if (VARIETY_MAP[key] !== undefined) return VARIETY_MAP[key];
    const equivalent = Object.entries(VARIETY_MAP).find(([mapKey]) => {
        const [mapEspecie, mapVariedad] = mapKey.split('|');
        return normalizeText(mapEspecie) === normalizeText(especie)
            && normalizeText(mapVariedad) === normalizeText(variedad);
    });
    if (equivalent) return equivalent[1];
    if (variedad === 'SIN VARIED' || variedad === 'SIN VARIEDAD' || variedad === especie) {
        return 'SIN VARIEDAD';
    }
    return variedad;
}

// ─── Chart instances ────────────────────────────────────────────────────
let charts = {};
// Las instancias de precios se administran por separado para no afectar los gráficos de cantidades.
const priceCharts = {
    evolution: null,
    ranking: null,
    variation: null,
    increases: null,
    decreases: null,
    marketComparison: null,
    procedencia: null
};

// ─── State ──────────────────────────────────────────────────────────────
let rawData = [];
let quantityData = [];
let filteredData = [];
// Price data is intentionally independent from quantity data.
let rawPriceData = [];
let priceData = [];
let validPriceData = [];
let futurePriceData = [];
let filteredPriceData = [];
let priceSeriesData = [];
let priceQualityMap = new Map();
let priceFutureDateCount = 0;
let priceUnitMode = 'comparable';
let spreadsheetInvalidCount = 0;
let heatmapFilter = 'TODOS';
let selectedYear = '2025';
const selectedUnit = 'TN';
let quantityFrequency = 'mensual';
let priceFrequency = 'mensual';
let commodityFrequency = 'mensual';
let commoditySource = 'sio';
const commodityDataBySource = {};
let commodityData = { diario: [], mensual: [], ultimos: [], resumen: [], semaforo: [] };
let commoditySelectedValues = [];
const commodityCharts = { trend: null, ranking: null, volume: null };

// ─── Boot ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);

async function init() {
    showLoading();
    wireModuleTabs();
    initMultiSelectControls();
    try {
        await loadQuantityData();
        wireFilters();
    } catch (e) {
        console.error('Error loading CSV:', e);
    }
    try {
        await loadPriceData();
    } catch (e) {
        console.error('Error loading wholesale price CSV:', e);
        setPriceStatus('No se pudo cargar la base de precios mayoristas.', true);
    }
    try {
        await loadCommodityData();
    } catch (e) {
        console.error('Error loading SIO commodity dashboard CSV:', e);
        setCommodityDataStatus('No se pudo cargar el módulo de commodities.', 'error');
        renderCommodityEmptyState();
    }
    hideLoading();
}

async function loadQuantityData() {
    const response = await fetch(CSV_PATH);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    quantityData = parseCSV(await response.text());
    rawData = quantityData;
    initQuantityFilters();
    applyQuantityFilters();
}

function initQuantityFilters() { populateFilters(); updateQuantityFrequencyOptions(); }
function applyQuantityFilters() { applyFilters(); }
function renderQuantityDashboard() { updateDashboard(); }
function updateQuantityDashboard() { updateDashboard(); }

function dateFromRecord(record, dateColumn = 'fecha') {
    if (typeof record === 'string') return record;
    if (record?.[dateColumn]) return String(record[dateColumn]);
    if (record?.day && record?.month && record?.year) return `${record.year}-${String(record.month).padStart(2, '0')}-${String(record.day).padStart(2, '0')}`;
    return '';
}

function detectFrequency(data, dateColumn = 'fecha') {
    const dates = data.map(row => dateFromRecord(row, dateColumn)).filter(value => /^\d{4}-\d{2}-\d{2}$/.test(value));
    if (dates.length >= 2) {
        const days = new Set(dates);
        const months = new Set(dates.map(value => value.slice(0, 7)));
        const years = new Set(dates.map(value => value.slice(0, 4)));
        if (days.size > months.size) return 'diaria';
        if (months.size > years.size) return 'mensual';
    }
    return data.some(row => row.month || row.mes) ? 'mensual' : 'anual';
}

function createTimeKey(date, frequency) {
    const value = dateFromRecord(date);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        const year = date?.year || date?.año;
        const month = date?.month || date?.mes;
        if (frequency === 'anual' && year) return String(year);
        if (frequency === 'mensual' && year && Number(month) >= 1 && Number(month) <= 12) return `${year}-${String(month).padStart(2, '0')}`;
        return '';
    }
    if (frequency === 'diaria') return value;
    if (frequency === 'anual') return value.slice(0, 4);
    return value.slice(0, 7);
}

function availableFrequencies(originalFrequency) {
    return originalFrequency === 'diaria' ? ['diaria', 'mensual', 'anual'] : originalFrequency === 'mensual' ? ['mensual', 'anual'] : ['anual'];
}

function updateFrequencySelect(id, originalFrequency, selected, onChange) {
    const select = document.getElementById(id);
    if (!select) return selected;
    const allowed = new Set(availableFrequencies(originalFrequency));
    [...select.options].forEach(option => { option.disabled = !allowed.has(option.value); });
    const next = allowed.has(selected) ? selected : [...allowed][0];
    select.value = next;
    select.onchange = () => { onChange(select.value); };
    return next;
}

function updateQuantityFrequencyOptions() {
    quantityFrequency = updateFrequencySelect('filterFrequency', detectFrequency(quantityData), quantityFrequency, value => { quantityFrequency = value; updateQuantityDashboard(); });
}

function updatePriceFrequencyOptions() {
    const select = document.getElementById('priceFilterFrequency');
    if (!select) return;
    const hasSpecificSpecies = document.getElementById('priceFilterEspecie')?.value !== 'TODOS';
    const allowed = new Set(availableFrequencies(detectFrequency(priceData)));
    if (!hasSpecificSpecies) allowed.delete('diaria');
    [...select.options].forEach(option => { option.disabled = !allowed.has(option.value); });
    priceFrequency = allowed.has(priceFrequency) ? priceFrequency : (allowed.has('mensual') ? 'mensual' : [...allowed][0]);
    select.value = priceFrequency;
    select.onchange = () => { priceFrequency = select.value; updatePriceDashboard(); };
    const frequencyStatus = document.getElementById('priceFrequencyStatus');
    if (frequencyStatus) {
        frequencyStatus.textContent = !hasSpecificSpecies && availableFrequencies(detectFrequency(priceData)).includes('diaria')
            ? 'Para visualizar detalle diario, seleccioná una especie específica. La vista general se muestra mensual para mantener legibilidad.' : '';
        frequencyStatus.classList.toggle('is-visible', Boolean(frequencyStatus.textContent));
    }
}

function aggregateQuantityData(data, frequency) {
    const groups = new Map();
    data.forEach(row => { const key = createTimeKey(dateFromRecord(row, 'fecha') || row, frequency); if (key) groups.set(key, (groups.get(key) || 0) + row.peso); });
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, value]) => ({ key, value }));
}

function aggregatePriceData(data, frequency) {
    const groups = new Map();
    data.forEach(row => { const key = createTimeKey(row.fecha || row, frequency); const value = getPriceValue(row); if (key && isValidPrice(value)) { const values = groups.get(key) || []; values.push(value); groups.set(key, values); } });
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, values]) => ({ key, value: values.reduce((sum, value) => sum + value, 0) / values.length }));
}

function calculateVariation(series, frequency) {
    return calculatePeriodVariation(series, frequency);
}

function calculatePeriodVariation(data, frequency) {
    const valid = data
        .filter(item => Number.isFinite(Number(item.value)) && Number(item.value) > 0 && item.key)
        .map(item => ({ ...item, value: Number(item.value) }))
        .sort((a, b) => String(a.key).localeCompare(String(b.key)));
    return valid.map((item, index) => {
        if (index === 0) return { ...item, variation: null, frequency };
        const previous = valid[index - 1].value;
        const variation = previous > 0 ? (item.value / previous - 1) * 100 : null;
        return { ...item, variation: Number.isFinite(variation) ? variation : null, frequency };
    });
}

function currentDateISO() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function wireModuleTabs() {
    document.querySelectorAll('.module-tab').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.module-tab').forEach(tab => {
                const active = tab === button;
                tab.classList.toggle('is-active', active);
                tab.setAttribute('aria-selected', String(active));
            });
            document.querySelectorAll('.module-view').forEach(view => view.classList.toggle('is-active', view.id === button.dataset.module));
            window.dispatchEvent(new Event('resize'));
        });
    });
}

// ─── Independent wholesale prices module ───────────────────────────────
function isValidOperationalDate(date) {
    return /^\d{4}-\d{2}-\d{2}$/.test(String(date || '')) && String(date) <= currentDateISO();
}

function filterFutureDates(data) {
    const futureRows = data.filter(row => row.fecha && !isValidOperationalDate(row.fecha));
    const validRows = data.filter(row => !row.fecha || isValidOperationalDate(row.fecha));
    return { validRows, futureRows };
}

async function loadPriceData() {
    let response = null;
    let sourcePath = PRICE_CSV_PATH;
    try { response = await fetch(PRICE_CSV_PATH); } catch (error) { console.warn('No se pudo acceder a la base general de precios; se probará el archivo de respaldo.', error); }
    if (!response?.ok) {
        response = await fetch(PRICE_CSV_FALLBACK_PATH);
        sourcePath = PRICE_CSV_FALLBACK_PATH;
        console.warn('Usando fallback PRECIOS_MAYORISTAS_2026_INTEGRADO.csv');
    }
    if (!response.ok) throw new Error(`No se encontró una base de precios (${response.status})`);
    const qualityResponse = await fetch('RESUMEN_SERIES_UTILIZABLES_PRECIOS_2026.csv').catch(() => null);
    if (qualityResponse?.ok) {
        priceSeriesData = parsePriceCSV(await qualityResponse.text());
        priceQualityMap = new Map(priceSeriesData.map(row => [priceSeriesKey(row), row.indicador_serie_utilizable || '']));
    }
    rawPriceData = processPriceData(parsePriceCSV(await response.text()), sourcePath);
    console.warn('Valores inválidos de planilla excluidos o normalizados:', spreadsheetInvalidCount);
    const dateSplit = filterFutureDates(rawPriceData);
    futurePriceData = dateSplit.futureRows;
    priceData = dateSplit.validRows.filter(row => isValidPrice(row.precioObservado));
    validPriceData = priceData;
    const invalidPriceCount = dateSplit.validRows.length - priceData.length;
    const years = getAvailablePriceYears(priceData);
    const datedPrices = priceData.map(row => row.fecha).filter(Boolean).sort();
    const rowsByYear = priceData.reduce((counts, row) => { if (Number.isFinite(row.year)) counts[row.year] = (counts[row.year] || 0) + 1; return counts; }, {});
    const rowsByYearMonth = priceData.reduce((counts, row) => { if (row.year && row.mes) { const key = `${row.year}-${String(monthNumber(row.mes)).padStart(2, '0')}`; counts[key] = (counts[key] || 0) + 1; } return counts; }, {});
    const currentYear = new Date().getFullYear();
    const suspiciousRows = priceData.filter(row => Number.isFinite(row.year) && row.year > currentYear + 1);
    priceFutureDateCount = priceData.filter(row => row.fecha && row.fecha > currentDateISO()).length;
    console.log('Archivo de precios cargado:', sourcePath);
    console.log('Total registros precios crudos:', rawPriceData.length);
    console.log('Total registros precios válidos:', priceData.length);
    console.log('Registros con precio observado:', priceData.filter(row => isValidPrice(row.precioObservado)).length);
    console.log('Registros con precio kg estimado:', priceData.filter(row => isValidPrice(row.precioKgEstimado)).length);
    console.log('Registros no comparables:', priceData.filter(row => !isValidPrice(row.precioKgEstimado)).length);
    console.log('Unidades observadas:', [...new Set(priceData.map(row => row.unidadPrecioObservado).filter(Boolean))]);
    console.log('Confianza conversión:', priceData.reduce((counts, row) => { const key = row.confianzaConversion || 'Sin informar'; counts[key] = (counts[key] || 0) + 1; return counts; }, {}));
    console.warn('Registros excluidos por precio inválido o cero:', invalidPriceCount);
    console.warn('Registros de precios con fecha futura excluidos:', futurePriceData.length);
    console.log('Rango de fechas precios:', datedPrices[0] || 'Sin fecha', datedPrices[datedPrices.length - 1] || 'Sin fecha');
    console.log('Años disponibles en precios:', years);
    console.log('Filas por año en precios:', rowsByYear);
    console.log('Filas de precios válidas por año-mes:', rowsByYearMonth);
    console.warn('Registros con años futuros o sospechosos:', suspiciousRows.length);
    console.log('Frecuencia original detectada en precios:', detectFrequency(priceData));
    if (priceFutureDateCount) console.warn('Fechas futuras excluidas del KPI último registro:', priceFutureDateCount);
    initPriceYearFilter();
    updatePriceFrequencyOptions();
    updatePriceDashboard();
}

function parsePriceCSV(text) {
    const lines = text.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = parseDelimitedLine(lines[0], ';').map(normalizePriceHeader);
    return lines.slice(1).map(line => {
        const values = parseDelimitedLine(line, ';');
        return headers.reduce((row, header, index) => { row[header] = values[index] ?? ''; return row; }, {});
    });
}

function parseDelimitedLine(line, separator) {
    const values = []; let value = ''; let quoted = false;
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"' && line[i + 1] === '"' && quoted) { value += '"'; i++; }
        else if (char === '"') quoted = !quoted;
        else if (char === separator && !quoted) { values.push(value); value = ''; }
        else value += char;
    }
    values.push(value);
    return values;
}

function normalizePriceHeader(value) {
    return String(value || '').trim().toLocaleLowerCase('es-AR').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function parsePriceNumber(value) {
    if (value === undefined || value === null || String(value).trim() === '') return null;
    const parsed = Number(String(value).replace(/\$/g, '').trim().replace(/\./g, '').replace(',', '.'));
    // Integrated prices use decimal points. Preserve those values when no comma exists.
    const raw = String(value).trim();
    const normalized = raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw.replace(/[^\d.-]/g, '');
    const number = Number(normalized);
    return Number.isFinite(number) ? number : (Number.isFinite(parsed) ? parsed : null);
}

function isValidPrice(value) {
    return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

function isComparablePriceRow(row) {
    return isValidPrice(row?.precioKgEstimado) && ['Alta', 'Media'].includes(row?.confianzaConversion);
}

function getPriceValue(row) {
    if (priceUnitMode === 'comparable') return row?.precioKgEstimado;
    return row?.precioObservado;
}

function getPriceMetricLabel() {
    return priceUnitMode === 'comparable' ? 'Precio estimado por kg' : 'Precio observado';
}

function getProductLabel(row) {
    const species = String(row?.especie || '').trim();
    const variety = String(row?.variedad || '').trim();
    return [species, variety && variety.toUpperCase() !== 'SIN VARIEDAD' ? variety : '']
        .filter(Boolean).join(' ') || 'Sin especificar';
}

function formatPeriodLabel(periodKey, frequency) {
    const key = String(periodKey || '');
    if (frequency === 'diaria') return key.split('-').reverse().join('/');
    if (frequency === 'mensual' && /^\d{4}-\d{2}$/.test(key)) {
        return `${MONTHS[Number(key.slice(5, 7)) - 1]} ${key.slice(0, 4)}`;
    }
    return key;
}

function buildAccumulatedVariationRanking(data, groupFields, frequency = 'diaria') {
    let extremeCount = 0;
    const grouped = new Map();
    data.forEach(row => {
        if (!isValidPrice(getPriceValue(row))) return;
        const key = groupFields.map(field => String(getPriceDimensionValue(row, field))).join('|');
        const label = groupFields.length === 2 && groupFields.includes('especie') && groupFields.includes('variedad')
            ? getProductLabel(row)
            : groupFields.map(field => formatPriceDimensionValue(row, field)).join(' · ');
        const group = grouped.get(key) || { label, rows: [] };
        group.rows.push(row);
        grouped.set(key, group);
    });
    const ranking = [...grouped.values()].map(group => {
        const rows = group.rows;
        if (rows.length < 5) return null;
        const byPeriod = new Map();
        rows.forEach(row => { const period = createTimeKey(row.fecha || row, frequency); const value = getPriceValue(row); if (period && isValidPrice(value)) { const values = byPeriod.get(period) || []; values.push(value); byPeriod.set(period, values); } });
        const periods = [...byPeriod.entries()].sort(([a], [b]) => a.localeCompare(b));
        if (periods.length < 2) return null;
        const first = { key: periods[0][0], value: periods[0][1].reduce((sum, value) => sum + value, 0) / periods[0][1].length };
        const last = { key: periods[periods.length - 1][0], value: periods[periods.length - 1][1].reduce((sum, value) => sum + value, 0) / periods[periods.length - 1][1].length };
        if (!isValidPrice(first.value) || !isValidPrice(last.value)) return null;
        const variation = (last.value / first.value - 1) * 100;
        if (!Number.isFinite(variation)) return null;
        if (Math.abs(variation) > 500) { extremeCount++; return null; }
        return { label: group.label, variation, firstValue: first.value, lastValue: last.value, firstPeriod: first.key, lastPeriod: last.key, firstDate: first.key, lastDate: last.key, observations: rows.length };
    }).filter(Boolean);
    if (extremeCount) console.warn('Variaciones extremas excluidas:', extremeCount);
    return ranking.sort((a, b) => Math.abs(b.variation) - Math.abs(a.variation));
}

function getPriceVariationGrouping(frequency) {
    const filters = getPriceFilters();
    const splitDimensions = getPriceSplitDimensions(filters);
    const species = getFilterValues(filters.especie);
    const variety = getFilterValues(filters.variedad);
    const provenance = getFilterValues(filters.procedencia);
    if (frequency !== 'diaria') return { groupFields: [...new Set(['especie', 'variedad', ...splitDimensions])], singleSeries: false };
    if (splitDimensions.length) return { groupFields: [...new Set(['especie', 'variedad', ...splitDimensions])], singleSeries: false };
    if (isAllSelected(species) || species.length !== 1) return { groupFields: [], singleSeries: false };
    if (isAllSelected(variety) || variety.length !== 1) return { groupFields: ['variedad'], singleSeries: false };
    if (isAllSelected(provenance) || provenance.length !== 1) return { groupFields: ['procedencia'], singleSeries: false };
    return { groupFields: [], singleSeries: true };
}

function processPriceData(rows, sourcePath = PRICE_CSV_PATH) {
    return rows.map(row => {
        const dateText = String(row.fecha || '').trim();
        const date = /^\d{4}-\d{2}-\d{2}$/.test(dateText) ? dateText : '';
        const monthNumber = date ? Number(date.slice(5, 7)) : MONTHS_FULL.findIndex(month => normalizeText(month) === normalizeText(row.mes)) + 1;
        const observed = parsePriceNumber(row.precio_observado) ?? parsePriceNumber(row.precio_promedio) ?? parsePriceNumber(row.precio);
        const estimated = parsePriceNumber(row.precio_kg_estimado);
        const average = estimated ?? observed;
        const minimum = parsePriceNumber(row.precio_min);
        const maximum = parsePriceNumber(row.precio_max);
        const rubroRaw = normalizeCategoryValue(row.rubro);
        const sourceText = normalizeText(sourcePath);
        const rubroKey = normalizeText(rubroRaw);
        const rubro = rubroKey.includes('HORTAL') ? 'Hortalizas' : rubroKey.includes('FRUT') ? 'Frutas' : rubroKey.includes('SUBPRODUCT') ? 'Subproductos' : rubroRaw || (sourceText.includes('HORTAL') ? 'Hortalizas' : sourceText.includes('FRUT') ? 'Frutas' : 'Sin clasificar');
        return {
            fecha: date, year: date ? Number(date.slice(0, 4)) : Number(row.año || row.ano) || null, month: monthNumber,
            mes: monthNumber >= 1 && monthNumber <= 12 ? MONTHS_FULL[monthNumber - 1] : normalizeCategoryValue(row.mes),
            rubro, especie: normalizeCategoryValue(row.especie) || 'Sin especificar', variedad: normalizeCategoryValue(row.variedad),
            mercado: normalizeCategoryValue(row.mercado), procedencia: normalizeCategoryValue(row.procedencia), unidad: normalizeCategoryValue(row.unidad) || 'Sin especificar', precio: observed,
            precioObservado: observed, unidadPrecioObservado: normalizeCategoryValue(row.unidad_precio_observado) || 'sin especificar', envase: normalizeCategoryValue(row.envase), kgBulto: parsePriceNumber(row.kg_bulto), precioKgEstimado: estimated, metodoConversion: normalizeCategoryValue(row.metodo_conversion_precio), confianzaConversion: normalizeCategoryValue(row.confianza_conversion_precio),
            precioMin: minimum, precioMax: maximum, precioPromedio: average,
            calidad: priceQualityMap.get(priceSeriesKey({ ...row, rubro, especie: row.especie, variedad: row.variedad })) || '', fuente: sourcePath
        };
    }).filter(row => row.rubro && row.especie);
}

function getAvailablePriceYears(data) {
    return [...new Set(data.map(row => Number(row.year)).filter(Number.isFinite))].sort((a, b) => a - b);
}

function initPriceYearFilter() {
    populatePriceFilters();
}

function getMultiSelectValues(selectId) {
    const select = document.getElementById(selectId);
    if (!select?.multiple) return select?.value || 'TODOS';
    return [...select.selectedOptions].map(option => option.value).filter(Boolean);
}

function isAllSelected(values) {
    const normalized = Array.isArray(values) ? values : [values];
    return !normalized.length || normalized.some(value => ['TODOS', 'TODAS', 'ALL', '**ALL**'].includes(String(value ?? '').trim().toUpperCase()));
}

function getSelectedValues(filterId) {
    const select = document.getElementById(filterId);
    if (!select) return ['TODOS'];
    const values = select.multiple
        ? [...select.selectedOptions].map(option => option.value).filter(Boolean)
        : [select.value || 'TODOS'];
    return isAllSelected(values) ? ['TODOS'] : values;
}

function isMultiSpecificSelection(values) {
    return !isAllSelected(values) && (Array.isArray(values) ? values : [values]).length > 1;
}

function matchesMultiSelect(value, selectedValues) {
    if (isAllSelected(selectedValues)) return true;
    const values = Array.isArray(selectedValues) ? selectedValues : [selectedValues];
    return values.includes(value || 'Sin especificar');
}

function matchesPriceFilter(row, key, selectedValues) {
    const value = key === 'especie'
        ? row.productoNormalizado || row.especie
        : key === 'variedad'
            ? row.variedad || 'Sin especificar'
            : key === 'procedencia'
                ? row.procedencia || 'Sin procedencia informada'
                : row[key];
    return matchesMultiSelect(value, selectedValues);
}

function updateMultiSelectSummary(selectId) {
    const summary = document.querySelector(`[data-multi-select="${selectId}"] .multi-select-summary`)
        || document.getElementById(`${selectId}Summary`);
    if (!summary) return;
    const values = getMultiSelectValues(selectId);
    const allLabel = {
        priceFilterRubro: 'Todos los rubros',
        priceFilterEspecie: 'Todas las especies',
        priceFilterVariedad: 'Todas las variedades',
        priceFilterMercado: 'Todos los mercados',
        priceFilterProcedencia: 'Todas las procedencias'
    }[selectId] || (selectId.includes('Mercado') ? 'Todos' : 'Todas');
    if (!values.length || values.includes('TODOS')) summary.textContent = allLabel;
    else if (values.length <= 2) summary.textContent = values.join(', ');
    else summary.textContent = `${values.slice(0, 2).join(', ')} y ${values.length - 2} más`;
    renderMultiSelectOptions(selectId);
}

function initMultiSelectControls() {
    document.querySelectorAll('[data-multi-select]').forEach(wrapper => {
        const selectId = wrapper.dataset.multiSelect;
        const trigger = wrapper.querySelector('.multi-select-trigger');
        const dropdown = wrapper.querySelector('.multi-select-dropdown');
        if (!trigger || !dropdown) return;
        trigger.addEventListener('click', event => {
            event.stopPropagation();
            const isOpen = wrapper.classList.toggle('is-open');
            trigger.setAttribute('aria-expanded', String(isOpen));
            if (isOpen) dropdown.focus();
        });
        dropdown.addEventListener('click', event => event.stopPropagation());
        renderMultiSelectOptions(selectId);
    });
    document.addEventListener('click', () => closeMultiSelects());
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeMultiSelects();
    });
}

function closeMultiSelects() {
    document.querySelectorAll('[data-multi-select].is-open').forEach(wrapper => {
        wrapper.classList.remove('is-open');
        wrapper.querySelector('.multi-select-trigger')?.setAttribute('aria-expanded', 'false');
    });
}

function renderMultiSelectOptions(selectId) {
    const wrapper = document.querySelector(`[data-multi-select="${selectId}"]`);
    const select = document.getElementById(selectId);
    const dropdown = wrapper?.querySelector('.multi-select-dropdown');
    if (!select || !dropdown) return;
    dropdown.innerHTML = '';
    [...select.options].forEach(option => {
        const item = document.createElement('div');
        item.className = 'multi-select-option';
        item.setAttribute('role', 'option');
        item.tabIndex = 0;
        item.setAttribute('aria-selected', String(option.selected));
        item.dataset.value = option.value;
        if (option.selected) item.classList.add('is-selected');
        const checkbox = document.createElement('span');
        checkbox.className = 'multi-select-checkbox';
        checkbox.setAttribute('aria-hidden', 'true');
        checkbox.textContent = option.selected ? '✓' : '';
        const label = document.createElement('span');
        label.className = 'multi-select-option-label';
        label.textContent = option.textContent;
        item.append(checkbox, label);
        item.addEventListener('click', () => {
            if (option.value === 'TODOS') {
                [...select.options].forEach(candidate => { candidate.selected = candidate.value === 'TODOS'; });
            } else {
                option.selected = !option.selected;
                const all = select.options[0];
                all.selected = false;
                if (![...select.options].some(candidate => candidate !== all && candidate.selected)) all.selected = true;
            }
            select.dispatchEvent(new Event('change', { bubbles: true }));
        });
        item.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                item.click();
            }
        });
        dropdown.appendChild(item);
    });
}

function setMultiSelectOptions(selectId, values, allLabel, selectedValues = []) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const unique = [...new Set(values.filter(value => String(value || '').trim()))];
    unique.sort((a, b) => String(a).localeCompare(String(b), 'es'));
    select.innerHTML = '';
    const all = new Option(allLabel, 'TODOS');
    select.add(all);
    unique.forEach(value => select.add(new Option(value, value)));
    const kept = selectedValues.filter(value => value === 'TODOS' || unique.includes(value));
    if (kept.length) [...select.options].forEach(option => { option.selected = kept.includes(option.value); });
    else all.selected = true;
}

function populatePriceFilters() {
    const selectedSpecies = getSelectedValues('priceFilterEspecie');
    const definitions = [
        ['priceFilterYear', validPriceData.map(row => row.year), 'Todos los años'],
        ['priceFilterRubro', validPriceData.map(row => row.rubro), 'Todos'],
        ['priceFilterMes', validPriceData.map(row => row.mes), 'Todos los meses'],
        ['priceFilterEspecie', validPriceData.map(row => row.especie), 'Todas las especies'],
        ['priceFilterVariedad', validPriceData.filter(row => !Array.isArray(selectedSpecies) || !selectedSpecies.length || selectedSpecies.includes('TODOS') || selectedSpecies.includes(row.especie)).map(row => row.variedad || 'Sin especificar'), 'Todas las variedades'],
        ['priceFilterMercado', validPriceData.map(row => row.mercado), 'Todos los mercados'],
        ['priceFilterProcedencia', validPriceData.map(row => row.procedencia), 'Todas'],
        ['priceFilterUnidad', validPriceData.map(row => row.unidad), 'Todas']
    ];
    definitions.forEach(([id, values, allLabel]) => {
        const select = document.getElementById(id);
        const current = select?.multiple ? getSelectedValues(id) : select.value;
        const unique = [...new Set(values.filter(value => String(value || '').trim()))];
        if (id === 'priceFilterMes') unique.sort((a, b) => monthNumber(a) - monthNumber(b));
        else unique.sort((a, b) => String(a).localeCompare(String(b), 'es'));
        populateSelect(select, unique, allLabel, value => value);
        if (select.multiple) {
            const currentValues = Array.isArray(current) ? current : [current];
            const kept = currentValues.filter(value => value === 'TODOS' || unique.includes(value));
            [...select.options].forEach(option => { option.selected = kept.includes(option.value); });
            if (!kept.length) select.options[0].selected = true;
        } else if (unique.includes(current)) select.value = current;
        select.onchange = () => {
            if (id === 'priceFilterEspecie') { updatePriceVarietyFilter(); updatePriceFrequencyOptions(); }
            if (select.multiple) updateMultiSelectSummary(id);
            updatePriceDashboard();
        };
        if (select.multiple) updateMultiSelectSummary(id);
    });
    const comparableFilter = document.getElementById('priceFilterComparable');
    if (comparableFilter) comparableFilter.onchange = () => {
        priceUnitMode = comparableFilter.value === 'comparables' ? 'comparable' : comparableFilter.value === 'no-comparables' ? 'nonComparable' : 'all';
        updatePriceDashboard();
    };
}

function updatePriceVarietyFilter() { populatePriceFilters(); }

function priceSeriesKey(row) {
    return [row.rubro, row.mercado, row.procedencia, row.especie, row.variedad, row.unidad]
        .map(value => normalizePriceHeader(value || '(sin informar)'))
        .join('|');
}

function monthNumber(value) {
    const index = MONTHS_FULL.findIndex(month => normalizeText(month) === normalizeText(value));
    return index >= 0 ? index + 1 : 99;
}

function getPriceFilters() {
    return {
        year: getSelectedValues('priceFilterYear'),
        mes: getSelectedValues('priceFilterMes'),
        rubro: getSelectedValues('priceFilterRubro'),
        especie: getSelectedValues('priceFilterEspecie'),
        variedad: getSelectedValues('priceFilterVariedad'),
        mercado: getSelectedValues('priceFilterMercado'),
        procedencia: getSelectedValues('priceFilterProcedencia'),
        unidad: getSelectedValues('priceFilterUnidad'),
        unidadComparable: document.getElementById('priceFilterComparable')?.value || 'comparables'
    };
}

function getFilteredPriceData() {
    const filters = getPriceFilters();
    priceUnitMode = filters.unidadComparable === 'comparables' ? 'comparable' : filters.unidadComparable === 'no-comparables' ? 'nonComparable' : 'all';
    const selectedYear = isAllSelected(filters.year) ? null : Number(filters.year[0]);
    return validPriceData.filter(row =>
        (filters.unidadComparable === 'comparables' ? isComparablePriceRow(row) : filters.unidadComparable === 'no-comparables' ? !isComparablePriceRow(row) && isValidPrice(row.precioObservado) : isValidPrice(row.precioObservado))
        &&
        (selectedYear === null || Number(row.year) === selectedYear)
        && Object.entries(filters).every(([key, value]) => key === 'year' || key === 'unidadComparable' || matchesPriceFilter(row, key, value))
    );
}

function applyPriceFilters() {
    filteredPriceData = getFilteredPriceData();
    return filteredPriceData;
}

function updatePriceDashboard() {
    const filters = getPriceFilters();
    const selectedYear = isAllSelected(filters.year) ? 'TODOS' : filters.year[0];
    const beforeYearFilterCount = validPriceData.length;
    const afterYearFilterCount = selectedYear === 'TODOS'
        ? beforeYearFilterCount
        : validPriceData.filter(row => Number(row.year) === Number(selectedYear)).length;
    applyPriceFilters();
    console.log('Filtros precios:', filters);
    console.log('Filtros de precios aplicados:', filters);
    console.log('Año de precios seleccionado:', selectedYear);
    console.log('Registros antes de filtrar por año:', beforeYearFilterCount);
    console.log('Registros después de filtrar por año:', afterYearFilterCount);
    console.log('Registros luego del filtro precio:', filteredPriceData.length);
    const hasData = filteredPriceData.length > 0;
    setPriceStatus(hasData ? '' : (priceData.length ? 'No hay precios disponibles para la combinación seleccionada. Revisá año, mercado, especie o mes.' : 'No se pudo cargar la base de precios mayoristas.'), !hasData);
    const unitStatus = document.getElementById('priceUnitStatus');
    if (unitStatus) {
        const nonComparableIncluded = priceUnitMode !== 'comparable' && filteredPriceData.some(row => !isComparablePriceRow(row));
        unitStatus.textContent = nonComparableIncluded ? 'Algunos precios no tienen unidad comparable en kg y se excluyen de indicadores por kg.' : '';
        unitStatus.classList.toggle('is-visible', nonComparableIncluded);
    }
    const splitDimensions = getPriceSplitDimensions(filters);
    const selectionSummary = document.getElementById('priceSelectionSummary');
    if (selectionSummary) {
        selectionSummary.textContent = splitDimensions.length
            ? `Resumen de selección filtrada · comparación separada por ${splitDimensions.map(formatPriceDimensionName).join(', ')}`
            : '';
        selectionSummary.classList.toggle('is-visible', splitDimensions.length > 0);
    }
    updatePriceKPIs();
    renderPriceCharts();
}

function getPriceAnalysisLevel(filters) {
    const species = getFilterValues(filters?.especie);
    const varieties = getFilterValues(filters?.variedad);
    const provenances = getFilterValues(filters?.procedencia);
    if (isAllSelected(species) || species.length !== 1) return 'general';
    if (isAllSelected(varieties) || varieties.length !== 1) return 'species_detail';
    if (isAllSelected(provenances) || provenances.length !== 1) return 'variety_detail';
    return 'single_series';
}

function getFilterValues(values) {
    if (Array.isArray(values)) return values.length ? values : ['TODOS'];
    return [values || 'TODOS'];
}

function getPriceSplitDimensions(filters = {}) {
    return ['mercado', 'rubro', 'especie', 'variedad', 'procedencia']
        .filter(dimension => isMultiSpecificSelection(getFilterValues(filters[dimension])));
}

function formatPriceDimensionName(dimension) {
    return { mercado: 'mercado', rubro: 'rubro', especie: 'especie', variedad: 'variedad', procedencia: 'procedencia' }[dimension] || dimension;
}

function getPriceDimensionValue(row, dimension) {
    if (dimension === 'especie') return row.productoNormalizado || row.especie || 'Sin especificar';
    if (dimension === 'variedad') return row.variedad || 'Sin especificar';
    if (dimension === 'procedencia') return row.procedencia || 'Sin procedencia informada';
    if (dimension === 'mercado') return row.mercado || 'Fuente sin informar';
    return row[dimension] || 'Sin informar';
}

function formatPriceDimensionValue(row, dimension) {
    return formatLabel(getPriceDimensionValue(row, dimension));
}

function getPriceSplitLabel(row, splitDimensions) {
    return splitDimensions.map(dimension => formatPriceDimensionValue(row, dimension)).join(' · ');
}

function getAvailablePriceVisualizations(filteredData, filters, frequency) {
    const level = getPriceAnalysisLevel(filters);
    const hasSplitSelection = getPriceSplitDimensions(filters).length > 0;
    const speciesCount = new Set(filteredData.map(row => row.especie).filter(Boolean)).size;
    const varietyCount = new Set(filteredData.map(row => row.variedad || 'Sin especificar')).size;
    const provenanceCount = new Set(filteredData.map(row => row.procedencia || 'Sin procedencia informada')).size;
    const marketCount = new Set(filteredData.map(row => row.mercado).filter(Boolean)).size;
    const periods = aggregatePriceData(filteredData, frequency).length;
    const isDaily = frequency === 'diaria';
    return {
        level,
        showSpeciesRanking: level === 'general' && (speciesCount >= 2 || hasSplitSelection),
        showVarietyRanking: level === 'species_detail' && (varietyCount >= 2 || hasSplitSelection),
        showProcedenciaComparison: level === 'variety_detail' && (provenanceCount >= 2 || hasSplitSelection),
        showMarketComparison: marketCount >= 1,
        showVariationBars: !isDaily && periods >= 2,
        showAccumulatedVariationCard: isDaily && periods >= 2,
        showIncreasesRanking: !isDaily && level !== 'single_series',
        showDecreasesRanking: !isDaily && level !== 'single_series'
    };
}

function setPriceStatus(message, visible) {
    const status = document.getElementById('priceStatus');
    status.textContent = message;
    status.classList.toggle('is-visible', Boolean(visible));
}

function updatePriceKPIs() {
    const values = filteredPriceData.map(getPriceValue).filter(isValidPrice);
    const average = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    const maximum = filteredPriceData.reduce((best, row) => { const value = getPriceValue(row); return isValidPrice(value) && (!best || value > best.value) ? { value, row } : best; }, null);
    const minimum = filteredPriceData.reduce((best, row) => { const value = getPriceValue(row); return isValidPrice(value) && (!best || value < best.value) ? { value, row } : best; }, null);
    const species = new Set(filteredPriceData.map(row => row.especie).filter(Boolean));
    const varieties = new Set(filteredPriceData.map(row => row.variedad || 'Sin especificar').filter(Boolean));
    const periodVariation = calculatePeriodVariation(aggregatePriceData(filteredPriceData, priceFrequency), priceFrequency).filter(item => Number.isFinite(item.variation));
    let largestIncrease = periodVariation.filter(item => item.variation > 0).sort((a, b) => b.variation - a.variation)[0];
    let largestDecrease = periodVariation.filter(item => item.variation < 0).sort((a, b) => a.variation - b.variation)[0];
    const today = currentDateISO();
    const dated = filteredPriceData.filter(row => row.fecha && row.fecha <= today).sort((a, b) => a.fecha.localeCompare(b.fecha));
    const undated = filteredPriceData.filter(row => !row.fecha);
    const latestUndated = undated.length ? undated.reduce((best, row) => (row.year > best.year || (row.year === best.year && monthNumber(row.mes) > monthNumber(best.mes))) ? row : best) : null;
    const latest = dated.length ? dated[dated.length - 1].fecha.split('-').reverse().join('/') : (latestUndated ? latestUndated.mes : 'Sin dato válido');
    const accumulated = aggregatePriceData(filteredPriceData, priceFrequency).filter(item => isValidPrice(item.value));
    const firstAccumulated = accumulated[0];
    const lastAccumulated = accumulated[accumulated.length - 1];
    if (priceFrequency === 'diaria' && firstAccumulated && lastAccumulated && firstAccumulated.key !== lastAccumulated.key) {
        const accumulatedChange = (lastAccumulated.value / firstAccumulated.value - 1) * 100;
        largestIncrease = accumulatedChange > 0 ? { variation: accumulatedChange, key: 'Del primer al último dato' } : null;
        largestDecrease = accumulatedChange < 0 ? { variation: accumulatedChange, key: 'Del primer al último dato' } : null;
    }
    const summary = document.getElementById('priceAccumulatedSummary');
    if (summary) {
        const hasAccumulated = priceFrequency === 'diaria' && accumulated.length >= 2;
        summary.hidden = !hasAccumulated;
        if (hasAccumulated) {
            const change = (lastAccumulated.value / firstAccumulated.value - 1) * 100;
            document.getElementById('priceAccumulatedValue').textContent = formatPercent(change);
            document.getElementById('priceAccumulatedFirst').textContent = formatCurrency(firstAccumulated.value);
            document.getElementById('priceAccumulatedLast').textContent = formatCurrency(lastAccumulated.value);
            document.getElementById('priceAccumulatedPeriod').textContent = `Entre ${formatPeriodLabel(firstAccumulated.key, priceFrequency)} y ${formatPeriodLabel(lastAccumulated.key, priceFrequency)}`;
        }
    }
    document.getElementById('priceKpiAverage').textContent = formatCurrency(average);
    document.getElementById('priceKpiMax').textContent = formatCurrency(maximum?.value);
    document.getElementById('priceKpiMin').textContent = formatCurrency(minimum?.value);
    document.getElementById('priceKpiMaxDetail').textContent = maximum ? `${maximum.row.especie}${maximum.row.variedad ? ` · ${maximum.row.variedad}` : ''}` : 'Sin datos';
    document.getElementById('priceKpiMinDetail').textContent = minimum ? `${minimum.row.especie}${minimum.row.variedad ? ` · ${minimum.row.variedad}` : ''}` : 'Sin datos';
    document.getElementById('priceKpiSpecies').textContent = species.size || '–';
    document.getElementById('priceKpiVarieties').textContent = varieties.size || '–';
    document.getElementById('priceKpiIncrease').textContent = largestIncrease ? formatPercent(largestIncrease.variation) : '–';
    document.getElementById('priceKpiIncreaseDetail').textContent = largestIncrease ? largestIncrease.key : 'Sin dos períodos';
    document.getElementById('priceKpiDecrease').textContent = largestDecrease ? formatPercent(largestDecrease.variation) : '–';
    document.getElementById('priceKpiDecreaseDetail').textContent = largestDecrease ? largestDecrease.key : 'Sin dos períodos';
    document.getElementById('priceKpiIncreaseLabel').textContent = priceFrequency === 'diaria' ? 'Variación acumulada' : 'Mayor suba';
    document.getElementById('priceKpiDecreaseLabel').textContent = priceFrequency === 'diaria' ? 'Variación acumulada' : 'Mayor baja';
    document.getElementById('priceKpiLast').textContent = latest;
    const comparableView = priceUnitMode === 'comparable';
    document.getElementById('priceKpiAverageLabel').textContent = comparableView ? 'Precio promedio por kg' : 'Precio observado promedio';
    const splitDimensions = getPriceSplitDimensions(getPriceFilters());
    document.getElementById('priceKpiAverageUnit').textContent = splitDimensions.length
        ? 'resumen de selección filtrada'
        : comparableView ? 'calculado sobre registros con unidad comparable' : 'según presentación original';
    document.getElementById('priceKpiMaxLabel').textContent = comparableView ? 'Precio máximo por kg' : 'Precio observado máximo';
    document.getElementById('priceKpiMinLabel').textContent = comparableView ? 'Precio mínimo por kg' : 'Precio observado mínimo';
}

function formatCurrency(value) {
    return Number.isFinite(value) ? `$ ${formatNumber(value)}` : '–';
}

function formatPrice(value) { return formatCurrency(value); }
function formatCurrencyARS(value) { return formatCurrency(value); }
function formatPercent(value) { return Number.isFinite(Number(value)) ? `${formatNumber(value)}%` : '–'; }
function formatDate(value) {
    const parts = String(value).split('-');
    return parts.length === 3 ? `${parts[2]}/${parts[1]}` : String(value);
}

function destroyPriceChart(chartKey) {
    const chart = priceCharts[chartKey];
    if (chart) chart.destroy();
    priceCharts[chartKey] = null;
}

function destroyAllPriceCharts() {
    Object.keys(priceCharts).forEach(destroyPriceChart);
}

function showChartMessage(containerId, message) {
    const element = document.getElementById(containerId);
    const container = element?.closest('.price-chart-canvas') || element;
    if (!container) return;
    const canvas = container.querySelector('canvas');
    if (canvas) canvas.style.display = 'none';
    const status = container.querySelector('.price-inline-status') || document.getElementById(`${containerId}Status`);
    if (status) {
        status.textContent = message;
        status.classList.add('is-visible');
    }
}

function clearChartMessage(containerId) {
    const element = document.getElementById(containerId);
    const container = element?.closest('.price-chart-canvas') || element;
    if (!container) return;
    const canvas = container.querySelector('canvas');
    if (canvas) canvas.style.display = '';
    const status = container.querySelector('.price-inline-status');
    if (status) {
        status.textContent = '';
        status.classList.remove('is-visible');
    }
}

function createPriceChart(chartKey, canvasId, config) {
    destroyPriceChart(chartKey);
    clearChartMessage(canvasId);
    const canvas = document.getElementById(canvasId);
    return canvas ? new Chart(canvas.getContext('2d'), config) : null;
}

function preparePriceEvolutionData(data, frequency, filters = getPriceFilters()) {
    const splitDimensions = getPriceSplitDimensions(filters);
    if (!splitDimensions.length) {
        const aggregate = aggregatePriceData(data, frequency).filter(item => isValidPrice(item.value));
        const values = aggregate.map(item => item.value);
        return {
            labels: aggregate.map(item => formatPeriodLabel(item.key, frequency)),
            values,
            meta: aggregate,
            splitDimensions,
            tooManySeries: false,
            series: [{ label: `Precio promedio ${frequency}`, data: values, meta: aggregate }]
        };
    }
    const periods = new Set();
    const grouped = new Map();
    data.filter(row => isValidPrice(getPriceValue(row))).forEach(row => {
        const period = createTimeKey(row.fecha || row, frequency);
        if (!period) return;
        const dimensionValues = splitDimensions.map(dimension => getPriceDimensionValue(row, dimension));
        const key = JSON.stringify(dimensionValues);
        const group = grouped.get(key) || { label: getPriceSplitLabel(row, splitDimensions), periods: new Map() };
        const values = group.periods.get(period) || [];
        values.push(getPriceValue(row));
        group.periods.set(period, values);
        periods.add(period);
        grouped.set(key, group);
    });
    const orderedPeriods = [...periods].sort((a, b) => a.localeCompare(b));
    const series = [...grouped.values()].sort((a, b) => a.label.localeCompare(b.label, 'es')).map(group => {
        const meta = orderedPeriods.map(period => {
            const values = group.periods.get(period) || [];
            return { key: period, value: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null, observations: values.length, dimensions: splitDimensions };
        });
        return { label: group.label, data: meta.map(item => item.value), meta };
    });
    return {
        labels: orderedPeriods.map(period => formatPeriodLabel(period, frequency)),
        values: series[0]?.data || [],
        meta: series[0]?.meta || [],
        splitDimensions,
        tooManySeries: series.length > 8,
        series
    };
}

function preparePriceRankingData(data, analysisLevel = 'general', filters = getPriceFilters()) {
    const field = analysisLevel === 'species_detail' ? 'variedad' : analysisLevel === 'variety_detail' ? 'procedencia' : 'especie';
    const dimensions = [...new Set([...getPriceSplitDimensions(filters), field])];
    const grouped = new Map();
    data.filter(row => isValidPrice(getPriceValue(row))).forEach(row => {
        const key = dimensions.map(dimension => String(getPriceDimensionValue(row, dimension))).join('|');
        const label = dimensions.length === 2 && dimensions.includes('especie') && dimensions.includes('variedad')
            ? getProductLabel(row)
            : dimensions.map(dimension => formatPriceDimensionValue(row, dimension)).join(' · ');
        const item = grouped.get(key) || { label, values: [], observations: 0, periods: [] };
        item.values.push(getPriceValue(row));
        item.observations++;
        const period = createTimeKey(row.fecha || row, priceFrequency);
        if (period) item.periods.push(period);
        grouped.set(label, item);
    });
    const ranking = [...grouped.values()].map(item => {
        const periods = item.periods.sort();
        return { ...item, average: item.values.reduce((sum, value) => sum + value, 0) / item.values.length, firstPeriod: periods[0], lastPeriod: periods.at(-1) };
    }).filter(item => isValidPrice(item.average)).sort((a, b) => b.average - a.average).slice(0, 10);
    return { labels: ranking.map(item => item.label), values: ranking.map(item => item.average), meta: ranking };
}

function preparePriceVariationData(data, frequency, filters = getPriceFilters()) {
    if (frequency === 'diaria') return { labels: [], values: [], meta: [] };
    const splitDimensions = getPriceSplitDimensions(filters);
    if (splitDimensions.length) {
        const evolution = preparePriceEvolutionData(data, frequency, filters);
        const series = evolution.series.map(item => {
            let previous = null;
            const meta = item.meta.map((period, index) => {
                const variation = isValidPrice(previous) && isValidPrice(period.value) ? (period.value / previous - 1) * 100 : null;
                if (isValidPrice(period.value)) previous = period.value;
                return { ...period, variation, key: period.key || index };
            });
            return { label: item.label, data: meta.map(period => period.variation), meta };
        });
        return {
            labels: evolution.labels,
            values: series[0]?.data || [],
            meta: series[0]?.meta || [],
            splitDimensions,
            tooManySeries: series.length > 8,
            series
        };
    }
    const series = calculatePeriodVariation(aggregatePriceData(data, frequency), frequency).filter(item => Number.isFinite(item.variation));
    return { labels: series.map(item => formatPeriodLabel(item.key, frequency)), values: series.map(item => item.variation), meta: series, splitDimensions, tooManySeries: false, series: [{ label: `Variación ${frequency}`, data: series.map(item => item.variation), meta: series }] };
}

function preparePriceIncreaseRankingData(data, frequency) {
    const grouping = getPriceVariationGrouping(frequency);
    const ranking = grouping.singleSeries ? [] : buildAccumulatedVariationRanking(data, grouping.groupFields, frequency).filter(item => item.variation > 0).sort((a, b) => b.variation - a.variation).slice(0, 10);
    return { labels: ranking.map(item => item.label), values: ranking.map(item => item.variation), meta: ranking, singleSeries: grouping.singleSeries, groupFields: grouping.groupFields };
}

function preparePriceDecreaseRankingData(data, frequency) {
    const grouping = getPriceVariationGrouping(frequency);
    const ranking = grouping.singleSeries ? [] : buildAccumulatedVariationRanking(data, grouping.groupFields, frequency).filter(item => item.variation < 0).sort((a, b) => a.variation - b.variation).slice(0, 10);
    return { labels: ranking.map(item => item.label), values: ranking.map(item => item.variation), meta: ranking, singleSeries: grouping.singleSeries, groupFields: grouping.groupFields };
}

function preparePriceMarketComparisonData(data) {
    const groups = new Map();
    data.filter(row => isValidPrice(getPriceValue(row)) && row.mercado).forEach(row => {
        const values = groups.get(row.mercado) || [];
        values.push(getPriceValue(row));
        groups.set(row.mercado, values);
    });
    const comparison = [...groups.entries()].map(([market, values]) => ({
        market,
        average: values.reduce((sum, value) => sum + value, 0) / values.length,
        observations: values.length
    })).filter(item => isValidPrice(item.average)).sort((a, b) => b.average - a.average);
    return { labels: comparison.map(item => item.market), values: comparison.map(item => item.average), meta: comparison };
}

function getTrafficLightStatus(variation) {
    if (variation < -50) return { key: 'review', label: 'Revisar' };
    if (variation < -5) return { key: 'decrease', label: 'Baja' };
    if (variation <= 5) return { key: 'stable', label: 'Estable' };
    if (variation <= 15) return { key: 'moderate', label: 'Suba moderada' };
    if (variation <= 50) return { key: 'strong', label: 'Suba fuerte' };
    return { key: 'review', label: 'Revisar' };
}

function calculateMonthlyPriceVariation(current, previous) {
    return isValidPrice(current) && isValidPrice(previous) ? (current / previous - 1) * 100 : null;
}

function calculateAccumulatedVariation(first, last) {
    return isValidPrice(first) && isValidPrice(last) ? (last / first - 1) * 100 : null;
}

function buildMonthlyPriceSemaphoreMatrix(data, filters = {}) {
    const groups = new Map();
    data.filter(row => isValidPrice(getPriceValue(row)) && (!row.fecha || isValidOperationalDate(row.fecha))).forEach(row => {
        const fields = ['mercado', 'rubro', 'especie', 'variedad', 'procedencia', 'unidad'];
        const key = fields.map(field => row[field] || (field === 'variedad' ? 'Sin especificar' : field === 'procedencia' ? 'Sin procedencia informada' : 'Sin informar')).join('|');
        const group = groups.get(key) || { row, observations: 0, monthlyValues: {} };
        group.observations++;
        const month = row.fecha ? row.fecha.slice(5, 7) : String(row.month || '').padStart(2, '0');
        if (/^(0[1-9]|1[0-2])$/.test(month)) {
            const values = group.monthlyValues[month] || [];
            values.push(getPriceValue(row));
            group.monthlyValues[month] = values;
        }
        groups.set(key, group);
    });
    return [...groups.values()].map(group => {
        const monthly = Object.fromEntries(Object.entries(group.monthlyValues).map(([month, values]) => [month, { price: values.reduce((sum, value) => sum + value, 0) / values.length, variation: null }]));
        const validMonths = Object.keys(monthly).sort();
        const shortPeriodFilter = document.getElementById('priceFilterMes')?.value && document.getElementById('priceFilterMes').value !== 'TODOS';
        if (validMonths.length < 2 || validMonths.length < 3 && !shortPeriodFilter) return null;
        const firstMonth = validMonths[0];
        const lastMonth = validMonths[validMonths.length - 1];
        const variation = calculateAccumulatedVariation(monthly[firstMonth].price, monthly[lastMonth].price);
        if (!Number.isFinite(variation)) return null;
        validMonths.slice(1).forEach((month, index) => { monthly[month].variation = calculateMonthlyPriceVariation(monthly[month].price, monthly[validMonths[index]].price); });
        const productLabel = getProductLabel(group.row);
        const market = group.row.mercado || 'Fuente sin informar';
        const splitDimensions = getPriceSplitDimensions(filters);
        const splitLabels = splitDimensions
            .filter(dimension => !['especie', 'variedad'].includes(dimension))
            .map(dimension => formatPriceDimensionValue(group.row, dimension));
        const rowLabel = [...new Set([productLabel, ...splitLabels])].join(' — ');
        return { ...group.row, productLabel, rowLabel, rowMeta: [group.row.rubro, group.row.procedencia ? `Origen: ${group.row.procedencia}` : ''].filter(Boolean).join(' · '), market, monthly, accumulatedVariation: variation, firstPeriod: firstMonth, lastPeriod: lastMonth, observations: group.observations, validMonths: validMonths.length, status: getTrafficLightStatus(variation) };
    }).filter(Boolean).sort((a, b) => String(a.mercado).localeCompare(String(b.mercado), 'es') || String(a.rubro).localeCompare(String(b.rubro), 'es') || String(a.productLabel).localeCompare(String(b.productLabel), 'es') || b.validMonths - a.validMonths).slice(0, 20);
}

function buildPriceTrafficLightTable(data, filters, frequency) {
    return buildMonthlyPriceSemaphoreMatrix(data, filters);
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}

function renderPriceTrafficLightTable(data, frequency) {
    const body = document.getElementById('priceTrafficLightBody');
    const status = document.getElementById('priceTrafficLightStatus');
    if (!body || !status) return;
    const rows = buildPriceTrafficLightTable(data, getPriceFilters(), frequency);
    body.innerHTML = rows.map(row => `<tr><td class="price-semaphore-product"><strong>${escapeHtml(row.rowLabel)}</strong><small>${escapeHtml(row.rowMeta)}</small></td>${MONTHS.map((_, index) => { const month = String(index + 1).padStart(2, '0'); const cell = row.monthly[month]; const value = cell?.price; const variation = cell?.variation; const cellClass = !cell ? '' : !Number.isFinite(variation) ? 'stable' : variation < -5 ? 'down-soft' : variation <= 0 ? 'stable' : variation <= 5 ? 'up-soft' : variation <= 15 ? 'up-medium' : 'up-strong'; return `<td class="price-semaphore-cell ${cellClass}">${value ? `<strong>${formatCurrency(value)}</strong>${Number.isFinite(variation) ? `<small>${variation >= 0 ? '↑' : '↓'}${formatPercent(Math.abs(variation))}</small>` : ''}` : '—'}</td>`; }).join('')}<td class="price-semaphore-variation">${formatPercent(row.accumulatedVariation)}</td><td><span class="price-semaphore-badge ${row.status.key}">${row.status.label}</span></td></tr>`).join('');
    status.textContent = rows.length ? '' : 'No hay suficientes precios mensuales para construir el semáforo con los filtros seleccionados.';
    status.classList.toggle('is-visible', !rows.length);
}

function renderPriceCharts() {
    destroyAllPriceCharts();
    const filters = getPriceFilters();
    const splitDimensions = getPriceSplitDimensions(filters);
    const visualizations = getAvailablePriceVisualizations(filteredPriceData, filters, priceFrequency);
    const evolution = preparePriceEvolutionData(filteredPriceData, priceFrequency, filters);
    const ranking = preparePriceRankingData(filteredPriceData, visualizations.level, filters);
    const variation = preparePriceVariationData(filteredPriceData, priceFrequency, filters);
    const increases = preparePriceIncreaseRankingData(filteredPriceData, priceFrequency);
    const decreases = preparePriceDecreaseRankingData(filteredPriceData, priceFrequency);
    const marketComparison = preparePriceMarketComparisonData(filteredPriceData);
    const insufficient = 'No hay datos suficientes para calcular esta visualización con los filtros seleccionados.';
    const comparable = 'No hay suficientes categorías comparables para construir este ranking.';
    const noComparable = 'La selección actual representa una única serie. La variación acumulada se muestra en los KPIs.';

    const metricLabel = getPriceMetricLabel();
    document.getElementById('priceTimeSeriesTitle').textContent = `Evolución ${priceFrequency} · ${metricLabel}`;
    document.getElementById('priceDailyMethodNote').hidden = priceFrequency !== 'diaria';
    const tooManySeries = 'La selección actual genera demasiadas series para una lectura clara. Reducí la cantidad de categorías seleccionadas.';
    if (evolution.tooManySeries) {
        showChartMessage('priceChartMonthly', tooManySeries);
    } else if (evolution.labels.length && evolution.series?.length) {
        const evolutionOptions = priceChartOptions(metricLabel);
        evolutionOptions.plugins.tooltip = {
            ...tooltipConfig(),
            callbacks: {
                label: context => {
                    const series = evolution.series[context.datasetIndex];
                    const item = series?.meta?.[context.dataIndex];
                    return [`Período: ${evolution.labels[context.dataIndex] || 'Sin período'}`, `${series?.label || metricLabel}: ${formatCurrency(item?.value)}`, `Observaciones: ${item?.observations || 0}`];
                }
            }
        };
        const colors = ['#34d399', '#60a5fa', '#fb923c', '#a78bfa', '#f472b6', '#facc15', '#22d3ee', '#fb7185'];
        priceCharts.evolution = createPriceChart('evolution', 'priceChartMonthly', {
            type: 'line',
            data: {
                labels: evolution.labels,
                datasets: evolution.series.map((series, index) => ({
                    label: splitDimensions.length ? series.label : `${metricLabel} ${priceFrequency}`,
                    data: series.data,
                    borderColor: colors[index % colors.length],
                    backgroundColor: `${colors[index % colors.length]}2a`,
                    fill: !splitDimensions.length,
                    tension: .3,
                    pointRadius: priceFrequency === 'diaria' ? 2 : 4
                }))
            },
            options: evolutionOptions
        });
    } else showChartMessage('priceChartMonthly', insufficient);

    const rankingTitle = visualizations.level === 'species_detail' ? 'Ranking de variedades por precio promedio' : visualizations.level === 'variety_detail' ? 'Ranking por procedencia de precio promedio' : 'Ranking de especies por precio promedio';
    const rankingDescription = visualizations.level === 'species_detail' ? 'Variedades con mayor precio promedio dentro de la especie seleccionada' : visualizations.level === 'variety_detail' ? 'Procedencias con mayor precio promedio dentro de la variedad seleccionada' : 'Especies con mayor precio promedio dentro del período seleccionado';
    document.getElementById('priceRankingTitle').textContent = rankingTitle;
    document.getElementById('priceRankingDesc').textContent = rankingDescription;
    document.getElementById('priceRankingCard').hidden = !(visualizations.showSpeciesRanking || visualizations.showVarietyRanking || visualizations.showProcedenciaComparison);
    if (!document.getElementById('priceRankingCard').hidden && ranking.labels.length >= 2) {
        const base = priceChartOptions(metricLabel, true);
        base.scales.x.beginAtZero = true;
        base.scales.x.suggestedMax = Math.max(...ranking.values) * 1.1;
        base.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => { const item = ranking.meta[context.dataIndex]; return [`${metricLabel}: ${formatCurrency(item.average)}`, `Observaciones: ${item.observations}`, `Período: ${formatPeriodLabel(item.firstPeriod, priceFrequency)} - ${formatPeriodLabel(item.lastPeriod, priceFrequency)}`]; } } };
        priceCharts.ranking = createPriceChart('ranking', 'priceChartRanking', { type: 'bar', data: { labels: ranking.labels, datasets: [{ label: metricLabel, data: ranking.values, backgroundColor: PALETTE }] }, options: base });
    } else if (!document.getElementById('priceRankingCard').hidden) showChartMessage('priceChartRanking', ranking.labels.length ? comparable : insufficient);
    document.getElementById('priceVariationCard').hidden = !visualizations.showVariationBars;
    if (variation.tooManySeries) {
        showChartMessage('priceChartVariation', tooManySeries);
    } else if (visualizations.showVariationBars && variation.values.length) {
        const variationOptions = priceChartOptions('Variación %');
        variationOptions.scales.y.ticks.callback = value => formatPercent(value);
        variationOptions.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => { const series = variation.series[context.datasetIndex]; const item = series?.meta?.[context.dataIndex]; return [`${series?.label || 'Variación'}: ${formatPercent(item?.variation)}`, `Observaciones: ${item?.observations || 0}`]; } } };
        const variationColors = ['#fb923c', '#60a5fa', '#a78bfa', '#34d399', '#f472b6', '#facc15', '#22d3ee', '#fb7185'];
        priceCharts.variation = createPriceChart('variation', 'priceChartVariation', { type: 'bar', data: { labels: variation.labels, datasets: variation.series.map((series, index) => ({ label: variation.splitDimensions?.length ? series.label : `Variación ${priceFrequency}`, data: series.data, backgroundColor: variation.splitDimensions?.length ? variationColors[index % variationColors.length] : series.data.map(value => value >= 0 ? '#fb923c' : '#60a5fa') })) }, options: variationOptions });
    } else if (visualizations.showVariationBars) showChartMessage('priceChartVariation', insufficient);

    const variationMeta = { diaria: ['Variación acumulada del período', 'Cambio entre el primer y último precio promedio disponible'], mensual: ['Variación mensual de precios', 'Cambio porcentual respecto al mes anterior'], anual: ['Variación anual de precios', 'Cambio porcentual respecto al año anterior'] }[priceFrequency];
    document.getElementById('priceVariationTitle').textContent = variationMeta[0];
    document.getElementById('priceVariationDesc').textContent = variationMeta[1];
    const renderVariationRanking = (chartKey, canvasId, statusId, prepared, color, label) => {
        if (prepared.labels.length < 2) { showChartMessage(canvasId, prepared.singleSeries ? noComparable : comparable); return; }
        const options = priceChartOptions('Variación %', true);
        const values = prepared.values;
        const min = Math.min(...values); const max = Math.max(...values); const extent = Math.max(Math.abs(min), Math.abs(max), 1) * 1.15;
        options.scales.x = { ...options.scales.x, min: min < 0 && max > 0 ? -extent : Math.min(0, min * 1.15), max: min < 0 && max > 0 ? extent : Math.max(0, max * 1.15), ticks: { callback: value => formatPercent(value) } };
        options.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => { const item = prepared.meta[context.dataIndex]; return [`Variación: ${formatPercent(item.variation)}`, `Precio inicial: ${formatCurrency(item.firstValue)}`, `Precio final: ${formatCurrency(item.lastValue)}`, `Período: ${formatPeriodLabel(item.firstPeriod, priceFrequency)} - ${formatPeriodLabel(item.lastPeriod, priceFrequency)}`, `Observaciones: ${item.observations}`]; } } };
        priceCharts[chartKey] = createPriceChart(chartKey, canvasId, { type: 'bar', data: { labels: prepared.labels, datasets: [{ label, data: values, backgroundColor: color }] }, options });
    };
    document.getElementById('priceIncreaseCard').hidden = !visualizations.showIncreasesRanking;
    document.getElementById('priceDecreaseCard').hidden = !visualizations.showDecreasesRanking;
    if (visualizations.showIncreasesRanking) renderVariationRanking('increases', 'priceChartIncreases', 'priceIncreaseStatus', increases, '#fb923c', 'Aumento %');
    if (visualizations.showDecreasesRanking) renderVariationRanking('decreases', 'priceChartDecreases', 'priceDecreaseStatus', decreases, '#60a5fa', 'Disminución %');
    const marketCard = document.getElementById('priceMarketCard');
    marketCard.hidden = !visualizations.showMarketComparison;
    if (visualizations.showMarketComparison && marketComparison.labels.length >= 2) {
        const options = priceChartOptions(metricLabel, true);
        options.scales.x.beginAtZero = true;
        options.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => { const item = marketComparison.meta[context.dataIndex]; return [`${metricLabel}: ${formatCurrency(item.average)}`, `Observaciones: ${item.observations}`]; } } };
        priceCharts.marketComparison = createPriceChart('marketComparison', 'priceChartMarket', { type: 'bar', data: { labels: marketComparison.labels, datasets: [{ label: metricLabel, data: marketComparison.values, backgroundColor: ['#34d399', '#60a5fa'] }] }, options });
    } else if (!marketCard.hidden) showChartMessage('priceChartMarket', 'La selección actual contiene un solo mercado.');
    const dailyDescription = priceFrequency === 'diaria' ? 'Variación acumulada entre primera y última fecha disponible' : 'Productos con mayor cambio entre el primer y último período';
    document.getElementById('priceIncreaseDesc').textContent = dailyDescription;
    document.getElementById('priceDecreaseDesc').textContent = dailyDescription;
    console.log('Frecuencia precios aplicada:', priceFrequency);
    console.log('Filtros precios:', filters);
    console.log('Dimensiones de separación:', splitDimensions);
    console.log('Cantidad de series generadas:', evolution.series?.length || 0);
    console.log('Series:', (evolution.series || []).map(series => series.label));
    console.log('Agrupación variación diaria:', increases.groupFields || decreases.groupFields || []);
    console.log('Series comparables para variación:', Math.max(increases.meta.length, decreases.meta.length));
    console.log('Subas mostradas:', increases.labels.length);
    console.log('Bajas mostradas:', decreases.labels.length);
    renderPriceTrafficLightTable(filteredPriceData, 'mensual');
}

function priceChartOptions(axisLabel, horizontal = false) {
    const options = defaultBarOptions(false);
    options.responsive = true;
    options.maintainAspectRatio = false;
    options.indexAxis = horizontal ? 'y' : 'x';
    options.scales.x.ticks.callback = horizontal ? value => formatCurrency(value) : function(value) { return this.getLabelForValue(value); };
    options.scales.y.ticks.callback = horizontal ? function(value) { return this.getLabelForValue(value); } : value => formatCurrency(value);
    options.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => ` ${formatCurrency(context.parsed.y ?? context.parsed.x)}` } };
    return options;
}

// ─── Independent agricultural commodities module ───────────────────────
function emptyCommodityData() {
    return { diario: [], mensual: [], ultimos: [], resumen: [], semaforo: [] };
}

async function loadCommoditySource(sourceKey) {
    const config = COMMODITY_SOURCE_CONFIG[sourceKey];
    const entries = await Promise.all(Object.entries(config.files).map(async ([key, file]) => {
        if (!file) return [key, []];
        const response = await fetch(`${config.path}${file}`);
        if (!response.ok) throw new Error(`${sourceKey}/${file}: HTTP ${response.status}`);
        return [key, parseCommodityCSV(await response.text())];
    }));
    return Object.fromEntries(entries);
}

function initCommoditySourceFilter() {
    const select = document.getElementById('commodityFilterSource');
    if (!select) return;
    select.innerHTML = Object.entries(COMMODITY_SOURCE_CONFIG).map(([value, config]) => `<option value="${value}">${escapeHtml(config.label)}</option>`).join('');
    select.value = commoditySource;
    if (!select.dataset.commodityBound) {
        select.addEventListener('change', () => setCommoditySource(select.value));
        select.dataset.commodityBound = 'true';
    }
}

function updateCommoditySourcePresentation() {
    const config = COMMODITY_SOURCE_CONFIG[commoditySource] || COMMODITY_SOURCE_CONFIG.sio;
    const subtitle = document.getElementById('commoditySourceSubtitle');
    const note = document.getElementById('commodityMethodNote');
    const frequency = document.getElementById('commodityFilterFrequency');
    if (subtitle) subtitle.textContent = config.subtitle;
    if (note) note.textContent = config.note;
    const operationsLabel = document.getElementById('commodityKpiOperationsLabel');
    if (operationsLabel) operationsLabel.textContent = config.operationsLabel;
    const operationsUnit = document.getElementById('commodityKpiOperationsUnit');
    if (operationsUnit) operationsUnit.textContent = config.operationsUnit;
    const latestVariationShort = document.getElementById('commodityLatestVariationShort');
    const latestVariationLong = document.getElementById('commodityLatestVariationLong');
    if (latestVariationShort) latestVariationShort.textContent = config.monthlyOnly ? 'Var. mensual' : 'Var. 7 días';
    if (latestVariationLong) latestVariationLong.textContent = config.monthlyOnly ? 'Var. interanual' : 'Var. 30 días';
    if (frequency) {
        const dailyOption = frequency.querySelector('option[value="diaria"]');
        if (dailyOption) dailyOption.disabled = Boolean(config.monthlyOnly);
        if (config.monthlyOnly && frequency.value === 'diaria') {
            frequency.value = 'mensual';
            commodityFrequency = 'mensual';
        }
    }
}

function updateCommoditySourceStatus() {
    const config = COMMODITY_SOURCE_CONFIG[commoditySource] || COMMODITY_SOURCE_CONFIG.sio;
    const summary = commodityData.resumen[0] || {};
    const count = Number(summary.filas_dashboard ?? summary.filas_analiticas ?? summary.filas_integradas) || 0;
    const sampleMode = summary.modo === 'muestra';
    const label = config.monthlyOnly ? 'registros mensuales' : 'operaciones';
    setCommodityDataStatus(count ? `${sampleMode ? 'Muestra de respaldo' : config.label} · ${formatNumber(count)} ${label}` : `${config.label} · Sin datos disponibles`, count ? (sampleMode ? 'sample' : 'ready') : '');
    const freshness = document.getElementById('commodityDataFreshness');
    const lastOperation = document.getElementById('commodityDataLastOperation');
    const operationRange = document.getElementById('commodityDataOperationRange');
    if (freshness) {
        const capture = String(summary.fecha_ultima_captura_sio || '').trim();
        const visible = commoditySource === 'sio';
        freshness.hidden = !visible;
        freshness.textContent = visible ? `Actualizado al: ${formatCommodityCapture(capture || summary.fecha_actualizacion_dashboard || summary.fecha_actualizacion)}` : '';
    }
    if (lastOperation) {
        const visible = commoditySource === 'sio';
        lastOperation.hidden = !visible;
        lastOperation.textContent = visible ? `Última operación informada: ${formatCommodityCapture(summary.fecha_ultima_operacion_sio || summary.fecha_max_operacion_sio || summary.fecha_max)}` : '';
    }
    if (operationRange) {
        const visible = commoditySource === 'sio';
        operationRange.hidden = !visible;
        const minDate = formatCommodityCapture(summary.fecha_min_operacion_sio || summary.fecha_min);
        const maxDate = formatCommodityCapture(summary.fecha_max_operacion_sio || summary.fecha_max);
        operationRange.textContent = visible ? `Rango de operaciones: ${minDate} — ${maxDate}` : '';
    }
}

function formatCommodityCapture(value) {
    const raw = String(value || '').trim();
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::\d{2})?)?/);
    if (!match) return 'sin fecha registrada';
    const dateLabel = `${match[3]}/${match[2]}/${match[1]}`;
    return match[4] ? `${dateLabel} ${match[4]}:${match[5]}` : dateLabel;
}

function setCommoditySource(sourceKey) {
    commoditySource = COMMODITY_SOURCE_CONFIG[sourceKey] ? sourceKey : 'sio';
    commodityData = commodityDataBySource[commoditySource] || emptyCommodityData();
    commoditySelectedValues = [];
    commodityFrequency = 'mensual';
    ['commodityFilterCommodity', 'commodityFilterMarket', 'commodityFilterCurrency', 'commodityFilterUnit', 'commodityFilterType'].forEach(id => {
        const control = document.getElementById(id);
        if (control) control.dataset.initialized = 'false';
    });
    const select = document.getElementById('commodityFilterSource');
    if (select) select.value = commoditySource;
    updateCommoditySourcePresentation();
    initCommodityFilters();
    updateCommoditySourceStatus();
    updateCommodityDashboard();
}

async function loadCommodityData() {
    await Promise.all(Object.keys(COMMODITY_SOURCE_CONFIG).map(async sourceKey => {
        try {
            commodityDataBySource[sourceKey] = await loadCommoditySource(sourceKey);
        } catch (error) {
            console.error(`Error loading ${sourceKey} commodity dashboard CSV:`, error);
            commodityDataBySource[sourceKey] = emptyCommodityData();
        }
    }));
    initCommoditySourceFilter();
    setCommoditySource(commoditySource);
}

function parseCommodityCSV(text) {
    const clean = String(text || '').replace(/^\uFEFF/, '').trim();
    if (!clean) return [];
    const lines = clean.split(/\r?\n/);
    const headers = parseDelimitedLine(lines[0], ';').map(normalizeCommodityHeader);
    return lines.slice(1).filter(line => line.trim()).map(line => {
        const values = parseDelimitedLine(line, ';');
        return headers.reduce((row, header, index) => { row[header] = values[index] ?? ''; return row; }, {});
    });
}

function normalizeCommodityHeader(value) {
    return String(value || '').trim().toLocaleLowerCase('es-AR').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
}

function commodityNumber(value) {
    const source = String(value ?? '').trim().replace(/\s/g, '');
    if (!source) return null;
    const scientific = /^[-+]?\d+(?:\.\d+)?e[-+]?\d+$/i.test(source);
    const raw = source.replace(/[^0-9,.\-eE+]/g, '');
    if (!raw) return null;
    const normalized = scientific
        ? raw
        : raw.includes(',') && raw.includes('.')
            ? raw.replace(/\./g, '').replace(',', '.')
            : raw.includes(',')
                ? raw.replace(',', '.')
                : raw;
    const number = Number(normalized);
    return Number.isFinite(number) ? number : null;
}

function commodityFilterValues(id) {
    if (id === 'commodityFilterCommodity') return commoditySelectedValues.length ? [...commoditySelectedValues] : ['TODOS'];
    const value = document.getElementById(id)?.value || 'TODOS';
    return [value];
}

function commodityMarketLabel(value) {
    const raw = String(value || '').trim();
    if (!raw) return 'Sin plaza';
    const shortRaw = raw.split(/[—–]/).pop().trim();
    const key = normalizeCommodityHeader(shortRaw).replace(/_/g, '');
    const labels = {
        rosario: 'Rosario',
        cordoba: 'Córdoba',
        quequen: 'Quequén',
        bblanca: 'Bahía Blanca',
        bahiablanca: 'Bahía Blanca',
        darsena: 'Dársena'
    };
    return labels[key] || shortRaw || raw;
}

function commodityMarketIsAll() {
    return (document.getElementById('commodityFilterMarket')?.value || 'TODOS') === 'TODOS';
}

function commoditySelectedMarket() {
    return document.getElementById('commodityFilterMarket')?.value || 'TODOS';
}

function commoditySelectionIssue(rows, latestRows = []) {
    const allRows = [...rows, ...latestRows];
    const dimensions = [
        ['moneda', 'commodityFilterCurrency', 'moneda'],
        ['unidad', 'commodityFilterUnit', 'unidad']
    ];
    for (const [field, filterId, label] of dimensions) {
        const values = [...new Set(allRows.map(row => String(row[field] || '').trim()).filter(Boolean))];
        if ((document.getElementById(filterId)?.value || 'TODOS') === 'TODOS' && values.length > 1) {
            return `Seleccione una ${label} para analizar la serie sin mezclar ${values.join(' y ')}.`;
        }
    }
    return '';
}

function commodityNumericMedian(values) {
    const numbers = values.map(value => commodityNumber(value)).filter(value => Number.isFinite(value)).sort((a, b) => a - b);
    if (!numbers.length) return null;
    const middle = Math.floor(numbers.length / 2);
    return numbers.length % 2 ? numbers[middle] : (numbers[middle - 1] + numbers[middle]) / 2;
}

function commoditySourceShort(row) {
    const source = String(row?.fuente || '').toLowerCase();
    if (source.includes('sio')) return 'SIO Granos';
    if (source.includes('secretaria') || source.includes('agricultura')) return 'Secretaría de Agricultura';
    return row?.fuente || 'Sin fuente';
}

function commodityPeriodValue(row) {
    return commodityFrequency === 'diaria' ? (row.fecha || row.periodo_ym) : (row.periodo_ym || row.fecha);
}

function setCommodityFilterHint(message = '', warning = false) {
    const hint = document.getElementById('commodityFilterCommodityHint');
    if (!hint) return;
    hint.textContent = message || 'Todos los commodities · seleccioná hasta 3 para comparar';
    hint.classList.toggle('is-warning', warning);
}

function updateCommodityMultiSummary() {
    const control = document.getElementById('commodityFilterCommodity');
    const summary = document.getElementById('commodityFilterCommoditySummary');
    const menu = document.getElementById('commodityFilterCommodityMenu');
    if (!control || !summary || !menu) return;
    summary.textContent = commoditySelectedValues.length ? commoditySelectedValues.slice(0, 2).join(', ') + (commoditySelectedValues.length > 2 ? ` +${commoditySelectedValues.length - 2}` : '') : 'Todos';
    menu.querySelectorAll('input[data-commodity-value]').forEach(input => {
        const value = input.dataset.commodityValue;
        const selected = value === 'TODOS' ? commoditySelectedValues.length === 0 : commoditySelectedValues.includes(value);
        input.checked = selected;
        input.closest('.commodity-multi-option')?.classList.toggle('is-selected', selected);
        const checkbox = input.closest('.commodity-multi-option')?.querySelector('.commodity-multi-checkbox');
        if (checkbox) checkbox.textContent = selected ? '✓' : '';
    });
}

function populateCommodityMultiSelect(values) {
    const control = document.getElementById('commodityFilterCommodity');
    const menu = document.getElementById('commodityFilterCommodityMenu');
    const trigger = document.getElementById('commodityFilterCommodityTrigger');
    if (!control || !menu || !trigger) return;
    const unique = [...new Set(values.filter(value => String(value || '').trim()))].sort((a, b) => String(a).localeCompare(String(b), 'es'));
    const initialized = control.dataset.initialized === 'true';
    commoditySelectedValues = initialized ? commoditySelectedValues.filter(value => unique.includes(value)).slice(0, 3) : [];
    menu.innerHTML = [
        { value: 'TODOS', label: 'Todos los commodities' },
        ...unique.map(value => ({ value, label: value })),
    ].map(option => `<label class="commodity-multi-option"><input type="checkbox" data-commodity-value="${escapeHtml(option.value)}"><span class="commodity-multi-checkbox" aria-hidden="true"></span><span class="commodity-multi-option-label">${escapeHtml(option.label)}</span></label>`).join('');
    if (!control.dataset.commodityBound) {
        trigger.addEventListener('click', () => {
            const isOpen = control.classList.toggle('is-open');
            trigger.setAttribute('aria-expanded', String(isOpen));
        });
        menu.addEventListener('change', event => {
            const input = event.target.closest('input[data-commodity-value]');
            if (!input) return;
            const value = input.dataset.commodityValue;
            if (value === 'TODOS') {
                if (input.checked) commoditySelectedValues = [];
                else input.checked = true;
                setCommodityFilterHint();
            } else if (input.checked) {
                if (commoditySelectedValues.length >= 3 && !commoditySelectedValues.includes(value)) {
                    input.checked = false;
                    setCommodityFilterHint('Máximo 3 commodities por comparación.', true);
                    updateCommodityMultiSummary();
                    return;
                }
                commoditySelectedValues = [...commoditySelectedValues.filter(item => item !== value), value];
                setCommodityFilterHint();
            } else {
                commoditySelectedValues = commoditySelectedValues.filter(item => item !== value);
                setCommodityFilterHint();
            }
            updateCommodityMultiSummary();
            updateCommodityDashboard();
        });
        document.addEventListener('click', event => {
            if (!control.contains(event.target)) {
                control.classList.remove('is-open');
                trigger.setAttribute('aria-expanded', 'false');
            }
        });
        control.dataset.commodityBound = 'true';
    }
    control.dataset.initialized = 'true';
    updateCommodityMultiSummary();
}

function populateCommoditySelect(id, values, allLabel, defaultValue) {
    const select = document.getElementById(id);
    if (!select) return;
    const unique = [...new Set(values.filter(value => String(value || '').trim()))].sort((a, b) => String(a).localeCompare(String(b), 'es'));
    if (id === 'commodityFilterCommodity') {
        populateCommodityMultiSelect(unique);
        return;
    }
    const initialized = select.dataset.initialized === 'true';
    const previous = initialized ? select.value : defaultValue;
    select.innerHTML = `<option value="TODOS">${allLabel}</option>`;
    unique.forEach(value => {
        const option = new Option(id === 'commodityFilterMarket' ? commodityMarketLabel(value) : value, value);
        select.appendChild(option);
    });
    select.value = previous === 'TODOS' || unique.includes(previous) ? previous : defaultValue;
    if (select.value !== 'TODOS' && !unique.includes(select.value)) select.value = unique[0] || 'TODOS';
    select.dataset.initialized = 'true';
    if (!select.dataset.commodityBound) {
        select.addEventListener('change', updateCommodityDashboard);
        select.dataset.commodityBound = 'true';
    }
}

function initCommodityFilters() {
    const optionRows = [...commodityData.mensual, ...commodityData.diario, ...commodityData.ultimos];
    const currencies = [...new Set(optionRows.map(row => row.moneda).filter(Boolean))];
    const units = [...new Set(optionRows.map(row => row.unidad).filter(Boolean))];
    const markets = [...new Set(optionRows.map(row => row.mercado).filter(Boolean))];
    const sourceConfig = COMMODITY_SOURCE_CONFIG[commoditySource] || COMMODITY_SOURCE_CONFIG.sio;
    const currencyDefault = sourceConfig.monthlyOnly && currencies.includes('ARS') ? 'ARS' : (currencies.includes('ARS') ? 'ARS' : (currencies[0] || 'TODOS'));
    const unitDefault = sourceConfig.monthlyOnly && units.includes('TN') ? 'TN' : (units[0] || 'TODOS');
    const localType = 'Precio interno mensual';
    const typeValues = optionRows.map(row => row.tipo_precio);
    const typeDefault = sourceConfig.monthlyOnly && typeValues.includes(localType) ? localType : 'TODOS';
    const rosario = markets.find(value => commodityMarketLabel(value) === 'Rosario');
    const marketDefault = sourceConfig.monthlyOnly ? (rosario || 'TODOS') : 'TODOS';
    populateCommoditySelect('commodityFilterCommodity', optionRows.map(row => row.commodity), 'Todos', 'TODOS');
    populateCommoditySelect('commodityFilterMarket', markets, 'Todas', marketDefault);
    populateCommoditySelect('commodityFilterCurrency', currencies, 'Todas', currencyDefault);
    populateCommoditySelect('commodityFilterUnit', units, 'Todas', unitDefault);
    populateCommoditySelect('commodityFilterType', typeValues, 'Todos', typeDefault);
    const frequency = document.getElementById('commodityFilterFrequency');
    if (frequency && !frequency.dataset.commodityBound) {
        frequency.value = commodityFrequency;
        frequency.addEventListener('change', () => { commodityFrequency = frequency.value; updateCommodityDashboard(); });
        frequency.dataset.commodityBound = 'true';
    }
}

function commodityRowMatches(row) {
    return [['commodityFilterCommodity', 'commodity'], ['commodityFilterMarket', 'mercado'], ['commodityFilterCurrency', 'moneda'], ['commodityFilterUnit', 'unidad'], ['commodityFilterType', 'tipo_precio']].every(([filterId, field]) => {
        const selected = commodityFilterValues(filterId);
        return selected.includes('TODOS') || selected.includes(String(row[field] || ''));
    });
}

function getCommodityFilteredRows() {
    const rows = commodityFrequency === 'diaria' ? commodityData.diario : commodityData.mensual;
    return rows.filter(commodityRowMatches).filter(row => {
        const price = commodityNumber(row.precio_mediana);
        return Number.isFinite(price) && price > 0;
    });
}

function getCommodityLatestRows() {
    return commodityData.ultimos.filter(commodityRowMatches).filter(row => {
        const price = commodityLatestPrice(row);
        return Number.isFinite(price) && price > 0;
    });
}

function commodityLatestPrice(row) {
    return commodityNumber(row.precio_mediana_ultimo_periodo ?? row.precio_mediana_ultimo_dia);
}

function commodityLatestDate(row) {
    return row.periodo_ultimo || row.fecha_ultima;
}

function setCommodityDataStatus(message, state = '') {
    const status = document.getElementById('commodityDataStatus');
    if (!status) return;
    status.textContent = message;
    status.classList.remove('is-ready', 'is-error');
    if (state === 'ready' || state === 'sample') status.classList.add('is-ready');
    if (state === 'error') status.classList.add('is-error');
}

function commodityPeriodLabel(value) {
    const raw = String(value || '');
    if (/^\d{4}-\d{2}$/.test(raw)) return `${MONTHS[Number(raw.slice(5, 7)) - 1]} ${raw.slice(0, 4)}`;
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return `${raw.slice(8, 10)}/${raw.slice(5, 7)}/${raw.slice(0, 4)}`;
    return raw || 'Sin dato';
}

function commodityPercent(value) {
    const number = commodityNumber(value);
    return Number.isFinite(number) ? `${formatNumber(number)}%` : '–';
}

function commodityStateClass(state) {
    return String(state || 'Sin dato').toLocaleLowerCase('es-AR').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '-');
}

function commoditySeriesKey(row, includeCondition = false) {
    return [row.commodity, row.fuente, row.mercado, row.moneda, row.unidad, row.tipo_precio, includeCondition ? row.condicion_comercial : ''].join('|');
}

function commoditySeriesContext() {
    const marketAll = commodityMarketIsAll();
    return {
        marketAll,
        marketMode: commoditySource === 'local_mensual' && marketAll && commoditySelectedValues.length === 1
    };
}

function commoditySeriesLabel(row, options = {}) {
    const label = options.marketMode ? commodityMarketLabel(row.mercado) : (row.commodity || 'Sin commodity');
    if (options.includeCondition && row.condicion_comercial && row.condicion_comercial !== 'Sin especificar') return `${label} (${row.condicion_comercial})`;
    return label;
}

function commodityUniqueSeriesLabels(items, options = {}) {
    const counts = new Map();
    items.forEach(item => {
        const row = item.row || item;
        const base = commoditySeriesLabel(row, options);
        const count = counts.get(base) || 0;
        counts.set(base, count + 1);
        if (!count) {
            item.label = base;
            return;
        }
        const suffix = options.marketMode ? (row.commodity || 'Serie') : (row.mercado ? commodityMarketLabel(row.mercado) : (row.tipo_precio || row.condicion_comercial || 'Serie'));
        item.label = `${base} · ${suffix}`;
    });
    return items;
}

function commodityTooltipLines(row, value, period, metricLabel = 'Precio mediano') {
    const source = row?.fuente || (COMMODITY_SOURCE_CONFIG[commoditySource]?.subtitle || 'Sin fuente');
    return [
        `Commodity: ${row?.commodity || 'Sin dato'}`,
        `Mercado/plaza: ${commodityMarketLabel(row?.mercado)}`,
        `Fuente: ${source}`,
        `Moneda: ${row?.moneda || 'Sin dato'}`,
        `Unidad: ${row?.unidad || 'Sin dato'}`,
        `Tipo de precio: ${row?.tipo_precio || 'Sin dato'}`,
        `Período: ${commodityPeriodLabel(period || commodityLatestDate(row))}`,
        `${metricLabel}: ${formatNumber(value)}`,
        `Var. mensual: ${commodityPercent(row?.variacion_mensual_pct ?? row?.variacion_7d_pct)}`,
        `Var. interanual: ${commodityPercent(row?.variacion_interanual_pct ?? row?.variacion_30d_pct)}`
    ].map(line => ` ${line}`);
}

function commodityChartOptions(type = 'line') {
    const options = type === 'bar' ? defaultBarOptions(false) : defaultLineOptions();
    options.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => {
        const value = context.chart.options.indexAxis === 'y' ? context.parsed.x : (Number.isFinite(context.parsed.y) ? context.parsed.y : context.parsed.x);
        const metadata = context.dataset.metadata?.[context.dataIndex];
        if (metadata) return commodityTooltipLines(metadata, value, context.dataset.periods?.[context.dataIndex], context.dataset.tooltipMetric || 'Precio mediano');
        return ` ${context.dataset.label || context.label}: ${formatNumber(value)}`;
    } } };
    options.scales.y.ticks.callback = value => formatNumber(value);
    return options;
}

function setCommodityChart(chartKey, canvasId, statusId, config, emptyMessage) {
    if (commodityCharts[chartKey]) commodityCharts[chartKey].destroy();
    commodityCharts[chartKey] = null;
    const canvas = document.getElementById(canvasId);
    const status = document.getElementById(statusId);
    if (!canvas || !status) return;
    if (!config) {
        canvas.style.display = 'none';
        status.textContent = emptyMessage;
        status.classList.add('is-visible');
        return;
    }
    canvas.style.display = 'block';
    status.textContent = '';
    status.classList.remove('is-visible');
    commodityCharts[chartKey] = new Chart(canvas.getContext('2d'), config);
}

function renderCommodityTrend(rows) {
    const context = commoditySeriesContext();
    const notice = document.getElementById('commodityTrendNotice');
    if (commoditySource === 'local_mensual' && context.marketAll && commoditySelectedValues.length !== 1) {
        setCommodityChart('trend', 'commodityPriceTrend', 'commodityPriceTrendStatus', null, 'Seleccione una plaza/mercado para visualizar la evolución sin mezclar referencias.');
        if (notice) notice.textContent = '';
        return;
    }
    const includeCondition = commodityFrequency === 'diaria';
    const groups = new Map();
    rows.forEach(row => {
        const key = context.marketMode ? row.mercado : commoditySeriesKey(row, includeCondition);
        const period = commodityPeriodValue(row);
        if (!period) return;
        const group = groups.get(key) || { row, values: new Map(), metadata: new Map() };
        group.values.set(period, commodityNumber(row.precio_mediana));
        group.metadata.set(period, row);
        groups.set(key, group);
    });
    const maxSeries = context.marketMode ? 4 : 6;
    const ordered = [...groups.values()].sort((a, b) => {
        const aPeriods = [...a.values.keys()].sort();
        const bPeriods = [...b.values.keys()].sort();
        return (bPeriods.at(-1) || '').localeCompare(aPeriods.at(-1) || '') || ((commodityNumber(b.values.get(bPeriods.at(-1))) || 0) - (commodityNumber(a.values.get(aPeriods.at(-1))) || 0));
    });
    const selected = commodityUniqueSeriesLabels(ordered.slice(0, maxSeries), { marketMode: context.marketMode, includeCondition }).filter(group => group.values.size);
    const truncated = groups.size > maxSeries;
    const labels = [...new Set(selected.flatMap(group => [...group.values.keys()]))].sort();
    const config = selected.length && labels.length ? { type: 'line', data: { labels: labels.map(commodityPeriodLabel), datasets: selected.map((group, index) => ({ label: group.label, data: labels.map(label => group.values.get(label) ?? null), metadata: labels.map(label => group.metadata.get(label) || group.row), periods: labels, borderColor: PALETTE[index % PALETTE.length], backgroundColor: PALETTE_ALPHA[index % PALETTE_ALPHA.length], borderWidth: 2, pointRadius: 2, tension: .22, spanGaps: commodityFrequency !== 'diaria' })) }, options: commodityChartOptions('line') } : null;
    setCommodityChart('trend', 'commodityPriceTrend', 'commodityPriceTrendStatus', config, 'No hay datos de precios para los filtros seleccionados.');
    if (notice) notice.textContent = truncated ? 'Se muestran las principales series para preservar legibilidad. Use los filtros para acotar la comparación.' : '';
}

function renderCommodityRanking(latestRows) {
    const context = commoditySeriesContext();
    const rows = [...latestRows].sort((a, b) => commodityLatestPrice(b) - commodityLatestPrice(a)).slice(0, 10).map(row => ({ row, label: '' }));
    commodityUniqueSeriesLabels(rows, { marketMode: context.marketMode });
    const config = rows.length ? { type: 'bar', data: { labels: rows.map(item => item.label), datasets: [{ label: 'Precio mediano último período', data: rows.map(item => commodityLatestPrice(item.row)), metadata: rows.map(item => item.row), periods: rows.map(item => commodityLatestDate(item.row)), backgroundColor: rows.map((_, index) => PALETTE[index % PALETTE.length]), borderRadius: 4, borderSkipped: false }] }, options: { ...commodityChartOptions('bar'), indexAxis: 'y', scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8', callback: value => formatNumber(value) } }, y: { grid: { display: false }, ticks: { color: '#b2c0cd', font: { family: "'Inter'", size: 10 } } } } } } : null;
    setCommodityChart('ranking', 'commodityRanking', 'commodityRankingStatus', config, 'No hay últimos precios para los filtros seleccionados.');
}

function renderCommodityVolume(rows) {
    const context = commoditySeriesContext();
    const local = commoditySource === 'local_mensual';
    const groups = new Map();
    rows.forEach(row => {
        const value = commodityNumber(local ? row.operaciones : row.volumen_total);
        if (!Number.isFinite(value) || value < 0) return;
        let key = row.commodity;
        if (local && context.marketMode) key = row.mercado;
        else if (local && context.marketAll) key = `${row.commodity}|${row.mercado}`;
        const group = groups.get(key) || { row, value: 0 };
        group.value += value;
        groups.set(key, group);
    });
    const values = [...groups.values()].sort((a, b) => b.value - a.value).slice(0, 10).map(item => ({ ...item, label: '' }));
    commodityUniqueSeriesLabels(values, { marketMode: context.marketMode });
    const metricLabel = local ? 'Observaciones con precio' : 'Volumen informado (TN)';
    const config = values.length ? { type: 'bar', data: { labels: values.map(item => item.label), datasets: [{ label: metricLabel, data: values.map(item => item.value), metadata: values.map(item => item.row), periods: values.map(item => commodityPeriodValue(item.row)), tooltipMetric: metricLabel, backgroundColor: '#60a5fa', borderRadius: 4, borderSkipped: false }] }, options: { ...commodityChartOptions('bar'), indexAxis: 'y', scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8', callback: value => formatNumber(value) } }, y: { grid: { display: false }, ticks: { color: '#b2c0cd', font: { family: "'Inter'", size: 10 } } } } } } : null;
    setCommodityChart('volume', 'commodityVolume', 'commodityVolumeStatus', config, local ? 'No hay observaciones para los filtros seleccionados.' : 'No hay volumen válido para los filtros seleccionados.');
}

function updateCommodityKpis(rows, latestRows) {
    const products = new Set(rows.map(row => row.commodity).filter(Boolean));
    const currencies = new Set(rows.map(row => row.moneda).filter(Boolean));
    const units = new Set(rows.map(row => row.unidad).filter(Boolean));
    const priceTypes = new Set(rows.map(row => row.tipo_precio).filter(Boolean));
    const dates = rows.map(row => commodityFrequency === 'diaria' ? row.fecha : row.periodo_ym).filter(Boolean).sort();
    const latestDates = latestRows.map(commodityLatestDate).filter(Boolean).sort();
    const latestPrices = latestRows.map(commodityLatestPrice).filter(value => Number.isFinite(value) && value > 0);
    const latestPrice = commodityNumericMedian(latestPrices);
    const monthlyValues = latestRows.map(row => commodityNumber(row.variacion_mensual_pct ?? row.variacion_7d_pct)).filter(value => Number.isFinite(value));
    const yoyValues = latestRows.map(row => commodityNumber(row.variacion_interanual_pct ?? row.variacion_30d_pct)).filter(value => Number.isFinite(value));
    const currencyLabel = currencies.size === 1 ? [...currencies][0] : currencies.size ? `${[...currencies].sort().join(' / ')} (separadas)` : 'moneda seleccionada';
    const unitLabel = units.size === 1 ? [...units][0] : units.size ? 'unidades separadas' : 'unidad seleccionada';
    const typeLabel = priceTypes.size === 1 ? ` · ${[...priceTypes][0]}` : ' · tipos de precio separados';
    const sourceConfig = COMMODITY_SOURCE_CONFIG[commoditySource] || COMMODITY_SOURCE_CONFIG.sio;
    document.getElementById('commodityKpiUpdate').textContent = commodityPeriodLabel(latestDates.at(-1) || dates.at(-1));
    document.getElementById('commodityKpiRange').textContent = dates.length ? `${commodityPeriodLabel(dates[0])} — ${commodityPeriodLabel(dates.at(-1))}` : 'Rango sin datos';
    document.getElementById('commodityKpiProducts').textContent = products.size || '–';
    document.getElementById('commodityKpiOperations').textContent = formatNumber(rows.reduce((sum, row) => sum + (commodityNumber(row.operaciones) || 0), 0));
    document.getElementById('commodityKpiCurrency').textContent = currencies.size === 1 ? [...currencies][0] : currencies.size ? 'Separadas' : '–';
    document.getElementById('commodityKpiMedian').textContent = Number.isFinite(latestPrice) ? formatNumber(latestPrice) : '–';
    document.getElementById('commodityKpiMedianUnit').textContent = latestRows.length ? `${currencyLabel.replace(' (separadas)', '')} / ${unitLabel.replace('unidades separadas', 'unidades')}${latestRows.length > 1 ? ` · ${latestRows.length} series` : ''}` : 'sin último precio';
    document.getElementById('commodityKpiMonthlyVariation').textContent = monthlyValues.length ? commodityPercent(commodityNumericMedian(monthlyValues)) : '–';
    document.getElementById('commodityKpiMonthlyVariationDetail').textContent = monthlyValues.length ? `mediana de ${monthlyValues.length} serie${monthlyValues.length === 1 ? '' : 's'}` : 'sin dato comparable';
    document.getElementById('commodityKpiYoYVariation').textContent = yoyValues.length ? commodityPercent(commodityNumericMedian(yoyValues)) : '–';
    document.getElementById('commodityKpiYoYVariationDetail').textContent = yoyValues.length ? `mediana de ${yoyValues.length} serie${yoyValues.length === 1 ? '' : 's'}` : 'sin dato comparable';
    const aggregationLabel = sourceConfig.monthlyOnly ? 'mediana de precios mensuales positivos' : 'mediana de operaciones con precio positivo';
    document.getElementById('commodityPriceScope').textContent = `Precios en ${currencyLabel} / ${unitLabel}${typeLabel} · ${aggregationLabel}`;
}

function renderCommoditySemaphore(rows) {
    const body = document.getElementById('commoditySemaphoreBody');
    const status = document.getElementById('commoditySemaphoreStatus');
    if (!body || !status) return;
    const context = commoditySeriesContext();
    if (commoditySource === 'local_mensual' && context.marketAll && commoditySelectedValues.length !== 1) {
        body.innerHTML = '';
        status.textContent = 'Seleccione una plaza/mercado para leer el semáforo sin mezclar referencias.';
        status.classList.add('is-visible');
        return;
    }
    const validRows = rows.filter(row => {
        const price = commodityNumber(row.precio_mediana);
        return Number.isFinite(price) && price > 0;
    });
    if (!validRows.length) { body.innerHTML = ''; status.textContent = 'No hay datos mensuales para los filtros seleccionados.'; status.classList.add('is-visible'); return; }
    const periods = [...new Set(validRows.map(row => row.periodo_ym || row.fecha).filter(Boolean))].sort().slice(-12);
    for (let index = 0; index < 12; index += 1) {
        const header = document.getElementById(`commoditySemaphoreMonth${index}`);
        if (header) header.textContent = periods[index] ? commodityPeriodLabel(periods[index]) : '—';
    }
    const groups = new Map();
    validRows.forEach(row => {
        const period = row.periodo_ym || row.fecha;
        if (!period || !periods.includes(period)) return;
        const key = context.marketMode ? row.mercado : (commoditySource === 'local_mensual' ? row.commodity : commoditySeriesKey(row));
        const group = groups.get(key) || { row, cells: new Map() };
        group.cells.set(period, row);
        groups.set(key, group);
    });
    const displayRows = [...groups.values()].map(group => ({ ...group, label: '' })).sort((a, b) => {
        const aLatest = periods.slice().reverse().map(period => a.cells.get(period)).find(Boolean);
        const bLatest = periods.slice().reverse().map(period => b.cells.get(period)).find(Boolean);
        return (commodityNumber(bLatest?.precio_mediana) || 0) - (commodityNumber(aLatest?.precio_mediana) || 0);
    });
    commodityUniqueSeriesLabels(displayRows, { marketMode: context.marketMode });
    const limitedRows = displayRows.slice(0, 10);
    status.textContent = displayRows.length > 10 ? 'Se muestran hasta 10 series. Use los filtros para acotar la matriz.' : '';
    status.classList.toggle('is-visible', displayRows.length > 10);
    body.innerHTML = limitedRows.map(item => {
        const latest = periods.slice().reverse().map(period => item.cells.get(period)).find(Boolean);
        const overallState = latest?.estado || 'Sin dato';
        const cells = periods.map(period => {
            const row = item.cells.get(period);
            const state = row?.estado || 'Sin dato';
            return `<td class="commodity-semaphore-cell"><span class="commodity-state ${commodityStateClass(state)}">${escapeHtml(state)}</span><small>${row ? escapeHtml(commodityPercent(row.variacion_mensual_pct)) : '–'}</small></td>`;
        });
        while (cells.length < 12) cells.push('<td class="commodity-semaphore-cell"><span class="commodity-state sin-dato">Sin dato</span><small>–</small></td>');
        return `<tr><td class="commodity-semaphore-series">${escapeHtml(item.label)}</td>${cells.join('')}<td><span class="commodity-state ${commodityStateClass(overallState)}">${escapeHtml(overallState)}</span></td></tr>`;
    }).join('');
}

function renderCommodityLatest(latestRows) {
    const body = document.getElementById('commodityLatestBody');
    const status = document.getElementById('commodityLatestStatus');
    if (!body || !status) return;
    if (!latestRows.length) { body.innerHTML = ''; status.textContent = 'No hay últimos precios para los filtros seleccionados.'; status.classList.add('is-visible'); return; }
    status.classList.remove('is-visible');
    body.innerHTML = [...latestRows].sort((a, b) => `${a.commodity}|${a.mercado}|${a.moneda}|${a.tipo_precio}`.localeCompare(`${b.commodity}|${b.mercado}|${b.moneda}|${b.tipo_precio}`)).map(row => {
        const state = row.estado || 'Sin dato';
        return `<tr><td>${escapeHtml(row.commodity)}</td><td>${escapeHtml(commoditySourceShort(row))}</td><td>${escapeHtml(commodityMarketLabel(row.mercado))}</td><td>${escapeHtml(row.moneda)}</td><td>${escapeHtml(row.unidad)}</td><td>${escapeHtml(row.tipo_precio)}</td><td>${escapeHtml(commodityPeriodLabel(commodityLatestDate(row)))}</td><td>${formatNumber(commodityLatestPrice(row))}</td><td>${formatNumber(commodityNumber(row.operaciones_ultimo_periodo ?? row.operaciones_ultimo_dia))}</td><td>${commodityPercent(row.variacion_mensual_pct ?? row.variacion_7d_pct)}</td><td>${commodityPercent(row.variacion_interanual_pct ?? row.variacion_30d_pct)}</td><td><span class="commodity-state ${commodityStateClass(state)}">${escapeHtml(state)}</span></td></tr>`;
    }).join('');
}

function updateCommodityChartHeadings() {
    const sourceConfig = COMMODITY_SOURCE_CONFIG[commoditySource] || COMMODITY_SOURCE_CONFIG.sio;
    const selectedCount = commoditySelectedValues.length;
    const marketAll = commodityMarketIsAll();
    const selectedCommodity = selectedCount === 1 ? commoditySelectedValues[0] : '';
    const selectedMarket = commoditySelectedMarket();
    const selectedMarketLabel = selectedMarket === 'TODOS' ? 'todas las plazas' : commodityMarketLabel(selectedMarket);
    const trendTitle = document.getElementById('commodityTrendTitle');
    const trendDesc = document.getElementById('commodityTrendDesc');
    const rankingTitle = document.getElementById('commodityRankingTitle');
    const rankingDesc = document.getElementById('commodityRankingDesc');
    const volumeTitle = document.getElementById('commodityVolumeTitle');
    const volumeDesc = document.getElementById('commodityVolumeDesc');
    const latestTitle = document.getElementById('commodityLatestTitle');
    const latestDesc = document.getElementById('commodityLatestDesc');
    const periodLabel = commodityFrequency === 'diaria' ? 'diario' : 'mensual';
    const gapLabel = commodityFrequency === 'diaria' ? 'Los días sin operaciones quedan como huecos.' : 'Cada punto resume el mes seleccionado.';
    const seriesTypeLabel = sourceConfig.monthlyOnly ? 'tipo de precio' : 'tipo de operación';
    if (sourceConfig.monthlyOnly) {
        const trendTitleValue = !selectedCount && !marketAll
            ? `Evolución mensual por commodity — ${selectedMarketLabel}`
            : selectedCommodity && marketAll
                ? `Evolución mensual de ${selectedCommodity} por plaza`
                : selectedCommodity && !marketAll
                    ? `Evolución mensual de ${selectedCommodity} — ${selectedMarketLabel}`
                    : `Evolución mensual por commodity — ${selectedMarketLabel}`;
        if (trendTitle) trendTitle.textContent = trendTitleValue;
        if (trendDesc) trendDesc.textContent = `Precio mediano en ARS / TN · ${marketAll ? 'comparación por plaza' : 'comparación por commodity'}. Cada punto resume el mes.`;
        if (rankingTitle) rankingTitle.textContent = selectedCommodity && marketAll ? 'Última mediana por plaza' : 'Última mediana por commodity';
        if (rankingDesc) rankingDesc.textContent = 'Último precio mensual disponible dentro de la selección';
        if (volumeTitle) volumeTitle.textContent = marketAll && selectedCommodity ? 'Observaciones por plaza' : 'Observaciones por commodity';
        if (volumeDesc) volumeDesc.textContent = 'Cantidad de registros mensuales con precio positivo';
    } else {
        if (trendTitle) trendTitle.textContent = `Precio mediano ${periodLabel}`;
        if (trendDesc) trendDesc.textContent = `Una serie por commodity, moneda, unidad y ${seriesTypeLabel}. ${gapLabel}`;
        if (rankingTitle) rankingTitle.textContent = selectedCount >= 2 ? 'Comparación de precios medianos recientes' : 'Precios medianos recientes';
        if (rankingDesc) rankingDesc.textContent = selectedCount >= 2 ? `Último precio por commodity y ${seriesTypeLabel}` : 'Precio por commodity en el último dato disponible';
        if (volumeTitle) volumeTitle.textContent = 'Volumen informado por commodity';
        if (volumeDesc) volumeDesc.textContent = 'Suma de toneladas del período visible';
    }
    if (sourceConfig.monthlyOnly) {
        if (latestTitle) latestTitle.textContent = 'Últimos precios mensuales por serie';
        if (latestDesc) latestDesc.textContent = 'Precio mediano del último mes disponible, con fuente y plaza visibles';
    } else {
        if (latestTitle) latestTitle.textContent = 'Últimos precios por serie';
        if (latestDesc) latestDesc.textContent = 'Precio mediano del último período disponible, con fuente y plaza visibles';
    }
}

function renderCommodityEmptyState() {
    Object.entries(commodityCharts).forEach(([key, chart]) => {
        if (chart) chart.destroy();
        commodityCharts[key] = null;
    });
    ['commodityPriceTrend', 'commodityRanking', 'commodityVolume'].forEach(id => { const canvas = document.getElementById(id); if (canvas) canvas.style.display = 'none'; });
    ['commodityPriceTrendStatus', 'commodityRankingStatus', 'commodityVolumeStatus', 'commoditySemaphoreStatus', 'commodityLatestStatus'].forEach(id => document.getElementById(id)?.classList.add('is-visible'));
    ['commoditySemaphoreBody', 'commodityLatestBody'].forEach(id => { const element = document.getElementById(id); if (element) element.innerHTML = ''; });
    ['commodityKpiUpdate', 'commodityKpiProducts', 'commodityKpiOperations', 'commodityKpiCurrency', 'commodityKpiMedian', 'commodityKpiMonthlyVariation', 'commodityKpiYoYVariation'].forEach(id => { const element = document.getElementById(id); if (element) element.textContent = '–'; });
    const notice = document.getElementById('commodityTrendNotice');
    if (notice) notice.textContent = '';
}

function updateCommodityDashboard() {
    const rows = getCommodityFilteredRows();
    const latestRows = getCommodityLatestRows();
    updateCommodityChartHeadings();
    const selectionIssue = commoditySelectionIssue(rows, latestRows);
    if (selectionIssue) {
        updateCommodityKpis([], []);
        document.getElementById('commodityKpiCurrency').textContent = 'Seleccionar';
        document.getElementById('commodityPriceScope').textContent = selectionIssue;
        setCommodityChart('trend', 'commodityPriceTrend', 'commodityPriceTrendStatus', null, selectionIssue);
        setCommodityChart('ranking', 'commodityRanking', 'commodityRankingStatus', null, selectionIssue);
        setCommodityChart('volume', 'commodityVolume', 'commodityVolumeStatus', null, selectionIssue);
        renderCommoditySemaphore([]);
        renderCommodityLatest([]);
        const notice = document.getElementById('commodityTrendNotice');
        if (notice) notice.textContent = selectionIssue;
        return;
    }
    updateCommodityKpis(rows, latestRows);
    renderCommodityTrend(rows);
    renderCommodityRanking(latestRows);
    renderCommodityVolume(rows);
    renderCommoditySemaphore(commodityData.semaforo.filter(commodityRowMatches));
    renderCommodityLatest(latestRows);
}

// ─── CSV Parsing ────────────────────────────────────────────────────────
function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    const rows = [];

    for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(';');
        if (cols.length < 7) continue;

        const rawSerie = normalizeText(cols[2]);
        // Skip duplicate TOMATE / PIMIENTO series
        if (rawSerie === 'TOMATE' || rawSerie === 'PIMIENTO') continue;

        // Normalize SERIE
        let serie = rawSerie;
        if (serie === 'FRUTA' || serie === 'FRUTAS') serie = 'FRUTAS';
        if (serie === 'HORTALIZA' || serie === 'HORTALIZAS') serie = 'HORTALIZAS';
        if (serie === 'SUBPRODUCTOS') serie = 'SUBPRODUCTOS';

        // Only keep FRUTAS and HORTALIZAS (skip SUBPRODUCTOS and others)
        if (serie !== 'FRUTAS' && serie !== 'HORTALIZAS') continue;

        // Parse date → month (1-indexed)
        const dateParts = cols[0].trim().split('/');
        if (dateParts.length < 3) continue;
        const day = parseInt(dateParts[0], 10);
        const month = parseInt(dateParts[1], 10); // 1-12
        const year = parseInt(dateParts[2], 10);
        if (isNaN(month) || month < 1 || month > 12) continue;

        // Parse weight (European format)
        const pesoStr = (cols[7] || '').trim().replace(/\./g, '').replace(',', '.');
        // The integrated CSV stores weights in kilograms; dashboard outputs are tonnes.
        const unidad = normalizeText(cols[8] || 'KG');
        const peso = parseFloat(pesoStr);
        if (isNaN(peso) || peso <= 0) continue;

        const mercado = normalizeLocation(cols[1]);
        const rawEspecie = normalizeText(cols[3]);
        const especie = normalizeEspecie(rawEspecie);
        const rawVariedad = normalizeText(cols[4]);
        const procedencia = normalizeLocation(cols[5]);

        let municipio = normalizeLocation(cols[6]);
        if (!municipio) municipio = procedencia;

        // Normalize variedad
        const variedad = normalizeVariedad(especie, rawVariedad);

        const origen = procedencia;
        rows.push({ day, month, year, mercado, serie, especie, variedad, municipio, peso, origen, unidad });
    }

    return rows;
}

// ─── Cascading Dynamic Filters ──────────────────────────────────────────
function wireFilters() {
    document.getElementById('filterYear').addEventListener('change', () => {
        selectedYear = document.getElementById('filterYear').value;
        updateHeaderSubtitle();
        updateSerieFilter();
        updateEspecieFilter();
        updateMunicipioFilter();
        applyFilters();
    });
    document.getElementById('filterOrigen').addEventListener('change', () => {
        const origen = document.getElementById('filterOrigen').value;
        const btnMunicipio = document.getElementById('filterMunicipio');
        const grpMunicipio = document.getElementById('filterGroupMunicipio');
        
        if (normalizeText(origen) === 'CORRIENTES') {
            grpMunicipio.style.display = 'flex';
            btnMunicipio.disabled = false;
        } else {
            grpMunicipio.style.display = 'none';
            btnMunicipio.value = 'TODOS';
            btnMunicipio.disabled = true;
        }

        updateSerieFilter();
        updateEspecieFilter();
        updateMunicipioFilter();
        applyFilters();
    });
    document.getElementById('filterDestino').addEventListener('change', () => {
        updateSerieFilter();
        updateEspecieFilter();
        updateMunicipioFilter();
        applyFilters();
    });
    document.getElementById('filterSerie').addEventListener('change', () => {
        updateEspecieFilter();
        updateMunicipioFilter();
        applyFilters();
    });
    document.getElementById('filterEspecie').addEventListener('change', () => {
        updateMunicipioFilter();
        applyFilters();
    });
    document.getElementById('filterMunicipio').addEventListener('change', () => {
        const selMunicipio = document.getElementById('filterMunicipio').value;
        if (selMunicipio !== 'TODOS') {
            document.getElementById('filterOrigen').value = 'Corrientes';
            updateSerieFilter();
        }
        updateEspecieFilter();
        applyFilters();
    });

    // Heatmap filter tabs
    const heatmapTabs = document.getElementById('heatmapTabs');
    if (heatmapTabs) {
        heatmapTabs.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                heatmapTabs.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                heatmapFilter = e.target.getAttribute('data-value');
                renderHeatmap();
            });
        });
    }
}

/** Populate all filters initially based on rawData */
function populateFilters() {
    populateYearFilter();
    updateOrigenFilter();
    updateDestinoFilter();
    updateSerieFilter();
    updateEspecieFilter();
    updateMunicipioFilter();
}

function unitLabel() { return 'tn'; }

function unitData() { return rawData; }

function populateYearFilter() {
    const sel = document.getElementById('filterYear');
    const years = getUniqueSortedValues(rawData, r => r.year, (a, b) => a - b);
    sel.innerHTML = '<option value="TODOS">Todos</option>';
    years.forEach(year => {
        const opt = document.createElement('option');
        opt.value = String(year);
        opt.textContent = String(year);
        sel.appendChild(opt);
    });
    if (years.map(String).includes(selectedYear)) sel.value = selectedYear;
    else {
        selectedYear = years.length ? String(years[years.length - 1]) : 'TODOS';
        sel.value = selectedYear;
    }
    updateHeaderSubtitle();
}

function updateOrigenFilter() {
    const sel = document.getElementById('filterOrigen');
    const currentOrigen = sel.value;
    const origenes = getUniqueSortedValues(unitData(), r => r.origen);
    populateSelect(sel, origenes, 'Todos', formatLabel);
    sel.value = origenes.includes(currentOrigen) ? currentOrigen : 'TODOS';
}

function updateDestinoFilter() {
    const sel = document.getElementById('filterDestino');
    const currentDestino = sel.value;
    const mercados = getUniqueSortedValues(unitData(), r => r.mercado);
    populateSelect(sel, mercados, 'Todos', formatLabel);
    sel.value = mercados.includes(currentDestino) ? currentDestino : 'TODOS';
}

function getUniqueSortedValues(records, valueGetter, compareFn = (a, b) => String(a).localeCompare(String(b), 'es')) {
    return [...new Set(records.map(valueGetter).filter(value => value !== undefined && value !== null && String(value).trim() !== ''))]
        .sort(compareFn);
}

function populateSelect(select, values, allLabel, formatValue = value => value) {
    select.innerHTML = `<option value="TODOS">${allLabel}</option>`;
    values.forEach(value => {
        const opt = document.createElement('option');
        opt.value = value;
        opt.textContent = formatValue(value);
        select.appendChild(opt);
    });
}

function updateHeaderSubtitle() {
    const yearLabel = selectedYear === 'TODOS' ? 'Todos los años' : selectedYear;
    document.getElementById('headerSubtitle').textContent = `Sistema de monitoreo de cantidades transadas y precios mayoristas · Provincia de Corrientes · ${yearLabel}`;
}

/** Update Serie filter based on selected Origen and Destino */
function updateSerieFilter() {
    const origen = document.getElementById('filterOrigen').value;
    const destino = document.getElementById('filterDestino').value;
    const currentSerie = document.getElementById('filterSerie').value;

    // Get available series for the selected origen/destino
    let subset = unitData();
    if (selectedYear !== 'TODOS') subset = subset.filter(r => String(r.year) === selectedYear);
    if (origen !== 'TODOS') subset = subset.filter(r => r.origen === origen);
    if (destino !== 'TODOS') subset = subset.filter(r => r.mercado === destino);
    const series = [...new Set(subset.map(r => r.serie))].sort();

    const sel = document.getElementById('filterSerie');
    sel.innerHTML = '<option value="TODOS">Todas</option>';
    series.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = formatLabel(s);
        sel.appendChild(opt);
    });

    // Restore previous selection if still available
    if (series.includes(currentSerie)) {
        sel.value = currentSerie;
    } else {
        sel.value = 'TODOS';
    }
}

/** Update Especie filter based on selected Origen, Destino, Serie and Municipio */
function updateEspecieFilter() {
    const origen = document.getElementById('filterOrigen').value;
    const destino = document.getElementById('filterDestino').value;
    const serie = document.getElementById('filterSerie').value;
    const municipio = document.getElementById('filterMunicipio') ? document.getElementById('filterMunicipio').value : 'TODOS';
    const currentEspecie = document.getElementById('filterEspecie').value;

    // Filter data
    let subset = unitData();
    if (selectedYear !== 'TODOS') subset = subset.filter(r => String(r.year) === selectedYear);
    if (origen !== 'TODOS') subset = subset.filter(r => r.origen === origen);
    if (destino !== 'TODOS') subset = subset.filter(r => r.mercado === destino);
    if (serie !== 'TODOS') subset = subset.filter(r => r.serie === serie);
    if (municipio !== 'TODOS') subset = subset.filter(r => r.municipio === municipio);

    const especies = [...new Set(subset.map(r => r.especie))].sort();

    const sel = document.getElementById('filterEspecie');
    sel.innerHTML = '<option value="TODOS">Todas (' + especies.length + ')</option>';
    especies.forEach(e => {
        const opt = document.createElement('option');
        opt.value = e;
        opt.textContent = formatLabel(e);
        sel.appendChild(opt);
    });

    // Restore previous selection if still available
    if (especies.includes(currentEspecie)) {
        sel.value = currentEspecie;
    } else {
        sel.value = 'TODOS';
    }
}

/** Update Municipio filter based on selected Origen, Destino, Serie and Especie */
function updateMunicipioFilter() {
    const origen = document.getElementById('filterOrigen').value;
    const destino = document.getElementById('filterDestino').value;
    const serie = document.getElementById('filterSerie').value;
    const especie = document.getElementById('filterEspecie') ? document.getElementById('filterEspecie').value : 'TODOS';
    const currentMunicipio = document.getElementById('filterMunicipio').value;

    // Filter data
    let subset = unitData();
    if (selectedYear !== 'TODOS') subset = subset.filter(r => String(r.year) === selectedYear);
    if (origen !== 'TODOS') subset = subset.filter(r => r.origen === origen);
    if (destino !== 'TODOS') subset = subset.filter(r => r.mercado === destino);
    if (serie !== 'TODOS') subset = subset.filter(r => r.serie === serie);
    if (especie !== 'TODOS') subset = subset.filter(r => r.especie === especie);

    const municipios = [...new Set(subset.map(r => r.municipio))].sort();

    const sel = document.getElementById('filterMunicipio');
    sel.innerHTML = '<option value="TODOS">Todos (' + municipios.length + ')</option>';
    municipios.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = formatLabel(m);
        sel.appendChild(opt);
    });

    // Restore previous selection if still available
    if (municipios.includes(currentMunicipio)) {
        sel.value = currentMunicipio;
    } else {
        sel.value = 'TODOS';
    }
}

function applyFilters() {
    const origen = document.getElementById('filterOrigen').value;
    const destino = document.getElementById('filterDestino').value;
    const serie = document.getElementById('filterSerie').value;
    const especie = document.getElementById('filterEspecie').value;
    const municipio = document.getElementById('filterMunicipio').value;

    filteredData = unitData().filter(r => {
        if (selectedYear !== 'TODOS' && String(r.year) !== selectedYear) return false;
        if (origen !== 'TODOS' && r.origen !== origen) return false;
        if (destino !== 'TODOS' && r.mercado !== destino) return false;
        if (serie !== 'TODOS' && r.serie !== serie) return false;
        if (especie !== 'TODOS' && r.especie !== especie) return false;
        if (municipio !== 'TODOS' && r.municipio !== municipio) return false;
        return true;
    });

    updateDashboard();
}

// ─── Dashboard update orchestrator ──────────────────────────────────────
function updateDashboard() {
    updateKPIs();
    renderMonthlyChart();
    renderMarketDonut();
    renderSeriesMonthly();
    renderTop10();
    renderHeatmap();
    renderMarketMonthly();
    renderSpeciesDonut();
    renderVarieties();
    renderSeasonalityTable();
}

// ─── KPI Calculations ──────────────────────────────────────────────────
function updateKPIs() {
    const total = sumPeso(filteredData);
    const frutas = sumPeso(filteredData.filter(r => r.serie === 'FRUTAS'));
    const hortalizas = sumPeso(filteredData.filter(r => r.serie === 'HORTALIZAS'));
    const bsas = sumPeso(filteredData.filter(r => r.mercado === 'Buenos Aires'));
    const ctes = sumPeso(filteredData.filter(r => r.mercado === 'Corrientes'));

    // Top especie
    const byEspecie = groupSum(filteredData, 'especie');
    const topEspecie = Object.entries(byEspecie).sort((a, b) => b[1] - a[1])[0];

    // Peak month
    const byMonth = monthlyTotals(filteredData);
    let peakIdx = 0, peakVal = 0;
    byMonth.forEach((v, i) => { if (v > peakVal) { peakVal = v; peakIdx = i; } });

    // Unique species
    const speciesSet = new Set(filteredData.map(r => r.especie));

    // Last date
    const latest = filteredData.reduce((best, r) => {
        if (!best || r.month > best.month || (r.month === best.month && r.day > best.day)) return r;
        return best;
    }, null);

    document.getElementById('totalProduction').textContent = formatWeight(total);
    document.getElementById('totalSpecies').textContent = speciesSet.size;
    document.getElementById('lastDate').textContent = latest ? `${MONTHS_FULL[latest.month - 1]} ${latest.year}` : '–';

    document.getElementById('kpiFrutas').textContent = formatNumber(frutas);
    document.getElementById('kpiHortalizas').textContent = formatNumber(hortalizas);
    document.getElementById('kpiBsas').textContent = formatNumber(bsas);
    document.getElementById('kpiCtes').textContent = formatNumber(ctes);
    ['kpiFrutasUnit', 'kpiHortalizasUnit', 'kpiBsasUnit', 'kpiCtesUnit'].forEach(id => {
        document.getElementById(id).textContent = unitLabel();
    });

    if (topEspecie) {
        document.getElementById('kpiTopEspecie').textContent = formatLabel(topEspecie[0]);
        document.getElementById('kpiTopEspecieTon').textContent = formatWeight(topEspecie[1]);
    } else {
        document.getElementById('kpiTopEspecie').textContent = '–';
        document.getElementById('kpiTopEspecieTon').textContent = 'Sin datos';
    }

    document.getElementById('kpiPeakMonth').textContent = filteredData.length ? MONTHS_FULL[peakIdx] : '–';
    document.getElementById('kpiPeakMonthTon').textContent = filteredData.length ? formatWeight(peakVal) : 'Sin datos';
}

// ─── Chart 1: Monthly Production (Stacked Area) ────────────────────────
function renderMonthlyChart() {
    const frutasSeries = aggregateQuantityData(filteredData.filter(r => r.serie === 'FRUTAS'), quantityFrequency);
    const hortSeries = aggregateQuantityData(filteredData.filter(r => r.serie === 'HORTALIZAS'), quantityFrequency);
    const labels = [...new Set([...frutasSeries, ...hortSeries].map(item => item.key))].sort();
    const frutaValues = new Map(frutasSeries.map(item => [item.key, item.value]));
    const hortValues = new Map(hortSeries.map(item => [item.key, item.value]));
    const displayLabels = labels.map(key => quantityFrequency === 'diaria' ? formatDate(key) : quantityFrequency === 'mensual' ? `${MONTHS_FULL[Number(key.slice(5, 7)) - 1]} ${key.slice(0, 4)}` : key);
    document.getElementById('quantityTimeSeriesTitle').textContent = `Producción ${quantityFrequency === 'diaria' ? 'diaria' : quantityFrequency === 'mensual' ? 'mensual' : 'anual'} total`;

    const cfg = {
        type: 'line',
        data: {
            labels: displayLabels,
            datasets: [
                {
                    label: 'Frutas',
                    data: labels.map(key => frutaValues.get(key) || 0),
                    borderColor: '#fb923c',
                    backgroundColor: 'rgba(251, 146, 60, 0.12)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointBackgroundColor: '#fb923c',
                    pointHoverRadius: 7,
                },
                {
                    label: 'Hortalizas',
                    data: labels.map(key => hortValues.get(key) || 0),
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52, 211, 153, 0.12)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointBackgroundColor: '#34d399',
                    pointHoverRadius: 7,
                }
            ]
        },
        options: {
            ...defaultLineOptions(),
            plugins: {
                ...defaultLineOptions().plugins,
                tooltip: tooltipConfig(),
            }
        }
    };

    charts.monthly = recreateChart('chartMonthly', charts.monthly, cfg);
}

// ─── Chart 2: Market Donut ──────────────────────────────────────────────
function renderMarketDonut() {
    const bsas = sumPeso(filteredData.filter(r => r.mercado === 'Buenos Aires'));
    const ctes = sumPeso(filteredData.filter(r => r.mercado === 'Corrientes'));

    const cfg = {
        type: 'doughnut',
        data: {
            labels: ['Buenos Aires', 'Corrientes'],
            datasets: [{
                data: [bsas, ctes],
                backgroundColor: ['rgba(96, 165, 250, 0.8)', 'rgba(167, 139, 250, 0.8)'],
                borderColor: ['#60a5fa', '#a78bfa'],
                borderWidth: 2,
                hoverOffset: 12,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '62%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: "'Inter'", size: 12, weight: 500 }, padding: 16, usePointStyle: true, pointStyleWidth: 12 }
                },
                tooltip: tooltipConfig(),
                datalabels: { display: false }
            }
        }
    };

    charts.market = recreateChart('chartMarket', charts.market, cfg);
}

// ─── Chart 3: Series Monthly ────────────────────────────────────────────
function renderSeriesMonthly() {
    const frutasMonthly = monthlyTotals(filteredData.filter(r => r.serie === 'FRUTAS'));
    const hortMonthly = monthlyTotals(filteredData.filter(r => r.serie === 'HORTALIZAS'));

    const cfg = {
        type: 'bar',
        data: {
            labels: MONTHS,
            datasets: [
                {
                    label: 'Frutas',
                    data: frutasMonthly,
                    backgroundColor: 'rgba(251, 146, 60, 0.7)',
                    borderColor: '#fb923c',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'Hortalizas',
                    data: hortMonthly,
                    backgroundColor: 'rgba(52, 211, 153, 0.7)',
                    borderColor: '#34d399',
                    borderWidth: 1,
                    borderRadius: 4,
                }
            ]
        },
        options: {
            ...defaultBarOptions(),
            plugins: {
                ...defaultBarOptions().plugins,
                tooltip: tooltipConfig(),
            }
        }
    };

    charts.seriesMonthly = recreateChart('chartSeriesMonthly', charts.seriesMonthly, cfg);
}

// ─── Chart 4: Top 10 Species ────────────────────────────────────────────
function renderTop10() {
    const byEspecie = groupSum(filteredData, 'especie');
    const sorted = Object.entries(byEspecie).sort((a, b) => b[1] - a[1]).slice(0, 10);

    const cfg = {
        type: 'bar',
        data: {
        labels: sorted.map(s => formatLabel(s[0])),
            datasets: [{
                label: unitLabel(),
                data: sorted.map(s => round2(s[1])),
                backgroundColor: sorted.map((_, i) => PALETTE[i % PALETTE.length] + 'cc'),
                borderColor: sorted.map((_, i) => PALETTE[i % PALETTE.length]),
                borderWidth: 1,
                borderRadius: 6,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNumber(v) }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#e2e8f0', font: { family: "'Inter'", size: 12, weight: 600 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: tooltipConfig(),
                datalabels: { display: false }
            }
        }
    };

    charts.top10 = recreateChart('chartTop10', charts.top10, cfg);
}

// ─── Chart 5: Heatmap ───────────────────────────────────────────────────
function renderHeatmap() {
    const container = document.getElementById('heatmapContainer');
    
    // Filtrar los datos localmente según la solapa seleccionada (Frutas, Hortalizas o Todas)
    let dataForHeatmap = filteredData;
    if (heatmapFilter !== 'TODOS') {
        dataForHeatmap = filteredData.filter(r => r.serie === heatmapFilter);
    }
    
    const byEspecie = groupSum(dataForHeatmap, 'especie');
    const sorted = Object.entries(byEspecie).sort((a, b) => b[1] - a[1]).slice(0, 20);
    const especies = sorted.map(s => s[0]);

    // Build matrix
    const matrix = {};
    let globalMax = 0;
    especies.forEach(esp => {
        matrix[esp] = new Array(12).fill(0);
        dataForHeatmap.filter(r => r.especie === esp).forEach(r => {
            matrix[esp][r.month - 1] += r.peso;
        });
        matrix[esp].forEach(v => { if (v > globalMax) globalMax = v; });
    });

    const cols = 13; // label + 12 months
    let html = `<div class="heatmap-grid" style="grid-template-columns: 140px repeat(12, 1fr);">`;

    // Header
    html += `<div class="heatmap-header-cell"></div>`;
    MONTHS.forEach(m => html += `<div class="heatmap-header-cell">${m}</div>`);

    // Rows
    especies.forEach(esp => {
        html += `<div class="heatmap-row-label" title="${esp}">${formatLabel(esp)}</div>`;
        for (let m = 0; m < 12; m++) {
            const val = matrix[esp][m];
            if (val === 0) {
                html += `<div class="heatmap-cell heatmap-cell-empty">-</div>`;
            } else {
                const intensity = Math.min(val / (globalMax * 0.5), 1);
                const h = 160 - intensity * 110; // green to orange
                const s = 60 + intensity * 20;
                const l = 15 + intensity * 30;
                    html += `<div class="heatmap-cell" style="background:hsla(${h},${s}%,${l}%,0.85);" title="${formatLabel(esp)} - ${MONTHS_FULL[m]}: ${formatWeight(round2(val))}">${formatNumber(round2(val))}</div>`;
            }
        }
    });

    html += '</div>';
    container.innerHTML = html;
}

// ─── Chart 6: Market Monthly (Stacked) ──────────────────────────────────
function renderMarketMonthly() {
    const bsasMonthly = monthlyTotals(filteredData.filter(r => r.mercado === 'Buenos Aires'));
    const ctesMonthly = monthlyTotals(filteredData.filter(r => r.mercado === 'Corrientes'));

    const cfg = {
        type: 'bar',
        data: {
            labels: MONTHS,
            datasets: [
                {
                    label: 'Buenos Aires',
                    data: bsasMonthly,
                    backgroundColor: 'rgba(96, 165, 250, 0.7)',
                    borderColor: '#60a5fa',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'Corrientes',
                    data: ctesMonthly,
                    backgroundColor: 'rgba(167, 139, 250, 0.7)',
                    borderColor: '#a78bfa',
                    borderWidth: 1,
                    borderRadius: 4,
                }
            ]
        },
        options: {
            ...defaultBarOptions(true),
            plugins: {
                ...defaultBarOptions(true).plugins,
                tooltip: tooltipConfig(),
            }
        }
    };

    charts.marketMonthly = recreateChart('chartMarketMonthly', charts.marketMonthly, cfg);
}

// ─── Chart 7: Species Donut ─────────────────────────────────────────────
function renderSpeciesDonut() {
    const byEspecie = groupSum(filteredData, 'especie');
    const sorted = Object.entries(byEspecie).sort((a, b) => b[1] - a[1]);
    const top8 = sorted.slice(0, 8);
    const restVal = sorted.slice(8).reduce((s, e) => s + e[1], 0);
    if (restVal > 0) top8.push(['Otros', restVal]);

    const cfg = {
        type: 'doughnut',
        data: {
            labels: top8.map(e => formatLabel(e[0])),
            datasets: [{
                data: top8.map(e => round2(e[1])),
                backgroundColor: top8.map((_, i) => PALETTE[i % PALETTE.length] + 'cc'),
                borderColor: top8.map((_, i) => PALETTE[i % PALETTE.length]),
                borderWidth: 1.5,
                hoverOffset: 10,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '55%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#94a3b8', font: { family: "'Inter'", size: 11, weight: 500 }, padding: 10, usePointStyle: true, pointStyleWidth: 10 }
                },
                tooltip: tooltipConfig(),
                datalabels: { display: false }
            }
        }
    };

    charts.speciesDonut = recreateChart('chartSpeciesDonut', charts.speciesDonut, cfg);
}

// ─── Chart 8: Top 15 Varieties ──────────────────────────────────────────
function renderVarieties() {
    const byVar = {};
    filteredData.forEach(r => {
        if (r.variedad === 'SIN VARIED') return;
        const key = r.especie + ' – ' + r.variedad;
        byVar[key] = (byVar[key] || 0) + r.peso;
    });
    const sorted = Object.entries(byVar).sort((a, b) => b[1] - a[1]).slice(0, 15);

    const cfg = {
        type: 'bar',
        data: {
            labels: sorted.map(s => formatLabel(s[0])),
            datasets: [{
                label: unitLabel(),
                data: sorted.map(s => round2(s[1])),
                backgroundColor: sorted.map((_, i) => PALETTE[i % PALETTE.length] + 'aa'),
                borderColor: sorted.map((_, i) => PALETTE[i % PALETTE.length]),
                borderWidth: 1,
                borderRadius: 5,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNumber(v) }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#e2e8f0', font: { family: "'Inter'", size: 11, weight: 500 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: tooltipConfig(),
                datalabels: { display: false }
            }
        }
    };

    charts.varieties = recreateChart('chartVarieties', charts.varieties, cfg);
}

// ─── Chart 9: Seasonality Table ─────────────────────────────────────────
function renderSeasonalityTable() {
    const container = document.getElementById('seasonalityTable');
    const byEspecie = groupSum(filteredData, 'especie');
    const sorted = Object.entries(byEspecie).sort((a, b) => b[1] - a[1]).slice(0, 25);
    const especies = sorted.map(s => s[0]);

    // Build matrix
    const matrix = {};
    especies.forEach(esp => {
        matrix[esp] = new Array(12).fill(0);
        filteredData.filter(r => r.especie === esp).forEach(r => {
            matrix[esp][r.month - 1] += r.peso;
        });
    });

    let html = `<table class="seasonality-table"><thead><tr><th>Especie</th>`;
    MONTHS.forEach(m => html += `<th>${m}</th>`);
    html += `<th class="total-col">Total</th></tr></thead><tbody>`;

    especies.forEach(esp => {
        const vals = matrix[esp];
        const total = vals.reduce((s, v) => s + v, 0);
        const maxVal = Math.max(...vals);
        html += `<tr><td>${formatLabel(esp)}</td>`;
        for (let m = 0; m < 12; m++) {
            const v = vals[m];
            const pct = maxVal > 0 ? (v / maxVal) * 100 : 0;
            let cls = '';
            if (v === 0) cls = 'season-low';
            else if (v === maxVal) cls = 'season-peak';
            else if (v > maxVal * 0.3) cls = 'season-active';
            else cls = 'season-low';

            html += `<td class="${cls}">`;
            if (v > 0) {
                html += `${formatNumber(round2(v))}<br><span class="season-bar" style="width:${Math.max(pct, 5)}%"></span>`;
            } else {
                html += `-`;
            }
            html += `</td>`;
        }
        html += `<td class="total-col">${formatNumber(round2(total))}</td></tr>`;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// ─── Helpers ────────────────────────────────────────────────────────────
function isInvalidSpreadsheetValue(value) {
    if (value === null || value === undefined) return true;
    const text = String(value).trim().toUpperCase();
    return !text || ['#REF!', '#N/A', '#VALUE!', '#DIV/0!', '#NAME?', '#NULL!', '#NUM!', 'NAN', 'UNDEFINED'].includes(text);
}

function cleanSpreadsheetErrors(value) {
    if (isInvalidSpreadsheetValue(value)) {
        if (value !== null && value !== undefined && String(value).trim()) spreadsheetInvalidCount++;
        return '';
    }
    return String(value).replace(/\s+/g, ' ').trim();
}

function normalizeCategoryValue(value) {
    const cleaned = cleanSpreadsheetErrors(value);
    return cleaned ? formatLabel(cleaned) : '';
}

function normalizeText(value) {
    return String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[.,;:_/\\()[\]{}'"-]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .toUpperCase();
}

function makeLocationKey(value) {
    return String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLocaleLowerCase('es-AR')
        .replace(/[^\p{L}\p{N}]+/gu, '')
        .toUpperCase();
}

function normalizeLocation(value) {
    const key = makeLocationKey(value);
    return LOCATION_EQUIVALENCES[key] || formatLabel(value);
}

function formatLabel(value) {
    if (value === undefined || value === null) return '';
    const words = String(value)
        .replace(/\s+/g, ' ')
        .trim()
        .toLocaleLowerCase('es-AR')
        .split(/(\s+|[-'])/);
    let firstWord = true;
    return words.map(word => {
        if (!word || /^\s+$/.test(word) || word === '-' || word === "'") return word;
        const lowerCaseConnector = /^(a|al|de|del|la|las|los|y|e|da|do)$/i.test(word);
        if (!firstWord && lowerCaseConnector) return word;
        firstWord = false;
        return word.charAt(0).toLocaleUpperCase('es-AR') + word.slice(1);
    }).join('');
}

function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '–';
    return number.toLocaleString('es-AR', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 1
    });
}

function formatWeight(value) {
    return `${formatNumber(value)} ${unitLabel()}`;
}

function sumPeso(arr) { return arr.reduce((s, r) => s + r.peso, 0); }

function groupSum(arr, key) {
    const map = {};
    arr.forEach(r => { map[r[key]] = (map[r[key]] || 0) + r.peso; });
    return map;
}

function monthlyTotals(arr) {
    const totals = new Array(12).fill(0);
    arr.forEach(r => { totals[r.month - 1] += r.peso; });
    return totals.map(v => round2(v));
}

function round2(n) { return Math.round(n * 100) / 100; }

function recreateChart(canvasId, existingChart, config) {
    if (existingChart) existingChart.destroy();
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, config);
}

function tooltipConfig() {
    return {
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        borderColor: 'rgba(52, 211, 153, 0.3)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        titleFont: { family: "'Inter'", size: 13, weight: 600 },
        bodyFont: { family: "'Inter'", size: 12 },
        callbacks: {
            label: function (ctx) {
                const val = ctx.parsed.y !== undefined ? ctx.parsed.y : ctx.parsed;
                return ` ${formatLabel(ctx.dataset.label || ctx.label)}: ${formatWeight(typeof val === 'object' ? ctx.raw : val)}`;
            }
        }
    };
}

function defaultLineOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        scales: {
            x: {
                grid: { color: 'rgba(255,255,255,0.04)' },
                ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 12, weight: 500 } }
            },
            y: {
                grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNumber(v) }
            }
        },
        plugins: {
            legend: {
                position: 'top',
                labels: { color: '#94a3b8', font: { family: "'Inter'", size: 12, weight: 500 }, padding: 16, usePointStyle: true, pointStyleWidth: 12 }
            },
            datalabels: { display: false }
        }
    };
}

function defaultBarOptions(stacked) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                stacked: !!stacked,
                grid: { color: 'rgba(255,255,255,0.04)' },
                ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 12, weight: 500 } }
            },
            y: {
                stacked: !!stacked,
                grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNumber(v) }
            }
        },
        plugins: {
            legend: {
                position: 'top',
                labels: { color: '#94a3b8', font: { family: "'Inter'", size: 12, weight: 500 }, padding: 16, usePointStyle: true, pointStyleWidth: 12 }
            },
            datalabels: { display: false }
        }
    };
}

// ─── Loading ────────────────────────────────────────────────────────────
function showLoading() {
    if (document.getElementById('loadingOverlay')) return;
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text">Cargando datos de producción…</div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) {
        el.classList.add('fade-out');
        setTimeout(() => el.remove(), 500);
    }
}
