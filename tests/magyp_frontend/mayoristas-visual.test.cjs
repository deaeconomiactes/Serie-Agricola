const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function context(){const ctx=vm.createContext({console,document:{addEventListener(){}}});vm.runInContext(fs.readFileSync('app.js','utf8'),ctx);return ctx;}

test('colores de mercados son consistentes independientemente del orden',()=>{
 const ctx=context();
 assert.equal(vm.runInContext("priceSeriesColor('Mercado Central de Buenos Aires · Redondo',1)",ctx),'#34d399');
 assert.equal(vm.runInContext("priceSeriesColor('Mercado de Corrientes · Redondo',0)",ctx),'#60a5fa');
});

test('evita repetir un ranking de una sola variedad y oculta la comparación con un mercado',()=>{
 const ctx=context();
 ctx.rows=[{fecha:'2026-04-01',especie:'Tomate',variedad:'Redondo',mercado:'Mercado Central de Buenos Aires',precioKgEstimado:100},
  {fecha:'2026-04-01',especie:'Tomate',variedad:'Redondo',mercado:'Mercado de Corrientes',precioKgEstimado:110}];
 ctx.filters={especie:['Tomate'],variedad:['TODOS'],procedencia:['Corrientes'],mercado:['Mercado Central de Buenos Aires','Mercado de Corrientes']};
 const result=JSON.parse(vm.runInContext("JSON.stringify(getAvailablePriceVisualizations(rows,filters,'mensual'))",ctx));
 assert.equal(result.showVarietyRanking,false);assert.equal(result.showMarketComparison,true);
 const single=JSON.parse(vm.runInContext("JSON.stringify(getAvailablePriceVisualizations(rows.slice(0,1),{...filters,mercado:['Mercado Central de Buenos Aires']},'mensual'))",ctx));
 assert.equal(single.showMarketComparison,false);
});
