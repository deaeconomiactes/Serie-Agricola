"""Local quantity UI smoke; independent CSV control, no acquisition."""
import argparse,csv,decimal,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

def run(url,channel,out):
 out.mkdir(parents=True,exist_ok=True);root=Path(__file__).resolve().parents[2];count=0;total=decimal.Decimal(0)
 with (root/'REGISTRO 2025 INTEGRADO.csv').open(encoding='utf-8-sig',newline='') as stream:
  for row in csv.DictReader(stream,delimiter=';'):
   if row['SERIE'].strip().upper() not in ['FRUTA','FRUTAS','HORTALIZA','HORTALIZAS'] or row['FECHA'].split('/')[-1]!='2025':continue
   try:value=decimal.Decimal(row['PESO'].replace('.','').replace(',','.'))
   except decimal.InvalidOperation:continue
   if value>0:count+=1;total+=value
 with sync_playwright() as pw:
  b=pw.chromium.launch(channel=channel,headless=True);page=b.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(url,wait_until='domcontentloaded');page.wait_for_function("document.getElementById('filterYear').options.length>1",timeout=120000);page.locator('#loadingOverlay').wait_for(state='hidden',timeout=120000)
  actual=page.evaluate('({count:filteredData.length,total:sumPeso(filteredData),raw:rawData.length,units:[...new Set(filteredData.map(r=>r.unidad))]})')
  assert actual['count']==count,(actual,count);assert abs(actual['total']-float(total))<1e-7;assert actual['units']==['TN']
  assert page.locator('#quantityVolume').inner_text()==page.locator('#totalProduction').text_content()
  assert 'Fuente estática' in page.locator('#quantityView').inner_text()
  assert not page.locator('#quantityRecords').evaluate('e=>e.open')
  assert not page.locator('#chartSpeciesDonut').is_visible();assert not page.locator('#chartMarket').is_visible()
  for target in ['quantitySummary','quantityProducts','quantityOrigins','quantitySeasonality']:
   page.locator(f'[data-qty-target={target}]').click();assert page.locator(f'[data-qty-target={target}]').get_attribute('aria-current')=='location'
  page.locator('#quantityMoreFilters > summary').click();assert page.locator('#filterDestino').is_visible();page.locator('#quantityMoreFilters > summary').press('Escape');assert not page.locator('#quantityMoreFilters').evaluate('e=>e.open')
  for width in [1440,1000,900,640,375]:
   page.set_viewport_size({'width':width,'height':1050})
   # Chart.js resizes asynchronously after the viewport event.
   page.wait_for_function('document.documentElement.scrollWidth<=innerWidth+1',timeout=5000)
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),width
   if width==375:assert not page.locator('.qt-rail').evaluate('e=>e.open')
   page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/f'{channel}-{width}.png'))
  page.set_viewport_size({'width':1440,'height':1050});page.locator('[data-qty-target=quantityRecords]').first.click();expect(page.locator('#quantityRecordBody > tr')).to_have_count(10)
  first=page.locator('#quantityRecordBody > tr').first.inner_text();page.locator('#quantityNext').click();assert page.locator('#quantityRecordBody > tr').first.inner_text()!=first
  page.locator('#quantityRecordSearch').fill('INEXISTENTE_XYZ');expect(page.locator('#quantityRecordBody > tr')).to_have_count(0);page.locator('#quantityRecordSearch').fill('');expect(page.locator('#quantityRecordBody > tr')).to_have_count(10)
  page.locator('#quantityRecordBody button').first.click();assert 'registro_interpretado' in page.locator('#quantityTechnical').inner_text()
  with page.expect_download() as info:page.locator('#quantityDownload').click()
  rows=list(csv.DictReader(Path(info.value.path()).open(encoding='utf-8-sig',newline=''),delimiter=';'));assert len(rows)==count
  assert sum(decimal.Decimal(row['Volumen']) for row in rows)==total
  comp=page.evaluate('Chart.getChart(document.getElementById("quantityCompositionChart")).data.datasets.map(d=>d.data)')
  for values in zip(*comp):assert all(v is None for v in values) or abs(sum(values)-100)<1e-9
  page.locator('#filterYear').select_option('2024');assert page.evaluate('filteredData.every(r=>r.year===2024)')
  page.locator('#filterYear').select_option('2025');page.locator('#quantityMoreFilters > summary').click();page.locator('#filterFrequency').select_option('diaria');page.locator('#quantityMoreFilters > summary').press('Escape')
  assert page.evaluate('quantityFrequency')=='diaria';assert page.evaluate('filteredData.length')==count
  page.locator('[data-module=priceView]').click();assert page.title()=='Precios mayoristas · Serie Agrícola';page.locator('[data-module=quantityView]').click();assert page.title()=='Cantidades transadas · Serie Agrícola'
  assert not errors,errors
  (out/'report.json').write_text(json.dumps({'result':'PASS','channel':channel,'control':actual,'independent_total':str(total),'errors':errors},indent=2),encoding='utf-8');b.close();print('PASS',channel,actual)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8771');p.add_argument('--channel',choices=['msedge','chrome'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.url,a.channel,a.output)
