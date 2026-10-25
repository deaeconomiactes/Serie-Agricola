const test=require('node:test');
const assert=require('node:assert/strict');
const C=require('../../carnes.js'),A=C.Analytics;
const fs=require('node:fs'),zlib=require('node:zlib');
const row=(year,month,value,change={})=>({source_id:'magyp_slaughter_'+(year===2026?'current':year),capture_id:'capture',source:'DNCCA',source_url:'https://www.magyp.gob.ar/',family:'slaughter',metric:'slaughter_heads',species:'bovinos',table_id:'slaughter/category_age',entity_type:'total',geography:'Argentina',category:'Total general',age_class:'',currency:'NOT_APPLICABLE',unit:'heads',weight_basis:'NOT_APPLICABLE',methodology:'published_all_classifications_total',frequency:'monthly',market:'',entity_id:'',entity_name:'',entity_activity:'',observation_date:`${year}-${String(month).padStart(2,'0')}-01`,period_end:`${year}-${String(month).padStart(2,'0')}-${new Date(Date.UTC(year,month,0)).getUTCDate()}`,value:String(value),value_status:'observed',...change});
const months=(year,value,change={})=>Array.from({length:12},(_,i)=>row(year,i+1,typeof value==='function'?value(i):value,change));
const state={family:'slaughter',group:'detail',frequency:'monthly',province:'Argentina',category:'TOTAL',method:'resolution_32_2018_dentition'};
test('YTD compares equal Jan–closure spans, and never published YTD or category weights',()=>{
 const data=[...months(2025,10),...months(2026,20).slice(0,9)],anchor=data.at(-1),r=A.derivedYTD(data,anchor);
 assert.equal(r.value,180);assert.equal(r.base,90);assert.equal(r.variation,100);assert.equal(r.count,9);
 assert.equal(A.derivedYTD(data,{...anchor,frequency:'year_to_date'}),null);
 assert.equal(A.derivedYTD(data,{...anchor,family:'carcass_weight'}),null);
});
test('YTD fails closed on missing current month, duplicate, null, mismatched methodology, source or unit',()=>{
 const data=[...months(2025,10),...months(2026,20).slice(0,9)],anchor=data.at(-1);
 assert.equal(A.derivedYTD(data.filter(r=>r.observation_date!=='2026-02-01'),anchor),null);
 assert.equal(A.derivedYTD([...data,data.at(-1)],anchor),null);
 for(const change of [{value:'',value_status:'missing'},{period_end:'2025-03-30'},{methodology:'other'},{source_id:'sspm_40_3'},{unit:'tonnes'}]){
  const changed=data.map(r=>r.observation_date==='2025-03-01'?{...r,...change}:r);
  assert.equal(A.derivedYTD(changed,anchor).variation,null);
 }
});
test('zero denominator is not growth; zero observed numerator is a genuine decline',()=>{
 const prior=months(2025,0),current=months(2026,20);assert.equal(A.derivedYTD([...prior,...current],current[1]).variation,null);
 const zeros=months(2026,0);assert.equal(A.derivedYTD([...months(2025,10),...zeros],zeros[1]).variation,-100);
});
test('mobile average uses exactly 12 calendar months and retains source rows',()=>{
 const data=[...months(2025,i=>i+1),...months(2026,24)];const ref=A.rollingReference(data,data[12]);
 assert.equal(ref.mean,(2+3+4+5+6+7+8+9+10+11+12+24)/12);assert.equal(ref.rows.length,12);
 assert.equal(A.rollingReference(data.filter(r=>r.observation_date!=='2025-07-01'),data[12]),null);
 assert.equal(A.rollingReference([...data,data[5]],data[12]),null);
 assert.equal(A.rollingReference(data.slice(12,21),data[20]),null);
});
test('series identity rejects economic dimensions, geography, currency, entity and publication drift',()=>{
 const base=row(2026,9,10);
 for(const change of [{species:'bovinos_y_bubalinos'},{metric:'other'},{market:'other'},{entity_id:'other'},{geography:'CORDOBA'},{currency:'ARS'},{source_id:'sspm_40_3'},{weight_basis:'other'},{age_class:'4 dientes'},{frequency:'annual'}])assert.equal(A.sameSeries(base,{...base,...change}),false);
 assert.equal(A.sameSeries(base,row(2025,9,10)),true);
});
const province=(name,value)=>row(2026,9,value,{table_id:'slaughter/province',entity_type:'province',geography:name,category:'All categories',methodology:'published province'});
test('Top 3 uses the published national denominator and requires a complete reconciled partition',()=>{
 const total=row(2026,9,100),data=[total,province('A',40),province('B',30),province('C',20),province('D',10)];
 const r=A.territorialDistribution(data,total);assert.equal(r.top3,90);assert.equal(r.items[0].rank,1);assert.equal(r.items[0].share,40);
 assert.equal(A.territorialDistribution(data.slice(0,-1),total),null);
 assert.equal(A.territorialDistribution([...data,data[1]],total),null);
 assert.equal(A.territorialDistribution(data.map(r=>r.geography==='D'?{...r,value:''}:r),total),null);
 assert.equal(A.territorialDistribution(data.map(r=>r.geography==='D'?{...r,capture_id:'different'}:r),total),null);
 assert.equal(A.territorialDistribution(data.map(r=>r===total?{...r,value:'0'}:r),total),null);
});
const category=(year,name,value,extra={})=>row(year,9,value,{entity_type:'category',category:name,age_class:'2 dientes',methodology:state.method,...extra});
test('composition p.p. compares matched, complete classifications and never province × category',()=>{
 const current=[row(2026,9,100),category(2026,'A',60),category(2026,'B',40)],previous=[row(2025,9,200),category(2025,'B',100),category(2025,'A',100)];
 const now=A.compositionDistribution(current,state,current[0]),before=A.compositionDistribution(previous,state,previous[0]);
 const change=A.compareComposition(now,before);assert.deepEqual(change.map(r=>r.pp),[10,-10]);
 assert.equal(A.compositionDistribution(current,{...state,province:'A'},current[0]),null);
 assert.equal(A.compositionDistribution(current.slice(0,-1),state,current[0]),null);
 assert.equal(A.compareComposition(now,{...before,items:before.items.slice(0,1)}),null);
 assert.equal(A.compareComposition(now,{...before,items:before.items.map(i=>({...i,row:{...i.row,methodology:'old'}}))}),null);
});
test('dentition comparison normalizes case/spacing only, preserves original labels and rejects normalized duplicates',()=>{
 const current=category(2026,'Vaca',100,{age_class:'más de 8 dientes'}),previous=category(2025,'Vaca',100,{age_class:' Más  de 8 dientes '});
 assert.equal(A.sameSeries(current,previous),true);assert.equal(previous.age_class,' Más  de 8 dientes ');
 assert.equal(A.sameSeries(current,{...previous,age_class:'8 dientes'}),false);
 assert.equal(A.compositionDistribution([row(2026,9,200),current,{...current,age_class:'Más de 8 dientes'}],state,row(2026,9,200)),null);
});
test('historical range excludes current month and seasonal baseline excludes selected year',()=>{
 const data=[...months(2021,1),...months(2022,2),...months(2023,3),...months(2024,4),...months(2025,5),...months(2026,100)];
 const ref=A.historicalReference(data,data.at(-1));assert.equal(ref.range.min,3);assert.equal(ref.range.max,100);
 assert.equal(ref.range.rows.at(-1).observation_date,'2026-11-01');assert.equal(ref.seasonality[0].mean,3);assert.equal(ref.years.length,5);
 assert.equal(A.historicalReference(data.slice(-24),data.at(-1)).seasonality,null);
});
test('historical baseline drops incomplete years, does not fill gaps and is unavailable for short weight series',()=>{
 const data=[...months(2023,3),...months(2024,4),...months(2025,5),...months(2026,6)];const missing=data.filter(r=>r.observation_date!=='2024-02-01');
 const ref=A.historicalReference(missing,data.at(-1));assert.equal(ref.years.length,2);assert.equal(ref.seasonality,null);assert.equal(ref.range,null);
 const weight=months(2026,250,{family:'carcass_weight',metric:'mean_carcass_weight',unit:'kg_carcass_bone_in'}).slice(0,9);
 assert.equal(A.rollingReference(weight,weight.at(-1)),null);assert.equal(A.historicalReference(weight,weight.at(-1)).range,null);
});
test('real frozen 2025/2026 classification compares all 15 components including Más/más without relabelling source rows',()=>{
 const data=JSON.parse(zlib.gunzipSync(fs.readFileSync('tests/carnes/fixtures/ui/analytics-composition-september.json.gz')));
 const current=data.filter(r=>r.observation_date==='2026-09-01'),previous=data.filter(r=>r.observation_date==='2025-09-01');
 const total=rows=>rows.find(r=>r.category==='Total general');
 const now=A.compositionDistribution(current,state,total(current)),before=A.compositionDistribution(previous,state,total(previous));
 const compared=A.compareComposition(now,before);assert.equal(compared.length,15);
 assert.ok(Math.abs(compared.find(i=>i.row.category==='Vaquillona' && i.row.age_class==='2 dientes').pp-(-3.84118692534242))<1e-10);
 const selected={...state,category:'Vaca',age:'más de 8 dientes',month:'09'};
 const old=C.selectedSeries(previous,selected),latest=C.selectedSeries(current,selected);
 assert.equal(old.length,1);assert.equal(old[0].age_class,'Más de 8 dientes');assert.equal(latest[0].age_class,'más de 8 dientes');
 assert.ok(C.yearAgo(latest[0],previous)<0);
});
