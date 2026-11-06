const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');const {createHash,webcrypto}=require('node:crypto');
global.crypto=webcrypto;const delivery=require('../../mayoristas-loader.js');const {readSources}=require('../../scripts/mayoristas/source_rows.cjs');const root=path.resolve(__dirname,'../..');const folder=process.env.MAYORISTAS_DELIVERY_ROOT?path.resolve(process.env.MAYORISTAS_DELIVERY_ROOT):path.join(root,delivery.BASE);const quiet={log(){},warn(){},error(){}};const digest=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const fetcher=()=>async url=>{const body=fs.readFileSync(path.join(folder,path.basename(url)));return {ok:true,arrayBuffer:async()=>body.buffer.slice(body.byteOffset,body.byteOffset+body.byteLength)}};
(async()=>{
 const selected=JSON.parse(process.env.MAYORISTAS_CONTROL);assert.ok(selected);
 const mark = label => {if(process.env.MAYORISTAS_MEMORY_TRACE)console.error('MEM',label,JSON.stringify(process.memoryUsage()));};
 const original=await readSources(root,{selection:selected,sourceOverrides:JSON.parse(process.env.MAYORISTAS_SOURCE_OVERRIDES||'{}')});const ctx=original.context;ctx.console=quiet;ctx.document.getElementById=()=>({value:"TODOS"});
 mark('referencia lista');if(global.gc)global.gc();mark('gc referencia');
 const loader=new delivery.Loader(fetcher());await loader.init();
 const controls=[];
 for(const {market,frequency,year} of [selected]) {
   const selection={year,frequency,markets:[market]};const actual=await loader.load(selection);
   mark('shard cargado');
   const expected=original.views[frequency].filter(r=>r.year===year&&r.mercado===market);
   if(actual.rows.length!==expected.length) throw Error(`${JSON.stringify(selection)} exact row order/content: cantidad distinta ${actual.rows.length} vs ${expected.length}`);
   const eq=require('node:util').isDeepStrictEqual;
   for(let i=0;i<expected.length;i++) if(!eq(actual.rows[i],expected[i])) {
    const a=actual.rows[i], b=expected[i], fields=[...new Set([...Object.keys(a),...Object.keys(b)])].filter(k=>!eq(a[k],b[k]));
    throw Error(`${JSON.stringify(selection)} exact row order/content: fila ${i} no coincide; campos: ${fields.slice(0,12).map(k=>`${k}=${JSON.stringify(a[k])}/${JSON.stringify(b[k])}`).join(', ')}`);
   }
   assert.deepEqual(actual.rows,expected,JSON.stringify(selection)+' exact row order/content');
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
        semaphore:buildMonthlyPriceSemaphoreMatrix(const_equivalence_rows,testFilters)})`,ctx));
   };
   mark('filas verificadas');
   const before=compute(expected);mark('referencia calculada');const after=compute(actual.rows);mark('entrega calculada');
   assert.deepEqual(after,before,JSON.stringify(selection)+' calculations');
   controls.push({...selection,rows:after.rows,average:after.average,minimum:after.minimum,maximum:after.maximum,latest:after.latest,exact_equal:true,sha256:digest(after)});
 }
 assert.equal(controls.length,1);
 if(process.env.MAYORISTAS_EQUIVALENCE_REPORT)fs.writeFileSync(process.env.MAYORISTAS_EQUIVALENCE_REPORT,JSON.stringify({controls,peak_rss_kb:process.resourceUsage().maxRSS},null,2)+'\n');
})().catch(error=>{console.error(error);process.exitCode=1});
