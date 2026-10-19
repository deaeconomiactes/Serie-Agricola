const test = require('node:test');
const assert = require('node:assert/strict');
const {describe, render} = require('../../update-status.js');
const metadata = {requested_date:'2026-10-05', last_valid_date:'2026-10-05', last_successful_update:'2026-10-06T13:34:47Z'};
for (const [status,label,tone,detail] of [
 ['UPDATED','Actualizado','success','Último dato: 05/10/2026'],
 ['NO_OP_ALREADY_CURRENT','Actualizado','success','Último dato: 05/10/2026'],
 ['NO_PUBLICATION','Sin nueva publicación','warning','Último dato disponible: 05/10/2026'],
 ['SOURCE_UNAVAILABLE','Último dato válido','warning','Fuente temporalmente no disponible · Última actualización exitosa: 06/10/2026 10:34'],
 ['MAGYP_LAST_VALID','Último dato válido','warning','Fuente temporalmente no disponible · Última actualización exitosa: 06/10/2026 10:34'],
 ['PIPELINE_ERROR','Error de actualización','error','Se conserva la última versión válida']
]) test('MCBA indicator '+status, () => {
 const view=describe({...metadata,status});
 assert.equal(view.label,label); assert.equal(view.tone,tone); assert.equal(view.details,detail);
 const node={ownerDocument:{createElement:()=>({})}, replaceChildren(){this.children=[];}, append(...items){this.children.push(...items);}};
 render(node,{...metadata,status},{});
 assert.equal(node.hidden,false); assert.equal(node.children[0].textContent,'MCBA · '+label);
 assert.equal(node.children[1].textContent,detail);
 render(node,{...metadata,status},{},false); assert.equal(node.hidden,true); assert.deepEqual(node.children,[]);
});
test('explicit result takes precedence over fallback source_status; aliases use published summary',()=>{
 const view=describe({result:'UPDATED',source_status:'MAGYP_LAST_VALID'}, {date_max:'2026-10-05'});
 assert.equal(view.tone,'success'); assert.equal(view.details,'Último dato: 05/10/2026');
 assert.equal(describe({status:'UPDATED',last_valid_date:'2001-01-01'}).tone,'success');
 assert.equal(describe({source_status:'MAGYP'}),null);
 assert.equal(describe(null),null);
 assert.match(describe({status:'UPDATED',last_valid_date:'2026-02-31'}).details,/No informada/);
});
