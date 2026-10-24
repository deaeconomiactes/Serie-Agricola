"""Local analytical acceptance: independent CSV arithmetic, references, race and keyboard."""
import argparse,csv,gzip,io,json,math
from pathlib import Path
from playwright.sync_api import sync_playwright

def run(url,channel,out):
    out.mkdir(parents=True,exist_ok=True)
    folder=Path('data/carnes/dashboard');index=json.loads((folder/'index.json').read_text())
    def source_rows(source,year):
        entry=index['sources'][source];f=next(f for f in entry['files'] if f['family']=='slaughter' and f['frequency']=='monthly' and f['year']==str(year))
        return list(csv.DictReader(io.StringIO(gzip.decompress((folder/f['path']).read_bytes()).decode())))
    def total_rows(rows):return sorted([r for r in rows if r['table_id']=='slaughter/category_age' and r['category']=='Total general' or r['source_id']=='sspm_40_3' and r['metric']=='vacunos_cabezas'],key=lambda r:r['observation_date'])
    current=source_rows('magyp_slaughter_current',2026);previous=source_rows('magyp_slaughter_2025',2025)
    now=total_rows(current);before=total_rows(previous);anchor=now[-1];month=int(anchor['observation_date'][5:7]);value=float(anchor['value'])
    current_ytd=sum(float(r['value']) for r in now if int(r['observation_date'][5:7])<=month)
    previous_ytd=sum(float(r['value']) for r in before if int(r['observation_date'][5:7])<=month)
    rolling_rows=[r for r in before if int(r['observation_date'][5:7])>month]+[r for r in now if int(r['observation_date'][5:7])<=month]
    rolling=sum(float(r['value']) for r in rolling_rows)/12
    provinces=sorted([r for r in current if r['entity_type']=='province' and r['observation_date']==anchor['observation_date']],key=lambda r:-float(r['value']))
    top3=sum(float(r['value']) for r in provinces[:3])/value*100
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel=channel,headless=True);page=browser.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url);page.locator('#loadingOverlay').wait_for(state='hidden',timeout=90000);page.locator('[data-module="carnesView"]').click()
        def ready():
            page.wait_for_function("document.getElementById('carnesRoot').getAttribute('aria-busy')==='false'")
            assert not page.locator('.carnes-notice').inner_text()
        ready()
        result=page.evaluate('''()=>{const v=document.getElementById('carnesRoot')._carnesView,a=v.analyticsResult;return {ytd:a.ytd.value,base:a.ytd.base,delta:a.ytd.variation,moving:a.rolling.mean,top3:a.territory.top3,composition:a.compositionChange.map(i=>({category:i.row.category,age:i.row.age_class,share:i.share,pp:i.pp})),payload:v.loader.metrics.bytes};}''')
        for actual,expected in [(result['ytd'],current_ytd),(result['base'],previous_ytd),(result['delta'],(current_ytd/previous_ytd-1)*100),(result['moving'],rolling),(result['top3'],top3)]:assert math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-9),(actual,expected)
        assert result['payload']==177440 and len(result['composition'])==15
        assert page.locator('.carnes-ranked-item').count()==6
        page.get_by_role('button',name='Ver todas las provincias',exact=True).click();assert page.locator('.carnes-ranked-item').count()==len(provinces)
        page.get_by_role('button',name='Ver primeras 6',exact=True).click()
        assert not page.locator('.carnes-records').first.is_visible()
        page.screenshot(path=str(out/f'{channel}-analytical-1440.png'),full_page=True)
        page.locator('.carnes-references > summary').click()
        page.wait_for_function("document.getElementById('carnesRoot')._carnesView.referenceResult!==null || document.querySelector('.carnes-references > p').textContent.startsWith('Referencias no disponibles:')")
        assert page.evaluate("document.getElementById('carnesRoot')._carnesView.referenceResult?.years.map(y=>y.year)")==[2024,2025],page.locator('.carnes-references > p').inner_text()
        assert page.locator('.carnes-heatmap-cell').count()==0
        assert '3 años' in page.locator('.carnes-references > p').inner_text()
        # Earlier DNCCA total rows include bubalinos: only SSPM's own history is used below.
        page.locator('#carnes-group').select_option('sspm');ready()
        if not page.locator('.carnes-references').evaluate('n=>n.open'):page.locator('.carnes-references > summary').click()
        page.wait_for_function("document.getElementById('carnesRoot')._carnesView.referenceResult?.seasonality && document.querySelectorAll('.carnes-heatmap-cell').length===72")
        historical=page.evaluate('''()=>{const v=document.getElementById('carnesRoot')._carnesView,r=v.referenceResult;return {min:r.range.min,max:r.range.max,count:r.range.rows.length,years:r.years.map(y=>y.year),season:r.seasonality.map(m=>m.mean),payload:v.loader.metrics.bytes};}''')
        histories={year:total_rows(source_rows('sspm_40_3',year)) for year in range(2021,2026)}
        assert historical['years']==list(range(2021,2026)) and historical['count']==36
        for m in range(12):assert math.isclose(historical['season'][m],sum(float(histories[y][m]['value']) for y in histories)/5,rel_tol=1e-12)
        sspm_now=total_rows(source_rows('sspm_40_3',2026));sspm_anchor=sspm_now[-1]
        month_index=lambda r:int(r['observation_date'][:4])*12+int(r['observation_date'][5:7])-1
        anchor_index=month_index(sspm_anchor)
        prior36=[r for year in range(2023,2026) for r in histories[year] if anchor_index-36<=month_index(r)<anchor_index]+[r for r in sspm_now if month_index(r)<anchor_index]
        assert len(prior36)==36
        assert historical['min']==min(float(r['value']) for r in prior36) and historical['max']==max(float(r['value']) for r in prior36)
        missing=page.locator('.carnes-heatmap-cell').nth(60+int(sspm_anchor['observation_date'][5:7]));missing.focus();assert 'Sin observación comparable' in page.locator('.carnes-heatmap-readout').inner_text()
        page.keyboard.press('ArrowLeft');assert 'Sin observación comparable' not in page.locator('.carnes-heatmap-readout').inner_text()
        page.keyboard.press('Enter');assert page.get_by_role('dialog').is_visible();page.keyboard.press('Escape')
        page.screenshot(path=str(out/f'{channel}-references-1440.png'),full_page=True)
        for width in [1000,900,640]:
            page.set_viewport_size({'width':width,'height':1050});page.screenshot(path=str(out/f'{channel}-references-{width}.png'),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.set_viewport_size({'width':1440,'height':1050})
        page.locator('#carnes-group').select_option('detail');ready()
        page.locator('.carnes-context-filters > summary').click();page.locator('#carnes-category').select_option('Vaca');ready();page.locator('#carnes-age').select_option('más de 8 dientes');ready()
        assert page.evaluate("document.getElementById('carnesRoot')._carnesView.analyticsResult.rolling!==null")
        assert '%' in page.locator('#carnesView .kpi-value').nth(1).inner_text()
        page.get_by_role('button',name='Producción bovina',exact=True).click();ready()
        assert not page.locator('.carnes-references').is_visible()
        assert page.evaluate("document.getElementById('carnesRoot')._carnesView.analyticsResult.rolling===null")
        page.get_by_role('button',name='Peso medio',exact=True).click();ready()
        assert page.evaluate("document.getElementById('carnesRoot')._carnesView.analyticsResult.ytd===null")
        assert not page.locator('.carnes-references').is_visible()
        # A delayed reference load for a different year must not publish into Production.
        page.get_by_role('button',name='Faena bovina',exact=True).click();ready();page.locator('#carnes-year').select_option('2025');ready()
        page.evaluate('''()=>{const v=document.getElementById('carnesRoot')._carnesView,original=v.loader.load.bind(v.loader);v.loader.load=(...args)=>args[3]==='2020'?new Promise((resolve,reject)=>{window.releaseMeatReference=()=>original(...args).then(r=>{resolve(r);window.meatReferenceReleased=true;},reject);}):original(...args);}''')
        if not page.locator('.carnes-references').evaluate('n=>n.open'):page.locator('.carnes-references > summary').click()
        page.wait_for_function("typeof window.releaseMeatReference==='function'")
        page.get_by_role('button',name='Producción bovina',exact=True).click();ready();page.evaluate('window.releaseMeatReference()')
        page.wait_for_function('window.meatReferenceReleased===true')
        assert not page.locator('.carnes-references').is_visible() and page.locator('.carnes-heatmap-cell').count()==0
        assert page.locator('#carnes-family').input_value()=='production'
        assert not errors,errors
        report={'result':'PASS','browser':channel,'independent_csv_matches':result,'history':historical,'javascript_errors':errors,'checks':['YTD','MM12','Top3','15 composition cells','ranking expansion','36-month range','5-year seasonality','heatmap missing vs zero','keyboard/detail','responsive','short-series suppression','delayed-history race']}
        (out/f'{channel}-analytics-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'browser':channel,'result':'PASS','initial_bytes':result['payload'],'expanded_bytes':historical['payload']}));browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',default='http://127.0.0.1:8767');parser.add_argument('--channel',choices=['msedge','chrome'],required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();run(a.url,a.channel,a.output)
