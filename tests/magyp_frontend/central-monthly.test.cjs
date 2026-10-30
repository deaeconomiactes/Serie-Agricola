const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
global.crypto=require('node:crypto').webcrypto;
global.MCBAPrices=require('../../mcba-prices.js');
const monthly=require('../../mcba-monthly.js');
const folder=path.join(__dirname,'../../data/mercado_central/dashboard/mcba');
const text=fs.readFileSync(path.join(folder,monthly.FILE),'utf8');
const marker=JSON.parse(fs.readFileSync(path.join(folder,'_SUCCESS.json'),'utf8'));
const rows=MCBAPrices.parseCSV(text,['date','price']);
// parseCSV's default contract is daily MAGyP; use the public monthly loader for checks.
test('official Central derived publication has valid hash, rows, period and source',async()=>{
 const result=await monthly.verify(text,marker);
 assert.ok(result.length>0);assert.equal(result.length,marker.record_count);
 const adapted=monthly.adapt(result.slice(0,1),['Enero']);
 assert.equal(adapted[0].data_source,'MERCADO_CENTRAL');
 assert.equal(adapted[0].fechaPrecision,'mensual');
 assert.match(adapted[0].metodoConversion,/derivada/);
 assert.equal(adapted[0].precioObservado,Number(result[0].price));
 assert.equal(adapted[0].volume,undefined);
});
test('el conteo se valida contra el manifiesto y no contra una cifra fija',async()=>{
 const first=await monthly.verify(text,marker);
 const header=text.slice(0,text.indexOf('\n'));
 const lines=text.trimEnd().split('\n');
 const columns=header.split(',');
 const idColumn=columns.indexOf('observation_id');
 // Change the ID of an otherwise valid row to model a later publication.
 const parsed=MCBAPrices.parseCSV(text,['date','price']);
 const sample=parsed[0];
 const csv=value=>`"${String(value ?? '').replace(/"/g,'""')}"`;
 const added=columns.map(name=>csv(name==='observation_id' ? sample.observation_id+'-new' : sample[name])).join(',');
 assert.ok(idColumn>=0);
 const expanded=lines.join('\n')+'\n'+added+'\n';
 const sha=require('node:crypto').createHash('sha256').update(expanded).digest('hex');
 const expandedMarker={...marker,files:{...marker.files,[monthly.FILE]:sha},record_count:first.length+1};
 assert.equal((await monthly.verify(expanded,expandedMarker)).length,first.length+1);
 await assert.rejects(monthly.verify(expanded,{...expandedMarker,record_count:first.length}),/Conteo/);
});
test('corrupt, empty, wrong currency/schema/date and duplicate monthly data fail closed',async()=>{
 await assert.rejects(monthly.verify(text+'\n',marker));
 assert.throws(()=>monthly.validate([]));
 for(const [field,value] of [['currency','USD'],['price_unit','box'],['price','NaN'],['schema_version','bad'],['date','2026-02-31'],['source_url','https://attacker.invalid/file']]) {
  assert.throws(()=>monthly.validate([{...rows[0],[field]:value}]));
 }
 assert.throws(()=>monthly.validate([rows[0],rows[0]]));
});
test('coverage by month/category preserves legacy holes and Corrientes without filling missing products',()=>{
 const old=[{mercado:MCBAPrices.MCBA,fecha:'2025-12-01',rubro:'Frutas',especie:'A'},
  {mercado:MCBAPrices.MCBA,fecha:'2026-01-02',rubro:'Frutas',especie:'Missing product'},
  {mercado:MCBAPrices.MCBA,fecha:'2026-01-02',rubro:'Hortalizas',especie:'B'},
  {mercado:'Mercado de Corrientes',fecha:'2026-01-02',rubro:'Frutas',especie:'A'}];
 const fresh=[{mercado:MCBAPrices.MCBA,fecha:'2026-01-01',rubro:'Frutas',especie:'A'}];
 const routed=monthly.route(old,fresh);
 assert.equal(routed.length,4);assert.ok(!routed.some(r=>r.especie==='Missing product'));
 assert.strictEqual(routed.find(r=>r.mercado==='Mercado de Corrientes'),old[3]);
 assert.ok(routed.includes(old[0]));assert.ok(routed.includes(old[2]));
});
test('source load failure is explicit legacy fallback; never substitutes daily MAGyP for monthly',async()=>{
 const previous=global.fetch;global.fetch=async()=>{throw Error('offline');};
 try {const result=await monthly.load();assert.deepEqual(result.rows,[]);assert.match(result.warning,/histórico validado/); assert.doesNotMatch(result.warning,/legacy|fallback|pipeline/i);}
 finally{global.fetch=previous;}
});
test('module routes daily MAGyP and monthly Central separately; annual remains legacy',()=>{
 const context=vm.createContext({console,document:{addEventListener(){}},MCBAPrices,MCBAMonthly:monthly});
 vm.runInContext(fs.readFileSync('app.js','utf8'),context);
 vm.runInContext(`
 const legacy={mercado:MCBAPrices.MCBA,fecha:'2026-01-02',rubro:'Frutas',data_source:'LEGACY',fechaPrecision:'diaria'};
 const daily={...legacy,data_source:'MAGYP'};
 const derived={...legacy,fecha:'2026-01-01',fechaPrecision:'mensual',data_source:'MERCADO_CENTRAL'};
 validPriceData=[legacy,daily,derived]; mcbaMonthlyData=[derived]; magypPriceInfo={};
 `,context);
 assert.equal(vm.runInContext("getPriceSourceRows('diaria')[0].data_source",context),'MAGYP');
 assert.equal(vm.runInContext("getPriceSourceRows('mensual')[0].data_source",context),'MERCADO_CENTRAL');
 assert.equal(vm.runInContext("getPriceSourceRows('anual')[0].data_source",context),'LEGACY');
});

test('official-only monthly selection is one homogeneous series without technical source split',()=>{
 const context=vm.createContext({console,document:{addEventListener(){}},MCBAPrices,MCBAMonthly:monthly});
 vm.runInContext(fs.readFileSync('app.js','utf8'),context);
 const result=JSON.parse(vm.runInContext(`JSON.stringify((()=>{
   const base={mercado:MCBAPrices.MCBA,especie:'Manzana',variedad:'Red',procedencia:'Río Negro',
     data_source:'MERCADO_CENTRAL',precioObservado:100,precioKgEstimado:100,confianzaConversion:'Alta'};
   return preparePriceEvolutionData([{...base,fecha:'2026-01-01'}, {...base,fecha:'2026-02-01'}],
     'mensual',{especie:['TODOS']});
 })())`,context));
 assert.equal(result.series.length,1);
 assert.ok(!result.splitDimensions.includes('data_source'));
 assert.doesNotMatch(result.series[0].label,/legacy|fallback|pipeline/i);
});

test('MCBA monthly metadata describes selected coverage and does not label historical years current',()=>{
 const nodes={};
 const node=id=>nodes[id]||(nodes[id]={value:id==='priceFilterMercado'?MCBAPrices.MCBA:'TODOS',
   classList:{toggle(){}},ownerDocument:{createElement:()=>({})},replaceChildren(){this.children=[];},
   append(...items){this.children.push(...items);}});
 const context=vm.createContext({console,document:{addEventListener(){},getElementById:node},
   MCBAPrices,MCBAMonthly:monthly,SourceUpdateStatus:require('../../update-status.js')});
 vm.runInContext(fs.readFileSync('app.js','utf8'),context);
 vm.runInContext(`priceFrequency='mensual';
   const base={mercado:MCBAPrices.MCBA,rubro:'Frutas',especie:'Manzana',precioObservado:100};
   filteredPriceData=[{...base,fecha:'2024-01-01',data_source:'LEGACY',source_status:'LEGACY'}];
   priceFreshnessBySource.mcba_monthly={status:'UPDATED',last_observation_date:'2026-10-19'};
   updatePriceSourceStatus();`,context);
 assert.match(nodes.mcbaMonthlyUpdateStatus.children[0].textContent,/Fuente estática/);
 assert.doesNotMatch(nodes.priceSourceStatus.textContent,/legacy|fallback|pipeline/i);
 assert.match(nodes.priceSourceStatus.textContent,/Fuente: Mercado Central de Buenos Aires/);
 vm.runInContext(`filteredPriceData=[{...base,fecha:'2026-10-01',data_source:'MERCADO_CENTRAL',source_status:'MERCADO_CENTRAL'}];updatePriceSourceStatus();`,context);
 assert.match(nodes.mcbaMonthlyUpdateStatus.children[0].textContent,/Actualizado/);
 assert.doesNotMatch(nodes.mcbaMonthlyUpdateStatus.title,/pipeline/i);
 assert.match(nodes.priceSourceStatus.textContent,/Agregación mensual derivada/);
 assert.match(nodes.priceSourceStatus.textContent,/Último período:/);
});
