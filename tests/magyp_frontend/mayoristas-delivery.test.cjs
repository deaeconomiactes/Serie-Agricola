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
// CI may validate a freshly generated candidate without changing tracked shards.
const folder=process.env.MAYORISTAS_DELIVERY_ROOT ? path.resolve(process.env.MAYORISTAS_DELIVERY_ROOT) : path.join(root,delivery.BASE);
const index=JSON.parse(fs.readFileSync(path.join(folder,'index.json'),'utf8'));
const quiet={log(){},warn(){},error(){}};
const digest=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
function fetcher(calls=[],modify=bytes=>bytes) {
 return async url=>{calls.push(url);const body=modify(fs.readFileSync(path.join(folder,path.basename(url))),url);return {ok:true,arrayBuffer:async()=>body.buffer.slice(body.byteOffset,body.byteOffset+body.byteLength)};};
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
 const loader=new delivery.Loader(async url=>{const body=fs.readFileSync(path.join(folder,path.basename(url)));const bytes=broken&&url.endsWith('.gz')?Buffer.concat([body,Buffer.from('x')]):body;return {ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};});
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
 const cases = [[index.markets[0],'diaria',[2026]],[index.markets[0],'mensual',[2024,2025,2026]],[index.markets[1],'mensual',[2025,2026]],[index.markets[1],'diaria',[2025,2026]],[index.markets[0],'anual',[2024,2025,2026]]].flatMap(([market,frequency,years])=>years.map(year=>({market,frequency,year})));
 const selectedCases = process.env.MAYORISTAS_CANDIDATE_SMOKE==='1' ? cases.filter(c=>c.market===index.markets[0] && c.frequency==='mensual' && c.year===2026) : cases;
 {
  const {spawnSync}=require('node:child_process');const os=require('node:os');const folder=fs.mkdtempSync(path.join(os.tmpdir(),'mayoristas-equivalence-'));const controls=[], failures=[];
  try {
   const reference=process.env.MAYORISTAS_DELIVERY_ROOT ? {states:[],overrides:{}} : require('../../scripts/mayoristas/validation_sources.cjs').materializeReferences(root,index,folder);
   for(const source of reference.states.filter(item=>item.state==='SOURCE_CHANGED'))console.log(`SOURCE_CHANGED: ${source.path} · el shard conserva la fuente identificada por su hash`);
   for(let i=0;i<selectedCases.length;i++) {
    const report=path.join(folder,`${i}.json`);
    const childEnv={...process.env,MAYORISTAS_CONTROL:JSON.stringify(selectedCases[i]),MAYORISTAS_EQUIVALENCE_REPORT:report,MAYORISTAS_SOURCE_OVERRIDES:JSON.stringify(reference.overrides)};delete childEnv.NODE_TEST_CONTEXT;
    const child=spawnSync(process.execPath,['--expose-gc','--max-old-space-size=1000',path.join(__dirname,'mayoristas-equivalence-control.cjs')],{cwd:root,encoding:'utf8',maxBuffer:4*1024*1024,env:childEnv});
    if(child.status!==0 || !fs.existsSync(report)) { failures.push({selection:selectedCases[i],error:(child.stderr||child.stdout||'Sin informe').slice(0,3000)});console.log(`Control ${i+1}/${selectedCases.length}: ${JSON.stringify(selectedCases[i])} FAIL`);continue; }
    const result=JSON.parse(fs.readFileSync(report,'utf8'));assert.equal(result.controls.length,1);controls.push({...result.controls[0],peak_rss_kb:result.peak_rss_kb});
    console.log(`Control ${i+1}/${selectedCases.length}: ${JSON.stringify(selectedCases[i])} PASS · RSS máximo ${result.peak_rss_kb} KiB`);
   }
   assert.equal(controls.length+failures.length,process.env.MAYORISTAS_CANDIDATE_SMOKE==='1'?1:11);
   if(process.env.MAYORISTAS_EQUIVALENCE_REPORT)fs.writeFileSync(process.env.MAYORISTAS_EQUIVALENCE_REPORT,JSON.stringify({controls,failures},null,2)+'\n');
   assert.deepEqual(failures,[],'Controles económicos fallidos');
  } finally {fs.rmSync(folder,{recursive:true,force:true});}
  return;
 }

});
test('source freshness is reported independently and the current monthly publication has valid integrity',async()=>{
 const sourceCheck=require('../../scripts/mayoristas/validation_sources.cjs'),states=sourceCheck.inspectInputs(root,index);
 global.MCBAPrices=require('../../mcba-prices.js');
 const monthly=require('../../mcba-monthly.js'),name=monthly.BASE+monthly.FILE,markerName=monthly.BASE+'_SUCCESS.json';
 const read=name=>fs.readFileSync(path.join(root,name),'utf8');
 const rows=await monthly.verify(read(name),JSON.parse(read(markerName)));assert.ok(rows.length);
 const changed=states.filter(s=>s.state==='SOURCE_CHANGED');
 if(!changed.length){console.log('CURRENT: fuentes y shard coinciden');return;}
 const monthlyChanged=changed.some(s=>s.path===name||s.path===markerName);
 if(monthlyChanged){
  const os=require('node:os'),folder=fs.mkdtempSync(path.join(os.tmpdir(),'mayoristas-freshness-'));
  try{const reference=sourceCheck.materializeReferences(root,index,folder),oldRead=name=>fs.readFileSync(reference.overrides[name]||path.join(root,name),'utf8');
   const prior=await monthly.verify(oldRead(name),JSON.parse(oldRead(markerName)));const status=sourceCheck.classifyMonthlyFreshness(prior,rows);
   console.log(`${status.state}: cobertura MCBA ${status.indexedDate} → ${status.currentDate}; ambas publicaciones coinciden con sus marcadores`);
  }finally{fs.rmSync(folder,{recursive:true,force:true});}
 }
 console.log(`SOURCE_CHANGED: ${changed.map(s=>s.path).join(', ')}`);
});
test('scope: wholesale opening cannot fetch integrated or upstream full source publications',()=>{
 const app=fs.readFileSync(path.join(root,'app.js'),'utf8');
 const opening=app.slice(app.indexOf('async function loadPriceData()'),app.indexOf('function parsePriceCSV'));
 assert.ok(opening.includes('MayoristasDelivery.Loader'));
 assert.doesNotMatch(opening,/fetch\(|MCBAPrices\.load|MCBAMonthly\.load/);
});
