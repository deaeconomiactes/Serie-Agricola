"""Comprobación optativa contra un servidor local del checkout."""
import csv
import io
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def run():
    for width in (1440,390):
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page(viewport={'width':width,'height':900},accept_downloads=True);errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto('http://127.0.0.1:8768',wait_until='domcontentloaded');page.locator('#loadingOverlay').wait_for(state='hidden',timeout=90000)
            page.locator('[data-module="carnesView"]').click();page.wait_for_function("document.getElementById('carnesRoot').getAttribute('aria-busy') === 'false'",timeout=90000)
            page.get_by_role('button',name='Exportaciones bovinas',exact=True).click();page.wait_for_function("document.querySelector('#carnes-export-end').options.length > 24",timeout=90000)
            page.locator('#carnes-export-start').select_option('2025-01-01');page.locator('#carnes-export-end').select_option('2026-09-01')
            panel=page.locator('.carnes-exports-panel:visible');assert '675.191,55' in panel.locator('.kpi-value').all_inner_texts()
            assert 'sin identificar explícitamente FOB' in panel.inner_text()
            assert panel.locator('canvas').count()==3
            with page.expect_download() as download:page.get_by_role('button',name='Descargar selección CSV',exact=True).click()
            rows=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))))
            assert len(rows)==21 and rows[0]['date']=='2025-01-01' and rows[-1]['date']=='2026-09-01'
            assert abs(float(rows[-1]['usd_per_tonne_rch'])-float(rows[-1]['usd_thousands'])*1000/float(rows[-1]['tonnes_rch']))<1e-8
            assert rows[-1]['raw_sha256'] and rows[-1]['source_locator']
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth') and not errors
            page.screenshot(path=str(Path(__import__('os').environ['TEMP'])/f'exportaciones-check-{width}.png'),full_page=True)
            browser.close()
    print(json.dumps({'result':'PASS','widths':[1440,390]}))

if __name__=='__main__':run()
