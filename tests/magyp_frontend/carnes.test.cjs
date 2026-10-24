const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const zlib=require('node:zlib');
const C=require('../../carnes.js');
const folder='tests/carnes/fixtures/ui/';
const index=JSON.parse(fs.readFileSync(folder+'index.json'));
function rows(source,family='slaughter',frequency='monthly',year='2026') {
    const entry=index.sources[source];const descriptor=entry.files.find(f=>f.family===family && f.frequency===frequency && f.year===year);
    return C.validateRows(C.parseCSV(zlib.gunzipSync(fs.readFileSync(folder+descriptor.path)).toString()),entry,descriptor);
}
const current=rows('magyp_slaughter_current');
const base={family:'slaughter',group:'detail',frequency:'monthly',year:'2026',month:'09',province:'Argentina',category:'TOTAL',age:'',method:'resolution_32_2018_dentition'};
function fetcher(requests,alter) {return async path=>{requests.push(path);const local=path.endsWith('CARNES_UPDATE_STATUS.json')?folder+'status.json':path.replace('data/carnes/dashboard/',folder);let body=fs.readFileSync(local);if(alter)body=alter(path,body);return new Response(body,{status:200});};}

test('Carnes is lazy: no eager script/data load in HTML; only own tab invokes module',()=>{
    const html=fs.readFileSync('index.html','utf8'),app=fs.readFileSync('app.js','utf8');
    assert.match(html,/data-module="carnesView"/);assert.doesNotMatch(html,/<script[^>]+src="carnes.js/);
    assert.match(app,/if \(button.dataset.module === 'carnesView'\) loadCarnesModule\(\)/);
    assert.doesNotMatch(fs.readFileSync('carnes.js','utf8'),/fetch\([^)]*(?:raw\/|normalized\/|analytical\/)/);
});
test('initial loader requests index/status only and shards are cached by hash',async()=>{
    const requests=[];const loader=new C.Loader(fetcher(requests));await loader.init();
    assert.equal(requests.length,2);assert.ok(requests.every(p=>p.endsWith('.json')));
    await loader.load('detail','slaughter','monthly','2026');assert.equal(requests.length,3);
    await loader.load('detail','slaughter','monthly','2026');assert.equal(requests.length,3);
    assert.ok(!requests.some(p=>p.includes('archive') || p.includes('2025')));
    assert.equal(loader.metrics.bytes,fs.statSync(folder+'index.json').size+fs.statSync(folder+'status.json').size+38312);
});
test('hash mismatch rejects fragment and is not cached as valid',async()=>{
    const loader=new C.Loader(fetcher([], (path,body)=>path.endsWith('.gz')?Buffer.from('invalid'):body));await loader.init();
    await assert.rejects(loader.load('detail','slaughter','monthly','2026'),/Hash/);assert.equal(loader.cache.size,0);
});
test('unknown schema, observed empty, duplicate and inconsistent provenance are rejected',()=>{
    const entry=index.sources.magyp_slaughter_current,descriptor=entry.files.find(f=>f.frequency==='monthly');
    assert.throws(()=>C.parseCSV('other,columns\n1,2\n'),/Schema/);
    for(const change of [{value:''},{value:' '},{value:'0x10'},{observation_date:'2026-02-30'},{schema_version:'unknown'},{raw_sha256:'x'},{entity_type:'establishment'}]) {
        const altered=current.map(r=>({...r}));Object.assign(altered[0],change);
        assert.throws(()=>C.validateRows(altered,entry,descriptor));
    }
    const duplicate=current.map(r=>({...r}));duplicate[1]={...duplicate[0]};assert.throws(()=>C.validateRows(duplicate,entry,descriptor));
});
test('CSV parser preserves quoted commas, quotes and line breaks',()=>{
    const raw={...current[0],value_raw:'valor, "publicado"\nsegunda línea'};
    const encode=value=>'"'+String(value ?? '').replaceAll('"','""')+'"';
    const body=C.FIELDS.join(',')+'\n'+C.FIELDS.map(key=>encode(raw[key])).join(',')+'\n';
    assert.equal(C.parseCSV(body)[0].value_raw,raw.value_raw);
    assert.throws(()=>C.parseCSV(C.FIELDS.join(',')+'\n"incompleto'),/incompleto/);
});
test('faena uses published provincial total once, never redundant entity totals',()=>{
    const series=C.selectedSeries(current,base);assert.equal(series.length,9);
    assert.ok(series.every(r=>r.table_id==='slaughter/category_age' && r.category==='Total general'));
    assert.equal(C.number(C.point(series,base).value),1045293);
    assert.ok(current.filter(r=>r.entity_type==='total').length>series.length);
});
test('province and category filters are mutually compatible, with explicit reset',()=>{
    const province=C.reconcile({...base,category:'Novillo',age:'6 dientes',province:'BUENOS AIRES'},'province');
    assert.equal(province.category,'TOTAL');assert.equal(province.age,'');
    const series=C.selectedSeries(current,province);assert.ok(series.every(r=>r.entity_type==='province' && r.geography==='BUENOS AIRES'));
    const category=C.reconcile({...province,category:'Novillo',age:'6 dientes'},'category');assert.equal(category.province,'Argentina');
    assert.ok(C.selectedSeries(current,category).every(r=>r.entity_type==='category' && r.geography==='Argentina'));
    assert.equal(C.reconcile({...province,family:'production'},'family').province,'Argentina');
});
test('provincial participation uses the same published national period and unit',()=>{
    const province=C.point(C.selectedSeries(current,{...base,province:'BUENOS AIRES'}),base);
    const national=C.point(C.selectedSeries(current,base),base);
    assert.equal(C.provincialShare(province,current),Number(province.value)/Number(national.value)*100);
    assert.equal(C.provincialShare(national,current),null);
});
test('interannual uses matching economic dimensions, including species and YTD closure',()=>{
    const row=C.point(C.selectedSeries(current,base),base);
    const before={...row,observation_date:'2025-09-01',period_end:'2025-09-30',value:String(Number(row.value)/2),source_id:'magyp_slaughter_2025'};
    assert.equal(C.yearAgo(row,[before]),100);
    for(const change of [{source_id:'sspm_40_3'},{unit:'other'},{species:'bovinos_y_bubalinos'},{methodology:'other'},{frequency:'annual'},{period_end:'2025-12-31'}])
        assert.equal(C.yearAgo(row,[{...before,...change}]),null);
    assert.equal(C.yearAgo(row,[before,before]),null);assert.equal(C.yearAgo(row,[{...before,value:'0'}]),null);
    assert.equal(C.yearAgo({...row,observation_date:'2024-02-01',period_end:'2024-02-29'},[{...before,observation_date:'2023-02-01',period_end:'2023-02-28'}]),100);
});
test('partial cumulative label uses closing month; annual remains separate',()=>{
    assert.equal(C.caption({frequency:'year_to_date',observation_date:'2026-01-01',period_end:'2026-09-30'}),'Acumulado enero–septiembre 2026');
    assert.equal(C.caption({frequency:'annual',observation_date:'2025-01-01',period_end:'2025-12-31'}),'Año completo 2025');
    const cumulative=rows('magyp_slaughter_current','slaughter','year_to_date');
    assert.ok(cumulative.every(r=>r.period_end==='2026-09-30'));
    const state={...base,frequency:'year_to_date'};
    assert.equal(C.selectedSeries(cumulative,state).length,1);
    for(const family of ['production','carcass_weight']) {
        const data=rows('magyp_production_current',family,'year_to_date');
        const selected=C.selectedSeries(data,{...state,family,group:'production'});
        assert.equal(selected.length,1);assert.equal(C.number(selected[0].value),null);
        assert.ok(!selected[0].table_id.includes('PARTICIPACION'));
    }
});
test('production selects published tonnes, without geographic or weight-basis invention',()=>{
    const data=rows('magyp_production_current','production');const state={...base,family:'production',group:'production'};
    const series=C.selectedSeries(data,state);assert.equal(series.length,9);assert.equal(Number(C.point(series,state).value),258237.5441099999);
    assert.ok(series.every(r=>r.unit==='tonnes_carcass_bone_in' && r.geography==='Argentina'));
    const sspm=rows('sspm_40_3','production');const national=C.selectedSeries(sspm,{...state,group:'sspm'});
    assert.ok(national.every(r=>r.weight_basis==='NOT_IDENTIFIED' && r.unit==='Toneladas'));
});
test('weight uses published category mean and never manufactures missing national mean',()=>{
    const data=rows('magyp_production_current','carcass_weight'),state={...base,family:'carcass_weight',group:'production'};
    assert.ok(C.selectedSeries(data,state).every(r=>C.number(r.value)===null));
    const chosen=C.selectedSeries(data,{...state,category:'Novillito',age:'2 dientes'});
    assert.equal(chosen.length,9);assert.ok(chosen.every(r=>C.number(r.value)>0 && r.unit==='kg_carcass_bone_in'));
    assert.equal(C.yearAgo(chosen[0],[]),null);
});
test('provisional, missing, zero and combined-species source flags remain explicit',()=>{
    assert.ok(current.some(r=>r.flags.includes('provisional_source_statement')));
    assert.equal(C.number('0'),0);assert.equal(C.number(''),null);
    const old=rows('magyp_slaughter_2018','slaughter','monthly','2018');assert.ok(old.every(r=>r.species==='bovinos_y_bubalinos'));
});
test('2019 classification composition never combines pre/post reform rows',()=>{
    const data=rows('magyp_slaughter_2019','slaughter','monthly','2019');const anchor=C.selectedSeries(data,base).at(-1);
    const modern=C.classificationRows(data,base,anchor),old=C.classificationRows(data,{...base,method:'pre_2019_weight_sex_categories'},anchor);
    assert.equal(modern.length,15);assert.equal(old.length,9);assert.ok(modern.every(r=>r.methodology===base.method));
});
test('status is metadata-driven; finished historical series never becomes calendar error',()=>{
    const entry=index.sources.magyp_slaughter_current;
    for(const state of ['UPDATED','SOURCE_UNAVAILABLE','NO_PUBLICATION','PIPELINE_ERROR'])assert.equal(C.sourceState(entry,{[entry.source_id]:{status:state}}).status,state);
    assert.equal(C.sourceState(entry,{[entry.source_id]:{status:'NO_OP_ALREADY_CURRENT'}}).status,'UPDATED');
    const archive=index.sources.magyp_indicators_archive;assert.equal(C.sourceState(archive,{}).status,'HISTORICAL_ENDED');
    assert.equal(C.sourceState(archive,{[archive.source_id]:{status:'SOURCE_UNAVAILABLE'}}).historical,true);
});
test('historical families retain separate monetary and physical magnitudes',()=>{
    const prices=rows('magyp_indicators_archive','livestock_price','monthly','2019');
    assert.equal(prices.filter(r=>r.metric==='novillo_price_ARS').length,8);
    assert.equal(prices.filter(r=>r.metric==='novillo_price_USD').length,8);
    const exports=rows('magyp_indicators_archive','exports','monthly','2019');assert.equal(new Set(exports.map(r=>r.unit)).size,3);
    assert.ok([...prices,...exports].every(r=>r.flags.includes('historical_series_ended_2019_08')));
});
