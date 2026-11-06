const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});try{
const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[],results=[];p.on('pageerror',e=>{errors.push(e.message);console.error('pageerror:',e.message);});
await p.goto(process.env.MAYORISTAS_URL || 'http://127.0.0.1:18769',{waitUntil:'domcontentloaded'});await p.locator('#loadingOverlay').waitFor({state:'hidden',timeout:120000});await p.locator('[data-module="priceView"]').click();await p.waitForFunction('typeof priceDeliveryActive!=="undefined" && priceDeliveryActive && !priceDeliveryPending',null,{timeout:120000});
async function select(id,values){await p.evaluate(({id,values})=>{const e=document.getElementById(id);for(const o of e.options)o.selected=values.includes(o.value);e.dispatchEvent(new Event('change',{bubbles:true}));},{id,values});await p.waitForFunction('!priceDeliveryPending && document.getElementById("priceView").getAttribute("aria-busy")==="false"',null,{timeout:120000});}
for(const year of ['2024','2025','2026']){
 await select('priceFilterYear',[year]);await select('priceFilterMercado',['TODOS']);await select('priceFilterProcedencia',['TODOS']);
 const prod=await p.evaluate(()=>[...document.querySelector('#priceFilterEspecie').options].map(x=>x.value).find(x=>x==='Tomate'));assert.ok(prod,year);await select('priceFilterEspecie',[prod]);
 const origin=await p.evaluate(()=>{let a=[...document.querySelector('#priceFilterProcedencia').options].map(x=>x.value);return a.includes('Corrientes')?'Corrientes':a.find(x=>x!=='TODOS')});assert.ok(origin);await select('priceFilterProcedencia',[origin]);
 const checks=await p.evaluate(()=>{
  const points=MayoristasExplore.summarize(getFilteredPriceData({frequency:'mensual',ignoreComparable:true})).filter(x=>x.value!==null), errors=[];
  const chart=exploreCharts[0],bars=exploreCharts[1],table=[...document.querySelectorAll('#exploreTable tbody tr')],cards=[...document.querySelectorAll('#exploreKpis .kpi-card')];
  for(const [i,series] of chart.data.datasets.entries()){
   const market=points.filter(x=>x.market===series.label), latest=market.at(-1);
   if(latest&&(!cards[i].textContent.includes(formatCurrency(latest.value))||!cards[i].textContent.includes(latest.month)))errors.push('KPI último '+series.label);
   for(const item of market){const j=chart.data.labels.indexOf(item.month);if(series.data[j]!==item.value)errors.push('gráfico '+item.month);if(!table.some(r=>r.cells[0].textContent===item.month&&r.cells[1].textContent===item.market&&r.cells[2].textContent===formatCurrency(item.value)))errors.push('tabla '+item.month);
    const prev=market.find(x=>MayoristasExplore.consecutive(x.month,item.month));const expected=prev?(item.value/prev.value-1)*100:null;const actual=bars.data.datasets[i].data[j];if(expected===null?actual!==null:Math.abs(expected-actual)>1e-9)errors.push('variación '+item.month);
   }
  }
  const a=points.filter(x=>x.market==='Mercado Central de Buenos Aires'),b=points.filter(x=>x.market==='Mercado de Corrientes');const common=a.map(x=>x.month).filter(m=>b.some(x=>x.month===m)).sort().at(-1);
  if(common){const va=a.find(x=>x.month===common).value,vb=b.find(x=>x.month===common).value;if(!cards[2].textContent.includes(formatPercent((vb/va-1)*100))||!cards[2].textContent.includes(common))errors.push('diferencia');}else if(!/Sin mes común|no corresponden al mismo período/.test(cards[2].textContent))errors.push('sin mes común');
  return errors;
 });assert.deepEqual(checks,[],`KPI/gráfico/tabla ${year}: ${checks.join(', ')}`);
 const current=await p.evaluate(()=>({status:document.getElementById('exploreStatus').textContent,charts:exploreCharts.map(x=>x.data.datasets.map(d=>d.data.filter(v=>v!==null).length)),cards:document.getElementById('exploreKpis').textContent}));assert.ok(current.charts.length===2 || /No encontramos precios/.test(current.status),JSON.stringify({year,current}));results.push({year,origin,...current});
}
await select('priceFilterYear',['TODOS']);await select('priceFilterEspecie',['Tomate']);await select('priceFilterProcedencia',['Corrientes']);let all=await p.evaluate(()=>({charts:exploreCharts.length,labels:exploreCharts[0]?.data.labels||[],memory:performance.memory?.usedJSHeapSize}));assert.equal(all.charts,2);assert.ok(all.labels.some(x=>x.startsWith('2024'))&&all.labels.some(x=>x.startsWith('2026')));results.push({year:'TODOS',...all});
await p.locator('#priceFilterReset').click();await p.waitForFunction('!priceDeliveryPending && document.getElementById("priceView").getAttribute("aria-busy")==="false"');assert.equal(await p.locator('#priceFilterYear').inputValue(),'2026');assert.equal(await p.locator('#priceOverview').isVisible(),true);
await select('priceFilterMercado',['Mercado de Corrientes']);await select('priceFilterEspecie',['Tomate']);await select('priceFilterProcedencia',['Corrientes']);
await p.locator('#priceAdvanced > summary').click();for(const f of ['diaria','anual','mensual']){await select('priceFilterFrequency',[f]);const info=await p.evaluate(()=>({frequency:priceFrequency,rows:filteredPriceData.length,plot:!!priceCharts.evolution,points:priceCharts.evolution?.data.labels.length||0}));results.push(info);assert.equal(info.frequency,f);assert.ok(info.rows>0&&info.plot&&info.points>0,JSON.stringify(info));}
// An available calendar month with no observations for the current market must clear prior charts.
await select('priceFilterYear',['2024']);await select('priceFilterMercado',['TODOS']);await select('priceFilterEspecie',['Tomate']);await select('priceFilterProcedencia',['Corrientes']);
const missing=await p.evaluate(()=>{const months=new Set(filteredPriceData.map(r=>r.fecha?.slice(5,7)));return [...document.getElementById('priceFilterMes').options].map(o=>o.value).find(v=>v!=='TODOS' && !months.has(String(monthNumber(v)).padStart(2,'0')))});
if(missing){await select('priceFilterMes',[missing]);const empty=await p.evaluate(()=>({charts:exploreCharts.length,status:document.getElementById('exploreStatus').textContent,table:document.querySelectorAll('#exploreTable tbody tr').length}));assert.equal(empty.charts,0);assert.equal(empty.table,0);assert.match(empty.status,/No encontramos precios/);results.push({missing,empty});} else throw Error('No se encontró un mes ausente para el caso de prueba');
assert.deepEqual(errors,[]);console.log(JSON.stringify({results,errors}));
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
