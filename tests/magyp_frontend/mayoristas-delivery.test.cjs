const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const zlib=require('node:zlib');
const vm=require('node:vm');
const {createHash,webcrypto}=require('node:crypto');
global.crypto=webcrypto;
const delivery=require('../../mayoristas-loader.js');
const {readSources}=require('../../scripts/mayoristas/source_rows.cjs');
const root=path.resolve(__dirname,'../..');
const folder=path.join(root,delivery.BASE);
const index=JSON.parse(fs.readFileSync(path.join(folder,'index.json'),'utf8'));
const quiet={log(){},warn(){},error(){}};
const digest=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
function fetcher(calls=[],modify=bytes=>bytes) {
 return async url=>{calls.push(url);const body=modify(fs.readFileSync(path.join(root,url)),url);return {ok:true,arrayBuffer:async()=>body.buffer.slice(body.byteOffset,body.byteOffset+body.byteLength)};};
}
test('index schema, exact counts, hashes and every published shard validate',async()=>{
 delivery.validateIndex(index);
 const loader=new delivery.Loader(fetcher());await loader.init();
 for(const f of index.fragments) {const rows=await loader.shard(f);assert.equal(rows.length,f.row_count);}
 assert.throws(()=>delivery.validateIndex({...index,schema_version:'other'}));
 assert.throws(()=>delivery.validateIndex({...index,fragments:[...index.fragments,index.fragments[0]]}));
 assert.throws(()=>delivery.validateIndex({...index,row_counts:{}}));
 assert.throws(()=>delivery.validateIndex({...index,fragments:[{...index.fragments[0],path:'../private.gz'}]}));
});
test('initial view loads only 2026 monthly for selected markets; hash cache reuses downloads',async()=>{
 const calls=[];const loader=new delivery.Loader(fetcher(calls));
 const result=await loader.load({year:2026,frequency:'mensual',markets:['TODOS']});
 assert.equal(result.rows.length,index.fragments.filter(f=>f.year===2026&&f.frequency==='mensual').reduce((sum,f)=>sum+f.row_count,0));
 assert.equal(calls.length,3);assert.ok(!calls.some(url=>/2024|2025|INTEGRADO/.test(url)));
 const initial=calls.length;await loader.load({year:2026,frequency:'mensual',markets:[index.markets[0]]});assert.equal(calls.length,initial);
 await loader.load({year:2025,frequency:'mensual',markets:[index.markets[0]]});assert.equal(calls.length,initial+1);
 assert.ok(calls.at(-1).includes('2025'));
});
test('corrupt hash, decompressed schema, count and HTTP failure reject without poisoning cache',async()=>{
 let broken=true;
 const loader=new delivery.Loader(async url=>{const body=fs.readFileSync(path.join(root,url));const bytes=broken&&url.endsWith('.gz')?Buffer.concat([body,Buffer.from('x')]):body;return {ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};});
 await loader.init();const f=index.fragments[0];await assert.rejects(loader.shard(f),/hash/);assert.equal(loader.cache.size,0);
 broken=false;await loader.shard(f);
 const rows=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(folder,f.path))));
 assert.throws(()=>delivery.validateRows(rows.slice(1),f),/conteo/);
 assert.throws(()=>delivery.validateRows([{...rows[0],year:1},...rows.slice(1)],f),/observación/);
 const offline=new delivery.Loader(async()=>({ok:false,status:503}));await assert.rejects(offline.load({}),/HTTP 503/);
});
test('late responses from previous selections are ignored and never become the current view',async()=>{
 let release;const gate=new Promise(resolve=>release=resolve);
 const loader=new delivery.Loader(async url=>{if(url.includes('2024'))await gate;return fetcher()(url);});
 await loader.init();const old=loader.load({year:2024,frequency:'mensual',markets:[index.markets[0]]});
 const current=await loader.load({year:2026,frequency:'mensual',markets:[index.markets[0]]});
 release();assert.equal(await old,null);assert.ok(current.rows.every(r=>r.year===2026));
});
test('exact economic equivalence: rows, KPIs, evolution, rankings, variation, semaphore and tables',async()=>{
 const original=await readSources(root);const ctx=original.context;ctx.console=quiet;ctx.document.getElementById=()=>({value:"TODOS"});
 const loader=new delivery.Loader(fetcher());await loader.init();
 const controls=[];
 for(const [market,frequency,years] of [[index.markets[0],'diaria',[2026]],[index.markets[0],'mensual',[2024,2025,2026]],[index.markets[1],'mensual',[2025,2026]],[index.markets[1],'diaria',[2025,2026]],[index.markets[0],'anual',[2024,2025,2026]]]) {
  for(const year of years) {
   const selection={year,frequency,markets:[market]};const actual=await loader.load(selection);
   const expected=original.views[frequency].filter(r=>r.year===year&&r.mercado===market);
   assert.equal(digest(actual.rows),digest(expected),JSON.stringify(selection)+' exact row order/content');
   ctx.testFilters={year:[String(year)],mercado:[market],mes:['TODOS'],rubro:['TODOS'],especie:['TODOS'],variedad:['TODOS'],procedencia:['TODOS'],unidad:['TODOS'],envase:['TODOS'],calidadMCBA:['TODOS'],tamanoMCBA:['TODOS'],gradoMCBA:['TODOS'],unidadComparable:'comparables'};
   const compute=rows=>{
    ctx.testRows=rows;ctx.testFrequency=frequency;
    return JSON.parse(vm.runInContext(`validPriceData=testRows;priceFrequency=testFrequency;priceDeliveryActive=true;getPriceFilters=()=>testFilters;
      const_equivalence_rows=getFilteredPriceData();
      JSON.stringify({rows:const_equivalence_rows.length,
        average:const_equivalence_rows.reduce((s,r)=>s+getPriceValue(r),0)/const_equivalence_rows.length,
        minimum:Math.min(...const_equivalence_rows.map(getPriceValue)),maximum:Math.max(...const_equivalence_rows.map(getPriceValue)),
        species:[...new Set(const_equivalence_rows.map(r=>r.especie))],varieties:[...new Set(const_equivalence_rows.map(r=>r.variedad))],
        latest:const_equivalence_rows.map(r=>r.fecha).sort().at(-1),
        evolution:preparePriceEvolutionData(const_equivalence_rows,priceFrequency,testFilters),
        ranking:preparePriceIncreaseRankingData(const_equivalence_rows,priceFrequency),
        decrease:preparePriceDecreaseRankingData(const_equivalence_rows,priceFrequency),
        variation:preparePriceVariationData(const_equivalence_rows,priceFrequency,testFilters),
        semaphore:buildMonthlyPriceSemaphoreMatrix(const_equivalence_rows,testFilters),
        tables:const_equivalence_rows})`,ctx));
   };
   const before=compute(expected),after=compute(actual.rows);
   assert.equal(digest(after),digest(before),JSON.stringify(selection)+' calculations');
   controls.push({...selection,rows:after.rows,average:after.average,minimum:after.minimum,maximum:after.maximum,latest:after.latest,exact_equal:true,sha256:digest(after)});
  }
 }
 assert.equal(controls.length,11);
 if(process.env.MAYORISTAS_EQUIVALENCE_REPORT)fs.writeFileSync(process.env.MAYORISTAS_EQUIVALENCE_REPORT,JSON.stringify({controls},null,2)+'\n');
});
test('scope: wholesale opening cannot fetch integrated or upstream full source publications',()=>{
 const app=fs.readFileSync(path.join(root,'app.js'),'utf8');
 const opening=app.slice(app.indexOf('async function loadPriceData()'),app.indexOf('function parsePriceCSV'));
 assert.ok(opening.includes('MayoristasDelivery.Loader'));
 assert.doesNotMatch(opening,/fetch\(|MCBAPrices\.load|MCBAMonthly\.load/);
});
