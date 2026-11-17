const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const zlib = require('node:zlib');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const current = fs.readFileSync('app.js','utf8');
const baseline = execFileSync('git',['show','d82fcbc:app.js'],{encoding:'utf8'});
function context(code=current) {
    const ctx=vm.createContext({console:{error(){}},document:{addEventListener(){},getElementById(){return {value:'TODOS'};}}});
    vm.runInContext(code,ctx);return ctx;
}

test('FOB permanece conservado en los archivos pero no se ofrece como fuente en el dashboard',()=>{
    const ctx=context();
    assert.ok(fs.readFileSync('data/magyp/dashboard/commodities/fob.csv.gz').length>0);
    const keys=JSON.parse(vm.runInContext('JSON.stringify(Object.keys(COMMODITY_SOURCE_CONFIG))',ctx));
    assert.ok(!keys.some(key=>/fob|rice/i.test(key)));
    const select={dataset:{},addEventListener(){},innerHTML:'',value:''};
    ctx.document={getElementById:id=>id==='commodityFilterSource'?select:null};
    vm.runInContext('initCommoditySourceFilter()',ctx);
    assert.doesNotMatch(select.innerHTML,/FOB|Arroz/i);
    assert.doesNotMatch(fs.readFileSync('commodities-ui.js','utf8'),/magyp_fob|magyp_rice_fob|Arroz FOB/i);
});

test('arroz interno se integra en Precio interno MAGyP sólo en ARS/QQ y ARS/KG',async()=>{
    const ctx=context();
    Object.assign(ctx,{Blob,Response,DecompressionStream});
    const state=fs.readFileSync('data/magyp/reports/RICE_PRICES_STATUS.json');
    ctx.fetch=async url=>{
        if(url.endsWith('/RICE_PRICES_STATUS.json'))return new Response(state);
        if(url.endsWith('/rice_internal.csv.gz'))return new Response(fs.readFileSync('data/magyp/dashboard/commodities/rice_internal.csv.gz'));
        assert.ok(url.endsWith('/internal.csv'));
        return new Response(fs.readFileSync('data/magyp/dashboard/commodities/internal.csv'));
    };
    const result=await vm.runInContext("loadCommoditySource('magyp_internal')",ctx);
    ctx.result=result;
    assert.ok(result.mensual.length);assert.ok(result.ultimos.length);assert.ok(result.semaforo.length);
    assert.equal(result.resumen.length,1);
    const riceRows=JSON.parse(vm.runInContext("JSON.stringify(result.mensual.filter(row=>row.commodity.includes('Arroz cáscara')))",ctx));
    assert.ok(riceRows.some(row=>row.unidad==='QQ'&&row.moneda==='ARS'));
    assert.ok(riceRows.some(row=>row.unidad==='KG'&&row.moneda==='ARS'));
    assert.ok(riceRows.every(row=>row.moneda==='ARS'&&['QQ','KG'].includes(row.unidad)));
    assert.ok(riceRows.every(row=>!Object.keys(row).some(key=>key.startsWith('fx_a3500_'))));
    const october=JSON.parse(vm.runInContext("JSON.stringify(result.mensual.filter(row=>row.periodo_ym==='2026-10'&&row.unidad==='QQ'&&row.moneda==='ARS').map(row=>[row.rice_variety_raw,Number(row.precio_mediana)]))",ctx));
    assert.ok(october.some(([variety,price])=>variety==='LARGO FINO'&&price===40000));
    assert.ok(october.some(([variety,price])=>variety==='LARGO ANCHO'&&price===48000));
    ctx.riceRows=riceRows;
    const visibleCsv=vm.runInContext('commodityRowsToCsv(riceRows)',ctx);
    assert.doesNotMatch(visibleCsv,/fx_a3500|USD\/QQ|BCRA/);
    assert.equal(vm.runInContext("priceFreshnessBySource.magyp_internal_rice.status",ctx),'NO_PUBLICATION');
    assert.equal(vm.runInContext("ricePublicationStates.magyp_internal_rice.coverage_start",ctx),'1992-09-01');
    const internal=zlib.gunzipSync(fs.readFileSync('data/magyp/dashboard/commodities/rice_internal.csv.gz')).toString('utf8');
    const fob=zlib.gunzipSync(fs.readFileSync('data/magyp/dashboard/commodities/rice_fob.csv.gz')).toString('utf8');
    ctx.internal=internal;ctx.fob=fob;
    assert.ok(vm.runInContext("parseReferenceCommodityBundle(internal,'magyp_rice_internal').mensual.every(row=>row.tipo_precio.startsWith('Precio interno arroz cáscara'))",ctx));
    assert.ok(vm.runInContext("parseReferenceCommodityBundle(fob,'magyp_rice_fob').mensual.every(row=>row.tipo_precio.startsWith('Referencia internacional FOB arroz'))",ctx));
    assert.throws(()=>vm.runInContext("parseReferenceCommodityBundle(fob,'magyp_rice_internal')",ctx));
});

test('el filtro general de período limita observaciones y últimos valores de arroz sin rellenar huecos',async()=>{
    const ctx=context();
    Object.assign(ctx,{Blob,Response,DecompressionStream});
    const state=fs.readFileSync('data/magyp/reports/RICE_PRICES_STATUS.json');
    ctx.fetch=async url=>url.endsWith('/RICE_PRICES_STATUS.json')?new Response(state):url.endsWith('/rice_internal.csv.gz')
        ?new Response(fs.readFileSync('data/magyp/dashboard/commodities/rice_internal.csv.gz'))
        :new Response(fs.readFileSync('data/magyp/dashboard/commodities/internal.csv'));
    ctx.data=await vm.runInContext("loadCommoditySource('magyp_internal')",ctx);
    ctx.document={getElementById:()=>({value:'TODOS'})};
    const result=JSON.parse(vm.runInContext(`commoditySource='magyp_internal';commodityFrequency='mensual';commodityHistoryMetadata.magyp_internal={};commodityData=data;
        commoditySelectedValues=['Arroz cáscara — largo fino'];
        commodityDateRangeApplied={from:'2026-01',to:'2026-05'};
        JSON.stringify({rows:getCommodityFilteredRows().filter(row=>row.commodity.includes('Arroz')).map(row=>row.periodo_ym),latest:getCommodityLatestRows().filter(row=>row.commodity.includes('Arroz')).map(row=>row.periodo_ultimo)})`,ctx));
    assert.ok(result.rows.length>0);
    assert.ok(result.rows.every(period=>period>='2026-01'&&period<='2026-05'));
    assert.ok(result.latest.every(period=>period==='2026-05'));
});

test('al seleccionar arroz se usa ARS/QQ y todas las plazas, con ARS/KG seleccionable',()=>{
    const ctx=context();
    const values={
        commodityFilterCurrency:['TODOS','ARS','USD'],
        commodityFilterUnit:['TODOS','TN','QQ','KG'],
        commodityFilterMarket:['TODOS','Rosario','Mercado interno — plaza no informada'],
        commodityFilterType:['TODOS','Precio interno mensual','Precio interno arroz cáscara']
    };
    const controls=Object.fromEntries(Object.entries(values).map(([id,options])=>[id,{value:'TODOS',options:options.map(value=>({value}))}]));
    ctx.document={getElementById:id=>controls[id]||null};
    vm.runInContext("commoditySource='magyp_internal';commoditySelectedValues=['Arroz cáscara largo fino'];adaptInternalCommoditySelection(['SOJA'])",ctx);
    assert.equal(controls.commodityFilterCurrency.value,'ARS');
    assert.equal(controls.commodityFilterUnit.value,'QQ');
    assert.equal(controls.commodityFilterMarket.value,'TODOS');
    assert.equal(controls.commodityFilterType.value,'TODOS');
    controls.commodityFilterUnit.value='KG';
    vm.runInContext("commoditySelectedValues=['Arroz cáscara largo fino','Arroz cáscara largo ancho'];adaptInternalCommoditySelection(['Arroz cáscara largo fino'])",ctx);
    assert.equal(controls.commodityFilterUnit.value,'KG');
});

test('la descarga general conserva fuente y hashes y omite la conversión USD/A3500',()=>{
    const ctx=context();
    ctx.rows=[{periodo_ym:'2026-10',commodity:'Arroz cáscara — largo fino',moneda:'ARS',unidad:'QQ',price:'40000.00',raw_sha256:'a'.repeat(64),source_url:'https://www.magyp.gob.ar/source',note:'valor; "original"'}];
    const csv=vm.runInContext('commodityRowsToCsv(rows)',ctx);
    assert.ok(csv.startsWith('\uFEFF'));
    assert.match(csv,/"raw_sha256"/);
    assert.doesNotMatch(csv,/fx_a3500|USD\/QQ|BCRA/);
    assert.match(csv,/"a{64}"/);
    assert.match(csv,/"valor; ""original"""/);
});

test('initial MAGyP internal source and source switches set frequency and KPI semantics',()=>{
    const ctx=context();
    assert.equal(vm.runInContext('commoditySource',ctx),'magyp_internal');
    const nodes=new Map();
    ctx.document={getElementById(id){
        if(!nodes.has(id))nodes.set(id,{value:'mensual',textContent:'',style:{},dataset:{},
            querySelector(){return {disabled:false};}});
        return nodes.get(id);
    }};
    vm.runInContext('initCommodityFilters=()=>{};updateCommoditySourceStatus=()=>{};updateCommodityDashboard=()=>{};',ctx);
    const frequencies={magyp_internal:'mensual',magyp_board:'diaria',magyp_fas:'diaria',
        magyp_futures:'diaria',sio:'mensual'};
    for(const [source,frequency] of Object.entries(frequencies)) {
        vm.runInContext(`setCommoditySource('${source}')`,ctx);
        assert.equal(vm.runInContext('commodityFrequency',ctx),frequency);
        assert.equal(nodes.get('commodityFilterSource').value,source);
        assert.equal(nodes.get('commodityLatestCountHeader').textContent,source==='sio'?'Operaciones':'Observaciones');
        assert.match(nodes.get('commodityKpiOperationsLabel').textContent,source==='sio'?/Operaciones/:/Observaciones/);
        assert.equal(nodes.get('commodityKpiMonthlyLabel').textContent,frequency==='diaria'?'Variación a 7 días':'Variación mensual');
        assert.ok(nodes.get('commoditySourceSubtitle').textContent);
        assert.ok(nodes.get('commodityMethodNote').textContent);
    }
});

test('futures observation dates remain separate from May 2027 contract maturity',()=>{
    const ctx=context();
    const nodes=new Map();
    ctx.document={getElementById(id){
        if(!nodes.has(id))nodes.set(id,{value:'mensual',textContent:'',style:{},querySelector(){return this.daily||(this.daily={});}});
        return nodes.get(id);
    }};
    ctx.sample={commodity:'SOJA',mercado:'CHICAGO',fuente:'MAGyP',moneda:'USD',unidad:'TN',tipo_precio:'Futuro / cierre',
        fecha:'2026-10-09',periodo_ym:'2026-10',periodo_ultimo:'2026-10-09',fecha_ultima:'2026-10-09',
        condicion_comercial:'MAY2027',position_raw:'MAY2027',shipment_window:'2027-05',series_id:'one',
        price:400,precio_mediana:400,precio_mediana_ultimo_periodo:400,operaciones:1};
    vm.runInContext("commoditySource='magyp_futures';commodityFrequency='diaria';updateCommoditySourcePresentation();updateCommodityKpis([sample],[sample]);",ctx);
    assert.equal(nodes.get('commodityKpiUpdate').textContent,'09/10/2026');
    assert.equal(nodes.get('commodityConditionLabel').textContent,'Vencimiento / Posición');
    assert.equal(nodes.get('commodityLatestPeriodHeader').textContent,'Cotización');
    assert.equal(vm.runInContext('commodityPeriodValue(sample)',ctx),'2026-10-09');
    assert.equal(vm.runInContext('commodityLatestDate(sample)',ctx),'2026-10-09');
    assert.match(vm.runInContext('commoditySeriesLabel(sample)',ctx),/Vencimiento: Mayo 2027 \(MAY2027\)/);
    const lines=JSON.parse(vm.runInContext('JSON.stringify(commodityTooltipLines(sample,400,"2026-10-09"))',ctx));
    assert.ok(lines.includes('Cotización: 09/10/2026'));
    assert.ok(lines.join(' ').includes('Mayo 2027 (MAY2027)'));
    vm.runInContext("commoditySource='magyp_internal';commodityFrequency='mensual';updateCommoditySourcePresentation();",ctx);
    const daily=nodes.get('commodityFilterFrequency').daily;
    assert.equal(daily.disabled,true);assert.equal(daily.hidden,true);
    assert.equal(nodes.get('commoditySourceSubtitle').textContent,'Precio interno mensual — MAGyP');
});

test('hover tooltip stays compact with long source links and equal-price series',()=>{
    const ctx=context();
    ctx.sample={commodity:'SOJA',mercado:'Rosario',fuente:'MAGyP',moneda:'ARS',unidad:'TN',
        tipo_precio:'Precio interno mensual',source_url:'https://www.magyp.gob.ar/'+ 'long-path/'.repeat(100),
        updated_at_utc:'2026-10-09T14:33:00Z',variacion_mensual_pct:2.5};
    const lines=JSON.parse(vm.runInContext('JSON.stringify(commodityTooltipLines(sample,466190.5,"2026-06","Precio de referencia"))',ctx));
    assert.ok(lines.every(line=>line.length<=42));
    assert.ok(lines.length<=9);
    assert.ok(lines.some(line=>line.includes('ARS / TN')));
    assert.ok(lines.some(line=>line.includes('MAGyP')));
    assert.ok(lines.includes('Fuente: MAGyP'));
    assert.ok(lines.every(line=>!line.includes('https://')));
    assert.equal(ctx.sample.source_url.length>500,true);
    const options=vm.runInContext('commodityChartOptions()',ctx);
    assert.equal(options.interaction.mode,'nearest');
    assert.equal(options.plugins.tooltip.mode,'nearest');
    assert.equal(options.plugins.tooltip.filter({},0),true);
    assert.equal(options.plugins.tooltip.filter({},1),false);
    vm.runInContext("commoditySource='magyp_fob';commodityFrequency='diaria'",ctx);
    ctx.sample={...ctx.sample,condicion_comercial:'2026-10/2026-11',circular:'2076',moneda:'Sin identificar',unidad:'Sin identificar'};
    const fob=JSON.parse(vm.runInContext('JSON.stringify(commodityTooltipLines(sample,290,"2026-10-08"))',ctx));
    assert.ok(fob.some(line=>line.includes('2026-10/2026-11')));
    assert.ok(fob.some(line=>line.includes('2076')));
    assert.ok(fob.every(line=>line.length<=42));
});

test('multiple reference series request a selection; single-series values and missing-data placeholders remain',()=>{
    const ctx=context();
    const nodes=new Map();
    ctx.document={getElementById(id){
        if(!nodes.has(id))nodes.set(id,{value:'TODOS',textContent:''});
        return nodes.get(id);
    }};
    ctx.input=fs.readFileSync('data/magyp/dashboard/commodities/internal.csv','utf8');
    vm.runInContext(`commoditySource='magyp_internal';commodityFrequency='mensual';
        commodityData=parseReferenceCommodityBundle(input);
        updateCommodityKpis(commodityData.mensual,commodityData.ultimos);`,ctx);
    for(const id of ['commodityKpiMedian','commodityKpiMonthlyVariation','commodityKpiYoYVariation']) {
        assert.equal(nodes.get(id).textContent,'Seleccioná una serie');
    }
    const expected=vm.runInContext(`(() => {
        const row=commodityData.ultimos[0];
        updateCommodityKpis(commodityData.mensual.filter(item=>item.series_id===row.series_id),[row]);
        return formatNumber(commodityLatestPrice(row));
    })()`,ctx);
    assert.equal(nodes.get('commodityKpiMedian').textContent,expected);
    vm.runInContext('updateCommodityKpis([],[])',ctx);
    assert.equal(nodes.get('commodityKpiMedian').textContent,'–');
});
test('every public reference bundle has all existing views and original grain',()=>{
    const ctx=context();
    for(const source of ['internal','board','fas','fob','futures']) {
        ctx.input=fs.readFileSync(`data/magyp/dashboard/commodities/${source}.csv`,'utf8');
        const result=JSON.parse(vm.runInContext('JSON.stringify(parseReferenceCommodityBundle(input))',ctx));
        assert.ok(result.mensual.length);assert.ok(result.ultimos.length);assert.ok(result.semaforo.length);
        assert.equal(result.resumen.length,1);
        if(source!=='internal')assert.ok(result.diario.length);
        if(source==='fob')assert.ok(result.diario.every(row=>row.moneda==='Sin identificar'&&row.unidad==='Sin identificar'));
        if(source==='futures')assert.ok(result.diario.every(row=>['CHICAGO','KANSAS'].includes(row.mercado)));
    }
});
test('empty, wrong schema, count mismatch and invalid trace rejected',()=>{
    const ctx=context();
    const body=fs.readFileSync('data/magyp/dashboard/commodities/board.csv','utf8');
    for(const input of ['',body.replaceAll('magyp-references-v1','unknown'),body.replaceAll(/\b[a-f0-9]{64}\b/g,'bad')]) {
        ctx.input=input;assert.throws(()=>vm.runInContext('parseReferenceCommodityBundle(input)',ctx));
    }
    ctx.input=fs.readFileSync('data/magyp/dashboard/commodities/fob.csv','utf8');
    assert.throws(()=>vm.runInContext("parseReferenceCommodityBundle(input, 'magyp_board')",ctx));
});
test('el archivo FOB conserva etiquetas y series originales para revisión posterior',()=>{
    const ctx=context();
    const bundle=zlib.gunzipSync(fs.readFileSync('data/magyp/dashboard/commodities/fob.csv.gz')).toString('utf8');
    ctx.bundle=bundle;
    const labels=JSON.parse(vm.runInContext(`JSON.stringify([...new Set(parseReferenceCommodityBundle(bundle,'magyp_fob').mensual.map(row=>row.condicion_comercial).filter(Boolean))])`,ctx));
    assert.ok(labels.length>1);
});
test('daily latest is the last closing observation, not the monthly median',()=>{
    const ctx=context();
    ctx.input=fs.readFileSync('data/magyp/dashboard/commodities/futures.csv','utf8');
    const result=JSON.parse(vm.runInContext(`commoditySource='magyp_futures';commodityFrequency='diaria';
        commodityData=parseReferenceCommodityBundle(input);
        JSON.stringify(getCommodityLatestRows())`,ctx));
    assert.ok(result.length);
    const daily=JSON.parse(vm.runInContext('JSON.stringify(commodityData.diario)',ctx));
    for(const row of result) {
        const dates=daily.filter(item=>item.series_id===row.series_id&&Number(item.price)>0)
            .map(item=>item.fecha).sort();
        assert.equal(row.periodo_ultimo,dates.at(-1));
    }
    assert.ok(result.every(row=>row.precio_mediana_ultimo_periodo===row.price));
    assert.ok(result.every(row=>row.variacion_mensual_pct===undefined));
});
test('legacy SIO/local series keys, parsing and filters match committed behavior',()=>{
    const before=context(baseline),after=context();
    for(const source of ['sio','local_mensual']) {
        const sample=`commoditySource='${source}';commodityData={diario:[],mensual:[
         {commodity:'Soja',fuente:'SIO',mercado:'Rosario',moneda:'ARS',unidad:'TN',tipo_precio:'Precio Hecho',precio_mediana:'100'},
         {commodity:'Soja',fuente:'SIO',mercado:'Rosario',moneda:'USD',unidad:'TN',tipo_precio:'Precio Hecho',precio_mediana:'0'}],ultimos:[]};
         JSON.stringify({rows:getCommodityFilteredRows(),key:commoditySeriesKey(commodityData.mensual[0]),
             normalized:normalizeCommodityRecord({unidad:'$/Tn',mercado:'Rosario'})})`;
        assert.equal(vm.runInContext(sample,after),vm.runInContext(sample,before));
    }
});
test('all preexisting controls/canvases remain in HTML',()=>{
    const html=fs.readFileSync('index.html','utf8');
    const old=execFileSync('git',['show','d82fcbc:index.html'],{encoding:'utf8'});
    const ids=text=>[...text.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
    const existing=new Set(ids(html));
    for(const id of ids(old))assert.ok(existing.has(id),id);
    assert.ok(html.includes('Tipo de referencia / Fuente'));
});
test('official download failure never reactivates retired manual prices; SIO remains independent',async()=>{
    const ctx=context();
    const requests=[];
    ctx.fetch=async url=>{
        requests.push(url);
        if(url.includes('data/magyp/'))return {ok:false,status:503};
        return {ok:true,text:async()=>fs.readFileSync(url,'utf8')};
    };
    vm.runInContext(`initCommoditySourceFilter=()=>{};setCommoditySource=()=>{};`,ctx);
    await vm.runInContext('loadCommodityData()',ctx);
    assert.equal(vm.runInContext('commodityDataBySource.magyp_internal.mensual.length',ctx),0);
    assert.equal(requests.some(url=>url.includes('commodities_local_mensual')),false);
    assert.ok(vm.runInContext('commodityDataBySource.sio.diario.length',ctx)>0);
});
