"""Opt-in Playwright UI acceptance against local prepared data; no acquisition."""
import argparse
import csv
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(url, channel, output):
    output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2]
    with (root/'data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_DIARIO.csv').open(encoding='utf-8-sig') as stream:
        rows=list(csv.DictReader(stream,delimiter=';'))
    target=next(r for r in rows if r['commodity']=='Maíz' and r['moneda']=='USD' and r['fecha']=='2026-09-09' and r['lugar_entrega']=='Rosario NEn destino')
    series=[r for r in rows if r['series_id']==target['series_id']]
    expected=max(series,key=lambda r:r['fecha'])['precio_mediana']
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel=channel,headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1050})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(url,wait_until='domcontentloaded')
        page.locator('#loadingOverlay').wait_for(state='hidden',timeout=120000)
        page.locator('[data-module="commodityView"]').click()
        try:
            page.locator('#commodityView[aria-busy="false"]').wait_for(timeout=120000)
        except Exception:
            page.screenshot(path=str(output/f'{channel}-failure.png'))
            print(json.dumps({'errors':errors,'state':page.locator('#commodityView').get_attribute('aria-busy'),
                              'status':page.locator('#commodityDataStatus').text_content()},ensure_ascii=False))
            raise
        page.locator('#commodityFilterSource').select_option('sio')
        page.locator('#commoditySioOriginGroup').wait_for(state='visible')
        assert page.locator('#commodityMarketLabel').text_content()=='Lugar de entrega'
        assert 'Seleccioná una serie' in page.locator('#commodityKpiMedian').inner_text()
        assert 'Sin plaza' not in page.locator('#commodityView').inner_text()
        assert 'no precio mensual oficial' in page.locator('#commodityMethodNote').inner_text()
        page.locator('#commodityFilterFrequency').select_option('diaria')
        page.locator('#commodityFilterCommodityTrigger').click()
        page.locator('#commodityFilterCommodityMenu').get_by_text('Maíz',exact=True).click()
        page.locator('#commodityFilterCommodityTrigger').click()
        page.locator('#commodityFilterCurrency').select_option('USD')
        page.locator('#commodityFilterMarket').select_option(target['lugar_entrega'])
        page.locator('#commodityFilterCondition').select_option(target['condicion_serie'])
        page.locator('#commodityFilterOrigin').select_option(target['procedencia'])
        actual=page.locator('#commodityKpiMedian').inner_text()
        assert actual==expected.replace('.',','),(actual,expected)
        assert page.locator('#commodityLatestBody tr').count()==1
        assert page.locator('#commodityPriceTrend').evaluate('(canvas)=>!!Chart.getChart(canvas)')
        for width in (1440,1000,900,640):
            page.set_viewport_size({'width':width,'height':1050})
            page.locator('#commodityView').scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(output/f'{channel}-sio-{width}.png'))
        page.locator('#commodityLatestBody summary').click()
        assert 'LA PAMPAREALICO' in page.locator('#commodityLatestBody').inner_text()
        assert 'Capturas:' in page.locator('#commodityLatestBody').inner_text()
        page.locator('#commodityFilterFrequency').select_option('mensual')
        assert 'agregación' in page.locator('#commodityMethodNote').inner_text().lower()
        assert page.locator('#commodityKpiMedian').inner_text()!='Seleccioná una serie'
        page.locator('#commodityFilterSource').select_option('magyp_internal')
        assert not page.locator('#commoditySioOriginGroup').is_visible()
        assert page.locator('#commodityMarketLabel').text_content()=='Mercado / plaza'
        assert page.locator('#commodityFilterFrequency').input_value()=='mensual'
        assert not errors,errors
        (output/f'{channel}-report.json').write_text(json.dumps({'channel':channel,'result':'PASS','widths':[1440,1000,900,640],'errors':errors,'selected_series':target['series_id'],'observed_price':actual},indent=2),encoding='utf-8')
        print(json.dumps({'channel':channel,'result':'PASS','observed_price':actual}))
        browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8768')
    parser.add_argument('--channel',choices=['msedge','chrome'],required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.url,args.channel,args.output)
