const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

test('limpiar filtros restaura valores iniciales y recarga una sola selección',()=>{
 const multi=['priceFilterRubro','priceFilterEspecie','priceFilterVariedad','priceFilterMercado','priceFilterProcedencia'];
 const single=['priceFilterMes','priceFilterUnidad','priceFilterEnvase','priceFilterCalidad','priceFilterTamano','priceFilterGrado'];
 const controls={};
 for(const id of multi) controls[id]={multiple:true,options:[{value:'TODOS',selected:false},{value:'otro',selected:true}]};
 for(const id of single) controls[id]={multiple:false,value:'otro'};
 controls.priceFilterYear={value:'2024'};controls.priceFilterFrequency={value:'diaria'};controls.priceFilterComparable={value:'todos'};
 const ctx=vm.createContext({console,controls,document:{addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];},getElementById(id){return controls[id]||null;}}});
 vm.runInContext(fs.readFileSync('app.js','utf8'),ctx);
 const result=JSON.parse(vm.runInContext(`priceDelivery={index:{years:[2024,2026,2025]}};priceFrequency='diaria';priceComparisonChoice='anterior';
  let calls=0;refreshPriceDelivery=()=>{calls++};resetPriceFilters();JSON.stringify({calls,frequency:priceFrequency,choice:priceComparisonChoice})`,ctx));
 assert.deepEqual(result,{calls:1,frequency:'mensual',choice:''});
 assert.equal(controls.priceFilterYear.value,'2026');assert.equal(controls.priceFilterFrequency.value,'mensual');assert.equal(controls.priceFilterComparable.value,'comparables');
 for(const id of multi) assert.deepEqual(controls[id].options.map(o=>o.selected),[true,false],id);
 for(const id of single) assert.equal(controls[id].value,'TODOS',id);
});
