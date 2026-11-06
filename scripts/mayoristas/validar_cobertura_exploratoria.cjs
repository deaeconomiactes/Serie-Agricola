/* Validación por año/frecuencia/mercado: no modifica los shards ni sus fuentes. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{webcrypto}=require('node:crypto');
global.crypto=webcrypto;
const root=path.resolve(__dirname,'../..'),delivery=require('../../mayoristas-loader.js'),explore=require('../../mayoristas-explore.js');
const dir=path.join(root,delivery.BASE), cutoff=process.env.MAYORISTAS_AS_OF || new Date().toISOString().slice(0,10);
const fetcher=async url=>{const buf=fs.readFileSync(path.join(dir,path.basename(url)));return {ok:true,arrayBuffer:async()=>buf.buffer.slice(buf.byteOffset,buf.byteOffset+buf.byteLength)}};
const csv=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
const med=arr=>{arr=arr.slice().sort((a,b)=>a-b);let i=Math.floor(arr.length/2);return arr.length%2?arr[i]:(arr[i-1]+arr[i])/2};
(async()=>{
 const index=delivery.validateIndex(JSON.parse(fs.readFileSync(path.join(dir,'index.json'),'utf8'))), matrix=new Map(), products=new Set(), origins=new Set(), failures=[];
 const stats=Object.fromEntries(index.years.map(y=>[y,{products:new Set(),markets:new Set(),months:new Set(),pass:0,noData:0,notComparable:0,comparisonNotComparable:0,fail:0,pairs:0,common:0,monthlyRows:0,future:0}]));
 let peak=0; const yearlyPairs={};
 for(const year of index.years){
  const pairMap=new Map(), st=stats[year];
  for(const frequency of ['diaria','mensual','anual']) for(const market of index.markets){
   const loader=new delivery.Loader(fetcher);await loader.init();let result=await loader.load({year,frequency,markets:[market]});
   const selected=new Map();
   for(const r of result.rows){
    const month=(r.fecha||'').slice(0,7);if(!month)continue;
    const key=JSON.stringify([market,r.data_source,r.especie,year,month,frequency,r.procedencia||'',r.variedad||'',r.fechaPrecision||'']);
    let item=matrix.get(key);if(!item){item={count:0,future:0};matrix.set(key,item)} item.count++;
    if(r.fecha>cutoff){item.future++;if(frequency==='mensual')st.future++;continue;}
    if(frequency!=='mensual')continue;
    st.monthlyRows++;st.products.add(r.especie);products.add(r.especie);origins.add(r.procedencia||'');st.markets.add(market);st.months.add(month);
    const k=JSON.stringify([r.especie,r.procedencia||'']);if(!selected.has(k))selected.set(k,[]);selected.get(k).push(r);
   }
   if(frequency==='mensual') for(const [key,rows] of selected){
    const actual=explore.summarize(rows), reference=new Map();
    for(const r of rows){const p=String(r.fechaPrecision||'').toLowerCase();if((r.moneda_normalizada||r.currency)!=='ARS'||r.conversion_validada===false||!['Alta','Media'].includes(r.confianzaConversion)||!Number.isFinite(r.precioKgEstimado)||r.precioKgEstimado<=0||!['diaria','mensual'].includes(p))continue;
      const month=r.fecha.slice(0,7);if(!reference.has(month))reference.set(month,{sources:new Set(),precisions:new Set(),days:new Map(),values:[],count:0});let g=reference.get(month);g.sources.add(r.data_source||'sin fuente');g.precisions.add(p);g.count++;g.values.push(r.precioKgEstimado);if(!g.days.has(r.fecha))g.days.set(r.fecha,[]);g.days.get(r.fecha).push(r.precioKgEstimado);
    }
    if(actual.length!==reference.size){failures.push({year,market,key,error:'conteo períodos'});st.fail++;}
    if(!pairMap.has(key))pairMap.set(key,new Map());const pair=pairMap.get(key);if(!pair.has(market))pair.set(market,new Map());
    const actualMonths=new Set(actual.map(p=>p.month));
    for(const month of new Set(rows.map(r=>r.fecha.slice(0,7)))) if(!actualMonths.has(month)){st.notComparable++;pair.get(market).set(month,null);}
    for(const p of actual){const ref=reference.get(p.month);let expected=null;if(ref&&ref.sources.size===1&&ref.precisions.size===1) expected=med(ref.precisions.has('diaria')?[...ref.days.values()].map(med):ref.values);
     if(!ref || p.observations!==ref.count || (expected===null?p.value!==null:Math.abs(p.value-expected)>1e-8*Math.max(1,expected))){failures.push({year,market,key,month:p.month,error:'mediana/cobertura'});st.fail++;}else if(expected===null)st.notComparable++;else st.pass++;
     pair.get(market).set(p.month,p.value);
    }
   }
   peak=Math.max(peak,process.memoryUsage().rss);result=null;loader.cache.clear();if(global.gc)global.gc();
   console.log(`${year} ${frequency} ${market}: completado`);
  }
  for(const [key,pair] of pairMap){const a=pair.get(index.markets[0])||new Map(),b=pair.get(index.markets[1])||new Map();const months=new Set([...a.keys(),...b.keys()]);st.pairs++;
   for(const m of months){if(!a.has(m)||!b.has(m)){st.noData++;continue}let x=a.get(m),y=b.get(m);if(x===null||y===null){st.comparisonNotComparable++;continue}if(!(Number.isFinite((y/x-1)*100)&&x>0&&y>0)){st.fail++;failures.push({year,key,month:m,error:'diferencia'});}else st.common++;}
  }
  yearlyPairs[year]=pairMap.size;
 }
 const out=path.join(root,'data/mayoristas/reports');fs.mkdirSync(out,{recursive:true});
 const header=['mercado','fuente','producto','año','mes','frecuencia_vista','procedencia','variedad','granularidad','registros','futuros'];
 const lines=[header.map(csv).join(',')];for(const [key,v] of matrix)lines.push([...JSON.parse(key),v.count,v.future].map(csv).join(','));
 fs.writeFileSync(path.join(out,'COBERTURA_EXPLORATORIA_MATRIZ.csv.gz'),require('node:zlib').gzipSync(Buffer.from(lines.join('\n')+'\n'),{level:9}));
 const raw={cutoff,years:index.years,products:[...products].sort(),origins:[...origins].sort(),markets:index.markets,frequencies:['diaria','mensual','anual'],combinations:matrix.size,peak_rss_bytes:peak,stats:Object.fromEntries(Object.entries(stats).map(([y,s])=>[y,{...s,products:[...s.products].sort(),markets:[...s.markets],months:[...s.months].sort()}])),failures};
 fs.writeFileSync(path.join(out,'COBERTURA_EXPLORATORIA_RESULTADOS.json'),JSON.stringify(raw,null,2)+'\n');
 console.log(JSON.stringify({cutoff,products:products.size,origins:origins.size,matrix:matrix.size,stats:raw.stats,failures:failures.length,peak}));if(failures.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
