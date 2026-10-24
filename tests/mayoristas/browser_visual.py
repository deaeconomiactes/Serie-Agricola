"""Opt-in visual and interaction checks for the institutional wholesale presentation.
Writes screenshots and exact rendered snapshots outside Git; no acquisition or transformation.
"""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--url',default='http://127.0.0.1:8767');p.add_argument('--channel',choices=['msedge','chrome'],default='msedge');a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(channel=a.channel,headless=True);page=b.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(a.url,wait_until='domcontentloaded',timeout=90000);page.locator('#loadingOverlay').wait_for(state='hidden',timeout=120000);page.locator('[data-module="priceView"]').click()
 def ready():page.locator('#priceView[aria-busy="false"]').wait_for(timeout=120000)
 ready();snap={}
 if page.locator('#priceMoreFilters').count():assert page.title()=='Precios mayoristas · Serie Agrícola'
 def snapshot():return page.evaluate('''()=>{const clone=document.getElementById('priceTrafficLightBody').cloneNode(true);clone.querySelectorAll('tr').forEach(tr=>tr.removeAttribute('hidden'));return ({filters:getPriceFilters(),frequency:priceFrequency,rows:filteredPriceData,kpis:Object.fromEntries([...document.querySelectorAll('#priceView .kpi-value')].map(e=>[e.id,e.textContent])),charts:Object.fromEntries(Object.entries(priceCharts).map(([k,c])=>[k,c?{labels:c.data.labels,datasets:c.data.datasets.map(d=>({label:d.label,data:d.data}))}:null])),table:clone.innerHTML})}''')
 snap['monthly']=snapshot()
 for w in [1440,900]:
  page.set_viewport_size({'width':w,'height':1050});page.screenshot(path=str(out/f'{a.channel}-{w}-monthly.png'),full_page=True)
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
 page.set_viewport_size({'width':1440,'height':1050})
 if page.locator('#priceMoreFilters').count():
  page.get_by_role('button',name='Metodología',exact=True).click();assert page.locator('#priceMethodology').evaluate('e=>e.open');page.locator('#priceMethodology > summary').click()
  page.locator('#priceFilterEspecieTrigger').click();menu=page.locator('[data-multi-select=priceFilterEspecie] .multi-select-dropdown');assert menu.is_visible();assert menu.evaluate('e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.left+15,r.top+15));}');page.locator('#priceFilterEspecieTrigger').click()
  page.locator('#priceMoreFilters').evaluate('(e)=>e.open=false');page.locator('#priceMoreFilters > summary').click();page.screenshot(path=str(out/f'{a.channel}-1440-filters.png'),full_page=True);page.locator('#priceMoreFilters > summary').press('Escape')
  assert not page.locator('#priceObservations').evaluate('e=>e.open')
  page.get_by_role('button',name='Detalle mensual',exact=True).click();assert page.locator('#priceObservations').evaluate('e=>e.open');assert page.locator('#priceObservations > summary').evaluate('e=>e===document.activeElement')
  page.screenshot(path=str(out/f'{a.channel}-1440-detail.png'),full_page=True)
  if page.locator('.price-semaphore-table tbody tr').count()>10:assert page.locator('.price-semaphore-table tbody tr:visible').count()<=10
  page.locator('#priceDetailSearch').fill('INEXISTENTE_XYZ');assert page.locator('.price-semaphore-table tbody tr:visible').count()==0;page.locator('#priceDetailSearch').fill('')
  page.locator('#priceObservations > summary').click()
  for w in [1000,640,375]:
   page.set_viewport_size({'width':w,'height':1050});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1');page.screenshot(path=str(out/f'{a.channel}-{w}.png'),full_page=True)
 page.locator('[data-module=quantityView]').click();assert page.title()=='Tránsito y Comercialización Frutihortícola – Serie 2024-2025'
 assert not errors,errors
 (out/f'{a.channel}-snapshot.json').write_text(json.dumps(snap,ensure_ascii=False),encoding='utf-8');b.close()
print('PASS',a.channel)
