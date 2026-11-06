/* Resolve the exact source snapshot recorded in a delivery index, without modifying the worktree. */
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto'),{execFileSync}=require('node:child_process');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function inspectInputs(root,index){return index.inputs.map(item=>{const file=path.resolve(root,item.path),rel=path.relative(root,file);if(rel.startsWith('..')||path.isAbsolute(rel))throw Error('Ruta de fuente fuera del repositorio');const current=hash(fs.readFileSync(file));return {path:item.path,indexed:item.sha256,current,state:current===item.sha256?'CURRENT':'SOURCE_CHANGED'};});}
function materializeReferences(root,index,folder){
 const states=inspectInputs(root,index),overrides={};
 for(const state of states.filter(s=>s.state==='SOURCE_CHANGED')){
  let revisions;try{revisions=execFileSync('git',['log','--format=%H','--',state.path],{cwd:root,encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim().split(/\r?\n/).filter(Boolean);}catch{throw Error(`SOURCE_SNAPSHOT_UNAVAILABLE: no se puede leer historial de ${state.path}`);}
  let contents=null;for(const rev of revisions){let bytes;try{bytes=execFileSync('git',['show',`${rev}:${state.path}`],{cwd:root,maxBuffer:128*1024*1024,stdio:['ignore','pipe','pipe']});}catch{continue;}if(hash(bytes)===state.indexed){contents=bytes;break;}}
  if(!contents)throw Error(`SOURCE_SNAPSHOT_UNAVAILABLE: no se encontró ${state.path} con SHA-256 ${state.indexed}`);
  const target=path.join(folder,`source-${Object.keys(overrides).length}`);fs.writeFileSync(target,contents);overrides[state.path]=target;
 }
 return {states,overrides};
}
function classifyMonthlyFreshness(indexed,current){
 const latest=rows=>rows.reduce((date,row)=>row.last_observation_date>date?row.last_observation_date:date,'');
 const indexedDate=latest(indexed),currentDate=latest(current);
 return {state:currentDate>indexedDate?'SOURCE_NEWER':currentDate===indexedDate?'SOURCE_CHANGED_SAME_COVERAGE':'SOURCE_OLDER',indexedDate,currentDate};
}
module.exports={inspectInputs,materializeReferences,classifyMonthlyFreshness};
