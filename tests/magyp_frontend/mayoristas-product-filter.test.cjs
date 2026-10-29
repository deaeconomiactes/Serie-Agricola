const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function makeSelect(multiple, initial = 'TODOS') {
 const select = {multiple, options: [{value:initial,textContent:initial,selected:true}],
  appendChild(option){this.options.push(option);},
  set innerHTML(value){this.options=[{value:'TODOS',textContent:value,selected:true}];},
  get value(){return this.options.find(o=>o.selected)?.value || 'TODOS';},
  set value(value){this.options.forEach(o=>{o.selected=o.value===value;});},
  get selectedOptions(){return this.options.filter(o=>o.selected);}};
 return select;
}

test('filtros y disponibilidad usan producto canónico de ambas fuentes',()=>{
 const ids = ['priceFilterYear','priceFilterMes','priceFilterRubro','priceFilterEspecie','priceFilterVariedad',
  'priceFilterMercado','priceFilterProcedencia','priceFilterUnidad','priceFilterEnvase','priceFilterCalidad','priceFilterTamano','priceFilterGrado'];
 const multi = new Set(['priceFilterRubro','priceFilterEspecie','priceFilterVariedad','priceFilterMercado','priceFilterProcedencia']);
 const controls=Object.fromEntries(ids.map(id=>[id,makeSelect(multi.has(id),id==='priceFilterYear'?'2026':'TODOS')]));
 const ctx=vm.createContext({console:{log(){},warn(){}},document:{addEventListener(){},querySelector(){return null;},
  getElementById(id){return controls[id]||null;},createElement(){return {value:'',textContent:'',selected:false};}}, controls});
 vm.runInContext(fs.readFileSync(process.env.PRICE_APP_PATH || 'app.js','utf8'),ctx);
 ctx.rows=[
  {year:2026,mercado:'A',especie:'Tomate',productoNormalizado:'Tomate',variedad:'Redondo',procedencia:'Corrientes'},
  {year:2026,mercado:'B',especie:'Tomate Perita',productoNormalizado:'Tomate',variedad:'Perita',procedencia:'Corrientes'},
  {year:2026,mercado:'B',especie:'Tomate Cherry',productoNormalizado:'Tomate',variedad:'Cherry',procedencia:'Corrientes'},
  {year:2026,mercado:'B',especie:'Sandia Redonda Rayada',producto_normalizado:'Sandía',variedad:'Redonda Rayada',procedencia:'Corrientes'},
  {year:2026,mercado:'B',especie:'Batata Colorada',productoNormalizado:'Batata',variedad:'Colorada',procedencia:'Corrientes'}];
 vm.runInContext("validPriceData=rows;priceDeliveryActive=true;priceDelivery={index:{years:[2026],markets:['A','B']}};populatePriceFilters()",ctx);
 const products=controls.priceFilterEspecie.options;
 assert.equal(products.filter(o=>o.value==='Tomate').length,1);
 assert.equal(products.find(o=>o.value==='Tomate').textContent,'Tomate · en todos los mercados');
 assert.ok(products.some(o=>o.value==='Sandía'));assert.ok(products.some(o=>o.value==='Batata'));
 assert.ok(!products.some(o=>['Tomate Perita','Tomate Cherry','Sandia Redonda Rayada','Batata Colorada'].includes(o.value)));
 controls.priceFilterEspecie.value='Tomate';
 vm.runInContext('populatePriceFilters();updatePriceVarietyFilter()',ctx);
 assert.deepEqual(controls.priceFilterVariedad.options.slice(1).map(o=>o.value).sort(),['Cherry','Perita','Redondo']);
 assert.equal(vm.runInContext("matchesPriceFilter(rows[1],'especie',['Tomate'])",ctx),true);
 assert.equal(vm.runInContext("getProductLabel(rows[1])",ctx),'Tomate Perita');
});
