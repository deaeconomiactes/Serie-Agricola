/* Delivery only. Economic adapters and source routing run in the reproducible build. */
(function(root) {
    'use strict';
    const BASE='data/mayoristas/dashboard/';
    const VERSION='mayoristas-shards-v1';
    const SOURCES=['LEGACY','MAGYP','MERCADO_CENTRAL'];
    const FREQUENCIES=['diaria','mensual','anual'];
    const fail=message=>{throw Error('PIPELINE/UI DATA ERROR: '+message);};
    const hash=async bytes=>[...new Uint8Array(await root.crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
    function validateIndex(index) {
        if(!index || index.schema_version!==VERSION || index.format!=='json+gzip' || !Array.isArray(index.fragments) || !index.fragments.length ||
            !Array.isArray(index.years) || !index.years.length || !Array.isArray(index.markets) || !index.metadata?.magypPriceInfo) fail('índice incompatible');
        const paths=new Set();const keys=new Set();
        for(const f of index.fragments) {
            const key=[f.market,f.frequency,f.year,f.source].join('|');
            if(f.schema_version!==VERSION || !SOURCES.includes(f.source) || !FREQUENCIES.includes(f.frequency) ||
                !Number.isInteger(f.year) || !index.years.includes(f.year) || !index.markets.includes(f.market) ||
                !Number.isInteger(f.row_count) || f.row_count<1 || !Number.isInteger(f.bytes) || f.bytes<1 || f.bytes>12000000 ||
                !Number.isInteger(f.expanded_bytes) || f.expanded_bytes<1 || f.expanded_bytes>120000000 ||
                !/^[a-f0-9]{64}$/.test(f.sha256) || !/^[a-z0-9_-]+\.json\.gz$/.test(f.path) || !f.path.includes(f.sha256.slice(0,16)) ||
                !Array.isArray(f.fields) || !['fecha','year','mercado','data_source','precioObservado','_runtime_order'].every(k=>f.fields.includes(k)) ||
                !Array.isArray(f.currency) || !f.currency.length || !Array.isArray(f.unit) || !f.unit.length ||
                paths.has(f.path) || keys.has(key)) fail('descriptor inválido');
            paths.add(f.path);keys.add(key);
        }
        for(const frequency of FREQUENCIES) if(index.fragments.filter(f=>f.frequency===frequency).reduce((n,f)=>n+f.row_count,0)!==index.row_counts?.[frequency]) fail('conteo de índice');
        return index;
    }
    function validateRows(rows,f) {
        if(!Array.isArray(rows) || rows.length!==f.row_count) fail('conteo de fragmento');
        const orders=new Set();const dates=[];
        for(const r of rows) {
            if(!r || r.year!==f.year || r.mercado!==f.market || r.data_source!==f.source ||
                !Number.isSafeInteger(r._runtime_order) || r._runtime_order<0 || orders.has(r._runtime_order) ||
                typeof r.precioObservado!=='number' || !Number.isFinite(r.precioObservado) || r.precioObservado<=0 ||
                Object.keys(r).some(k=>!f.fields.includes(k)) ||
                !f.currency.includes(r.currency || 'Sin identificar') || !f.unit.includes(r.unidadPrecioObservado || 'Sin identificar')) fail('observación incompatible');
            if(r.fecha) {
                if(!/^\d{4}-\d{2}-\d{2}$/.test(r.fecha) || r.fecha.slice(0,4)!==String(f.year) || !Number.isFinite(Date.parse(r.fecha+'T00:00:00Z')) || new Date(r.fecha+'T00:00:00Z').toISOString().slice(0,10)!==r.fecha) fail('fecha inválida');
                dates.push(r.fecha);
            }
            orders.add(r._runtime_order);
        }
        dates.sort();if((dates[0]||null)!==f.first_observation || (dates.at(-1)||null)!==f.last_observation) fail('cobertura inconsistente');
        return rows;
    }
    function expandDimensions(row) {
        if (row._normalization_schema !== 'v1') return row;
        const originalCurrency = row.moneda_original ?? String(row.currency || '').trim();
        const currencyKey = String(row.currency || originalCurrency).toUpperCase();
        const currency = ['ARS','USD','EUR','BRL','PYG','UYU','CLP','BOB'].includes(currencyKey) ? currencyKey : 'UNKNOWN';
        const unit = row.unidadPrecioObservado === '$/kg' ? 'kg' : row.unidadPrecioObservado === '$/bulto' ? 'bulto' : 'UNKNOWN';
        const weight = Number(row.kgBulto); const kg = Number.isFinite(weight) && weight > 0 ? weight : null;
        const declared = /\bX\s*(\d+(?:[.,]\d+)?)\s*KG\b/i.exec(row.envase || '');
        const validated = unit === 'kg' || Boolean(unit === 'bulto' && kg && declared && Number(declared[1].replace(',','.')) === kg && !/\bMAZOS?\b/i.test(row.envase || ''));
        return {...row, producto_raw:row.producto_raw ?? row.product_raw ?? row.especie ?? '',
            variedad_raw:row.variedad_raw ?? row.variety_raw ?? row.variedad ?? '',
            procedencia_raw:row.procedencia_raw ?? row.origin_raw ?? row.procedencia ?? '',
            mercado_raw:row.mercado_raw ?? row.mercado ?? '', envase_raw:row.envase_raw ?? row.package_raw ?? row.envase ?? '',
            unidad_raw:row.unidad_raw ?? row.price_unit ?? row.unidadPrecioObservado ?? '',
            tamanio_raw:row.tamanio_raw ?? row.size_raw ?? row.tamanoMCBA ?? '', calidad_raw:row.calidad_raw ?? row.quality_raw ?? row.calidadMCBA ?? '',
            grado_raw:row.grado_raw ?? row.grade_raw ?? row.gradoMCBA ?? '',
            producto_normalizado:row.especie, variedad_normalizada:row.variedad, procedencia_normalizada:row.procedencia,
            mercado_normalizado:row.mercado, envase_normalizado:row.envase, tamanio_normalizado:row.tamanoMCBA || '',
            calidad_normalizada:row.calidadMCBA || '', grado_normalizado:row.gradoMCBA || '',
            unidad_normalizada:unit, moneda_original:originalCurrency, moneda_normalizada:currency,
            factor_conversion:unit === 'kg' ? 1 : unit === 'bulto' && kg ? 1/kg : null,
            peso_utilizado:kg, conversion_validada:validated, fuente_original:row.fuente_original ?? row.fuente ?? ''};
    }
    class Loader {
        constructor(fetcher=root.fetch?.bind(root)) {this.fetcher=fetcher;this.cache=new Map();this.request=0;this.metrics={bytes:0,requests:[]};}
        async response(path) {
            const response=await this.fetcher(BASE+path,{cache:'no-cache'});
            if(!response.ok)throw Error(`No se pudo cargar Mayoristas (HTTP ${response.status})`);
            const bytes=await response.arrayBuffer();this.metrics.bytes+=bytes.byteLength;this.metrics.requests.push({path,bytes:bytes.byteLength});return bytes;
        }
        async init() {
            if(!this.index) {
                const buffer=await this.response('index.json');
                try {this.index=validateIndex(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buffer)));}
                catch(error) {if(error.message.startsWith('PIPELINE/UI DATA ERROR'))throw error;fail('índice malformado');}
            }
            return this.index;
        }
        descriptors({year='TODOS',markets=['TODOS'],frequency='mensual'}) {
            return this.index.fragments.filter(f=>f.frequency===frequency && (year==='TODOS'||f.year===Number(year)) &&
                (!markets.length||markets.includes('TODOS')||markets.includes(f.market)));
        }
        async shard(f) {
            if(!this.cache.has(f.sha256)) {
                const promise=(async()=>{
                    const buffer=await this.response(f.path);
                    if(buffer.byteLength!==f.bytes || await hash(buffer)!==f.sha256) fail('hash/tamaño inválido');
                    try {
                    const reader=new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
                    const chunks=[];let size=0;
                    while(true) {const {done,value}=await reader.read();if(done)break;size+=value.length;
                        if(size>f.expanded_bytes){await reader.cancel();fail('tamaño expandido inválido');}chunks.push(value);}
                    if(size!==f.expanded_bytes)fail('fragmento incompleto');
                    const text=new TextDecoder('utf-8',{fatal:true}).decode(await new Blob(chunks).arrayBuffer());
                    return validateRows(JSON.parse(text),f);
                    } catch(error) {if(error.message.startsWith('PIPELINE/UI DATA ERROR'))throw error;fail('fragmento comprimido o JSON inválido');}
                })().catch(error=>{this.cache.delete(f.sha256);throw error;});
                this.cache.set(f.sha256,promise);
            }
            return this.cache.get(f.sha256);
        }
        async load(selection) {
            const request=++this.request;await this.init();
            const descriptors=this.descriptors(selection);const chunks=[];
            // Bound concurrency even for an explicit "Todos los años" selection.
            for(let i=0;i<descriptors.length;i+=3) {
                chunks.push(...await Promise.all(descriptors.slice(i,i+3).map(f=>this.shard(f))));
                if(request!==this.request)return null;
            }
            if(request!==this.request)return null;
            const rows=chunks.flat().sort((a,b)=>a._runtime_order-b._runtime_order);
            if(new Set(rows.map(r=>r._runtime_order)).size!==rows.length)fail('filas duplicadas entre fragmentos');
            return {rows:rows.map(({_runtime_order,...row})=>expandDimensions(row)),metadata:this.index.metadata};
        }
    }
    const api={BASE,VERSION,Loader,validateIndex,validateRows,hash};
    if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MayoristasDelivery=api;
})(typeof globalThis!=='undefined'?globalThis:this);
