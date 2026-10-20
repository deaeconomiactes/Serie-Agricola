const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const indicator = require('../../update-status.js');
function metadata(summary) {
 const context=vm.createContext({document:{addEventListener(){}}, console});
 vm.runInContext(fs.readFileSync('app.js','utf8'),context);
 context.summary=summary;
 return vm.runInContext('commodityUpdateMetadata(summary)',context);
}
for(const [status,label,tone] of [
 ['UPDATED','Actualizado','success'],['NO_OP_ALREADY_CURRENT','Actualizado','success'],
 ['NO_PUBLICATION','Sin nueva publicación','warning'],['SOURCE_UNAVAILABLE','Último dato válido','warning'],
 ['LAST_VALID','Último dato válido','warning'],['PIPELINE_ERROR','Error de actualización','error']
]) test('Commodities published status '+status,()=>{
 const summary={status,fecha_max:'2026-10-09',fecha_actualizacion_dashboard:'2026-10-10T13:00:00Z'};
 const node={ownerDocument:{createElement:()=>({})},replaceChildren(){this.children=[];},append(...children){this.children.push(...children);}};
 indicator.render(node,metadata(summary),{},true,{sourceLabel:'Commodities',showDates:true,showUnknown:true});
 assert.equal(node.hidden,false);
 assert.equal(node.className,'source-update-status source-update-status--'+tone);
 assert.equal(node.children[0].textContent,'Commodities · '+label);
 assert.match(node.children[1].textContent,/Último dato: 09\/10\/2026/);
 assert.match(node.children[1].textContent,/Actualización exitosa: 10\/10\/2026 10:00/);
});
test('missing acquisition status remains neutral; economic estado and dates never imply success',()=>{
 const value=metadata({estado:'UPDATED',fecha_max:'2026-10-09',fecha_actualizacion_dashboard:'2026-10-10T13:00:00Z'});
 const view=indicator.describe(value,{}, {sourceLabel:'Commodities',showDates:true,showUnknown:true});
 assert.equal(view.label,'Estado no informado'); assert.equal(view.tone,'neutral');
 assert.match(view.details,/09\/10\/2026/);
 assert.equal(indicator.describe(metadata({status:'UPDATED',fecha_max:'2001-01-01'})).tone,'success');
});
test('switching family clears previous status instead of inheriting UPDATED',()=>{
 const options={sourceLabel:'Commodities',showDates:true,showUnknown:true};
 assert.equal(indicator.describe(metadata({result:'UPDATED'}),{},options).tone,'success');
 assert.equal(indicator.describe(metadata({result:'NO_PUBLICATION'}),{},options).tone,'warning');
 assert.equal(indicator.describe(metadata({}),{},options).tone,'neutral');
});
test('actual module status refresh uses only the selected family metadata',()=>{
 const nodes=new Map();
 const document={addEventListener(){},getElementById(id){
  if(!nodes.has(id)) nodes.set(id,{ownerDocument:{createElement:()=>({})},replaceChildren(){this.children=[];},append(...children){this.children.push(...children);}});
  return nodes.get(id);
 }};
 const ctx=vm.createContext({document,console,SourceUpdateStatus:indicator});
 vm.runInContext(fs.readFileSync('app.js','utf8'),ctx);
 vm.runInContext('setCommodityDataStatus=()=>{};',ctx);
 for(const [source,status] of [['magyp_internal','UPDATED'],['magyp_board','SOURCE_UNAVAILABLE'],['magyp_fas','NO_PUBLICATION'],['magyp_fob','NO_OP_ALREADY_CURRENT'],['magyp_futures','PIPELINE_ERROR'],['sio','LAST_VALID']]) {
  ctx.summary={result:status,filas_dashboard:1,fecha_max:'2026-10-09',fecha_actualizacion_dashboard:'2026-10-10T13:00:00Z'};
  vm.runInContext(`commoditySource='${source}';commodityData={resumen:[summary]};updateCommoditySourceStatus();`,ctx);
  assert.equal(nodes.get('commodityUpdateStatus').children[0].textContent,'Commodities · '+indicator.describe(ctx.summary).label);
  assert.match(nodes.get('commodityDataFreshness').textContent,/10\/10\/2026/);
 }
 ctx.summary={filas_dashboard:1,fecha_max:'2026-10-09'};
 vm.runInContext('commodityData={resumen:[summary]};updateCommoditySourceStatus();',ctx);
 assert.equal(nodes.get('commodityUpdateStatus').children[0].textContent,'Commodities · Estado no informado');
});
