const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const mcba = require('../../mcba-prices.js');
const current = fs.readFileSync('app.js', 'utf8').replace(/\r\n/g,'\n');
// Committed baseline, independently executed against the same legacy input.
const original = execFileSync('git', ['show', '5fb5987:app.js'], {encoding:'utf8'}).replace(/\r\n/g,'\n');
const input = fs.readFileSync('PRECIOS_MAYORISTAS_INTEGRADO.csv','utf8');
function context(code, initialize = true) {
    const selections = {
        priceFilterYear:'2025', priceFilterMes:'TODOS', priceFilterEspecie:'TODOS',
        priceFilterVariedad:'TODOS',priceFilterRubro:'TODOS',priceFilterProcedencia:'TODOS',
        priceFilterUnidad:'TODOS',priceFilterMercado:'Mercado de Corrientes',priceFilterComparable:'comparables'
    };
    const ctx = vm.createContext({
        console:{log(){},warn(){}}, MCBAPrices:mcba,
        document:{addEventListener(){},getElementById(id){return {value:selections[id] || 'TODOS',multiple:false};}},
        input
    });
    vm.runInContext(code,ctx);
    if (initialize) vm.runInContext(`validPriceData = filterFutureDates(processPriceData(parsePriceCSV(input), 'PRECIOS_MAYORISTAS_INTEGRADO.csv')).validRows.filter(r => isValidPrice(r.precioObservado));
        validPriceData = validPriceData.map(r=>({...r,data_source:'LEGACY'}));`,ctx);
    return ctx;
}
test('Corrientes rows, price averages, rankings and monthly semaphore match committed baseline', () => {
    const before = context(original), after = context(current);
    const expression = `JSON.stringify({
        rows: getFilteredPriceData(),
        evolution: aggregatePriceData(getFilteredPriceData(), 'mensual'),
        ranking: preparePriceRankingData(getFilteredPriceData(), 'general', getPriceFilters()),
        semaphore: buildMonthlyPriceSemaphoreMatrix(getFilteredPriceData(),getPriceFilters())
    })`;
    assert.equal(vm.runInContext(expression,after),vm.runInContext(expression,before));
});
test('MCBA daily evolution and ranking label and separate MAGyP from uncovered legacy', () => {
    const ctx = context(current, false);
    const result = vm.runInContext(`JSON.stringify((() => {
        const base = {mercado:MCBAPrices.MCBA,especie:'Manzana',variedad:'Red',procedencia:'Río Negro',
            precioObservado:100,precioKgEstimado:100,confianzaConversion:'Alta'};
        const data = [{...base,fecha:'2026-08-19',data_source:'MAGYP'},
            {...base,fecha:'2026-08-18',data_source:'LEGACY'}];
        const filters = {especie:['TODOS']};
        return {
            evolution:preparePriceEvolutionData(data,'diaria',filters).series,
            ranking:preparePriceRankingData(data,'general',filters).labels
        };
    })())`,ctx);
    const parsed = JSON.parse(result);
    assert.equal(parsed.evolution.length,2);
    assert.ok(parsed.evolution.some(r=>r.label==='MAGyP'));
    assert.ok(parsed.evolution.some(r=>r.label==='Legacy'));
    assert.equal(parsed.ranking.length,2);
    assert.ok(parsed.ranking.some(label=>label.includes('MAGyP')));
});
test('quantity functions and original commodity source configurations remain unchanged', () => {
    // Function boundaries include the full bodies, avoiding assertions about only signatures.
    const extract = (text,name) => text.slice(text.indexOf('function '+name+'('),text.indexOf('\nfunction ',text.indexOf('function '+name+'(')+1));
    for (const name of ['aggregateQuantityData','updateQuantityDashboard','updateKPIs','renderMonthlyChart',
        'updateCommodityDashboard','getCommodityFilteredRows']) {
        assert.ok(original.includes('function '+name+'('), name);
        assert.equal(extract(current,name),extract(original,name),name);
    }
    const config = text => text.slice(text.indexOf('const COMMODITY_SOURCE_CONFIG'),text.indexOf('const COMMODITY_SOURCE_CONFIG')+1200);
    assert.equal(config(current),config(original));
});
