/* ======================================================================
   Dashboard Agrícola – Corrientes 2025  |  app.js
   ====================================================================== */

// ─── Constants ──────────────────────────────────────────────────────────
const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
const MONTHS_FULL = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const CSV_PATH = 'REGISTRO 2025 INTEGRADO.csv';
const PRICE_CSV_PATH = 'PRECIOS_MAYORISTAS_INTEGRADO.csv';
const PRICE_CSV_FALLBACK_PATH = 'PRECIOS_MAYORISTAS_2026_INTEGRADO.csv';

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
let heatmapFilter = 'TODOS';
let selectedYear = '2025';
const selectedUnit = 'TN';
let quantityFrequency = 'mensual';
let priceFrequency = 'mensual';

// ─── Boot ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);

async function init() {
    showLoading();
    wireModuleTabs();
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
    data.forEach(row => { const key = createTimeKey(row.fecha || row, frequency); if (key && isValidPrice(row.precioPromedio)) { const values = groups.get(key) || []; values.push(row.precioPromedio); groups.set(key, values); } });
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
    const dateSplit = filterFutureDates(rawPriceData);
    futurePriceData = dateSplit.futureRows;
    priceData = dateSplit.validRows.filter(row => isValidPrice(row.precioPromedio));
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
        if (!isValidPrice(row.precioPromedio)) return;
        const key = groupFields.map(field => String(row[field] || (field === 'variedad' ? 'Sin especificar' : 'Sin procedencia informada'))).join('|');
        const label = groupFields.length === 1 ? (String(row[groupFields[0]] || '').trim() || (groupFields[0] === 'variedad' ? 'Sin especificar' : 'Sin procedencia informada')) : getProductLabel(row);
        const group = grouped.get(key) || { label, rows: [] };
        group.rows.push(row);
        grouped.set(key, group);
    });
    const ranking = [...grouped.values()].map(group => {
        const rows = group.rows;
        if (rows.length < 5) return null;
        const byPeriod = new Map();
        rows.forEach(row => { const period = createTimeKey(row.fecha || row, frequency); if (period) { const values = byPeriod.get(period) || []; values.push(row.precioPromedio); byPeriod.set(period, values); } });
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
    if (frequency !== 'diaria') return { groupFields: ['especie', 'variedad'], singleSeries: false };
    const species = getMultiSelectValues('priceFilterEspecie');
    const variety = getMultiSelectValues('priceFilterVariedad');
    const provenance = getMultiSelectValues('priceFilterProcedencia');
    if (!species.length || species.includes('TODOS') || species.length !== 1) return { groupFields: [], singleSeries: false };
    if (!variety.length || variety.includes('TODOS') || variety.length !== 1) return { groupFields: ['variedad'], singleSeries: false };
    if (!provenance.length || provenance.includes('TODOS') || provenance.length !== 1) return { groupFields: ['procedencia'], singleSeries: false };
    return { groupFields: [], singleSeries: true };
}

function processPriceData(rows, sourcePath = PRICE_CSV_PATH) {
    return rows.map(row => {
        const dateText = String(row.fecha || '').trim();
        const date = /^\d{4}-\d{2}-\d{2}$/.test(dateText) ? dateText : '';
        const monthNumber = date ? Number(date.slice(5, 7)) : MONTHS_FULL.findIndex(month => normalizeText(month) === normalizeText(row.mes)) + 1;
        const average = parsePriceNumber(row.precio_promedio) ?? parsePriceNumber(row.precio);
        const minimum = parsePriceNumber(row.precio_min);
        const maximum = parsePriceNumber(row.precio_max);
        const rubroRaw = normalizeText(row.rubro);
        const rubro = rubroRaw.includes('HORTAL') ? 'Hortalizas' : rubroRaw.includes('FRUT') ? 'Frutas' : rubroRaw;
        return {
            fecha: date, year: date ? Number(date.slice(0, 4)) : Number(row.año || row.ano) || null, month: monthNumber,
            mes: monthNumber >= 1 && monthNumber <= 12 ? MONTHS_FULL[monthNumber - 1] : normalizeText(row.mes),
            rubro, especie: formatLabel(row.especie), variedad: formatLabel(row.variedad),
            mercado: formatLabel(row.mercado), procedencia: formatLabel(row.procedencia), unidad: formatLabel(row.unidad) || 'Sin especificar', precio: parsePriceNumber(row.precio),
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

function matchesMultiSelect(value, selectedValues) {
    if (!Array.isArray(selectedValues) || !selectedValues.length || selectedValues.includes('TODOS')) return true;
    return selectedValues.includes(value || 'Sin especificar');
}

function updateMultiSelectSummary(selectId) {
    const summary = document.getElementById(`${selectId}Summary`);
    if (!summary) return;
    const values = getMultiSelectValues(selectId);
    summary.textContent = !values.length || values.includes('TODOS') ? (selectId.includes('Mercado') ? 'Todos' : 'Todas') : `${values.length} seleccionadas`;
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
    const selectedSpecies = getMultiSelectValues('priceFilterEspecie');
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
        const current = select?.multiple ? getMultiSelectValues(id) : select.value;
        const unique = [...new Set(values.filter(value => String(value || '').trim()))];
        if (id === 'priceFilterMes') unique.sort((a, b) => monthNumber(a) - monthNumber(b));
        else unique.sort((a, b) => String(a).localeCompare(String(b), 'es'));
        populateSelect(select, unique, allLabel, value => value);
        if (select.multiple) {
            const kept = current.filter(value => value === 'TODOS' || unique.includes(value));
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

function getFilteredPriceData() {
    const species = getMultiSelectValues('priceFilterEspecie');
    const varieties = getMultiSelectValues('priceFilterVariedad');
    const markets = getMultiSelectValues('priceFilterMercado');
    const provenances = getMultiSelectValues('priceFilterProcedencia');
    const filters = {
        rubro: document.getElementById('priceFilterRubro').value,
        year: document.getElementById('priceFilterYear').value,
        mes: document.getElementById('priceFilterMes').value,
        especie: species,
        variedad: varieties,
        mercado: markets,
        procedencia: provenances,
        unidad: document.getElementById('priceFilterUnidad').value
    };
    const selectedYear = filters.year === 'TODOS' ? null : Number(filters.year);
    return validPriceData.filter(row =>
        (selectedYear === null || Number(row.year) === selectedYear)
        && Object.entries(filters).every(([key, value]) => key === 'year' || (Array.isArray(value) ? matchesMultiSelect(row[key], value) : value === 'TODOS' || row[key] === value))
    );
}

function applyPriceFilters() {
    filteredPriceData = getFilteredPriceData();
    return filteredPriceData;
}

function updatePriceDashboard() {
    const selectedYear = document.getElementById('priceFilterYear')?.value || 'TODOS';
    const beforeYearFilterCount = validPriceData.length;
    const afterYearFilterCount = selectedYear === 'TODOS'
        ? beforeYearFilterCount
        : validPriceData.filter(row => Number(row.year) === Number(selectedYear)).length;
    applyPriceFilters();
    const currentPriceFilters = ['priceFilterYear', 'priceFilterRubro', 'priceFilterMes', 'priceFilterEspecie', 'priceFilterVariedad', 'priceFilterMercado', 'priceFilterProcedencia', 'priceFilterUnidad']
        .reduce((filters, id) => { filters[id] = document.getElementById(id)?.value || 'TODOS'; return filters; }, {});
    console.log('Filtros de precios aplicados:', currentPriceFilters);
    console.log('Año de precios seleccionado:', selectedYear);
    console.log('Registros antes de filtrar por año:', beforeYearFilterCount);
    console.log('Registros después de filtrar por año:', afterYearFilterCount);
    console.log('Registros luego del filtro precio:', filteredPriceData.length);
    const hasData = filteredPriceData.length > 0;
    setPriceStatus(hasData ? '' : (priceData.length ? 'No hay precios disponibles para la combinación seleccionada. Revisá año, mercado, especie o mes.' : 'No se pudo cargar la base de precios mayoristas.'), !hasData);
    updatePriceKPIs();
    renderPriceCharts();
}

function getPriceAnalysisLevel(filters) {
    const species = Array.isArray(filters?.especie) ? filters.especie : [filters?.especie || 'TODOS'];
    const varieties = Array.isArray(filters?.variedad) ? filters.variedad : [filters?.variedad || 'TODOS'];
    const provenances = Array.isArray(filters?.procedencia) ? filters.procedencia : [filters?.procedencia || 'TODOS'];
    if (!species.length || species.includes('TODOS') || species.length !== 1) return 'general';
    if (!varieties.length || varieties.includes('TODOS') || varieties.length !== 1) return 'species_detail';
    if (!provenances.length || provenances.includes('TODOS') || provenances.length !== 1) return 'variety_detail';
    return 'single_series';
}

function getAvailablePriceVisualizations(filteredData, filters, frequency) {
    const level = getPriceAnalysisLevel(filters);
    const speciesCount = new Set(filteredData.map(row => row.especie).filter(Boolean)).size;
    const varietyCount = new Set(filteredData.map(row => row.variedad || 'Sin especificar')).size;
    const provenanceCount = new Set(filteredData.map(row => row.procedencia || 'Sin procedencia informada')).size;
    const marketCount = new Set(filteredData.map(row => row.mercado).filter(Boolean)).size;
    const periods = aggregatePriceData(filteredData, frequency).length;
    const isDaily = frequency === 'diaria';
    return {
        level,
        showSpeciesRanking: level === 'general' && speciesCount >= 2,
        showVarietyRanking: level === 'species_detail' && varietyCount >= 2,
        showProcedenciaComparison: level === 'variety_detail' && provenanceCount >= 2,
        showMarketComparison: marketCount >= 2,
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
    const values = filteredPriceData.map(row => row.precioPromedio).filter(isValidPrice);
    const average = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    const maximum = filteredPriceData.reduce((best, row) => { const value = isValidPrice(row.precioMax) ? row.precioMax : row.precioPromedio; return isValidPrice(value) && (!best || value > best.value) ? { value, row } : best; }, null);
    const minimum = filteredPriceData.reduce((best, row) => { const value = isValidPrice(row.precioMin) ? row.precioMin : row.precioPromedio; return isValidPrice(value) && (!best || value < best.value) ? { value, row } : best; }, null);
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

function preparePriceEvolutionData(data, frequency) {
    const series = aggregatePriceData(data, frequency).filter(item => isValidPrice(item.value));
    return { labels: series.map(item => formatPeriodLabel(item.key, frequency)), values: series.map(item => item.value), meta: series };
}

function preparePriceRankingData(data, analysisLevel = 'general') {
    const field = analysisLevel === 'species_detail' ? 'variedad' : analysisLevel === 'variety_detail' ? 'procedencia' : 'especie';
    const grouped = new Map();
    data.filter(row => isValidPrice(row.precioPromedio)).forEach(row => {
        const label = field === 'variedad'
            ? (row.variedad || 'Sin especificar')
            : field === 'procedencia'
                ? (row.procedencia || 'Sin procedencia informada')
                : row.especie || 'Sin especificar';
        const item = grouped.get(label) || { label, values: [], observations: 0, periods: [] };
        item.values.push(row.precioPromedio);
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

function preparePriceVariationData(data, frequency) {
    if (frequency === 'diaria') return { labels: [], values: [], meta: [] };
    const series = calculatePeriodVariation(aggregatePriceData(data, frequency), frequency).filter(item => Number.isFinite(item.variation));
    return { labels: series.map(item => formatPeriodLabel(item.key, frequency)), values: series.map(item => item.variation), meta: series };
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
    data.filter(row => isValidPrice(row.precioPromedio) && row.mercado).forEach(row => {
        const values = groups.get(row.mercado) || [];
        values.push(row.precioPromedio);
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
    if (variation < 0) return { key: 'decrease', label: 'Baja' };
    if (variation <= 5) return { key: 'stable', label: 'Estable' };
    if (variation <= 15) return { key: 'moderate', label: 'Suba moderada' };
    return { key: 'strong', label: 'Suba fuerte' };
}

function buildPriceTrafficLightTable(data, frequency) {
    const groups = new Map();
    data.filter(row => isValidPrice(row.precioPromedio)).forEach(row => {
        const fields = ['mercado', 'rubro', 'especie', 'variedad', 'procedencia', 'unidad'];
        const key = fields.map(field => row[field] || (field === 'variedad' ? 'Sin especificar' : field === 'procedencia' ? 'Sin procedencia informada' : 'Sin informar')).join('|');
        const group = groups.get(key) || { row, observations: 0, periods: new Map() };
        group.observations++;
        const period = createTimeKey(row.fecha || row, frequency);
        if (period) { const values = group.periods.get(period) || []; values.push(row.precioPromedio); group.periods.set(period, values); }
        groups.set(key, group);
    });
    return [...groups.values()].map(group => {
        const periods = [...group.periods.entries()].sort(([a], [b]) => a.localeCompare(b));
        if (periods.length < 2) return null;
        const first = periods[0][1].reduce((sum, value) => sum + value, 0) / periods[0][1].length;
        const last = periods.at(-1)[1].reduce((sum, value) => sum + value, 0) / periods.at(-1)[1].length;
        const variation = (last / first - 1) * 100;
        return isValidPrice(first) && isValidPrice(last) && Number.isFinite(variation) ? { ...group.row, first, last, variation, firstPeriod: periods[0][0], lastPeriod: periods.at(-1)[0], observations: group.observations, status: getTrafficLightStatus(variation) } : null;
    }).filter(Boolean).sort((a, b) => Math.abs(b.variation) - Math.abs(a.variation)).slice(0, 20);
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}

function renderPriceTrafficLightTable(data, frequency) {
    const body = document.getElementById('priceTrafficLightBody');
    const status = document.getElementById('priceTrafficLightStatus');
    if (!body || !status) return;
    const rows = buildPriceTrafficLightTable(data, frequency);
    body.innerHTML = rows.map(row => `<tr><td><span class="traffic-light ${row.status.key}">${row.status.label}</span></td><td>${escapeHtml(row.mercado)}</td><td>${escapeHtml(row.rubro)}</td><td>${escapeHtml(row.especie)}</td><td>${escapeHtml(row.variedad || 'Sin especificar')}</td><td>${escapeHtml(row.procedencia || 'Sin procedencia informada')}</td><td>${formatCurrency(row.first)}</td><td>${formatCurrency(row.last)}</td><td>${formatPercent(row.variation)}</td><td>${escapeHtml(formatPeriodLabel(row.firstPeriod, frequency))}</td><td>${escapeHtml(formatPeriodLabel(row.lastPeriod, frequency))}</td><td>${row.observations}</td></tr>`).join('');
    status.textContent = rows.length ? '' : 'No hay datos suficientes para calcular esta visualización con los filtros seleccionados.';
    status.classList.toggle('is-visible', !rows.length);
}

function renderPriceCharts() {
    destroyAllPriceCharts();
    const filters = {
        especie: getMultiSelectValues('priceFilterEspecie'),
        variedad: getMultiSelectValues('priceFilterVariedad'),
        procedencia: getMultiSelectValues('priceFilterProcedencia'),
        mercado: getMultiSelectValues('priceFilterMercado')
    };
    const visualizations = getAvailablePriceVisualizations(filteredPriceData, filters, priceFrequency);
    const evolution = preparePriceEvolutionData(filteredPriceData, priceFrequency);
    const ranking = preparePriceRankingData(filteredPriceData, visualizations.level);
    const variation = preparePriceVariationData(filteredPriceData, priceFrequency);
    const increases = preparePriceIncreaseRankingData(filteredPriceData, priceFrequency);
    const decreases = preparePriceDecreaseRankingData(filteredPriceData, priceFrequency);
    const marketComparison = preparePriceMarketComparisonData(filteredPriceData);
    const insufficient = 'No hay datos suficientes para calcular esta visualización con los filtros seleccionados.';
    const comparable = 'No hay suficientes categorías comparables para construir este ranking.';
    const noComparable = 'La selección actual representa una única serie. La variación acumulada se muestra en los KPIs.';

    document.getElementById('priceTimeSeriesTitle').textContent = `Evolución ${priceFrequency} del precio promedio`;
    document.getElementById('priceDailyMethodNote').hidden = priceFrequency !== 'diaria';
    if (evolution.values.length) {
        priceCharts.evolution = createPriceChart('evolution', 'priceChartMonthly', { type: 'line', data: { labels: evolution.labels, datasets: [{ label: `Precio promedio ${priceFrequency}`, data: evolution.values, borderColor: '#34d399', backgroundColor: 'rgba(52,211,153,.16)', fill: true, tension: .3, pointRadius: priceFrequency === 'diaria' ? 2 : 4 }] }, options: priceChartOptions('Precio promedio') });
    } else showChartMessage('priceChartMonthly', insufficient);

    const rankingTitle = visualizations.level === 'species_detail' ? 'Ranking de variedades por precio promedio' : visualizations.level === 'variety_detail' ? 'Ranking por procedencia de precio promedio' : 'Ranking de especies por precio promedio';
    const rankingDescription = visualizations.level === 'species_detail' ? 'Variedades con mayor precio promedio dentro de la especie seleccionada' : visualizations.level === 'variety_detail' ? 'Procedencias con mayor precio promedio dentro de la variedad seleccionada' : 'Especies con mayor precio promedio dentro del período seleccionado';
    document.getElementById('priceRankingTitle').textContent = rankingTitle;
    document.getElementById('priceRankingDesc').textContent = rankingDescription;
    document.getElementById('priceRankingCard').hidden = !(visualizations.showSpeciesRanking || visualizations.showVarietyRanking || visualizations.showProcedenciaComparison);
    if (!document.getElementById('priceRankingCard').hidden && ranking.labels.length >= 2) {
        const base = priceChartOptions('Precio promedio', true);
        base.scales.x.beginAtZero = true;
        base.scales.x.suggestedMax = Math.max(...ranking.values) * 1.1;
        base.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => { const item = ranking.meta[context.dataIndex]; return [`Precio promedio: ${formatCurrency(item.average)}`, `Observaciones: ${item.observations}`, `Período: ${formatPeriodLabel(item.firstPeriod, priceFrequency)} - ${formatPeriodLabel(item.lastPeriod, priceFrequency)}`]; } } };
        priceCharts.ranking = createPriceChart('ranking', 'priceChartRanking', { type: 'bar', data: { labels: ranking.labels, datasets: [{ label: 'Precio promedio', data: ranking.values, backgroundColor: PALETTE }] }, options: base });
    } else if (!document.getElementById('priceRankingCard').hidden) showChartMessage('priceChartRanking', ranking.labels.length ? comparable : insufficient);
    document.getElementById('priceVariationCard').hidden = !visualizations.showVariationBars;
    if (visualizations.showVariationBars && variation.values.length) {
        const variationOptions = priceChartOptions('Variación %');
        variationOptions.scales.y.ticks.callback = value => formatPercent(value);
        priceCharts.variation = createPriceChart('variation', 'priceChartVariation', { type: 'bar', data: { labels: variation.labels, datasets: [{ label: `Variación ${priceFrequency}`, data: variation.values, backgroundColor: variation.values.map(value => value >= 0 ? '#fb923c' : '#60a5fa') }] }, options: variationOptions });
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
        const options = priceChartOptions('Precio promedio', true);
        options.scales.x.beginAtZero = true;
        options.plugins.tooltip = { ...tooltipConfig(), callbacks: { label: context => { const item = marketComparison.meta[context.dataIndex]; return [`Precio promedio: ${formatCurrency(item.average)}`, `Observaciones: ${item.observations}`]; } } };
        priceCharts.marketComparison = createPriceChart('marketComparison', 'priceChartMarket', { type: 'bar', data: { labels: marketComparison.labels, datasets: [{ label: 'Precio promedio', data: marketComparison.values, backgroundColor: ['#34d399', '#60a5fa'] }] }, options });
    } else if (!marketCard.hidden) showChartMessage('priceChartMarket', 'La selección actual contiene un solo mercado.');
    const dailyDescription = priceFrequency === 'diaria' ? 'Variación acumulada entre primera y última fecha disponible' : 'Productos con mayor cambio entre el primer y último período';
    document.getElementById('priceIncreaseDesc').textContent = dailyDescription;
    document.getElementById('priceDecreaseDesc').textContent = dailyDescription;
    console.log('Frecuencia precios aplicada:', priceFrequency);
    console.log('Agrupación variación diaria:', increases.groupFields || decreases.groupFields || []);
    console.log('Series comparables para variación:', Math.max(increases.meta.length, decreases.meta.length));
    console.log('Subas mostradas:', increases.labels.length);
    console.log('Bajas mostradas:', decreases.labels.length);
    renderPriceTrafficLightTable(filteredPriceData, priceFrequency);
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
    document.getElementById('headerSubtitle').textContent = `Provincia de Corrientes · ${yearLabel}`;
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
