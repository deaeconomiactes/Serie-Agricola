/* ======================================================================
   Dashboard Agrícola – Corrientes 2025  |  app.js
   ====================================================================== */

// ─── Constants ──────────────────────────────────────────────────────────
const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
const MONTHS_FULL = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const CSV_PATH = 'REGISTRO 2025.csv';

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
    if (variedad === 'SIN VARIED' || variedad === 'SIN VARIEDAD' || variedad === especie) {
        return 'SIN VARIEDAD';
    }
    return variedad;
}

// ─── Chart instances ────────────────────────────────────────────────────
let charts = {};

// ─── State ──────────────────────────────────────────────────────────────
let rawData = [];
let filteredData = [];
let heatmapFilter = 'TODOS';

// ─── Boot ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);

async function init() {
    showLoading();
    try {
        const text = await fetch(CSV_PATH).then(r => r.text());
        rawData = parseCSV(text);
        populateFilters();
        applyFilters();
        wireFilters();
    } catch (e) {
        console.error('Error loading CSV:', e);
    }
    hideLoading();
}

// ─── CSV Parsing ────────────────────────────────────────────────────────
function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    const rows = [];

    for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(';');
        if (cols.length < 7) continue;

        const rawSerie = (cols[2] || '').trim().toUpperCase();
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
        const peso = parseFloat(pesoStr);
        if (isNaN(peso) || peso <= 0) continue;

        const mercado = (cols[1] || '').trim().toUpperCase();
        const rawEspecie = (cols[3] || '').trim().toUpperCase();
        const especie = normalizeEspecie(rawEspecie);
        const rawVariedad = (cols[4] || '').trim().toUpperCase();
        const procedencia = (cols[5] || '').trim().toUpperCase();

        let municipio = (cols[6] || '').trim().toUpperCase();
        if (!municipio) municipio = procedencia;

        // Normalize variedad
        const variedad = normalizeVariedad(especie, rawVariedad);

        const origen = procedencia;
        rows.push({ day, month, year, mercado, serie, especie, variedad, municipio, peso, origen });
    }

    return rows;
}

// ─── Cascading Dynamic Filters ──────────────────────────────────────────
function wireFilters() {
    document.getElementById('filterOrigen').addEventListener('change', () => {
        const origen = document.getElementById('filterOrigen').value;
        const btnMunicipio = document.getElementById('filterMunicipio');
        const grpMunicipio = document.getElementById('filterGroupMunicipio');
        
        if (origen === 'CORRIentes' || origen === 'CORRIENTES') {
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
            document.getElementById('filterOrigen').value = 'CORRIENTES';
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
    populateOrigenFilter();
    populateDestinoFilter();
    updateSerieFilter();
    updateEspecieFilter();
    updateMunicipioFilter();
}

function populateOrigenFilter() {
    const sel = document.getElementById('filterOrigen');
    const origenes = [...new Set(rawData.map(r => r.origen))].sort();
    sel.innerHTML = '<option value="TODOS">Todos</option>';
    origenes.forEach(o => {
        const opt = document.createElement('option');
        opt.value = o;
        opt.textContent = capitalizeWords(o);
        sel.appendChild(opt);
    });
}

function populateDestinoFilter() {
    const sel = document.getElementById('filterDestino');
    const mercados = [...new Set(rawData.map(r => r.mercado))].sort();
    sel.innerHTML = '<option value="TODOS">Todos</option>';
    mercados.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m === 'BSAS' ? 'Buenos Aires' : capitalize(m);
        sel.appendChild(opt);
    });
}

/** Update Serie filter based on selected Origen and Destino */
function updateSerieFilter() {
    const origen = document.getElementById('filterOrigen').value;
    const destino = document.getElementById('filterDestino').value;
    const currentSerie = document.getElementById('filterSerie').value;

    // Get available series for the selected origen/destino
    let subset = rawData;
    if (origen !== 'TODOS') subset = subset.filter(r => r.origen === origen);
    if (destino !== 'TODOS') subset = subset.filter(r => r.mercado === destino);
    const series = [...new Set(subset.map(r => r.serie))].sort();

    const sel = document.getElementById('filterSerie');
    sel.innerHTML = '<option value="TODOS">Todas</option>';
    series.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = capitalize(s);
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
    let subset = rawData;
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
        opt.textContent = capitalize(e);
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
    let subset = rawData;
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
        opt.textContent = capitalizeWords(m);
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

    filteredData = rawData.filter(r => {
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
    const bsas = sumPeso(filteredData.filter(r => r.mercado === 'BSAS'));
    const ctes = sumPeso(filteredData.filter(r => r.mercado === 'CORRIENTES'));

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
    const maxMonth = filteredData.reduce((m, r) => Math.max(m, r.month), 0);

    document.getElementById('totalProduction').textContent = formatNum(total) + ' tn';
    document.getElementById('totalSpecies').textContent = speciesSet.size;
    document.getElementById('lastDate').textContent = maxMonth > 0 ? MONTHS_FULL[maxMonth - 1] : '–';

    document.getElementById('kpiFrutas').textContent = formatNum(frutas);
    document.getElementById('kpiHortalizas').textContent = formatNum(hortalizas);
    document.getElementById('kpiBsas').textContent = formatNum(bsas);
    document.getElementById('kpiCtes').textContent = formatNum(ctes);

    if (topEspecie) {
        document.getElementById('kpiTopEspecie').textContent = capitalize(topEspecie[0]);
        document.getElementById('kpiTopEspecieTon').textContent = formatNum(topEspecie[1]) + ' tn';
    }

    document.getElementById('kpiPeakMonth').textContent = MONTHS_FULL[peakIdx] || '–';
    document.getElementById('kpiPeakMonthTon').textContent = formatNum(peakVal) + ' tn';
}

// ─── Chart 1: Monthly Production (Stacked Area) ────────────────────────
function renderMonthlyChart() {
    const frutasMonthly = monthlyTotals(filteredData.filter(r => r.serie === 'FRUTAS'));
    const hortMonthly = monthlyTotals(filteredData.filter(r => r.serie === 'HORTALIZAS'));

    const cfg = {
        type: 'line',
        data: {
            labels: MONTHS,
            datasets: [
                {
                    label: 'Frutas',
                    data: frutasMonthly,
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
                    data: hortMonthly,
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
    const bsas = sumPeso(filteredData.filter(r => r.mercado === 'BSAS'));
    const ctes = sumPeso(filteredData.filter(r => r.mercado === 'CORRIENTES'));

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
            labels: sorted.map(s => capitalize(s[0])),
            datasets: [{
                label: 'Toneladas',
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
                    ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNum(v) }
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
        html += `<div class="heatmap-row-label" title="${esp}">${capitalize(esp)}</div>`;
        for (let m = 0; m < 12; m++) {
            const val = matrix[esp][m];
            if (val === 0) {
                html += `<div class="heatmap-cell heatmap-cell-empty">-</div>`;
            } else {
                const intensity = Math.min(val / (globalMax * 0.5), 1);
                const h = 160 - intensity * 110; // green to orange
                const s = 60 + intensity * 20;
                const l = 15 + intensity * 30;
                html += `<div class="heatmap-cell" style="background:hsla(${h},${s}%,${l}%,0.85);" title="${capitalize(esp)} - ${MONTHS_FULL[m]}: ${formatNum(round2(val))} tn">${formatNum(round2(val))}</div>`;
            }
        }
    });

    html += '</div>';
    container.innerHTML = html;
}

// ─── Chart 6: Market Monthly (Stacked) ──────────────────────────────────
function renderMarketMonthly() {
    const bsasMonthly = monthlyTotals(filteredData.filter(r => r.mercado === 'BSAS'));
    const ctesMonthly = monthlyTotals(filteredData.filter(r => r.mercado === 'CORRIENTES'));

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
            labels: top8.map(e => capitalize(e[0])),
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
            labels: sorted.map(s => capitalizeWords(s[0])),
            datasets: [{
                label: 'Toneladas',
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
                    ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNum(v) }
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
        html += `<tr><td>${capitalize(esp)}</td>`;
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
                html += `${formatNum(round2(v))}<br><span class="season-bar" style="width:${Math.max(pct, 5)}%"></span>`;
            } else {
                html += `-`;
            }
            html += `</td>`;
        }
        html += `<td class="total-col">${formatNum(round2(total))}</td></tr>`;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// ─── Helpers ────────────────────────────────────────────────────────────
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

function formatNum(n) {
    if (n === undefined || n === null || isNaN(n)) return '–';
    return n.toLocaleString('es-AR', { maximumFractionDigits: 1 });
}

function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

function capitalizeWords(str) {
    if (!str) return '';
    return str.split(/(\s+|–)/).map(w => {
        if (w === '–' || w.trim() === '') return w;
        return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
    }).join('');
}

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
                return ` ${ctx.dataset.label || ctx.label}: ${formatNum(typeof val === 'object' ? ctx.raw : val)} tn`;
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
                ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNum(v) }
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
                ticks: { color: '#94a3b8', font: { family: "'Inter'", size: 11 }, callback: v => formatNum(v) }
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
