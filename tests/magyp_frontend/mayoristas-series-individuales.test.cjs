const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function context() {
    const ctx = vm.createContext({console, document:{addEventListener(){}}});
    vm.runInContext(fs.readFileSync('app.js', 'utf8'), ctx);
    return ctx;
}

test('las series individuales conservan mercado, origen, variedad, presentación, moneda, calidad y fuente', () => {
    const ctx = context();
    const row = {mercado:'Buenos Aires', productoNormalizado:'Naranja', procedencia:'Corrientes', variedad:'Valencia',
        moneda_normalizada:'ARS', envase:'Cajón', kg_raw:18, calidadMCBA:'Primera', tamanoMCBA:'Mediano',
        gradoMCBA:'P/I', data_source:'MCBA', source_status:'publicado', fechaPrecision:'mensual',
        fecha:'2026-03-01', precioKgEstimado:100, precioObservado:1800, unidadPrecioObservado:'bulto'};
    ctx.rows = [row, {...row, fecha:'2026-04-01'},
        ...Object.entries({mercado:'Corrientes',procedencia:'Salta',variedad:'Ombligo',moneda_normalizada:'USD',
            envase:'Bolsa',kg_raw:20,calidadMCBA:'Segunda',tamanoMCBA:'Grande',gradoMCBA:'P/II',
            data_source:'OTRA',source_status:'otra',fechaPrecision:'diaria'}).map(([field,value])=>({...row,[field]:value})),
        {...row, fecha:'',precioKgEstimado:null}];
    const groups = JSON.parse(vm.runInContext("JSON.stringify(getIndividualPriceSeries(rows,'comparable','mensual'))", ctx));
    assert.equal(groups.length, 13);
    assert.equal(groups[0].rows.length, 2);
    assert.ok(groups.every(group => group.rows.every(item => item.mercado === group.rows[0].mercado)));
    assert.match(groups[0].label, /Naranja Valencia.*Corrientes.*Cajón.*ARS\/kg/);
});

test('los precios originales se separan por unidad y se descartan filas sin período o precio', () => {
    const ctx = context();
    ctx.rows = [{mercado:'Corrientes',especie:'Papa',fecha:'2026-01-01',precioObservado:100,unidadPrecioObservado:'bolsa'},
        {mercado:'Corrientes',especie:'Papa',fecha:'2026-02-01',precioObservado:120,unidadPrecioObservado:'kg'},
        {mercado:'Corrientes',especie:'Papa',precioObservado:120,unidadPrecioObservado:'kg'},
        {mercado:'Corrientes',especie:'Papa',fecha:'2026-02-01',precioObservado:null,unidadPrecioObservado:'kg'}];
    const groups = JSON.parse(vm.runInContext("JSON.stringify(getIndividualPriceSeries(rows,'all','mensual'))",ctx));
    assert.equal(groups.length,2);
    assert.equal(groups.reduce((sum,group)=>sum+group.rows.length,0),2);
    assert.ok(groups.some(group=>group.label.includes('/bolsa')));
    assert.ok(groups.some(group=>group.label.includes('/kg')));
});
