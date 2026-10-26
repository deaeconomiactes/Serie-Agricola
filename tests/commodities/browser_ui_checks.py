"""Local visual-layer acceptance on actual prepared publications; no acquisition.

python tests/commodities/browser_ui_checks.py --channel msedge --output ABSOLUTE_PATH
"""
import argparse, csv, io, json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(url, channel, out):
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=channel, headless=True)
        page = browser.new_page(viewport={'width':1440, 'height':1050})
        errors=[];page.on('pageerror', lambda error:errors.append(str(error)))
        page.goto(url,wait_until='domcontentloaded',timeout=90000)
        page.locator('#loadingOverlay').wait_for(state='hidden',timeout=120000)
        page.wait_for_function("document.getElementById('filterYear').options.length>1",timeout=120000)
        page.locator('[data-module=commodityView]').click()
        page.locator('#commodityView[aria-busy=false]').wait_for(timeout=120000)
        assert not errors,errors
        results={}
        for family in ['magyp_internal','magyp_board','magyp_fas','magyp_fob','magyp_futures','sio']:
            if page.locator('#commodityFilterSource').input_value()!=family:
                page.locator(f'[data-co-family={family}]').click()
                page.wait_for_function('(f)=>commoditySource===f',arg=family,timeout=120000)
            assert page.title()=='Commodities agrícolas · Serie Agrícola',(page.title(),errors)
            assert page.locator(f'[data-co-family={family}]').get_attribute('aria-current')=='page'
            assert page.locator('#commodityUpdateStatus').is_visible()
            page.locator('#commodityMoreFilters > summary').click()
            assert page.locator('#commodityFilterSource').is_visible()
            assert page.locator('#commoditySioOriginGroup').is_visible()==(family=='sio')
            page.locator('#commodityMoreFilters > summary').press('Escape')
            assert not page.locator('#commodityMoreFilters').evaluate('e=>e.open')
            assert not page.locator('#commodityObservations').evaluate('e=>e.open')
            page.locator('#commodityObservations > summary').click()
            total=page.locator('#commodityLatestBody > tr').count()
            assert page.locator('#commodityLatestBody > tr:visible').count()<=10
            if total>10:
                page.locator('#commodityDetailNext').click()
                assert page.locator('#commodityDetailPage').inner_text().startswith('2 /')
            page.locator('#commodityDetailSearch').fill('SIN_RESULTADO_XYZ')
            assert page.locator('#commodityLatestBody > tr:visible').count()==0
            page.locator('#commodityDetailSearch').fill('')
            with page.expect_download() as info:page.locator('#commodityDownload').click()
            content=Path(info.value.path()).read_text(encoding='utf-8-sig')
            assert len(list(csv.reader(io.StringIO(content),delimiter=';')))==total+1
            page.locator('#commodityObservations > summary').click()
            results[family]={'detail_rows':total}
            for width in [1440,1000,900,640,375]:
                page.set_viewport_size({'width':width,'height':1050})
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(family,width)
                if width==375:
                    assert not page.locator('.co-rail').evaluate('e=>e.open')
                    page.locator('.co-rail > summary').click()
                    assert page.locator(f'[data-co-family={family}]').is_visible()
                    page.locator('.co-rail > summary').click()
            page.set_viewport_size({'width':1440,'height':1050})
        # Curve is an exact projection of published observations, not an averaged or rolled series.
        page.locator('[data-co-family=magyp_futures]').click()
        page.wait_for_function('commoditySource==="magyp_futures"')
        assert not page.locator('#commodityCurvePanel').is_visible()
        target=page.evaluate('(()=>{const r=getCommodityFilteredRows()[0];return {product:r.commodity,market:r.mercado};})()')
        page.locator('#commodityFilterCommodityTrigger').click()
        page.locator('#commodityFilterCommodityMenu').get_by_text(target['product'],exact=True).click()
        page.locator('#commodityFilterCommodityTrigger').click()
        page.locator('#commodityFilterMarket').select_option(target['market'])
        assert page.locator('#commodityCurvePanel').is_visible()
        data=page.evaluate('''()=>{const c=Chart.getChart(document.getElementById('commodityCurve'));const date=document.getElementById('commodityCurveDate').value;return {date,labels:c.data.labels,values:c.data.datasets[0].data,rows:getCommodityFilteredRows().filter(r=>r.fecha===date)};}''')
        assert len(data['labels'])==len(data['rows'])>=2
        for label,value in zip(data['labels'],data['values']):
            row=next(r for r in data['rows'] if r['condicion_comercial']==label)
            assert value==float(row['precio_mediana'])
        assert 'Observación: '+data['date'] in page.locator('#commodityCurveDescription').inner_text()
        page.screenshot(path=str(out/f'{channel}-curve.png'),full_page=True)
        results['curve']={'date':data['date'],'points':len(data['labels'])}
        page.locator('[data-module=priceView]').click()
        assert page.title()=='Precios mayoristas · Serie Agrícola'
        page.locator('[data-module=commodityView]').click()
        assert page.title()=='Commodities agrícolas · Serie Agrícola'
        assert not errors,errors
        (out/f'{channel}.json').write_text(json.dumps({'result':'PASS','errors':errors,'families':results},indent=2,ensure_ascii=False),encoding='utf-8')
        browser.close();print('PASS',channel)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8770');parser.add_argument('--channel',choices=['msedge','chrome'],required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.url,args.channel,args.output)
