const test=require('node:test'),assert=require('node:assert/strict');
const {describe,shares}=require('../../cantidades-analytics.js');
const row=(especie,peso,origen='A',unidad='TN')=>({especie,peso,origen,unidad});
test('quantity shares use the full selected denominator and merge repeated products',()=>{
 const rows=[row('Papa',20),row('Papa',30,'B'),row('Tomate',25),row('Lechuga',25)];const copy=structuredClone(rows),result=describe(rows);
 assert.equal(result.total,100);assert.equal(result.products[0].name,'Papa');assert.equal(result.products[0].share,50);assert.equal(result.origins[0].share,70);assert.deepEqual(rows,copy);
});
test('Top 5 includes exactly five products and is not normalized over the top ranking',()=>{
 const r=describe(Array.from({length:10},(_,i)=>row(String(i),i+1)));assert.equal(r.top5,(10+9+8+7+6)/55*100);assert.equal(r.products.length,10);
});
test('mixed units and non-positive/invalid quantities cannot create new concentration metrics',()=>{
 for(const rows of [[row('A',1),row('B',1000,'A','KG')],[row('A',0)],[row('A',NaN)],[row('A',-1)]])assert.equal(describe(rows).compatible,false);
});
test('empty selection has no synthetic participation or top product',()=>{
 const r=describe([]);assert.equal(r.total,0);assert.equal(r.top5,null);assert.deepEqual(r.products,[]);
});
test('monthly composition is 100 percent only with observed positive totals; absent months stay gaps',()=>{
 const source=[[25,0,40],[75,0,60]],copy=structuredClone(source);assert.deepEqual(shares(source),[[25,null,40],[75,null,60]]);assert.deepEqual(source,copy);
});
test('invalid composition inputs do not silently become zero or a percentage',()=>{
 assert.deepEqual(shares([[1,-2],[NaN,3]]),[[null,null],[null,null]]);
});
