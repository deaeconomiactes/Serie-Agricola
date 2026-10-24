"""Opt-in local browser acceptance; pip install playwright, installed Edge/Chrome.

Not discovered by unittest. Starts no acquisition and writes screenshots outside Git.
Run against a locally served checkout: --url http://127.0.0.1:8767.
"""
import argparse
import json
import csv
import io
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(url, channel, output):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel=channel,headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
        errors=[];requests=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:requests.append(request.url))
        page.goto(url,wait_until='domcontentloaded')
        page.locator('[data-module="carnesView"]').wait_for()
        # Existing modules finish their normal boot before tab interactions.
        page.locator('#loadingOverlay').wait_for(state='hidden',timeout=90000)
        assert not any('/data/carnes/' in r or '/carnes.js' in r for r in requests)
        page.locator('[data-module="carnesView"]').click()
        def ready():
            page.wait_for_function("document.getElementById('carnesRoot').getAttribute('aria-busy') === 'false'")
            assert not page.locator('.carnes-notice').inner_text(),page.locator('.carnes-notice').inner_text()
        def change(key,value):
            if key=='family':
                page.get_by_role('button',name={'slaughter':'Faena bovina','production':'Producción bovina','carcass_weight':'Peso medio'}[value],exact=True).click();ready();return
            if key in ['province','category','age','method']:
                if not page.locator('.carnes-context-filters').evaluate('n=>n.open'):page.locator('.carnes-context-filters > summary').click()
            page.locator('#carnes-'+key).select_option(value);ready()
        ready()
        assert page.get_by_role('button',name='Faena bovina',exact=True).get_attribute('aria-pressed')=='true'
        assert page.locator('#carnes-year').is_visible() and page.locator('#carnes-group').is_visible()
        assert not page.locator('#carnes-category').is_visible(), 'Contextual filters start collapsed'
        assert not page.locator('.carnes-records').first.is_visible(), 'Observation table starts closed'
        page.locator('.carnes-rail').get_by_role('button',name='Metodología',exact=True).click()
        assert page.locator('.carnes-methodology').evaluate('n=>n.open')
        page.locator('.carnes-methodology > summary').click()
        page.locator('.carnes-rail').get_by_role('button',name='Observaciones',exact=True).click()
        assert page.locator('.carnes-records').first.is_visible()
        page.keyboard.press('Enter')
        assert not page.locator('.carnes-records').first.is_visible()
        page.locator('.carnes-rail').get_by_role('button',name='Observaciones',exact=True).click()
        assert page.locator('.carnes-records').first.is_visible()
        assert page.locator('.carnes-observations > summary').evaluate('e=>e===document.activeElement')
        page.keyboard.press('Enter')
        assert not page.locator('.carnes-records').first.is_visible()
        page.locator('.carnes-observations > summary').click()
        page.keyboard.press('Enter')
        assert not page.locator('.carnes-records').first.is_visible(), 'Keyboard can close the table'
        page.keyboard.press('Enter')
        page.locator('.carnes-records .carnes-detail-button').first.click()
        assert page.get_by_role('dialog').is_visible()
        page.locator('.carnes-technical > summary').click()
        assert 'raw_sha256' in page.get_by_role('dialog').inner_text()
        page.keyboard.press('Escape')
        assert not page.get_by_role('dialog').is_visible()
        assert page.locator('.carnes-records .carnes-detail-button').first.evaluate('n=>n===document.activeElement')
        page.locator('.carnes-observations > summary').click()
        assert not page.locator('.header-summary').is_visible(), 'Quantity KPIs must not appear as meat KPIs'
        page.locator('.carnes-context-filters > summary').click()
        page.locator('#carnes-category').focus()
        page.keyboard.press('Escape')
        assert not page.locator('.carnes-context-filters').evaluate('n=>n.open')
        assert page.locator('.carnes-context-filters > summary').evaluate('n=>n===document.activeElement')
        assert page.locator('#carnesView .kpi-value').first.inner_text()=='1.045.293'
        assert page.locator('#carnesView .carnes-state').inner_text()=='Actualizado'
        assert 'Dato provisorio' in page.locator('.carnes-selection-note').inner_text()
        assert page.locator('#carnesView canvas').first.evaluate('(canvas)=>!!Chart.getChart(canvas)')
        assert not any('indicators_archive' in r for r in requests)
        initial=page.evaluate('document.getElementById("carnesRoot")._carnesView.loader.metrics')
        page.locator('#carnesView').scroll_into_view_if_needed()
        page.screenshot(path=str(output/f'{channel}-desktop.png'),full_page=True)

        change('province','BUENOS AIRES')
        assert page.locator('#carnes-category').is_disabled()
        assert 'no aplican' in page.locator('.carnes-method').text_content()
        assert not page.locator('#carnes-category').is_visible()
        share=page.locator('#carnesView .kpi-value').nth(3).inner_text();assert '%' in share
        change('province','Argentina');change('category','Novillo');change('age','6 dientes')
        assert page.locator('#carnes-province').input_value()=='Argentina'
        change('category','TOTAL');change('year','2019')
        assert page.locator('#carnes-method').is_visible()
        assert 'bubalinos' in page.locator('#carnes-species option:checked').text_content()
        change('method','pre_2019_weight_sex_categories')
        assert 'Clasificación anterior' in page.locator('#carnesView .carnes-composition .chart-desc').inner_text()
        change('year','2026');change('frequency','year_to_date')
        assert 'Acumulado enero–septiembre 2026' in page.locator('#carnesView .kpi-unit').first.inner_text()
        assert not page.locator('#carnes-month').is_visible()
        change('frequency','monthly')

        page.get_by_role('button',name='Producción bovina',exact=True).click()
        page.get_by_role('button',name='Peso medio',exact=True).click();ready()
        assert page.locator('#carnes-family').input_value()=='carcass_weight'
        assert page.locator('#carnes-category').input_value()=='Novillito'
        assert 'kg res con hueso' in page.locator('#carnesView .kpi-unit').first.inner_text()
        assert not page.locator('#carnes-province').is_visible()
        page.screenshot(path=str(output/f'{channel}-weight.png'),full_page=True)
        change('category','TOTAL')
        assert page.locator('#carnesView .kpi-value').first.inner_text()=='Sin dato publicado'
        assert 'sin resultado' in page.locator('.carnes-selection-note').inner_text()
        change('family','production')
        assert 'toneladas res con hueso' in page.locator('#carnesView .kpi-unit').first.inner_text()
        assert not page.locator('#carnesView .carnes-breakdown .chart-card').first.is_visible()
        change('group','sspm')
        assert 'no identificada' in page.locator('.carnes-selection-note').inner_text()
        change('family','slaughter');change('group','sspm');change('year','1980')
        assert not page.locator('#carnes-province').is_visible()
        assert page.locator('#carnesView .carnes-records tbody tr').count()==10
        page.locator('.carnes-observations > summary').click()
        with page.expect_download() as download_info:
            page.get_by_role('button',name='Descargar selección CSV',exact=True).click()
        downloaded=list(csv.DictReader(io.StringIO(Path(download_info.value.path()).read_text(encoding='utf-8-sig'))))
        assert len(downloaded)==12, 'Export includes every observation beyond visible rows'
        expected=page.evaluate('''()=>{const v=document.getElementById('carnesRoot')._carnesView;return v.series.map(r=>Object.fromEntries(Carnes.FIELDS.map(k=>[k,r[k]])));}''')
        assert downloaded==expected, 'Export retains all original values, units and trace fields'
        page.get_by_role('button',name='Siguiente',exact=True).click()
        assert page.locator('#carnesView .carnes-records tbody tr').count()==2
        page.get_by_role('button',name='Anterior',exact=True).click()
        page.get_by_label('Buscar observaciones',exact=True).fill('enero')
        assert page.locator('#carnesView .carnes-records tbody tr').count()==1
        page.get_by_label('Buscar observaciones',exact=True).fill('')
        assert page.locator('#carnesView .carnes-records tbody tr').count()==10
        change('frequency','annual')
        assert 'Año completo' in page.locator('#carnesView .kpi-unit').first.inner_text()
        change('group','detail');change('frequency','monthly');change('year','2026')

        for status,label in [('SOURCE_UNAVAILABLE','Último dato válido'),('NO_PUBLICATION','Sin nueva publicación'),('PIPELINE_ERROR','Error de actualización'),('UPDATED','Actualizado')]:
            page.evaluate('''status=>{const v=document.getElementById('carnesRoot')._carnesView;
                v.loader.states.magyp_slaughter_current.status=status;v.render();}''',status)
            assert label in page.locator('#carnesView .carnes-state').inner_text()
        before_history=len([r for r in requests if 'indicators_archive' in r]);assert before_history==0
        # A corrupt new shard must not replace the rendered last-valid selection.
        prior=page.locator('#carnesView .kpi-value').first.inner_text()
        pattern='**/magyp_slaughter_2024-slaughter-monthly-2024-*.csv.gz'
        page.route(pattern,lambda route:route.fulfill(status=200,body=b'corrupt'))
        page.locator('#carnes-year').select_option('2024')
        page.wait_for_function("document.getElementById('carnesRoot').getAttribute('aria-busy') === 'false'")
        assert 'conserva la' in page.locator('.carnes-notice').inner_text()
        assert page.locator('#carnesView .kpi-value').first.inner_text()==prior
        page.unroute(pattern);change('year','2026')
        page.locator('.carnes-history > summary').click()
        if page.locator('.carnes-context-filters').evaluate('n=>n.open'):page.locator('.carnes-context-filters > summary').click()
        page.locator('.carnes-observations > summary').click()
        page.wait_for_function("document.querySelector('#carnes-history-year') && document.querySelector('.carnes-history-content tbody tr')")
        assert 'Serie histórica finalizada' in page.locator('.carnes-history-content .carnes-metadata').inner_text()
        page.locator('#carnes-history-metric').select_option('novillo_price_USD')
        page.wait_for_function("document.querySelector('.carnes-history-content tbody').innerText.includes('USD/kg vivo')")
        page.locator('#carnes-history-family').select_option('exports')
        page.wait_for_function("document.querySelector('.carnes-history-content tbody').innerText.includes('toneladas equivalentes')")
        page.locator('.carnes-history > summary').click()
        for width in [1440,1000,900,640]:
            page.set_viewport_size({'width':width,'height':1000})
            page.locator('#carnesView').scroll_into_view_if_needed()
            page.screenshot(path=str(output/f'{channel}-{width}.png'),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), f'Unexpected horizontal page overflow: {width}'
            assert page.locator('#carnesView .kpi-card:visible').count()<=4
        assert not errors,errors
        page.locator('[data-module="priceView"]').click()
        assert page.locator('#priceView').evaluate("n=>n.classList.contains('is-active')")
        assert not page.locator('.header-summary').is_visible()
        page.locator('[data-module="commodityView"]').click()
        assert page.locator('#commodityView').evaluate("n=>n.classList.contains('is-active')")
        assert not page.locator('.header-summary').is_visible()
        page.locator('[data-module="quantityView"]').click()
        assert page.locator('.header-summary').is_visible()
        report={'browser':channel,'initial_carnes_payload':initial,'javascript_errors':errors,
            'checks':'PASS: lazy, filters, province/category, annual/YTD, provisional, weight missing, rapid selection, statuses, history, responsive, existing tabs'}
        (output/f'{channel}-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'browser':channel,'initial_bytes':initial['bytes'],'initial_requests':len(initial['requests']),'result':'PASS'}))
        browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8767')
    parser.add_argument('--channel',choices=['msedge','chrome'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.url,args.channel,args.output)
