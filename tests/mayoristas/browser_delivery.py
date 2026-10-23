"""Local Edge/Chrome acceptance; no source acquisition. Evidence stays outside Git."""
import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(url, channel, output):
    output.mkdir(parents=True,exist_ok=True)
    result={'channel':channel,'errors':[],'selections':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel=channel,headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1050})
        page.on('pageerror',lambda error:result['errors'].append(str(error)))
        page.goto(url,wait_until='domcontentloaded')
        page.locator('#loadingOverlay').wait_for(state='hidden',timeout=120000)
        assert not page.evaluate("performance.getEntriesByType('resource').some(r=>r.name.includes('/data/mayoristas/'))")
        start=time.monotonic();page.locator('[data-module="priceView"]').click()
        page.locator('#priceView[aria-busy="false"]').wait_for(timeout=120000)
        page.wait_for_function('priceDeliveryActive')
        result['initial']={'seconds':round(time.monotonic()-start,3),**page.evaluate("({...priceDelivery.metrics,rows:filteredPriceData.length,year:document.getElementById('priceFilterYear').value,memory:performance.memory?.usedJSHeapSize})")}
        assert result['initial']['year']=='2026'
        assert result['initial']['bytes']<1500000
        assert len(result['initial']['requests'])==3
        assert page.evaluate('priceCharts.evolution instanceof Chart') if page.evaluate("typeof priceCharts!=='undefined' && !!priceCharts.evolution") else page.locator('#priceView canvas').count()>0
        # A bad new year must keep both the previous chart data and selected controls.
        page.locator('#priceFilterMes').select_option('Mayo')
        previous=page.evaluate('JSON.stringify(filteredPriceData)')
        page.route('**/data/mayoristas/dashboard/*2024*.json.gz',lambda route:route.fulfill(status=200,body=b'corrupt'))
        page.locator('#priceFilterYear').select_option('2024')
        page.wait_for_function("document.getElementById('priceDeliveryStatus').textContent.includes('última vista válida')")
        assert page.evaluate('JSON.stringify(filteredPriceData)')==previous
        assert page.locator('#priceFilterYear').input_value()=='2026'
        assert page.locator('#priceFilterMes').input_value()=='Mayo'
        assert 'PIPELINE/UI DATA ERROR' in page.locator('#priceDeliveryStatus').text_content()
        page.unroute('**/data/mayoristas/dashboard/*2024*.json.gz')
        page.locator('#priceFilterMes').select_option('TODOS')
        for year in ['2024','2025','2026']:
            start=time.monotonic();before=page.evaluate('priceDelivery.metrics.bytes')
            page.locator('#priceFilterYear').select_option(year)
            page.wait_for_function("document.getElementById('priceView').getAttribute('aria-busy')==='false'")
            assert page.evaluate('validPriceData.every(r=>String(r.year)===document.getElementById("priceFilterYear").value)')
            result['selections'].append({'year':year,'seconds':round(time.monotonic()-start,3),'bytes':page.evaluate('priceDelivery.metrics.bytes')-before})
        # Keep the actual multi-select behavior; choose MCBA through the control event.
        page.evaluate("const s=document.getElementById('priceFilterMercado');[...s.options].forEach(o=>o.selected=o.value==='Mercado Central de Buenos Aires');s.dispatchEvent(new Event('change',{bubbles:true}));")
        page.wait_for_function("document.getElementById('priceView').getAttribute('aria-busy')==='false'")
        before=page.evaluate('priceDelivery.metrics.bytes');page.locator('#priceFilterFrequency').select_option('diaria')
        page.wait_for_function("document.getElementById('priceView').getAttribute('aria-busy')==='false'")
        assert page.evaluate("validPriceData.every(r=>r.mercado===MCBAPrices.MCBA) && validPriceData.some(r=>r.data_source==='MAGYP')")
        result['frequency_change_bytes']=page.evaluate('priceDelivery.metrics.bytes')-before
        page.locator('#priceFilterFrequency').select_option('mensual')
        page.wait_for_function("document.getElementById('priceView').getAttribute('aria-busy')==='false'")
        # Rapidly superseded selection cannot overwrite the final selection.
        page.evaluate("const y=document.getElementById('priceFilterYear');y.value='2025';y.dispatchEvent(new Event('change'));y.value='2026';y.dispatchEvent(new Event('change'));")
        page.wait_for_function("document.getElementById('priceView').getAttribute('aria-busy')==='false'")
        assert page.evaluate('validPriceData.every(r=>r.year===2026)')
        for width in [1440,1000,900,640]:
            page.set_viewport_size({'width':width,'height':1050});page.locator('#priceView').scroll_into_view_if_needed()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.screenshot(path=str(output/f'{channel}-{width}.png'))
        urls=page.evaluate("performance.getEntriesByType('resource').map(r=>r.name)")
        assert not any('PRECIOS_MAYORISTAS' in u or '/data/magyp/dashboard/mcba/' in u or '/data/mercado_central/' in u for u in urls)
        result['last_view_rows']=page.evaluate('filteredPriceData.length')
        assert not result['errors'],result['errors']
        browser.close()
    (output/f'{channel}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8768')
    parser.add_argument('--channel',choices=['msedge','chrome'],required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.url,args.channel,args.output)
