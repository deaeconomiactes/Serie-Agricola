const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const source=fs.readFileSync('app.js','utf8');
function context(code=source) {
 const nodes=new Map();
 const ctx=vm.createContext({console,document:{addEventListener(){},getElementById(id){
  if(!nodes.has(id))nodes.set(id,{value:'TODOS',textContent:'',innerHTML:'',style:{},dataset:{},classList:{add(){},remove(){},toggle(){}}});
  return nodes.get(id);
 }}});
 vm.runInContext(code,ctx);return {ctx,nodes};
}
function row(id,changes={}) {return {schema_version:'sio-transactions-v2',series_id:id,
 commodity:'Maíz',moneda:'USD',unidad:'TN',tipo_precio:'Precio Hecho',fuente:'SIO Granos',
 lugar_entrega:'Rosario NEn destino',procedencia:'Córdoba',condicion_comercial:'Entrega inmediata',
 condicion_serie:'Comercial: Entrega inmediata · Pago: Contra entrega · Evento: Contrato',
 periodo_ym:'2026-09',precio_mediana:'100',operaciones:'1',...changes};}

test('delivery places, missing delivery and old multiple-delivery aggregates have distinct labels',()=>{
 const {ctx}=context();ctx.rows=[row('a'),row('b',{lugar_entrega:'',delivery_status:'MISSING'}),
  {fuente:'SIO Granos',lugares_entrega:'Rosario|Quequén'}];
 const values=JSON.parse(vm.runInContext("commoditySource='sio';JSON.stringify(rows.map(r=>commodityMarketLabel(commodityMarketValue(r))))",ctx));
 assert.deepEqual(values,['Rosario NEn destino','Lugar no informado','Múltiples lugares (agregado histórico)']);
});

test('daily and monthly filters preserve delivery, conditions, origin and currency',()=>{
 const {ctx,nodes}=context();ctx.rows=[row('a'),row('b',{lugar_entrega:'Rosario SEn destino'}),
  row('c',{condicion_serie:'Pago: A plazo'}),row('d',{moneda:'ARS'}),row('e',{procedencia:'Santa Fe'})];
 vm.runInContext("commoditySource='sio';commodityData={mensual:rows,diario:rows.map(r=>({...r,fecha:'2026-09-09'})),ultimos:[]}",ctx);
 nodes.set('commodityFilterMarket',{value:'Rosario NEn destino'});
 nodes.set('commodityFilterCurrency',{value:'USD'});
 nodes.set('commodityFilterOrigin',{value:'Córdoba'});
 nodes.set('commodityFilterCondition',{value:ctx.rows[0].condicion_serie});
 for(const frequency of ['mensual','diaria']) {
  assert.equal(vm.runInContext(`commodityFrequency='${frequency}';getCommodityFilteredRows().length`,ctx),1);
  assert.equal(vm.runInContext('getCommodityFilteredRows()[0].series_id',ctx),'a');
 }
});

test('monthly latest is the last monthly event aggregate, not the last daily observation',()=>{
 const {ctx}=context();ctx.rows=[row('a',{periodo_ym:'2026-08',precio_mediana:'80'}),row('a',{periodo_ym:'2026-09',precio_mediana:'120'})];
 vm.runInContext("commoditySource='sio';commodityFrequency='mensual';commodityData={mensual:rows,diario:[],ultimos:[{...rows[1],precio_mediana_ultimo_dia:'200',fecha_ultima:'2026-09-09'}]}",ctx);
 assert.equal(vm.runInContext('commodityLatestPrice(getCommodityLatestRows()[0])',ctx),120);
 assert.equal(vm.runInContext('commodityLatestDate(getCommodityLatestRows()[0])',ctx),'2026-09');
});

test('multiple SIO series request one series; a single series retains its observed median',()=>{
 const {ctx,nodes}=context();ctx.rows=[row('a'),row('b',{lugar_entrega:'Zona 5En origen',precio_mediana:'200'})];
 vm.runInContext("commoditySource='sio';updateCommodityKpis(rows,rows.map(r=>({...r,precio_mediana_ultimo_dia:r.precio_mediana,fecha_ultima:'2026-09-09'})))",ctx);
 assert.equal(nodes.get('commodityKpiMedian').textContent,'Seleccioná una serie');
 vm.runInContext("updateCommodityKpis(rows.slice(0,1),[{...rows[0],precio_mediana_ultimo_dia:'100',fecha_ultima:'2026-09-09'}])",ctx);
 assert.equal(nodes.get('commodityKpiMedian').textContent,'100');
});

test('SIO semaphore retains separate rows for condition/place and uses monthly cells',()=>{
 const {ctx,nodes}=context();ctx.rows=[row('a',{variacion_mensual_pct:'10',estado:'Suba moderada'}),row('b',{condicion_serie:'Pago: A plazo',estado:'Sin dato'})];
 vm.runInContext("commoditySource='sio';renderCommoditySemaphore(rows)",ctx);
 const html=nodes.get('commoditySemaphoreBody').innerHTML;
 assert.equal((html.match(/<tr>/g)||[]).length,2);
 assert.ok(html.includes('Contra entrega'));assert.ok(html.includes('A plazo'));
});

test('all public SIO views have event lineage and 590 observations reconcile without double counting',()=>{
 const {ctx}=context();const counts={};
 for(const kind of ['DIARIO','MENSUAL','ULTIMOS','SEMAFORO']) {
  ctx.input=fs.readFileSync(`data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_${kind}.csv`,'utf8');
  const rows=JSON.parse(vm.runInContext('JSON.stringify(parseCommodityCSV(input))',ctx));
  assert.ok(rows.every(r=>r.schema_version==='sio-transactions-v2'&&r.series_id.length===64&&JSON.parse(r.event_ids).length>0));
  const ids=rows.flatMap(r=>JSON.parse(r.event_ids));
  if(kind!=='ULTIMOS') {assert.equal(ids.length,new Set(ids).size);counts[kind]=ids.length;}
 }
 assert.equal(counts.DIARIO,counts.MENSUAL);assert.equal(counts.DIARIO,counts.SEMAFORO);
 const audit=JSON.parse(fs.readFileSync('data/commodities_sio/reports/SIO_GRAIN_AUDIT.json','utf8'));
 assert.equal(counts.DIARIO,audit.eligible_events);
});

test('quoted SIO delivery ranges preserve line breaks, escaped quotes, semicolons and event lineage',()=>{
 const {ctx}=context();
 ctx.input='\uFEFFcommodity;fecha_entrega;event_ids;procedencia\r\nMaíz;"01/12/2026\n31/12/2026";"[""id:1""]";"Lugar; ""A"""\r\nTrigo;"01/01/2027\r\n31/01/2027";"[""id:2""]";Origen\r\n';
 const rows=JSON.parse(vm.runInContext('JSON.stringify(parseCommodityCSV(input))',ctx));
 assert.equal(rows.length,2);
 assert.equal(rows[0].fecha_entrega,'01/12/2026\n31/12/2026');
 assert.equal(rows[1].fecha_entrega,'01/01/2027\r\n31/01/2027');
 assert.equal(rows[0].procedencia,'Lugar; "A"');
 assert.deepEqual(JSON.parse(rows[0].event_ids),['id:1']);
 ctx.input='commodity;fecha_entrega\nMaíz;"sin cierre';
 assert.throws(()=>vm.runInContext('parseCommodityCSV(input)',ctx),/comillas sin cerrar/);
});

test('other MAGyP reference family rows, series and latest values match the pre-SIO implementation',()=>{
 const baseline=execFileSync('git',['show','abe1249:app.js'],{encoding:'utf8'});
 const before=context(baseline).ctx,after=context().ctx;
 for(const family of ['internal','board','fas','fob','futures']) {
  for(const ctx of [before,after])ctx.input=fs.readFileSync(`data/magyp/dashboard/commodities/${family}.csv`,'utf8');
  const expression=`commoditySource='magyp_${family}';commodityData=parseReferenceCommodityBundle(input);commodityFrequency='mensual';JSON.stringify({rows:getCommodityFilteredRows(),latest:getCommodityLatestRows(),keys:commodityData.mensual.map(r=>commoditySeriesKey(r))})`;
  assert.equal(vm.runInContext(expression,after),vm.runInContext(expression,before),family);
 }
});
