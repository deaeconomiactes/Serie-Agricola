(function(root){
'use strict';
const median = values => { const a=values.slice().sort((x,y)=>x-y), n=a.length; return n ? (a[(n-1)>>1]+a[n>>1])/2 : null; };
function summarize(rows){
 const groups=new Map();
 for(const r of rows){
  const v=r.precioKgEstimado, currency=r.moneda_normalizada || r.currency;
  const precision=String(r.fechaPrecision||'').toLowerCase();
  if(currency!=='ARS'||r.conversion_validada===false||!['Alta','Media'].includes(r.confianzaConversion)||!Number.isFinite(v)||v<=0||!/^\d{4}-\d{2}-\d{2}$/.test(r.fecha||'')||!['diaria','mensual'].includes(precision)) continue;
  const month=r.fecha.slice(0,7),key=JSON.stringify([r.mercado,month]);
  if(!groups.has(key))groups.set(key,{market:r.mercado,month,precisions:new Set(),sources:new Set(),methods:new Set(),confidence:new Set(),days:new Map(),monthly:[],observations:0});
  const g=groups.get(key);g.precisions.add(precision);g.sources.add(r.data_source||'sin fuente');g.methods.add(r.metodoConversion||'método no informado');g.confidence.add(r.confianzaConversion);g.observations++;
  if(precision==='diaria'){if(!g.days.has(r.fecha))g.days.set(r.fecha,[]);g.days.get(r.fecha).push(v);}else g.monthly.push(v);
 }
 return [...groups.values()].map(g=>{
  const compatible=g.precisions.size===1 && g.sources.size===1;
  const daily=g.precisions.has('diaria');
  return {market:g.market,month:g.month,value:compatible?median(daily?[...g.days.values()].map(median):g.monthly):null,
   observations:g.observations,days:daily?g.days.size:null,source:[...g.sources].join(', '),methods:[...g.methods].join(', '),confidence:[...g.confidence].join(', '),precision:daily?'diaria':'mensual',incompatible:!compatible};
 }).sort((a,b)=>a.month.localeCompare(b.month)||a.market.localeCompare(b.market));
}
function consecutive(a,b){return /^\d{4}-\d{2}$/.test(a||'') && /^\d{4}-\d{2}$/.test(b||'') && (Number(b.slice(0,4))*12+Number(b.slice(5)))-(Number(a.slice(0,4))*12+Number(a.slice(5)))===1;}
const api={median,summarize,consecutive};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.MayoristasExplore=api;
})(typeof globalThis!=='undefined'?globalThis:this);
