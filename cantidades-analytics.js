/* Read-only descriptive shares. No acquisition, conversion or modification of source rows. */
(function(root){
    'use strict';
    function describe(rows){
        const compatible=rows.every(r=>r.unidad==='TN'&&Number.isFinite(r.peso)&&r.peso>0);
        if(!compatible)return {compatible:false,total:null,products:[],origins:[]};
        const total=rows.reduce((sum,r)=>sum+r.peso,0);
        const ranking=key=>{
            const groups=new Map();for(const row of rows)groups.set(row[key],(groups.get(row[key])||0)+row.peso);
            return [...groups].map(([name,value])=>({name,value,share:total?value/total*100:null})).sort((a,b)=>b.value-a.value);
        };
        const products=ranking('especie'),origins=ranking('origen');
        return {compatible:true,total,products,origins,top5:total?products.slice(0,5).reduce((s,r)=>s+r.value,0)/total*100:null};
    }
    function shares(series){
        return series.map(values=>values.map((value,index)=>{
            const period=series.map(row=>row[index]);
            if(period.some(v=>!Number.isFinite(v)||v<0))return null;
            const total=period.reduce((s,v)=>s+v,0);return total?value/total*100:null;
        }));
    }
    const api={describe,shares};if(typeof module==='object'&&module.exports)module.exports=api;else root.QuantityAnalytics=api;
})(typeof window==='object'?window:globalThis);
