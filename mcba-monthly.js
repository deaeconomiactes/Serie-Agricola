/* Monthly derived views of official Mercado Central daily XLS books; separate from MAGyP. */
(function(root) {
 'use strict';
 const BASE='data/mercado_central/dashboard/mcba/';
 const FILE='MCBA_MC_MONTHLY_DERIVED.csv';
 const VERSION='mcba-central-monthly-v1';
 const REQUIRED=['date','period','type','product_raw','product_normalized','variety_raw','variety_normalized',
  'origin_raw','origin_normalized','package_raw','package_normalized','kg_raw','quality','size','grade',
  'price','price_min','price_max','currency','price_unit','observed_days','first_observation_date',
  'last_observation_date','source','source_url','capture_timestamp','capture_id','raw_sha256','schema_version','observation_id','method'];
 function validate(rows) {
  if(!rows.length)throw Error('Vista mensual vacía');
  const ids=new Set();
  for(const r of rows) {
   const day=new Date(r.date+'T00:00:00Z');
   if(r.schema_version!==VERSION || r.source!=='MERCADO_CENTRAL' || r.currency!=='ARS' || r.price_unit!=='kg' ||
    !Number.isFinite(day.valueOf()) || day.toISOString().slice(0,10)!==r.date || r.date!==r.period+'-01' ||
    !['Frutas','Hortalizas'].includes(r.type) || !r.product_normalized || !(Number(r.price)>0) || !Number.isFinite(Number(r.price)) ||
    !Number.isInteger(Number(r.observed_days)) || Number(r.observed_days)<1 || Number(r.observed_days)>31 ||
    r.last_observation_date.slice(0,7)!==r.period || !Number.isFinite(Date.parse(r.capture_timestamp)) ||
    !/^[a-f0-9]{64}$/.test(r.raw_sha256) || !r.capture_id || !r.observation_id || ids.has(r.observation_id)) throw Error('Contrato mensual inválido');
   const url=new URL(r.source_url);
   if(url.protocol!=='https:' || !['mercadocentral.gob.ar','www.mercadocentral.gob.ar'].includes(url.hostname) || url.username || url.password)throw Error('Fuente mensual inválida');
   ids.add(r.observation_id);
  }
  return rows;
 }
 async function verify(text,marker) {
  const bytes=new TextEncoder().encode(text);
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  if(hash!==marker.files?.[FILE])throw Error('Publicación mensual incompleta');
  const rows=validate(MCBAPrices.parseCSV(text,REQUIRED));
  if(rows.length!==marker.record_count)throw Error('Conteo mensual inválido');
  return rows;
 }
 async function load() {
  try {
   const get=async name=>{const response=await fetch(BASE+name,{cache:'no-store'});if(!response.ok)throw Error('Fuente mensual no disponible');return response.text();};
   const [body,marker]=await Promise.all([get(FILE),get('_SUCCESS.json')]);
   const rows=await verify(body,JSON.parse(marker));
   return {rows,warning:''};
  } catch(_) {return {rows:[],warning:'Vista mensual Mercado Central no disponible; se mantiene legacy.'};}
 }
 function adapt(rows,months,label=value=>value||'') {
  return rows.map(r=>({...r,fecha:r.date,year:Number(r.date.slice(0,4)),month:Number(r.date.slice(5,7)),
   mes:months[Number(r.date.slice(5,7))-1],fechaPrecision:'mensual',rubro:r.type,
   especie:label(r.product_normalized),variedad:label(r.variety_normalized),procedencia:label(r.origin_normalized),
   mercado:MCBAPrices.MCBA,envase:label(r.package_normalized),unidad:'$/kg',
   calidadMCBA:r.quality,tamanoMCBA:r.size,gradoMCBA:r.grade,kgBulto:null,
   precio:Number(r.price),precioObservado:Number(r.price),precioKgEstimado:Number(r.price),precioPromedio:Number(r.price),
   precioMin:Number(r.price_min),precioMax:Number(r.price_max),unidadPrecioObservado:'$/kg',
   metodoConversion:'Media mensual derivada de modales diarios por serie; días observados',confianzaConversion:'Alta',
   data_source:'MERCADO_CENTRAL',source_status:'MERCADO_CENTRAL',fuente:r.source_url,last_update:r.capture_timestamp}));
 }
 function route(legacy,monthly) {
  // Coverage is decided at month/category before product filters; no filling missing dimensions.
  const covered=new Set(monthly.map(r=>r.fecha.slice(0,7)+'|'+r.rubro));
  return legacy.filter(r=>r.mercado!==MCBAPrices.MCBA || !covered.has(r.fecha.slice(0,7)+'|'+r.rubro)).concat(monthly);
 }
 const api={BASE,FILE,VERSION,validate,verify,load,adapt,route};
 if(typeof module!=='undefined' && module.exports)module.exports=api;else root.MCBAMonthly=api;
})(typeof globalThis!=='undefined'?globalThis:this);
