const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const mcba = require('../../mcba-prices.js');
function context() {
    const ctx = vm.createContext({ MCBAPrices:mcba, console, document:{addEventListener(){},getElementById(){return {value:'TODOS'};}} });
    vm.runInContext(fs.readFileSync('app.js','utf8'),ctx);
    vm.runInContext("priceUnitMode='observed';",ctx);
    return ctx;
}
function result(expression) { return JSON.parse(vm.runInContext(`JSON.stringify(${expression})`,context())); }

test('ranking preserves all observations when technical identity differs from its label',()=>{
    const r=result(`preparePriceRankingData([
        {fecha:'2026-01-01',especie:'Banana',procedencia:'Ecuador',precioObservado:100},
        {fecha:'2026-02-01',especie:'Banana',procedencia:'Ecuador',precioObservado:300}
    ],'general',{procedencia:['Ecuador','Brasil']})`);
    assert.equal(r.meta.length,1);
    assert.equal(r.meta[0].observations,2);
    assert.equal(r.values[0],200);
});

test('monthly and annual changes require the preceding calendar period; December crosses year correctly',()=>{
    const monthly=result(`calculatePeriodVariation([
        {key:'2025-12',value:100},{key:'2026-01',value:120},
        {key:'2026-03',value:180},{key:'2026-04',value:198}],'mensual')`);
    assert.ok(Math.abs(monthly[1].variation-20)<1e-9);
    assert.equal(monthly[2].variation,null);
    assert.ok(Math.abs(monthly[3].variation-10)<1e-9);
    assert.equal(result(`calculatePeriodVariation([{key:'2024',value:100},{key:'2026',value:120}],'anual')`)[1].variation,null);
});

test('split variation does not bridge a missing month in either series',()=>{
    const r=result(`preparePriceVariationData([
        {fecha:'2026-01-01',especie:'Banana',precioObservado:100},
        {fecha:'2026-03-01',especie:'Banana',precioObservado:120},
        {fecha:'2026-02-01',especie:'Manzana',precioObservado:50},
        {fecha:'2026-03-01',especie:'Manzana',precioObservado:60}
    ],'mensual',{especie:['Banana','Manzana']})`);
    assert.equal(r.series.find(s=>s.label==='Banana').meta.at(-1).variation,null);
    assert.ok(Math.abs(r.series.find(s=>s.label==='Manzana').meta.at(-1).variation-20)<1e-9);
});

test('monthly semaphore rejects mixed years and never bridges absent calendar months',()=>{
    const base=`{mercado:'MCBA',rubro:'Frutas',especie:'Banana',variedad:'A',unidad:'$/kg'}`;
    assert.deepEqual(result(`buildMonthlyPriceSemaphoreMatrix([
        {...${base},fecha:'2025-01-01',precioObservado:100},
        {...${base},fecha:'2026-01-01',precioObservado:200}])`),[]);
    const r=result(`buildMonthlyPriceSemaphoreMatrix([
        {...${base},fecha:'2026-01-01',precioObservado:100},
        {...${base},fecha:'2026-03-01',precioObservado:200},
        {...${base},fecha:'2026-04-01',precioObservado:300}])`);
    assert.equal(r[0].monthly['03'].variation,null);
    assert.equal(r[0].monthly['04'].variation,50);
});

test('freshness tooltip uses institutional wording',()=>{
    const view=require('../../update-status.js').describe({status:'UPDATED',last_valid_date:'2026-10-05'});
    assert.doesNotMatch(view.title,/legacy|fallback|pipeline|normalized/i);
});

test('closed price modules are not loaded at boot; repeated openings reuse one load and failures allow retry',async()=>{
    const ctx=context();
    ctx.SourceUpdateStatus={loadFreshness:async()=>({})};
    ctx.window={dispatchEvent(){}};ctx.Event=class {};
    ctx.document.getElementById=()=>({setAttribute(){}});
    vm.runInContext(`let auditLoads = {price:0,commodity:0};
        showLoading=hideLoading=wireModuleTabs=initMultiSelectControls=wireFilters=()=>{};
        loadQuantityData=async()=>{};
        setPriceStatus=setCommodityDataStatus=()=>{};
        loadPriceData=async()=>{auditLoads.price++;};
        loadCommodityData=async()=>{auditLoads.commodity++;};`,ctx);
    await vm.runInContext('init()',ctx);
    assert.equal(vm.runInContext('auditLoads.price+auditLoads.commodity',ctx),0);
    await vm.runInContext(`Promise.all([loadPriceModuleOnDemand('priceView'),loadPriceModuleOnDemand('priceView')])`,ctx);
    assert.equal(vm.runInContext('auditLoads.price',ctx),1);
    vm.runInContext(`console={error(){}};loadCommodityData=async()=>{auditLoads.commodity++;throw Error('offline');};`,ctx);
    await vm.runInContext(`loadPriceModuleOnDemand('commodityView')`,ctx);
    vm.runInContext('loadCommodityData=async()=>{auditLoads.commodity++;};',ctx);
    await vm.runInContext(`loadPriceModuleOnDemand('commodityView')`,ctx);
    assert.equal(vm.runInContext('auditLoads.commodity',ctx),2);
});
