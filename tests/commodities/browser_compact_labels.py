"""Compact labels retain full references and original economic chart data."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright

p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8770');p.add_argument('--channel',default='chrome');p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
baseline=json.loads(a.baseline.read_text(encoding='utf-8'));results={}
with sync_playwright() as pw:
 b=pw.chromium.launch(channel=a.channel,headless=True);page=b.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(a.url,wait_until='domcontentloaded');page.wait_for_function("document.getElementById('filterYear').options.length>1",timeout=120000);page.locator('[data-module=commodityView]').click();page.locator('#commodityView[aria-busy=false]').wait_for(timeout=120000)
 for family in ['sio','magyp_futures']:
  page.locator(f'[data-co-family={family}]').click();page.wait_for_function('(f)=>commoditySource===f',arg=family,timeout=120000)
  actual=page.evaluate('''()=>({rows:getCommodityFilteredRows(),latest:getCommodityLatestRows(),charts:Object.fromEntries(Object.entries(commodityCharts).map(([k,c])=>[k,c?{labels:c.data.labels,datasets:c.data.datasets.map(d=>({label:d.label,data:d.data}))}:null]))})''')
  for key in ['rows','latest','charts']:assert actual[key]==baseline[family][key],(family,key)
  assert page.evaluate('''html=>{const t=document.createElement('template');t.innerHTML=html;const cells=rows=>Array.from(rows,r=>Array.from(r.cells,c=>c.dataset.fullLabel||c.textContent));return JSON.stringify(cells(t.content.querySelectorAll('tr')))===JSON.stringify(cells(document.getElementById('commoditySemaphoreBody').rows));}''',baseline[family]['semaphore']),(family,'matrix values/labels')
  option_values=page.evaluate('''()=>Object.fromEntries([...document.querySelectorAll('#commodityView select[id^=commodityFilter]')].filter(e=>!e.closest('.filter-group')?.hidden).map(e=>[e.id,[...e.options].map(o=>[o.value,o.dataset.fullLabel||o.text,o.disabled])]))''')
  normalize_options=lambda options:[[value,' '.join(label.split()),disabled] for value,label,disabled in options]
  for key,options in option_values.items():assert normalize_options(options)==normalize_options(baseline[family]['filters'][key]['options']),(family,key)
  labels=page.evaluate('''()=>{const c=Chart.getChart(document.getElementById('commodityPriceTrend'));return c.legend.legendItems.map((item,i)=>({short:item.text,full:c.data.datasets[item.datasetIndex].label}));}''')
  assert all(len(item['short'])<=46 for item in labels)
  page.locator('#commodityLabelKey > summary').click()
  full=page.locator('#commodityLabelKey .co-series-labels dd').all_text_contents()
  assert all(item['full'] in full for item in labels if len(item['full'])>32)
  page.locator('#commodityLabelKey > summary').click()
  page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(a.output/f'{family}-1440.png'),full_page=True)
  if family=='sio':
   page.locator('#commodityHistoryPanel > summary').click();page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(a.output/'sio-matrix-1440.png'),full_page=True);page.locator('#commodityHistoryPanel > summary').click()
  page.locator('#commodityMoreFilters > summary').click()
  options=page.locator('#commodityView option[data-full-label]').evaluate_all('(items)=>items.map(o=>({short:o.textContent,full:o.dataset.fullLabel,title:o.title,aria:o.getAttribute("aria-label")}))')
  assert all(len(o['short'])<45 and o['full']==o['title']==o['aria'] for o in options)
  page.locator('#commodityMoreFilters > summary').press('Escape')
  for width in [900,375]:
   page.set_viewport_size({'width':width,'height':1050});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1');page.screenshot(path=str(a.output/f'{family}-{width}.png'))
  page.set_viewport_size({'width':1440,'height':1050});results[family]={'economic_equivalence':True,'short_labels':len(labels),'full_filter_options':len(options)}
 assert not errors,errors
 (a.output/'report.json').write_text(json.dumps(results,indent=2),encoding='utf-8');b.close();print('PASS',a.channel,json.dumps(results))
