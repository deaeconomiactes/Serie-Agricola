const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function context(){const ctx=vm.createContext({console,document:{addEventListener(){}}});vm.runInContext(fs.readFileSync(process.env.PRICE_APP_PATH || 'app.js','utf8'),ctx);return ctx;}
function run(ctx,rows,filters={mercado:['A','B'],especie:['Tomate'],procedencia:['Corrientes'],variedad:['TODOS']}){
 ctx.rows=rows;ctx.filters=filters;return JSON.parse(vm.runInContext("JSON.stringify(comparableMarketSelection(rows,filters,'mensual'))",ctx));
}
const row=(market,overrides={})=>({mercado:market,especie:'Tomate',procedencia:'Corrientes',variedad:'Redondo',moneda_normalizada:'ARS',
 fecha:'2026-04-01',fechaPrecision:market==='A'?'mensual':'diaria',envase:market==='A'?'Torito':'Torito X 18 Kg',kg_raw:market==='A'?'18':'',kgBulto:market==='B'?18:null,
 precioKgEstimado:100,confianzaConversion:'Alta',data_source:market==='A'?'MERCADO_CENTRAL':'LEGACY',...overrides});

test('0, 1 y varias combinaciones conservan variedad, moneda, presentación y atributos',()=>{
 const ctx=context();const a=row('A',{calidadMCBA:'Primera',tamanoMCBA:'MEDIANO',gradoMCBA:'P/I'});const b=row('B');
 assert.equal(run(ctx,[a,row('B',{envase:'Bolsa X 18 Kg'})]).status,'NO_COMMON_PRESENTATION');
 const one=run(ctx,[a,b,row('B',{variedad:'Cherry'})]);
 assert.equal(one.status,'COMPARABLE');assert.equal(one.combinations.length,1);assert.equal(one.rows.length,2);
 assert.match(one.note,/no informados/);assert.match(one.label,/REDONDO/i);
 const multiple=run(ctx,[a,row('A',{calidadMCBA:'Segunda',tamanoMCBA:'MEDIANO',gradoMCBA:'P/I'}),b]);
 assert.equal(multiple.combinations.length,2);
 assert.ok(multiple.combinations.every(c=>c.rows.filter(r=>r.mercado==='A').length===1));
 ctx.choice=multiple.combinations[1].key;vm.runInContext('priceComparisonChoice=choice',ctx);
 assert.equal(run(ctx,[a,row('A',{calidadMCBA:'Segunda',tamanoMCBA:'MEDIANO',gradoMCBA:'P/I'}),b]).key,ctx.choice);
 const frequencies=run(context(),[a,row('A',{calidadMCBA:'Primera',tamanoMCBA:'MEDIANO',gradoMCBA:'P/I',fechaPrecision:'diaria'}),b]);
 assert.equal(frequencies.combinations.length,2);
});

test('no cruza monedas, pesos, variedades, calidades incompatibles ni períodos sin solapamiento',()=>{
 for(const changes of [{moneda_normalizada:'USD'},{moneda_normalizada:'UNKNOWN'}]){
  const ctx=context();assert.equal(run(ctx,[row('A'),row('B',changes)]).status,'NO_COMPARABLE_CURRENCY');
 }
 for(const changes of [{kgBulto:20,envase:'Torito X 20 Kg'},
  {variedad:'Perita'},{fecha:'2026-05-01'},{conversion_validada:false},{envase:'Doc. de Mazo X 18 Kg'}]){
  const ctx=context();assert.equal(run(ctx,[row('A',{calidadMCBA:'Primera'}),row('B',changes)]).status,'NO_COMMON_PRESENTATION');
 }
 assert.equal(run(context(),[row('A',{calidadMCBA:'Primera'}),row('B',{calidadMCBA:'Segunda'})]).status,'NO_COMMON_PRESENTATION');
 assert.equal(run(context(),[row('A',{gradoMCBA:'P/I'}),row('B',{gradoMCBA:'P I'})]).status,'NO_COMMON_PRESENTATION');
 assert.equal(run(context(),[row('A'),row('B',{fechaPrecision:'anual'})]).status,'NO_COMMON_PRESENTATION');
 assert.equal(run(context(),[row('A'),row('B'),row('B',{moneda_normalizada:'UNKNOWN'})]).combinations.length,1);
});

test('la misma intersección funciona con otros productos y conserva las fuentes separadas',()=>{
 for(const [product,variety] of [['Papa','Blanca'],['Cebolla','Colorada'],['Zanahoria','Nantes']]) {
  const ctx=context();const filters={mercado:['A','B'],especie:[product],procedencia:['Salta'],variedad:['TODOS']};
  const a=row('A',{especie:product,procedencia:'Salta',variedad:variety});
  const b=row('B',{especie:product,procedencia:'Salta',variedad:variety});
  const result=run(ctx,[a,b],filters);assert.equal(result.status,'COMPARABLE');assert.equal(result.combinations.length,1);
  assert.deepEqual(result.rows.map(r=>r.data_source).sort(),['LEGACY','MERCADO_CENTRAL']);
 }
});
