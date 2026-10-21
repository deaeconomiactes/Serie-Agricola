/* Prepared official history only. No source API is queried by the dashboard. */
const CommodityHistory = (() => {
    'use strict';
    const ROOT = 'data/magyp/dashboard/commodities/history/';
    const VERSION = 'magyp-history-v1';
    const families = new Set(['internal', 'board', 'fas', 'fob', 'futures']);
    const cache = new Map();
    const dailyCache = [];
    let indexPromise;
    async function index() {
        if (!indexPromise) indexPromise = fetch(`${ROOT}index.json`).then(response => {
            if (!response.ok) throw new Error('Histórico oficial no disponible');
            return response.json();
        }).then(value => {
            if (value.schema_version !== VERSION || !value.families || Object.keys(value.families).some(key => !families.has(key))) throw new Error('Índice histórico incompatible');
            return value;
        }).catch(error => { indexPromise = null; throw error; });
        return indexPromise;
    }
    async function read(family, descriptor) {
        if (!families.has(family) || !descriptor || !/^[a-z0-9.-]+-[a-f0-9]{16}\.gz$/.test(descriptor.path)
            || !/^[a-f0-9]{64}$/.test(descriptor.sha256) || descriptor.bytes > 5000000 || descriptor.decoded_bytes > 45000000) throw new Error('Archivo histórico fuera de contrato');
        const response = await fetch(`${ROOT}${family}/${descriptor.path}`);
        if (!response.ok) throw new Error('No se pudo cargar el histórico oficial');
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength !== descriptor.bytes) throw new Error('Histórico truncado');
        const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
        if (hash !== descriptor.sha256) throw new Error('Hash histórico inválido');
        const text = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
        if (new TextEncoder().encode(text).length !== descriptor.decoded_bytes) throw new Error('Tamaño histórico inválido');
        return text;
    }
    async function metadata(family) {
        const catalog = await index();
        const entry = catalog.families[family];
        if (!entry || entry.schema_version !== VERSION || entry.family !== family) throw new Error('Familia histórica no disponible');
        return entry;
    }
    async function registry(family, entry) {
        const key = `${family}/${entry.registry.sha256}`;
        if (!cache.has(key)) cache.set(key, read(family, entry.registry).then(JSON.parse));
        try {
            const value = await cache.get(key);
            if (value.schema_version !== VERSION || value.family !== family || !value.series || !value.captures) throw new Error('Diccionario histórico incompatible');
            return value;
        } catch (error) { cache.delete(key); throw error; }
    }
    function expand(rows, dictionary, family, frequency) {
        const types = {internal: 'Precio interno mensual', board: 'Pizarra provisional', fas: 'FAS teórico', fob: 'FOB oficial', futures: 'Futuro / histórico publicado'};
        const ids = new Set();
        return rows.map(row => {
            const series = dictionary.series[row.series_key];
            const capture = dictionary.captures[row.capture_key];
            if (!series || !capture || !/^[a-f0-9]{64}$/.test(series.series_id) || series.series_id.slice(0,16) !== row.series_key
                || !/^[a-f0-9]{64}$/.test(capture.sha256) || !(family === 'futures' ? ['Futuro / histórico publicado','Futuro / cierre'].includes(series.tipo_precio) : series.tipo_precio.startsWith(types[family]))
                || !series.moneda || !series.unidad || row.value_status !== 'positive' || !/^\d+(?:\.\d+)?$/.test(row.price) || !(Number(row.price) > 0)
                || !/^\d{4}-\d{2}-\d{2}$/.test(row.fecha) || !Number.isFinite(Date.parse(row.fecha))
                || new Date(row.fecha).toISOString().slice(0,10) !== row.fecha) throw new Error('Observación histórica inválida');
            const url = new URL(capture.source_url);
            if (url.protocol !== 'https:' || !['www.magyp.gob.ar','magyp.gob.ar','dinem.magyp.gob.ar','infra.datos.gob.ar'].includes(url.hostname) || url.username || url.password) throw new Error('Origen histórico inválido');
            const id = `${series.series_id}/${frequency === 'mensual' ? row.fecha.slice(0,7) : row.fecha}`;
            if (ids.has(id)) throw new Error('Observación histórica duplicada');
            ids.add(id);
            const inputs = String(row.aggregation_captures || row.capture_key).split('|');
            if (inputs.some(key => !Object.hasOwn(dictionary.captures, key))) throw new Error('Agregación sin trazabilidad');
            const change = row.variacion_mensual_pct === '' ? null : Number(row.variacion_mensual_pct);
            // Mismos umbrales del bundle corriente references.state().
            const state = change === null || !Number.isFinite(change) ? 'Sin dato' : Math.abs(change) > 50 ? 'Revisar' : change < -5 ? 'Baja' : change <= 5 ? 'Estable' : change <= 20 ? 'Suba moderada' : 'Suba fuerte';
            return {...series, ...row, estado:state, fecha:row.fecha, periodo_ym:row.fecha.slice(0,7),
                fuente:'MAGyP', frecuencia:frequency, precio_mediana:row.price,
                raw_sha256:capture.sha256, capture_id:capture.capture_id,
                updated_at_utc:capture.captured_at_utc, source_url:capture.source_url,
                schema_version:VERSION, observation_id:id,
                ...(frequency === 'diaria' ? {variacion_mensual_pct:undefined,variacion_interanual_pct:undefined} : {}),
                coverage_note:family === 'internal' ? 'Valor mensual publicado por MAGyP' :
                    family === 'fob' ? 'Serie SSPM publicada; índice calendario, no fecha de publicación MAGyP confirmada. Mensual: mediana de valores publicados.' :
                    'Mensual: mediana de días observados, sin interpolación. Ver flags de calidad.'};
        });
    }
    async function load(family, frequency, year, parseCSV) {
        const entry = await metadata(family);
        const descriptor = frequency === 'mensual' ? entry.monthly : entry.daily[year];
        if (!descriptor) return [];
        const key = `${family}/${descriptor.sha256}`;
        if (frequency === 'diaria') {
            const previous = dailyCache.indexOf(key);
            if (previous >= 0) dailyCache.splice(previous,1);
            dailyCache.push(key);
            while (dailyCache.length > 4) cache.delete(dailyCache.shift());
        }
        if (!cache.has(key)) cache.set(key, (async () => {
            const [text, dict] = await Promise.all([read(family, descriptor), registry(family, entry)]);
            const rows = parseCSV(text);
            if (rows.length !== descriptor.rows || rows.some(row => Object.keys(row).join('|') !== entry.columns.join('|'))) throw new Error('Schema/conteo histórico incompatible');
            return expand(rows, dict, family, frequency);
        })());
        try { return await cache.get(key); } catch (error) { cache.delete(key); throw error; }
    }
    const monthKey = row => `${row.series_id}/${row.periodo_ym || row.fecha.slice(0,7)}`;
    const dayKey = row => `${row.series_id}/${row.fecha}`;
    function moveDay(day,delta) {
        const value=new Date(`${day}T00:00:00Z`);value.setUTCDate(value.getUTCDate()+delta);
        return value.toISOString().slice(0,10);
    }
    function flags(row) {
        const values = Array.isArray(row.quality_flags) ? row.quality_flags : String(row.quality_flags || '').split('|').filter(Boolean);
        if (row.product_code === 'GI' && row.tipo_precio.startsWith('FAS teórico') && !values.some(value => value.startsWith('sunflower_formula_'))) {
            return [...values, row.fecha < '2019-02-14' ? 'sunflower_formula_pre_2019_02_14' : 'sunflower_formula_from_2019_02_14'];
        }
        return values;
    }
    function method(row) { return flags(row).filter(value => value.startsWith('sunflower_formula_')).sort().join('|'); }
    function shift(period, months) {
        const [year,month] = period.split('-').map(Number);
        const total = year*12 + month-1 + months;
        return `${Math.floor(total/12)}-${String(total%12+1).padStart(2,'0')}`;
    }
    function decimalValues(values) {
        if (values.some(value => !/^\d+(?:\.\d+)?$/.test(String(value)))) throw new Error('Precio agregado no decimal');
        const scale = Math.max(...values.map(value => (String(value).split('.')[1] || '').length));
        return {scale, values:values.map(value => {
            const [integer,fraction=''] = String(value).split('.');
            return BigInt(integer + fraction.padEnd(scale,'0'));
        })};
    }
    function decimalString(value, scale) {
        const negative = value < 0n;const raw = (negative ? -value : value).toString().padStart(scale+1,'0');
        const fraction = scale ? raw.slice(-scale).replace(/0+$/,'') : '';
        return `${negative ? '-' : ''}${scale ? raw.slice(0,-scale) : raw}${fraction ? '.'+fraction : ''}`;
    }
    function percentage(value, prior) {
        if (!prior) return {value:'',state:'Sin dato'};
        const pair = decimalValues([value,prior]).values;
        if (pair[1] <= 0n) return {value:'',state:'Sin dato'};
        const numerator = (pair[0]-pair[1])*100n, denominator = pair[1];
        const absolute = numerator < 0n ? -numerator : numerator;
        const state = absolute > 50n*denominator ? 'Revisar' : numerator < -5n*denominator ? 'Baja' : numerator <= 5n*denominator ? 'Estable' : numerator <= 20n*denominator ? 'Suba moderada' : 'Suba fuerte';
        return {value:decimalString(numerator*10n**12n/denominator,12),state};
    }
    function aggregate(part) {
        part.sort((a,b) => a.fecha.localeCompare(b.fecha));
        const last=part.at(-1), prices=decimalValues(part.map(row => row.precio_mediana ?? row.price));
        prices.values.sort((a,b) => a < b ? -1 : a > b ? 1 : 0);
        const count=prices.values.length, middle=Math.floor(count/2);
        const median=count%2 ? decimalString(prices.values[middle],prices.scale) : decimalString((prices.values[middle-1]+prices.values[middle])*5n,prices.scale+1);
        return {...last,row_kind:'mensual',frecuencia:'mensual',periodo_ym:last.fecha.slice(0,7),price:median,precio_mediana:median,
            operaciones:count,precio_min:decimalString(prices.values[0],prices.scale),precio_max:decimalString(prices.values.at(-1),prices.scale),
            precio_promedio:decimalString(prices.values.reduce((sum,value)=>sum+value,0n)*10n**28n/BigInt(count),prices.scale+28),
            updated_at_utc:part.reduce((stamp,row)=>row.updated_at_utc>stamp?row.updated_at_utc:stamp,''),
            quality_flags:[...new Set(part.flatMap(flags))].sort().join('|'),
            coverage_note:'Mediana de observaciones diarias oficiales de la misma serie; sin interpolación.',
            aggregation_captures:[...new Set(part.map(row=>row.capture_id))].sort().join('|'),
            aggregation_inputs:part.map(row=>({date:row.fecha,capture_id:row.capture_id,raw_sha256:row.raw_sha256,source_url:row.source_url,source_locator:row.source_locator || row.observation_id}))};
    }
    function merge(current, monthly, daily, observations = [], coverage = {}, historicalInputs = daily) {
        const revisedDays = new Set([...current.diario,...observations].map(dayKey));
        const result = {...current,diario:[...daily.filter(row=>!revisedDays.has(dayKey(row))),...current.diario]};
        const combined = new Map(historicalInputs.map(row=>[dayKey(row),row]));
        current.diario.forEach(row=>combined.set(dayKey(row),row));
        observations.filter(row=>row.frecuencia !== 'mensual').forEach(row=>{
            if(row.value_status === 'positive') combined.set(dayKey(row),{...row,precio_mediana:row.price});
            else combined.delete(dayKey(row));
        });
        const revised=[...current.diario,...observations.filter(row=>row.frecuencia!=='mensual')];
        const dailyTargets=new Set(revised.map(dayKey));
        revised.forEach(row=>{
            for(const days of [7,30]) dailyTargets.add(`${row.series_id}/${moveDay(row.fecha,days)}`);
        });
        result.diario=result.diario.map(row=>{
            if(!dailyTargets.has(dayKey(row)))return row;
            const updated={...row};
            for(const days of [7,30]) {
                const prior=combined.get(`${row.series_id}/${moveDay(row.fecha,-days)}`);
                updated[`variacion_${days}d_pct`]=prior && method(row)===method(prior) ?
                    percentage(row.precio_mediana ?? row.price,prior.precio_mediana ?? prior.price).value : '';
            }
            return updated;
        });
        const merged = new Map(monthly.map(row=>[monthKey(row),row]));
        const affected = new Set(observations.map(monthKey));
        current.mensual.forEach(row=>{
            const key=monthKey(row);
            if (!merged.has(key)) merged.set(key,row);
            affected.add(key);
        });
        const publishedMonths = new Set(observations.filter(row=>row.frecuencia==='mensual').map(monthKey));
        const currentMonthly = new Map(current.mensual.map(row=>[monthKey(row),row]));
        const groups = new Map();
        combined.forEach(row=>{
            const key=monthKey(row);
            if (!affected.has(key)) return;
            if (!groups.has(key)) groups.set(key,[]);
            groups.get(key).push(row);
        });
        for (const key of affected) {
            if (publishedMonths.has(key)) {
                if (currentMonthly.has(key)) merged.set(key,currentMonthly.get(key));else merged.delete(key);
            } else if (groups.has(key)) merged.set(key,aggregate(groups.get(key)));
            else if (historicalInputs.length || !merged.has(key)) merged.delete(key);
        }
        const targets=new Set(affected);
        for (const key of affected) {
            const series=key.slice(0,key.lastIndexOf('/')), period=key.slice(key.lastIndexOf('/')+1);
            targets.add(`${series}/${shift(period,1)}`);targets.add(`${series}/${shift(period,12)}`);
        }
        for (const key of targets) {
            const row=merged.get(key);if(!row)continue;
            const lookup=months=>merged.get(`${row.series_id}/${shift(row.periodo_ym,-months)}`);
            const prior=lookup(1),year=lookup(12);
            const short=prior && method(row)===method(prior) ? percentage(row.precio_mediana,prior.precio_mediana) : {value:'',state:'Sin dato'};
            const long=year && method(row)===method(year) ? percentage(row.precio_mediana,year.precio_mediana).value : '';
            merged.set(key,{...row,variacion_mensual_pct:short.value,variacion_interanual_pct:long,estado:short.state});
        }
        result.mensual=[...merged.values()];
        const latest = new Map();
        result.mensual.forEach(row => {
            if (!latest.has(row.series_id) || latest.get(row.series_id).periodo_ym < row.periodo_ym) latest.set(row.series_id,row);
        });
        result.ultimos = [...latest.values()].map(row => ({...row,periodo_ultimo:row.periodo_ym,fecha_ultima:row.fecha,
            precio_mediana_ultimo_periodo:row.precio_mediana,operaciones_ultimo_periodo:row.operaciones}));
        result.semaforo = result.mensual;
        const summary = current.resumen[0] || {};
        const dates = [...result.mensual.map(row => row.fecha), coverage.oldest_verified_date, coverage.latest_verified_date].filter(Boolean).sort();
        const captured = result.mensual.reduce((stamp,row) => row.updated_at_utc > stamp ? row.updated_at_utc : stamp, summary.fecha_actualizacion_dashboard || '');
        result.resumen = [{...summary, fecha_min:dates[0] || summary.fecha_min, fecha_max:dates.at(-1) || summary.fecha_max,
            fecha_actualizacion_dashboard:captured,
            filas_dashboard:result.mensual.reduce((sum,row) => sum + (Number(row.operaciones) || 1),0)}];
        return result;
    }
    async function assemble(family,current,year,parseCSV) {
        const entry=await metadata(family);
        const monthly=await load(family,'mensual',null,parseCSV);
        const keys=new Set(monthly.map(monthKey));
        const years=new Set((current._observations || []).filter(row=>row.frecuencia!=='mensual' && keys.has(monthKey(row))).map(row=>row.fecha.slice(0,4)));
        if ([...years].some(value=>!entry.daily[value])) throw new Error('Faltan observaciones diarias para revisar el agregado histórico');
        const knownSeries=new Set(monthly.map(row=>row.series_id));
        (current._observations || []).filter(row=>row.frecuencia!=='mensual' && knownSeries.has(row.series_id)).forEach(row=>{
            for(const days of [-30,0,30]) {
                const value=moveDay(row.fecha,days).slice(0,4);
                if(entry.daily[value])years.add(value);
            }
        });
        if(year && year!=='TODOS') years.add(year);
        const inputs=(await Promise.all([...years].map(value=>load(family,'diaria',value,parseCSV)))).flat();
        const counts=new Map();inputs.forEach(row=>counts.set(monthKey(row),(counts.get(monthKey(row)) || 0)+1));
        const affected=new Set((current._observations || []).filter(row=>row.frecuencia!=='mensual').map(monthKey));
        if(monthly.some(row=>affected.has(monthKey(row)) && Number(row.operaciones)!==counts.get(monthKey(row)))) {
            throw new Error('Detalle diario incompleto para revisar el mes histórico');
        }
        const selected=year ? inputs.filter(row=>row.fecha.startsWith(year)) : [];
        return merge(current,monthly,selected,current._observations,entry.coverage,inputs);
    }
    return {index, metadata, load, merge, expand, assemble};
})();
if (typeof module !== 'undefined') module.exports = CommodityHistory;
