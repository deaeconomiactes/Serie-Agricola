/* Local Edge smoke for the wholesale filter panel and reset action. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1310,height:800}});const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(process.env.MAYORISTAS_URL || 'http://127.0.0.1:8768',{waitUntil:'domcontentloaded'});
  await page.locator('#loadingOverlay').waitFor({state:'hidden',timeout:120000});
  await page.locator('[data-module="priceView"]').click();
  await page.waitForFunction('typeof priceDeliveryActive !== "undefined" && priceDeliveryActive && !priceDeliveryPending',null,{timeout:120000});
  await page.locator('#priceMoreFilters > summary').click();
  for (const width of [1440,1310,1000,640,360]) {
   await page.setViewportSize({width,height:800});
   const layout=await page.evaluate(()=>{
    const rect=id=>document.querySelector(id).getBoundingClientRect();
    const panel=rect('.sa-price-more-grid'),summary=rect('#priceMoreFilters > summary'),filters=rect('#priceView .price-filters'),reset=rect('#priceFilterReset');
    return {panel:{top:panel.top,bottom:panel.bottom,left:panel.left,right:panel.right},summary:{bottom:summary.bottom,right:summary.right},
     filters:{left:filters.left,right:filters.right,bottom:filters.bottom},reset:{left:reset.left},overflow:document.documentElement.scrollWidth>innerWidth+1};
   });
   assert.ok(layout.panel.top>=layout.summary.bottom,JSON.stringify(layout));
   assert.ok(layout.panel.left>=layout.filters.left && layout.panel.right<=layout.filters.right,JSON.stringify(layout));
   assert.ok(layout.panel.bottom<=layout.filters.bottom,JSON.stringify(layout));
   assert.ok(layout.summary.right<=layout.reset.left,JSON.stringify(layout));
   assert.equal(layout.overflow,false,JSON.stringify(layout));
  }
  await page.setViewportSize({width:1310,height:800});
  if(process.env.MAYORISTAS_SCREENSHOT_DIR) await page.screenshot({path:require('path').join(process.env.MAYORISTAS_SCREENSHOT_DIR,'filtros-mayoristas.png')});
  const choose=async(id,values)=>page.evaluate(({id,values})=>{const s=document.getElementById(id);[...s.options].forEach(o=>o.selected=values.includes(o.value));s.dispatchEvent(new Event('change',{bubbles:true}));},{id,values});
  await choose('priceFilterMercado',['Mercado de Corrientes']);await page.waitForFunction('!priceDeliveryPending');
  await choose('priceFilterEspecie',['Tomate']);await choose('priceFilterProcedencia',['Corrientes']);await choose('priceFilterVariedad',['Perita']);
  await page.locator('#priceFilterYear').selectOption('2025');await page.waitForFunction('!priceDeliveryPending');
  await page.locator('#priceFilterFrequency').selectOption('diaria');await page.waitForFunction('!priceDeliveryPending');
  await page.locator('#priceFilterComparable').selectOption('todos');
  await page.locator('#priceFilterReset').click();await page.waitForFunction('!priceDeliveryPending');
  const state=await page.evaluate(()=>({filters:getPriceFilters(),frequency:priceFrequency,loaded:[...new Set(validPriceData.map(r=>r.mercado))],year:document.getElementById('priceFilterYear').value}));
  assert.equal(state.year,'2026');assert.equal(state.frequency,'mensual');assert.equal(state.filters.unidadComparable,'comparables');
  for(const key of ['mes','rubro','especie','variedad','mercado','procedencia','unidad','envase','calidadMCBA','tamanoMCBA','gradoMCBA']) assert.deepEqual(state.filters[key],['TODOS'],key);
  assert.equal(state.loaded.length,2);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({widths:[1440,1310,1000,640,360],state,errors}));
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
