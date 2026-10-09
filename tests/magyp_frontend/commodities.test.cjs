const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const current = fs.readFileSync('app.js','utf8');
const baseline = execFileSync('git',['show','d82fcbc:app.js'],{encoding:'utf8'});
function context(code=current) {
    const ctx=vm.createContext({console:{error(){}},document:{addEventListener(){},getElementById(){return {value:'TODOS'};}}});
    vm.runInContext(code,ctx);return ctx;
}

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
        magyp_fob:'diaria',magyp_futures:'diaria',sio:'mensual'};
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
test('FOB windows/circulars remain separate at monthly frequency',()=>{
    const ctx=context();
    const result=vm.runInContext(`commoditySource='magyp_fob';commodityFrequency='mensual';
      [commoditySeriesKey({commodity:'Posición A',series_id:'one',condicion_comercial:'2026-10/2026-10'}),
       commoditySeriesKey({commodity:'Posición A',series_id:'two',condicion_comercial:'2026-11/2026-11'})]`,ctx);
    assert.notEqual(result[0],result[1]);
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
test('internal download failure uses independent legacy fallback',async()=>{
    const ctx=context();
    ctx.fetch=async url=>{
        if(url.includes('data/magyp/'))return {ok:false,status:503};
        return {ok:true,text:async()=>fs.readFileSync(url,'utf8')};
    };
    vm.runInContext(`initCommoditySourceFilter=()=>{};setCommoditySource=()=>{};`,ctx);
    await vm.runInContext('loadCommodityData()',ctx);
    assert.equal(vm.runInContext('commodityDataBySource.magyp_internal.resumen[0].modo',ctx),'legacy_fallback');
    assert.ok(vm.runInContext('commodityDataBySource.magyp_internal.mensual.length',ctx)>0);
    assert.ok(vm.runInContext('commodityDataBySource.sio.diario.length',ctx)>0);
});
