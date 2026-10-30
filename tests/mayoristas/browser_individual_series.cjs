/* Exercise broad filters without presenting incompatible series as a comparison. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
    const browser = await chromium.launch({channel:'msedge',headless:true});
    try {
        const page = await browser.newPage({viewport:{width:1310,height:800}});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.goto('http://127.0.0.1:8768/', {waitUntil:'domcontentloaded'});
        await page.locator('#loadingOverlay').waitFor({state:'hidden',timeout:120000});
        await page.locator('[data-module="priceView"]').click();
        await page.waitForFunction('priceDeliveryActive && !priceDeliveryPending', null, {timeout:120000});
        const select = async (id,value) => page.evaluate(({id,value}) => {
            const el = document.getElementById(id);
            [...el.options].forEach(option => { option.selected = option.value === value; });
            el.dispatchEvent(new Event('change',{bubbles:true}));
        },{id,value});
        await page.evaluate(() => {
            const select = document.getElementById('priceFilterMercado');
            [...select.options].forEach(option => { option.selected = ['Mercado Central de Buenos Aires','Mercado de Corrientes'].includes(option.value); });
            select.dispatchEvent(new Event('change',{bubbles:true}));
        });
        await page.waitForFunction(() => !priceDeliveryPending,null,{timeout:120000});
        for (const product of ['Naranja','Banana','Cebolla']) {
            await select('priceFilterEspecie',product);
            await page.waitForFunction(() => !priceDeliveryPending && Boolean(priceCharts.evolution),null,{timeout:120000});
            assert.match(await page.locator('#priceComparisonStatus').innerText(),/Serie individual, no es comparación entre mercados/);
            assert.equal(await page.locator('#priceIndividualSeriesControl').isVisible(),true);
            assert.equal(await page.evaluate('priceCharts.evolution.data.datasets.length'),1);
            const data = await page.evaluate(() => {
                const groups = getIndividualPriceSeries(filteredPriceData,priceUnitMode,priceFrequency);
                const group = groups.find(item => item.key === document.getElementById('priceIndividualSeriesChoice').value);
                return {options:groups.length,markets:[...new Set(group.rows.map(row=>row.mercado))],product:group.rows.map(getPriceProduct)};
            });
            assert.ok(data.options > 1);
            assert.equal(data.markets.length,1);
            assert.ok(data.product.every(value=>value===product));
            if (product === 'Naranja' && process.env.MAYORISTAS_SCREENSHOT_DIR) {
                await page.locator('#priceComparisonStatus').scrollIntoViewIfNeeded();
                await page.screenshot({path:require('path').join(process.env.MAYORISTAS_SCREENSHOT_DIR,'naranja-series.png')});
            }
            console.log(`${product}: ${data.options} series individuales disponibles`);
            const oldKey = await page.locator('#priceIndividualSeriesChoice').inputValue();
            await page.locator('#priceIndividualSeriesChoice').selectOption({index:1});
            assert.notEqual(await page.locator('#priceIndividualSeriesChoice').inputValue(),oldKey);
            assert.equal(await page.evaluate('priceIndividualSeriesChoice'),await page.locator('#priceIndividualSeriesChoice').inputValue());
            assert.equal(await page.evaluate('priceCharts.evolution.data.datasets.length'),1);
        }
        await select('priceFilterEspecie','Tomate');
        await select('priceFilterProcedencia','Corrientes');
        await page.waitForFunction(() => !priceDeliveryPending && priceCharts.evolution?.data.datasets.length === 2,null,{timeout:120000});
        assert.match(await page.locator('#priceComparisonStatus').innerText(),/Comparación utilizada/);
        assert.equal(await page.locator('#priceIndividualSeriesControl').isVisible(),false);
        assert.deepEqual(errors,[]);
        console.log('Naranja, Banana y Cebolla: series individuales; Tomate/Corrientes: comparación entre mercados.');
    } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
