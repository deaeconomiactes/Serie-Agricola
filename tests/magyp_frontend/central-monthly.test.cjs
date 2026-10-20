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
 assert.equal(result.length,3723);assert.equal(result.length,marker.record_count);
 const adapted=monthly.adapt(result.slice(0,1),['Enero']);
 assert.equal(adapted[0].data_source,'MERCADO_CENTRAL');
 assert.equal(adapted[0].fechaPrecision,'mensual');
 assert.match(adapted[0].metodoConversion,/derivada/);
 assert.equal(adapted[0].precioObservado,Number(result[0].price));
 assert.equal(adapted[0].volume,undefined);
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
 try {const result=await monthly.load();assert.deepEqual(result.rows,[]);assert.match(result.warning,/legacy/);}
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
