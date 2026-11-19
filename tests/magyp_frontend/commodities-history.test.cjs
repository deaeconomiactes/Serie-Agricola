const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto').webcrypto;
const source = fs.readFileSync('commodity-history.js','utf8');
function context(corrupt = false) {
    const requests = [];
    const ctx = vm.createContext({console:{log:console.log,error(){},warn(){}}, crypto, Blob, Response, DecompressionStream, TextEncoder, URL,
        document:{addEventListener(){},getElementById(){return null;}},
        fetch:async url => {
            requests.push(url);
            if (!fs.existsSync(url)) return new Response('',{status:404});
            const body = fs.readFileSync(url);
            return new Response(corrupt && url.endsWith('.gz') ? Buffer.from('corrupt') : body);
        }});
    vm.runInContext(source,ctx);
    vm.runInContext(fs.readFileSync('app.js','utf8'),ctx);
    return {ctx,requests};
}
function sample() {
    const id='a'.repeat(64);
    return {row:{fecha:'1995-01-03',series_key:id.slice(0,16),capture_key:'capture',price:'100',price_raw:'100,00',
        value_status:'positive',variacion_mensual_pct:'10',aggregation_captures:''},
        dictionary:{series:{[id.slice(0,16)]:{series_id:id,commodity:'MAIZ',fuente:'MAGyP',mercado:'CHICAGO',
            tipo_precio:'Futuro / histórico publicado',moneda:'USD',unidad:'TN',position_raw:'MAY1996',shipment_window:'1996-05'}},
        captures:{capture:{source_url:'https://www.magyp.gob.ar/prices.php',sha256:'b'.repeat(64),capture_id:'capture',captured_at_utc:'2026-10-21T12:00:00Z'}}}};
}

test('all official monthly histories and early daily shards validate real hashes and economic dimensions',async()=>{
    const {ctx}=context();
    for (const family of ['internal','board','fas','fob','futures']) {
        const entry=await vm.runInContext(`CommodityHistory.metadata('${family}')`,ctx);
        const monthly=await vm.runInContext(`CommodityHistory.load('${family}','mensual',null,parseCommodityCSV)`,ctx);
        assert.equal(monthly.length,entry.monthly.rows);
        assert.ok(monthly.every(row=>row.series_id && row.source_url && row.raw_sha256 && row.moneda && row.unidad));
        if(family!=='internal') {
            const year=Object.keys(entry.daily).sort()[0];
            const rows=await vm.runInContext(`CommodityHistory.load('${family}','diaria','${year}',parseCommodityCSV)`,ctx);
            assert.equal(rows.length,entry.daily[year].rows);
            assert.ok(rows.every(row=>row.fecha.startsWith(year)));
        }
    }
});

test('history preserves observation date, contract maturity and original price independently',()=>{
    const {ctx}=context();const {row,dictionary}=sample();ctx.rows=[row];ctx.dictionary=dictionary;
    const result=vm.runInContext("CommodityHistory.expand(rows,dictionary,'futures','diaria')",ctx);
    assert.equal(result[0].fecha,'1995-01-03');assert.equal(result[0].shipment_window,'1996-05');
    assert.equal(result[0].price_raw,'100,00');assert.equal(result[0].estado,'Suba moderada');
});

test('history rejects unknown family, duplicate observations and unofficial URL',()=>{
    const {ctx}=context();const {row,dictionary}=sample();ctx.rows=[row];ctx.dictionary=dictionary;
    assert.throws(()=>vm.runInContext("CommodityHistory.expand(rows,dictionary,'board','diaria')",ctx));
    ctx.rows=[row,row];assert.throws(()=>vm.runInContext("CommodityHistory.expand(rows,dictionary,'futures','diaria')",ctx));
    ctx.rows=[row];dictionary.captures.capture.source_url='https://evil.test/a';
    assert.throws(()=>vm.runInContext("CommodityHistory.expand(rows,dictionary,'futures','diaria')",ctx));
});

test('current revised zero or missing masks historical positive; no cross-series averaging',()=>{
    const {ctx}=context();
    ctx.current={diario:[],mensual:[],ultimos:[],semaforo:[],resumen:[]};
    ctx.history=[{series_id:'ARS-series',fecha:'2020-01-01',periodo_ym:'2020-01',precio_mediana:'100',moneda:'ARS'},
        {series_id:'USD-series',fecha:'2020-01-01',periodo_ym:'2020-01',precio_mediana:'10',moneda:'USD'}];
    ctx.observations=[{series_id:'ARS-series',fecha:'2020-01-01',periodo_ym:'2020-01',value_status:'zero',frecuencia:'mensual'}];
    const result=vm.runInContext('CommodityHistory.merge(current,history,[],observations)',ctx);
    assert.equal(result.mensual.length,1);assert.equal(result.mensual[0].moneda,'USD');
    assert.equal(result.mensual[0].precio_mediana,'10');
});

test('corrupt history cannot replace a validated current bundle',async()=>{
    const {ctx}=context(true);
    await assert.rejects(vm.runInContext("CommodityHistory.load('internal','mensual',null,parseCommodityCSV)",ctx));
    const result=await vm.runInContext("loadCommoditySource('magyp_internal')",ctx);
    assert.ok(result.mensual.length>0);assert.ok(result.resumen[0].fecha_max.startsWith('2026'));
});

test('bad historical shard keeps validated official current data without reactivating retired static prices',async()=>{
    const {ctx,requests}=context(true);
    vm.runInContext(`initCommoditySourceFilter=()=>{};setCommoditySource=()=>{};
        const realLoad=loadCommoditySource;loadCommoditySource=async key=>key==='sio'?emptyCommodityData():realLoad(key);`,ctx);
    await vm.runInContext('loadCommodityData()',ctx);
    assert.equal(requests.filter(url=>url.includes('commodities_local_mensual')).length,0);
    assert.equal(vm.runInContext("Object.hasOwn(commodityDataBySource,'local_mensual')",ctx),false);
    assert.ok(vm.runInContext('commodityDataBySource.magyp_internal.mensual.length',ctx)>0);
});

test('daily zero revises one day before monthly median; successor variations and lineage update',()=>{
    const {ctx}=context();
    const daily=[10,20,30,40,50].map((price,index)=>({series_id:'series',fecha:`2026-10-0${index+1}`,periodo_ym:'2026-10',
        price:String(price),precio_mediana:String(price),value_status:'positive',frecuencia:'diaria',capture_id:'history',raw_sha256:'a'.repeat(64),updated_at_utc:'2026-10-21T12:00:00Z'}));
    ctx.history=[{...daily[4],precio_mediana:'30',operaciones:5},
        {...daily[0],fecha:'2026-09-30',periodo_ym:'2026-09',precio_mediana:'10'},
        {...daily[0],fecha:'2026-11-30',periodo_ym:'2026-11',precio_mediana:'50'},
        {...daily[0],fecha:'2027-10-31',periodo_ym:'2027-10',precio_mediana:'100'}];
    ctx.daily=daily;ctx.current={diario:[],mensual:[],resumen:[]};
    ctx.observations=[{...daily[4],value_status:'zero',price:'0'}];
    const result=vm.runInContext('CommodityHistory.merge(current,history,daily,observations)',ctx);
    const october=result.mensual.find(row=>row.periodo_ym==='2026-10');
    assert.equal(october.precio_mediana,'25');assert.equal(october.operaciones,4);
    assert.equal(october.variacion_mensual_pct,'150');assert.equal(october.estado,'Revisar');
    assert.equal(result.mensual.find(row=>row.periodo_ym==='2026-11').variacion_mensual_pct,'100');
    assert.equal(result.mensual.find(row=>row.periodo_ym==='2027-10').variacion_interanual_pct,'300');
    assert.equal(october.aggregation_inputs.length,4);assert.ok(october.aggregation_inputs.every(row=>row.raw_sha256==='a'.repeat(64)));
});

test('current daily price does not replace full historical month with partial monthly snapshot',()=>{
    const {ctx}=context();
    const sample={series_id:'series',periodo_ym:'2026-10',frecuencia:'diaria',value_status:'positive',capture_id:'history',updated_at_utc:'2026-10-21T12:00:00Z'};
    const daily=[10,20,30,40,50].map((price,index)=>({...sample,fecha:`2026-10-0${index+1}`,price:String(price),precio_mediana:String(price)}));
    const revised={...daily[4],price:'100',precio_mediana:'100',capture_id:'current'};
    ctx.history=[{...daily[4],precio_mediana:'30',operaciones:5}];ctx.daily=daily;
    ctx.current={diario:[revised],mensual:[{...revised,operaciones:1}],resumen:[]};ctx.observations=[revised];
    const result=vm.runInContext('CommodityHistory.merge(current,history,daily,observations)',ctx);
    assert.equal(result.mensual[0].precio_mediana,'30');assert.equal(result.mensual[0].operaciones,5);
    assert.equal(result.mensual[0].aggregation_captures,'current|history');
});

test('decimal median and negative five percent boundary preserve existing economic thresholds',()=>{
    const {ctx}=context();
    ctx.current={diario:[],mensual:[],resumen:[]};ctx.daily=[];
    ctx.history=[{series_id:'s',fecha:'2026-09-30',periodo_ym:'2026-09',precio_mediana:'100'}];
    ctx.observations=[1,2].map(day=>({series_id:'s',fecha:`2026-10-0${day}`,periodo_ym:'2026-10',price:'95',value_status:'positive',frecuencia:'diaria'}));
    const result=vm.runInContext('CommodityHistory.merge(current,history,daily,observations)',ctx);
    const row=result.mensual.find(row=>row.periodo_ym==='2026-10');assert.equal(row.variacion_mensual_pct,'-5');assert.equal(row.estado,'Estable');
    ctx.observations[0].price='0.1';ctx.observations[1].price='0.2';
    const decimal=vm.runInContext('CommodityHistory.merge(current,[],daily,observations)',ctx);
    assert.equal(decimal.mensual[0].precio_mediana,'0.15');
});

test('daily comparisons use final revised values and update exact 7/30-day successors',()=>{
    const {ctx}=context();
    const make=(date,price)=>({series_id:'s',fecha:date,periodo_ym:date.slice(0,7),price:String(price),precio_mediana:String(price),
        value_status:'positive',frecuencia:'diaria',variacion_7d_pct:'old',variacion_30d_pct:'old'});
    ctx.daily=[make('2026-09-30',100),make('2026-10-07',120),make('2026-10-30',130)];
    const revised=make('2026-09-30',110);
    ctx.current={diario:[revised],mensual:[],resumen:[]};ctx.observations=[revised];
    const result=vm.runInContext('CommodityHistory.merge(current,[],daily,observations)',ctx);
    assert.equal(result.diario.find(row=>row.fecha==='2026-10-07').variacion_7d_pct,'9.090909090909');
    assert.equal(result.diario.find(row=>row.fecha==='2026-10-30').variacion_30d_pct,'18.181818181818');
});

test('real joined SORGO history supplies current 7d and 30d baselines',async()=>{
    const {ctx}=context();
    const current=await vm.runInContext("loadCommoditySource('magyp_board')",ctx);
    const joined=await vm.runInContext("CommodityHistory.assemble('board',commodityCurrentData.magyp_board,'2026',parseCommodityCSV)",ctx);
    const rows=joined.diario.filter(row=>row.commodity==='SORGO' && row.mercado==='ROSARIO');
    const one=rows.find(row=>row.fecha==='2026-10-07'),two=rows.find(row=>row.fecha==='2026-10-16');
    assert.ok(one);assert.ok(two);assert.ok(one.variacion_7d_pct);assert.ok(two.variacion_30d_pct);
    assert.equal(one.variacion_mensual_pct,undefined);
    assert.ok(current.mensual.find(row=>row.commodity==='SORGO' && row.mercado==='ROSARIO' && row.periodo_ym==='2026-10').operaciones>=5);
});

test('complete official cutover does not fetch the retired static monthly datasets',async()=>{
    const {ctx,requests}=context();
    vm.runInContext(`initCommoditySourceFilter=()=>{}; setCommoditySource=()=>{};
        const realLoad=loadCommoditySource;
        loadCommoditySource=async key=>key==='sio'?emptyCommodityData():realLoad(key);`,ctx);
    await vm.runInContext('loadCommodityData()',ctx);
    assert.equal(vm.runInContext("Object.hasOwn(COMMODITY_SOURCE_CONFIG,'local_mensual')",ctx),false);
    assert.equal(requests.filter(url=>url.includes('commodities_local_mensual')).length,0);
    assert.ok(vm.runInContext('commodityDataBySource.magyp_internal.mensual.length',ctx)>4000);
    assert.equal(vm.runInContext("commodityDataBySource.magyp_internal.mensual.filter(row=>row.periodo_ym==='2020-01' && row.commodity==='SOJA' && row.mercado==='ROSARIO').length",ctx),1);
});

test('historical year scopes observations, never contract maturity, and does not affect SIO',()=>{
    const {ctx}=context();
    vm.runInContext("commoditySource='magyp_futures';commodityHistoryMetadata.magyp_futures={};commodityHistoryYear='1995'",ctx);
    assert.equal(vm.runInContext("commodityHistoryYearMatches({fecha:'1995-01-03',shipment_window:'1996-05'})",ctx),true);
    assert.equal(vm.runInContext("commodityHistoryYearMatches({fecha:'1996-01-03',shipment_window:'1995-05'})",ctx),false);
    vm.runInContext("commoditySource='sio'",ctx);
    assert.equal(vm.runInContext("commodityHistoryYearMatches({fecha:'2026-10-21'})",ctx),true);
});

test('internal rice supplement remains selectable across year, range, source and frequency changes',async()=>{
    const {ctx,requests}=context();
    const names=['Arroz cáscara — largo fino','Arroz cáscara — largo ancho'];
    const run=expression=>vm.runInContext(expression,ctx);
    const riceRows=()=>run("commodityData.mensual.filter(row=>row.periodo_ym.startsWith('2025') && row.commodity.startsWith('Arroz cáscara'))");
    const riceNames=rows=>[...new Set(rows.map(row=>row.commodity))].sort();
    const assertRice2025=()=>{
        const options=run('getCommodityFilterOptionRows()');
        const results=run('getCommodityFilteredRows()');
        assert.deepEqual(riceNames(options.filter(row=>row.periodo_ym.startsWith('2025') && row.commodity.startsWith('Arroz cáscara'))),names.slice().sort());
        assert.deepEqual(riceNames(results.filter(row=>row.commodity.startsWith('Arroz cáscara'))),names.slice().sort());
        const keys=results.map(row=>`${row.series_id}|${row.periodo_ym}`);
        assert.equal(new Set(keys).size,keys.length,'results must not duplicate a series/month after reassembly');
        assert.ok(run('getCommodityLatestRows()').some(row=>row.commodity===names[0]));
        const csv=run(`commodityRowsToCsv(getCommodityFilteredRows())`);
        assert.match(csv,/Arroz cáscara/);
        assert.doesNotMatch(csv,/U\$S|FOB/);
    };

    let data=await run("loadCommoditySource('magyp_internal')");ctx.testData=data;
    run("commoditySource='magyp_internal';commodityDataBySource.magyp_internal=testData;commodityData=testData;commodityFrequency='mensual';commodityHistoryYear='2025';");
    await run("loadCommodityHistoryYear('magyp_internal','2025')");
    run('commodityData=commodityDataBySource.magyp_internal;initCommodityFilters()');
    assertRice2025();

    run("commodityHistoryYear='TODOS';commodityDateRangeApplied={from:'',to:''}");
    await run("loadCommodityHistoryYear('magyp_internal','TODOS')");
    run('commodityData=commodityDataBySource.magyp_internal');
    assert.deepEqual(riceNames(riceRows()),names.slice().sort());
    assert.equal(new Set(run('commodityData.mensual').map(row=>`${row.series_id}|${row.periodo_ym}`)).size,run('commodityData.mensual.length'));

    run("commodityDateRangeApplied={from:'2025-01',to:'2025-12'};initCommodityFilters()");
    assertRice2025();
    run("commodityDateRangeApplied={from:'',to:''};commodityHistoryYear='2025'");
    await run("loadCommodityHistoryYear('magyp_internal','2025')");
    run('commodityData=commodityDataBySource.magyp_internal;initCommodityFilters()');
    assertRice2025();

    const dateControls={commodityDateRangeFrom:{value:'',dataset:{},addEventListener(){}},commodityDateRangeTo:{value:'',dataset:{},addEventListener(){}}};
    const quickButton={dataset:{commodityRange:'12m'},addEventListener(_event,handler){this.activate=handler;}};
    ctx.dateControls=dateControls;ctx.quickButton=quickButton;
    run("document.getElementById=id=>dateControls[id]||null;document.querySelectorAll=()=>[quickButton];commodityDateRangeApplied={from:'2020-01',to:'2020-12'};updateCommodityDashboard=()=>{};initCommodityDateRangeFilters()");
    quickButton.activate();
    assert.deepEqual({...run('commodityDateRangeApplied')},{from:'2025-01',to:'2025-12'},'quick ranges should use the selected year, not a stale manual range');
    assertRice2025();

    const board=await run("loadCommoditySource('magyp_board')");ctx.testBoard=board;
    run("commoditySource='magyp_board';commodityDataBySource.magyp_board=testBoard;commodityData=testBoard;commodityFrequency='diaria';commodityHistoryYear='2025'");
    await run("loadCommodityHistoryYear('magyp_board','2025')");
    run('commodityData=commodityDataBySource.magyp_board');
    assert.ok(run('getCommodityFilterOptionRows().length')>0);
    assert.equal(run("getCommodityFilterOptionRows().some(row=>row.commodity.startsWith('Arroz cáscara'))"),false);
    run("commodityFrequency='mensual'");
    assert.ok(run('getCommodityFilterOptionRows().length')>0);
    run("commodityFrequency='diaria'");
    await run("loadCommodityHistoryYear('magyp_board','2025')");
    run('commodityData=commodityDataBySource.magyp_board');
    assert.equal(run("new Set(commodityData.diario.map(row=>`${row.series_id}|${row.fecha}`)).size"),run('commodityData.diario.length'));

    run("commoditySource='magyp_internal';commodityData=commodityDataBySource.magyp_internal;commodityFrequency='mensual';commodityHistoryYear='2025';commodityDateRangeApplied={from:'',to:''};initCommodityFilters()");
    await run("loadCommodityHistoryYear('magyp_internal','2025')");
    run('commodityData=commodityDataBySource.magyp_internal');
    assertRice2025();
    assert.equal(requests.filter(url=>url.endsWith('rice_internal.csv.gz')).length,1,'the supplement should be fetched once despite switching views');
});

test('history indicator shows effective last data without hiding current workflow error',()=>{
    const {ctx}=context();ctx.SourceUpdateStatus={render(node,metadata){ctx.shown=metadata;}};
    vm.runInContext(`commoditySource='magyp_fob';commodityHistoryMetadata.magyp_fob={};
        commodityData={resumen:[{filas_dashboard:10,fecha_max:'2026-10-20',fecha_actualizacion_dashboard:'2026-10-21T12:00:00Z'}]};
        priceFreshnessBySource.magyp_fob={status:'PIPELINE_ERROR',last_observation_date:'2026-10-19',last_successful_update:'2026-10-19T12:00:00Z'};
        updateCommoditySourceStatus();`,ctx);
    assert.equal(ctx.shown.status,'PIPELINE_ERROR');assert.equal(ctx.shown.last_valid_date,'2026-10-20');
    assert.equal(ctx.shown.last_successful_update,'2026-10-19T12:00:00Z');
});
