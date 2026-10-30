/* Local smoke test. NODE_PATH must include the bundled playwright package. */
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.MAYORISTAS_URL || 'http://127.0.0.1:8768',{waitUntil:'domcontentloaded'});
 await page.locator('#loadingOverlay').waitFor({state:'hidden',timeout:120000});
 const start=Date.now();await page.locator('[data-module="priceView"]').click();
 await page.waitForFunction('typeof priceDeliveryActive !== "undefined" && priceDeliveryActive && !priceDeliveryPending',null,{timeout:120000});
 const performance=await page.evaluate(()=>({seconds:(Date.now()-window.__testStart)/1000,requests:priceDelivery.metrics.requests.length,
  bytes:priceDelivery.metrics.bytes,heap:window.performance.memory?.usedJSHeapSize}));
 performance.seconds=(Date.now()-start)/1000;
 const initialProducts=await page.locator('#priceFilterEspecie option').evaluateAll(options=>options.map(o=>({value:o.value,label:o.textContent})));
 const tomato=initialProducts.filter(o=>o.value==='Tomate');
 if(tomato.length!==1||!tomato[0].label.includes('en todos los mercados'))throw Error(JSON.stringify(initialProducts));
 if(initialProducts.some(o=>['Tomate Perita','Tomate Redondo','Tomate Cherry','Sandia Redonda Rayada'].includes(o.value)))throw Error(JSON.stringify(initialProducts));
 if(process.env.MAYORISTAS_SCREENSHOT_DIR) {
  await page.locator('#priceFilterEspecieTrigger').click();
  await page.screenshot({path:require('path').join(process.env.MAYORISTAS_SCREENSHOT_DIR,'producto.png')});
  await page.locator('#priceFilterEspecieTrigger').click();
 }
 async function select(id,values){await page.evaluate(({id,values})=>{const el=document.getElementById(id);[...el.options].forEach(o=>o.selected=values.includes(o.value));el.dispatchEvent(new Event('change',{bubbles:true}));},{id,values});}
 await select('priceFilterMercado',['Mercado Central de Buenos Aires','Mercado de Corrientes']);
 await page.waitForFunction('!priceDeliveryPending');
 await select('priceFilterEspecie',['Tomate']);
 await select('priceFilterProcedencia',['Corrientes']);
 const monthlyStatus=await page.locator('#mcbaMonthlyUpdateStatus').textContent();
 if(!monthlyStatus.includes('Actualizado')||monthlyStatus.includes('Error de actualización'))throw Error(`Estado mensual incorrecto: ${monthlyStatus}`);
 const result=await page.evaluate(()=>({counts:Object.fromEntries([...new Set(filteredPriceData.map(r=>r.mercado))].map(m=>[m,filteredPriceData.filter(r=>r.mercado===m).length])),
  status:document.getElementById('priceComparisonStatus').textContent,
  variety:[...document.getElementById('priceFilterVariedad').options].map(o=>o.value),
  plot:!!priceCharts.evolution}));
 if(!result.counts['Mercado Central de Buenos Aires']||!result.counts['Mercado de Corrientes'])throw Error(JSON.stringify(result));
 if(!result.status.includes('Tomate Redondo')||!result.plot)throw Error(JSON.stringify(result));
 if(!['Cherry','Perita','Redondo'].every(v=>result.variety.includes(v)))throw Error(JSON.stringify(result));
 const automatic=await page.evaluate(()=>({options:[...document.getElementById('priceComparisonChoice').options].map(o=>o.textContent),
  visible:!document.getElementById('priceComparisonControl').hidden,series:priceCharts.evolution?.data?.datasets?.map(x=>x.label)||[]}));
 if(automatic.options.length<2||!automatic.visible||automatic.series.length!==2)throw Error(JSON.stringify(automatic));
 if(process.env.MAYORISTAS_SCREENSHOT_DIR) await page.screenshot({path:require('path').join(process.env.MAYORISTAS_SCREENSHOT_DIR,'automatica.png')});
 const alternative=await page.evaluate(()=>{const el=document.getElementById('priceComparisonChoice');el.value=el.options[1].value;el.dispatchEvent(new Event('change',{bubbles:true}));return {selected:el.options[el.selectedIndex].textContent,status:document.getElementById('priceComparisonStatus').textContent,series:priceCharts.evolution?.data?.datasets?.length};});
 if(alternative.series!==2||!alternative.status.includes(alternative.selected))throw Error(JSON.stringify(alternative));
 await select('priceFilterVariedad',['Redondo']);
 for(const [id,value] of [['priceFilterCalidad','Primera'],['priceFilterTamano','MEDIANO'],['priceFilterGrado','P/I']])
  await page.evaluate(({id,value})=>{const el=document.getElementById(id);el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}));},{id,value});
 const pair=await page.evaluate(()=>({status:document.getElementById('priceComparisonStatus').textContent,
  series:priceCharts.evolution?.data?.datasets?.map(x=>x.label)||[]}));
 if(pair.series.length!==2||!pair.status.includes('TORITO'))throw Error(JSON.stringify(pair));
 if(process.env.MAYORISTAS_SCREENSHOT_DIR) {
  await page.locator('#priceEvolutionPanel').scrollIntoViewIfNeeded();
  await page.screenshot({path:require('path').join(process.env.MAYORISTAS_SCREENSHOT_DIR,'comparacion.png')});
 }
 await select('priceFilterMercado',['Mercado de Corrientes']);
 await page.waitForFunction('!priceDeliveryPending');
 await select('priceFilterVariedad',['Perita']);
 await page.evaluate(()=>{const el=document.getElementById('priceFilterEnvase');el.value='Torito X 18 Kg';el.dispatchEvent(new Event('change',{bubbles:true}));});
 const single=await page.evaluate(()=>({rows:filteredPriceData.length,plot:!!priceCharts.evolution,
  status:document.getElementById('priceComparisonStatus').textContent}));
 if(!single.rows||!single.plot||!single.status.includes('ARS'))throw Error(JSON.stringify(single));
 if(errors.length)throw Error(errors.join('\n'));
 console.log(JSON.stringify({performance,tomato,result,automatic,alternative,pair,single,errors}));await browser.close();
})().catch(error=>{console.error(error);process.exitCode=1;});
