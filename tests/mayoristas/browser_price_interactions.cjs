/* Edge acceptance for period exploration, series visibility and semaphore cells. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1310,height:800}});const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:8768',{waitUntil:'domcontentloaded'});
  await page.locator('#loadingOverlay').waitFor({state:'hidden',timeout:120000});
  await page.locator('[data-module="priceView"]').click();await page.waitForFunction('typeof priceDeliveryActive !== "undefined" && priceDeliveryActive && !priceDeliveryPending',null,{timeout:120000});
  const select=async(id,value)=>page.evaluate(({id,value})=>{const el=document.getElementById(id);[...el.options].forEach(o=>o.selected=o.value===value);el.dispatchEvent(new Event('change',{bubbles:true}));},{id,value});
  await select('priceFilterEspecie','Tomate');await select('priceFilterProcedencia','Corrientes');
  await page.waitForFunction('Boolean(priceCharts.evolution)');
  const monthlyStatus=await page.evaluate(()=>priceFreshnessBySource.mcba_monthly);
  if(monthlyStatus?.status==='UPDATED') {
   const text=await page.locator('#mcbaMonthlyUpdateStatus').textContent();
   assert.match(text,/Actualizado/);
   assert.doesNotMatch(text,/Error de actualización/);
  }
  const before=await page.evaluate(()=>({datasets:priceCharts.evolution.data.datasets.map(d=>d.data),rows:filteredPriceData.length,filters:getPriceFilters()}));
  assert.equal(before.datasets.length,2);
  assert.equal(await page.locator('#priceKpiGrid').isVisible(),false);
  assert.ok((await page.locator('#priceKpiScopeNote').innerText()).includes('no mezclar mercados'));
  assert.equal(await page.locator('#priceKpiSpecies').innerText(),'1');
  assert.notEqual(await page.locator('#priceKpiLast').innerText(),'Sin dato válido');
  assert.equal(await page.locator('#priceEvolutionLegend button').count(),2);
  await page.locator('#pricePeriodSelect').selectOption('0');
  let inspected=await page.locator('#pricePeriodValues').innerText();assert.ok(inspected.includes('Mercado Central de Buenos Aires')&&inspected.includes('Mercado de Corrientes'));
  await page.locator('#priceEvolutionLegend button').first().click();
  assert.equal(await page.locator('#priceEvolutionLegend button').first().getAttribute('aria-pressed'),'false');
  assert.equal(await page.evaluate('priceCharts.evolution.isDatasetVisible(0)'),false);
  inspected=await page.locator('#pricePeriodValues').innerText();assert.ok(!inspected.includes('Mercado Central de Buenos Aires')&&inspected.includes('Mercado de Corrientes'));
  await page.locator('#priceEvolutionLegend button').first().click();
  await page.locator('#priceChartMonthly').scrollIntoViewIfNeeded();
  const point=await page.evaluate(()=>{const chart=priceCharts.evolution,rect=chart.canvas.getBoundingClientRect(),p=chart.getDatasetMeta(0).data[2].getProps(['x','y'],true);return {x:rect.left+p.x,y:rect.top+p.y};});
  await page.mouse.click(point.x,point.y);await page.waitForFunction("document.getElementById('pricePeriodSelect').value==='2'");
  const after=await page.evaluate(()=>({datasets:priceCharts.evolution.data.datasets.map(d=>d.data),rows:filteredPriceData.length,filters:getPriceFilters()}));
  assert.deepEqual(after,before);
  for(const width of [1440,1000,640,360]) {
   await page.setViewportSize({width,height:800});
   assert.equal(await page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),false,`desborde ${width}px`);
   assert.equal(await page.locator('#pricePeriodSelect').isVisible(),true);
  }
  await page.setViewportSize({width:1310,height:800});
  if(process.env.MAYORISTAS_SCREENSHOT_DIR) {
   await page.locator('#priceEvolutionPanel').scrollIntoViewIfNeeded();
   await page.screenshot({path:require('path').join(process.env.MAYORISTAS_SCREENSHOT_DIR,'evolucion-interactiva.png')});
  }
  await page.locator('#priceObservations > summary').click();
  const first=page.locator('#priceTrafficLightBody .sa-semaphore-cell-button').first();await first.click();
  assert.equal(await first.getAttribute('aria-pressed'),'true');
  const detail=await page.locator('#priceSemaphoreDetail').innerText();assert.ok(detail.includes('Variación respecto al mes anterior') && detail.includes('$'));
  const second=page.locator('#priceTrafficLightBody .sa-semaphore-cell-button').nth(1);await second.focus();await page.keyboard.press('Enter');
  assert.equal(await second.getAttribute('aria-pressed'),'true');assert.equal(await first.getAttribute('aria-pressed'),'false');
  await page.locator('#priceDetailOrder').selectOption('increase');
  const changes=await page.locator('#priceTrafficLightBody tr').evaluateAll(rows=>rows.map(row=>Number(row.dataset.variation)));
  assert.ok(changes.every((value,index)=>!index||changes[index-1]>=value));
  await page.locator('#priceDetailSearch').fill('Tomate');assert.ok((await page.locator('#priceDetailCount').innerText()).includes('productos'));
  if(process.env.MAYORISTAS_SCREENSHOT_DIR) {
   await page.locator('#priceObservations').scrollIntoViewIfNeeded();
   await page.screenshot({path:require('path').join(process.env.MAYORISTAS_SCREENSHOT_DIR,'semaforo-interactivo.png')});
  }
  assert.deepEqual(errors,[]);console.log(JSON.stringify({periods:before.datasets[0].length,series:before.datasets.length,semaphoreRows:changes.length,errors}));
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
