const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'../..');
const {makeNormalizer}=require('../../scripts/mayoristas/normalize.cjs');
const products=require('../../data/mayoristas/config/producto_variedad_aliases.json');
const origins=require('../../data/mayoristas/config/procedencia_aliases.json');
const blank={especie:'Producto',variedad:'',procedencia:'Corrientes',mercado:'Mercado de Corrientes',
 unidadPrecioObservado:'$/bulto',kgBulto:10,precioObservado:100,precioKgEstimado:10,confianzaConversion:'Media'};
const normalize=makeNormalizer(root,{mensual:[blank]});

test('approved mappings preserve available raw fields and cover at least ten products',()=>{
 const approved=products.filter(r=>r.status==='APPROVED');
 assert.ok(new Set(approved.map(r=>r.producto)).size>=10);
 for(const rule of approved) {
  const result=normalize({...blank,especie:rule.raw,legacy_especie_raw:rule.raw});
  assert.equal(result.producto_raw,rule.raw);assert.equal(result.especie,rule.producto);assert.equal(result.variedad,rule.variedad);
 }
 const review=products.find(r=>r.status==='REVIEW_REQUIRED');
 assert.equal(normalize({...blank,especie:review.raw}).especie,review.raw);
 const sandia=normalize({...blank,especie:'Sandia Redonda Rayada',legacy_especie_raw:'Sandia Redonda Rayada'});
 assert.equal(sandia.especie,'Sandía');assert.equal(sandia.variedad,'Redonda Rayada');
 assert.equal(sandia.producto_raw,'Sandia Redonda Rayada');
 const base=normalize({...blank,especie:'Sandia',variedad:'Redonda Ra'});
 assert.equal(base.especie,'Sandía');assert.equal(base.variedad,'Redonda Ra');
});
test('provenance aliases are explicit and preserve provinces versus subregions',()=>{
 const approved=origins.filter(r=>r.status==='APPROVED');assert.ok(approved.length>=10);
 for(const rule of approved) {
  const result=normalize({...blank,procedencia:rule.raw,legacy_procedencia_raw:rule.raw});
  assert.equal(result.procedencia,rule.canonical);assert.equal(result.procedencia_raw,rule.raw);
 }
 assert.equal(normalize({...blank,procedencia:'Ctes.'}).procedencia,normalize({...blank,procedencia:'Corrientes'}).procedencia);
 assert.notEqual(normalize({...blank,procedencia:'S.bs.as.'}).procedencia,normalize({...blank,procedencia:'Buenos Aires'}).procedencia);
});
test('currency is independent from unit and conversion metadata survives',()=>{
 const row=normalize(blank);assert.equal(row.moneda_normalizada,'UNKNOWN');assert.equal(row.unidad_normalizada,'bulto');
 assert.equal(row.factor_conversion,0.1);assert.equal(row.peso_utilizado,10);assert.equal(row.precioKgEstimado,10);
 assert.equal(normalize({...blank,currency:'ARS'}).moneda_normalizada,'ARS');
 assert.equal(normalize({...blank,currency:'$'}).moneda_normalizada,'UNKNOWN');
 assert.equal(normalize({...blank,envase:'Caja X 10 Kg'}).conversion_validada,true);
 assert.equal(normalize({...blank,envase:'Granel X Kg'}).conversion_validada,false);
});
test('comparison blocks unknown currency and incompatible units, varieties and packages',()=>{
 const ctx=vm.createContext({console,document:{addEventListener(){}}});
 vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx);
 const base={especie:'Producto',variedad:'Uno',procedencia:'Origen',envase:'Caja',fechaPrecision:'mensual',
  precioKgEstimado:1,precioObservado:1,confianzaConversion:'Alta',unidad_normalizada:'kg',moneda_normalizada:'ARS'};
 ctx.rows=[{...base,mercado:'A'},{...base,mercado:'B'}];
 const compare=()=>vm.runInContext("comparePriceMarkets(rows,{mercado:['A','B']}).status",ctx);
 assert.equal(compare(),'COMPARABLE');ctx.rows[1].moneda_normalizada='UNKNOWN';assert.equal(compare(),'NO_COMPARABLE_CURRENCY');
 ctx.rows[1].moneda_normalizada='ARS';ctx.rows[1].variedad='Dos';assert.equal(compare(),'NO_COMMON_VARIETY');
 ctx.rows[1].variedad='Uno';ctx.rows[1].envase='Bolsa';assert.equal(compare(),'NO_COMMON_PRESENTATION');
 ctx.rows[1].envase='Caja';ctx.rows[1].precioKgEstimado=null;assert.equal(compare(),'NO_COMPARABLE_UNIT');
});
test('monthly and annual aggregation weights dates and months equally',()=>{
 const ctx=vm.createContext({console,document:{addEventListener(){}}});
 vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx);
 ctx.rows=[{fecha:'2026-01-01',precioKgEstimado:10},{fecha:'2026-01-01',precioKgEstimado:30},
  {fecha:'2026-01-02',precioKgEstimado:100},{fecha:'2026-02-01',precioKgEstimado:200}];
 assert.deepEqual(JSON.parse(vm.runInContext("JSON.stringify(aggregatePriceData(rows,'mensual'))",ctx)),
  [{key:'2026-01',value:60},{key:'2026-02',value:200}]);
 assert.deepEqual(JSON.parse(vm.runInContext("JSON.stringify(aggregatePriceData(rows,'anual'))",ctx)),[{key:'2026',value:130}]);
});
test('2026 production shards retain both tomato markets and the confirmed source currency',async()=>{
 global.crypto=require('node:crypto').webcrypto;
 const {Loader}=require('../../mayoristas-loader.js');
 const folder=process.env.MAYORISTAS_DELIVERY_ROOT ? path.resolve(process.env.MAYORISTAS_DELIVERY_ROOT) : path.join(root,'data/mayoristas/dashboard');
 const loader=new Loader(async url=>{const body=fs.readFileSync(path.join(folder,path.basename(url)));return {ok:true,arrayBuffer:async()=>body.buffer.slice(body.byteOffset,body.byteOffset+body.byteLength)};});
 const {rows}=await loader.load({year:2026,frequency:'mensual',markets:['TODOS']});
 const sandia=rows.filter(r=>r.producto_raw==='Sandia Redonda Rayada');
 assert.ok(sandia.length>0);
 assert.ok(sandia.every(r=>r.especie==='Sandía'&&r.variedad==='Redonda Rayada'));
 const tomato=rows.filter(r=>r.especie==='Tomate'&&r.procedencia==='Corrientes');
 const central=tomato.filter(r=>r.mercado==='Mercado Central de Buenos Aires');
 const corrientes=tomato.filter(r=>r.mercado==='Mercado de Corrientes');
 assert.ok(central.length>0);assert.ok(corrientes.length>0);
 assert.ok(central.every(r=>r.moneda_normalizada==='ARS'&&r.procedencia_raw));
 assert.ok(corrientes.every(r=>r.moneda_normalizada==='ARS'&&r.moneda_original===''&&r.producto_raw.toUpperCase().startsWith('TOMATE ')));
 assert.ok(corrientes.some(r=>r.fecha<='2026-10-29'));
 const pairs=new Map();
 for(const row of rows.filter(r=>r.fecha && r.fecha<='2026-10-29')) {
  const pair=JSON.stringify([row.especie,row.procedencia]);
  const group=pairs.get(pair)||[];group.push(row);pairs.set(pair,group);
 }
 const common=[...pairs].filter(([,group])=>new Set(group.map(r=>r.mercado)).size===2);
 assert.ok(new Set(common.map(([pair])=>JSON.parse(pair)[0])).size>=10);
 assert.ok(new Set(common.map(([pair])=>JSON.parse(pair)[1])).size>=10);
 const ctx=vm.createContext({console,document:{addEventListener(){}}});
 vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx);
 ctx.tomato=tomato.filter(r=>r.fecha && r.fecha<='2026-10-29');
 const actual=JSON.parse(vm.runInContext(`JSON.stringify(comparableMarketSelection(tomato,{mercado:['Mercado Central de Buenos Aires','Mercado de Corrientes'],especie:['Tomate'],procedencia:['Corrientes'],variedad:['TODOS']},'mensual'))`,ctx));
 assert.equal(actual.status,'COMPARABLE');assert.ok(actual.combinations.length>0);
 const redondo=actual.combinations.find(candidate=>candidate.variety==='REDONDO' && /P\/I/.test(candidate.label));
 assert.ok(redondo);assert.match(redondo.label,/Tomate Redondo/);
 for(const month of ['2026-04','2026-05','2026-06','2026-07','2026-08']) assert.ok(redondo.months.includes(month));
 assert.ok(redondo.rows.length>0);assert.ok(redondo.rows.every(r=>r.variedad==='Redondo'));
 for(const candidate of actual.combinations) {
  assert.equal(new Set(candidate.rows.map(r=>r.mercado)).size,2);
  assert.equal(new Set(candidate.rows.map(r=>r.variedad.toUpperCase())).size,1);
 }
 const matched=new Set(actual.combinations.map(candidate=>candidate.variety));
 assert.ok(actual.unavailableVarieties.every(variety=>!matched.has(variety.toUpperCase())));
 for(const product of ['Zanahoria','Berenjena','Pepino']) {
  const entry=common.find(([pair])=>JSON.parse(pair)[0]===product);assert.ok(entry,product+' tiene datos en ambos mercados');
  const [,origin]=JSON.parse(entry[0]);ctx.otherRows=entry[1];ctx.otherFilters={mercado:['Mercado Central de Buenos Aires','Mercado de Corrientes'],especie:[product],procedencia:[origin],variedad:['TODOS']};
  const result=JSON.parse(vm.runInContext("JSON.stringify(comparableMarketSelection(otherRows,otherFilters,'mensual'))",ctx));
  if(result.status==='COMPARABLE') for(const candidate of result.combinations) {
   assert.equal(new Set(candidate.rows.map(r=>r.mercado)).size,2);
   assert.ok(candidate.rows.every(r=>r.especie===product && r.procedencia===origin));
   assert.ok(candidate.months.length>0);
  }
 }
 for(const [,group] of common) {
  ctx.rows=group;
  assert.notEqual(vm.runInContext("comparePriceMarkets(rows,{mercado:['Mercado Central de Buenos Aires','Mercado de Corrientes']}).status",ctx),'NO_COMPARABLE_CURRENCY');
 }
});
test('source currency is confirmed independently of raw unit and doubtful bundles are rejected',()=>{
 const row=normalize({...blank,data_source:'LEGACY',envase:'Torito X 10 Kg'});
 assert.equal(row.moneda_original,'');assert.equal(row.moneda_normalizada,'ARS');assert.equal(row.precioKgEstimado,10);
 assert.equal(normalize({...blank,data_source:'LEGACY',envase:'Doc. de Mazo X 10 Kg'}).conversion_validada,false);
});
test('monthly market comparison requires matching variety and package and retains shared periods',()=>{
 const ctx=vm.createContext({console,document:{addEventListener(){}}});vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx);
 const dims={especie:'Tomate',variedad:'Redondo',procedencia:'Corrientes',fechaPrecision:'mensual'};
 ctx.rows=[{...dims,mercado:'A',fecha:'2026-05-01',moneda_normalizada:'ARS',envase:'Torito',kg_raw:'18',precioKgEstimado:10,confianzaConversion:'Alta'},
  {...dims,mercado:'B',fecha:'2026-05-20',moneda_normalizada:'ARS',envase:'Torito X 18 Kg',kgBulto:18,precioKgEstimado:20,confianzaConversion:'Media',conversion_validada:true},
  {...dims,mercado:'B',fecha:'2026-05-20',moneda_normalizada:'ARS',envase:'Doc. de Mazo X 18 Kg',kgBulto:18,precioKgEstimado:30,confianzaConversion:'Media',conversion_validada:false}];
 ctx.filters={mercado:['A','B'],especie:['Tomate'],variedad:['Redondo'],procedencia:['Corrientes']};
 assert.equal(vm.runInContext("comparableMarketSelection(rows,filters,'mensual').status",ctx),'COMPARABLE');
 assert.equal(vm.runInContext("comparableMarketSelection(rows,filters,'mensual').rows.length",ctx),2);
 ctx.rows[0].envase='Perdido';assert.equal(vm.runInContext("comparableMarketSelection(rows,filters,'mensual').status",ctx),'NO_COMMON_PRESENTATION');
});
