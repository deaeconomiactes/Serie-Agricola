const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{createHash,webcrypto}=require('node:crypto');
const {inspectInputs,materializeReferences,classifyMonthlyFreshness}=require('../../scripts/mayoristas/validation_sources.cjs');
const hash=value=>createHash('sha256').update(value).digest('hex');
test('recupera exactamente el snapshot CRLF desde un blob Git LF sin aceptar cambios de contenido',()=>{
 const {execFileSync}=require('node:child_process'),root=fs.mkdtempSync(path.join(os.tmpdir(),'mayoristas-crlf-'));
 const git=(...args)=>execFileSync('git',args,{cwd:root,stdio:'pipe'});
 try{
  git('init');git('config','user.name','Test');git('config','user.email','test@example.invalid');
  fs.writeFileSync(path.join(root,'.gitattributes'),'*.csv text eol=lf\n');
  fs.writeFileSync(path.join(root,'fuente.csv'),'nombre,precio\nTomate,10\n');git('add','.');git('commit','-m','snapshot');
  fs.writeFileSync(path.join(root,'fuente.csv'),'nombre,precio\nTomate,20\n');
  const expected=Buffer.from('nombre,precio\r\nTomate,10\r\n'),index={inputs:[{path:'fuente.csv',sha256:hash(expected)}]};
  const result=materializeReferences(root,index,root);assert.deepEqual(fs.readFileSync(result.overrides['fuente.csv']),expected);
  assert.equal(fs.readFileSync(path.join(root,'fuente.csv'),'utf8'),'nombre,precio\nTomate,20\n');
  index.inputs[0].sha256=hash('nombre,precio\r\nTomate,11\r\n');assert.throws(()=>materializeReferences(root,index,root),/SOURCE_SNAPSHOT_UNAVAILABLE/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('distingue una fuente cambiada de la fotografía registrada sin alterar ninguna',()=>{const root=fs.mkdtempSync(path.join(os.tmpdir(),'mayoristas-source-state-'));try{fs.writeFileSync(path.join(root,'fuente.csv'),'publicación nueva');const index={inputs:[{path:'fuente.csv',sha256:hash('publicación anterior')}]};const [result]=inspectInputs(root,index);assert.equal(result.state,'SOURCE_CHANGED');assert.equal(result.indexed,hash('publicación anterior'));assert.equal(fs.readFileSync(path.join(root,'fuente.csv'),'utf8'),'publicación nueva');index.inputs[0].sha256=hash('publicación nueva');assert.equal(inspectInputs(root,index)[0].state,'CURRENT');}finally{fs.rmSync(root,{recursive:true,force:true});}});
test('un CSV mensual alterado no pasa la integridad del marcador',async()=>{global.crypto=webcrypto;global.MCBAPrices=require('../../mcba-prices.js');const m=require('../../mcba-monthly.js'),root=path.resolve(__dirname,'../..');const text=fs.readFileSync(path.join(root,m.BASE,m.FILE),'utf8'),marker=JSON.parse(fs.readFileSync(path.join(root,m.BASE,'_SUCCESS.json'),'utf8'));await assert.rejects(m.verify(text+'\n',marker),/incompleta/i);});
test('no sustituye una fotografía ausente por la fuente actual',()=>{const root=fs.mkdtempSync(path.join(os.tmpdir(),'mayoristas-no-history-'));try{fs.writeFileSync(path.join(root,'fuente.csv'),'nueva');const index={inputs:[{path:'fuente.csv',sha256:hash('anterior')}]};assert.throws(()=>materializeReferences(root,index,root),/SOURCE_SNAPSHOT_UNAVAILABLE/);}finally{fs.rmSync(root,{recursive:true,force:true});}});
test('identifica nueva cobertura, igualdad o retroceso sin inferir valores',()=>{const row=date=>[{last_observation_date:date}];assert.equal(classifyMonthlyFreshness(row('2026-11-04'),row('2026-11-05')).state,'SOURCE_NEWER');assert.equal(classifyMonthlyFreshness(row('2026-11-04'),row('2026-11-04')).state,'SOURCE_CHANGED_SAME_COVERAGE');assert.equal(classifyMonthlyFreshness(row('2026-11-05'),row('2026-11-04')).state,'SOURCE_OLDER');});
