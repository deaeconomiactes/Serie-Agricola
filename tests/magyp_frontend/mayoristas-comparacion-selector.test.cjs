const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
global.crypto=webcrypto;const delivery=require('../../mayoristas-loader.js');
const root=path.resolve(__dirname,'../..'),folder=path.join(root,delivery.BASE);
const fetcher=async url=>{const b=fs.readFileSync(path.join(folder,path.basename(url)));return {ok:true,arrayBuffer:async()=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)}};
test('Tomate Corrientes conserva cinco claves, orden y detalle por fuente',async()=>{
 const loader=new delivery.Loader(fetcher);const {rows}=await loader.load({year:2026,frequency:'mensual',markets:['TODOS']});
 const ctx=vm.createContext({console,document:{addEventListener(){}}});vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx);
 ctx.rows=rows;const result=vm.runInContext(`comparableMarketSelection(rows.filter(r=>getPriceProduct(r)==='Tomate' && r.procedencia==='Corrientes' && r.fecha<='2026-11-06'),{mercado:['Mercado Central de Buenos Aires','Mercado de Corrientes'],especie:['Tomate'],procedencia:['Corrientes'],variedad:['TODOS']},'mensual')`,ctx);
 assert.equal(result.combinations.length,5);assert.equal(new Set(result.combinations.map(c=>c.key)).size,5);
 assert.ok(result.combinations.every((c,i,a)=>i===0||a[i-1].months.length>=c.months.length));assert.equal(result.key,result.combinations[0].key);
 const rendered=[];for(const item of result.combinations){ctx.item=item;const v=vm.runInContext('priceComparisonPresentation(item)',ctx);assert.match(v.main,/Tomate Redondo.*Torito 18 kg/i);assert.match(v.secondary,/Buenos Aires vs Corrientes.*ARS\/kg/);rendered.push(v.secondary);assert.match(v.details.find(x=>x[0]==='Mercado de Corrientes')[1],/Calidad: no informado.*Tamaño: no informado.*Grado: no informado/);assert.ok(v.details.find(x=>x[0]==='Mercado Central de Buenos Aires')[1].includes('registros'));}
 assert.equal(new Set(rendered).size,5);
 ctx.choice=result.combinations[1].key;vm.runInContext('priceComparisonChoice=choice',ctx);const alternative=vm.runInContext(`comparableMarketSelection(rows.filter(r=>getPriceProduct(r)==='Tomate' && r.procedencia==='Corrientes' && r.fecha<='2026-11-06'),{mercado:['Mercado Central de Buenos Aires','Mercado de Corrientes'],especie:['Tomate'],procedencia:['Corrientes'],variedad:['TODOS']},'mensual')`,ctx);assert.equal(alternative.key,ctx.choice);assert.notEqual(alternative.key,result.key);
});

test('ambos selectores comparten búsqueda, teclado y retorno de foco sin cambiar claves',()=>{
 class Node {constructor(id=''){this.id=id;this.hidden=false;this.open=false;this.value='';this.textContent='';this.attrs={};this.children=[];this.events={};this.classList={add(){}};}addEventListener(name,fn){this.events[name]=fn;}setAttribute(k,v){this.attrs[k]=String(v);}removeAttribute(k){delete this.attrs[k];}replaceChildren(...nodes){this.children=[...nodes];}append(...nodes){this.children.push(...nodes);}appendChild(node){this.children.push(node);}focus(){doc.activeElement=this;}showModal(){this.open=true;}close(){this.open=false;}scrollIntoView(){}fire(name,event={}){this.events[name]?.({preventDefault(){},...event});}}
 const ids=['priceIndividualSeriesControl','priceIndividualSeriesChoice','priceSeriesDetail','priceSeriesDetailList','priceSeriesDialog','priceSeriesSearch','priceSeriesList','priceSeriesCount','priceSeriesClose','priceSeriesDialogTitle','priceComparisonControl','priceComparisonTrigger','priceComparisonDetail','priceComparisonDetailList'];const nodes=Object.fromEntries(ids.map(id=>[id,new Node(id)]));
 const doc={activeElement:null,addEventListener(){},createElement(){return new Node()},getElementById(id){return nodes[id]||null;}};
 const ctx=vm.createContext({console,document:doc});vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx);
 const row={mercado:'Mercado Central de Buenos Aires',especie:'Tomate',variedad:'Redondo',procedencia:'Corrientes',envase:'Torito',kg_raw:18,moneda_normalizada:'ARS',calidadMCBA:'Primera',tamanoMCBA:'MEDIANO',gradoMCBA:'P/I',fecha:'2026-04-01',fechaPrecision:'mensual',data_source:'MERCADO_CENTRAL'};
 const other={...row,mercado:'Mercado de Corrientes',calidadMCBA:'',tamanoMCBA:'',gradoMCBA:'',fechaPrecision:'diaria',data_source:'LEGACY'};
 ctx.item={key:'original',label:'referencia',variety:'REDONDO',presentation:'TORITO|18',months:['2026-04'],rows:[row,other]};
 ctx.comparison={...ctx.item,combinations:[ctx.item,{...ctx.item,key:'alternativa',rows:[{...row,calidadMCBA:'Segunda'},other]}]};
 vm.runInContext("updatePriceDashboard=()=>{}; updateIndividualSeriesControl([{key:'individual-a',label:'uno',rows:[item.rows[0]]},{key:'individual-b',label:'dos',rows:[item.rows[0]]}],{key:'individual-a',label:'uno',rows:[item.rows[0]]},'comparable','mensual');updateComparisonSeriesControl(comparison,'')",ctx);
 nodes.priceComparisonTrigger.fire('click');assert.equal(nodes.priceSeriesDialog.open,true);assert.equal(nodes.priceSeriesList.children.length,2);assert.equal(nodes.priceSeriesList.children[0].attrs['aria-selected'],'true');
 nodes.priceSeriesSearch.fire('keydown',{key:'ArrowDown'});nodes.priceSeriesSearch.fire('keydown',{key:'Enter'});assert.equal(vm.runInContext('priceComparisonChoice',ctx),'alternativa');assert.equal(doc.activeElement,nodes.priceComparisonTrigger);
 nodes.priceIndividualSeriesChoice.fire('click');assert.equal(nodes.priceSeriesDialog.open,true);nodes.priceSeriesSearch.value='TOMATE';nodes.priceSeriesSearch.fire('input');assert.equal(nodes.priceSeriesList.children.length,2);nodes.priceSeriesDialog.fire('cancel');assert.equal(doc.activeElement,nodes.priceIndividualSeriesChoice);
});
