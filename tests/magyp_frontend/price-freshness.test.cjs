const test=require('node:test');
const assert=require('node:assert/strict');
const status=require('../../update-status.js');
test('static sources disclose manual update and never fabricate a successful timestamp',()=>{
 const view=status.describe({status:'STATIC',last_observation_date:'2026-08-25'}, {}, {sourceLabel:'Corrientes',showDates:true});
 assert.equal(view.label,'Fuente estática'); assert.equal(view.tone,'neutral');
 assert.match(view.details,/25\/08\/2026/); assert.match(view.details,/Actualización exitosa: No informada/);
 assert.match(view.details,/sin automatización/);
});
test('freshness report loads explicit family states and tolerates unavailable metadata',async()=>{
 const original=global.fetch;
 try {
  global.fetch=async()=>({ok:true,json:async()=>({schema_version:'price-freshness-v1',sources:[
   {source_family:'sio',status:'SOURCE_UNAVAILABLE'}, {source_family:'corrientes',status:'STATIC'},
   {source_family:'bad',status:'unexpected'}]})});
  assert.equal((await status.loadFreshness()).sio.status,'SOURCE_UNAVAILABLE');
  assert.equal((await status.loadFreshness()).corrientes.status,'STATIC');
  assert.equal((await status.loadFreshness()).bad,undefined);
  global.fetch=async()=>{throw Error('offline');};
  assert.deepEqual(await status.loadFreshness(),{});
 } finally {global.fetch=original;}
});
