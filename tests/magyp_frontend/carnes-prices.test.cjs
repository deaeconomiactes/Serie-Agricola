const test=require('node:test');
const assert=require('node:assert/strict');
const C=require('../../carnes.js');

test('daily chart does not connect days without an observation',()=>{
 const rows=[{observation_date:'2026-11-06',value:'10'},{observation_date:'2026-11-09',value:'12'}];
 assert.deepEqual(C.dailyChartRows(rows).map(r=>r.value),['10','','','12']);assert.equal(rows.length,2);
});

test('A3500 conversion uses the dated prior quote, never extrapolates or bridges long gaps',()=>{
 const fx={schema_version:'bcra-a3500-v1',source:'https://www.bcra.gob.ar/tipo-cambio-referencia-comunicacion-a-3500-tcnpm/',raw_sha256:'a'.repeat(64),capture_date:'2026-11-13T12:20:03Z',rates:[['2026-11-06',1500],['2026-11-10',1510],['2026-11-12',1544.432]]};
 C.validateRates(fx);assert.deepEqual(C.rateForDate(fx.rates,'2026-11-09'),['2026-11-06',1500]);assert.equal(C.rateForDate(fx.rates,'2026-11-13'),null);assert.equal(C.rateForDate(fx.rates,'2026-11-05'),null);
 const row={observation_date:'2026-11-09',value:'4500',value_status:'observed',currency:'ARS',unit:'ARS/kg vivo'};const converted=C.convertPrice(row,fx);
 assert.equal(converted.value,'3');assert.equal(converted.fx_date,'2026-11-06');assert.equal(converted.original_ars_kg,'4500');assert.equal(row.currency,'ARS');
 assert.equal(C.convertPrice({...row,observation_date:'2026-11-13'},fx).value,'');
 assert.throws(()=>C.validateRates({...fx,rates:[...fx.rates,fx.rates[0]]}));
 assert.equal(C.rateForDate([['2026-01-01',1],['2026-02-01',2]],'2026-01-20'),null);
});
test('published BCRA capture contains the verified 12 November 2026 reference',()=>{
 const fx=C.validateRates(require('../carnes/fixtures/bcra-a3500-sample.json'));
 assert.deepEqual(C.rateForDate(fx.rates,'2026-11-12'),['2026-11-12',1544.432]);
 const result=C.convertPrice({observation_date:'2026-11-12',value:'4393.97',value_status:'observed'},fx);
 assert.ok(Math.abs(Number(result.value)-4393.97/1544.432)<1e-12);
});

test('daily MAG prices are discoverable separately from INMAG and finished Liniers history',()=>{
    const sources={
        mag_prices_history_novillos:{source_id:'mag_prices_history_novillos',files:[{family:'livestock_price',frequency:'daily',year:'2026',path:'novillos.csv.gz'}]},
        mag_prices_detail:{source_id:'mag_prices_detail',files:[{family:'livestock_price',frequency:'daily',year:'2026',path:'detail.csv.gz'}]},
        mag_inmag:{source_id:'mag_inmag',files:[{family:'livestock_index',frequency:'daily',year:'2026',path:'inmag.csv.gz'}]},
        magyp_indicators_archive:{source_id:'magyp_indicators_archive',files:[{family:'livestock_price',frequency:'monthly',year:'2019',path:'liniers.csv.gz'}]},
    };
    const loader=new C.Loader(async()=>{throw new Error('not used');});loader.index={sources};
    assert.deepEqual(loader.entries('prices').map(e=>e.source_id).sort(),['mag_prices_detail','mag_prices_history_novillos']);
    assert.deepEqual(loader.entries('inmag').map(e=>e.source_id),['mag_inmag']);
    assert.equal(loader.descriptors('prices','livestock_price','daily').length,2);
    assert.equal(loader.descriptors('archive','livestock_price','monthly')[0].entry.source_id,'magyp_indicators_archive');
});

test('multi-capture daily rows validate their own RAW evidence and dates',()=>{
    const entry={source_id:'mag_prices_history_novillos',source_url:'https://mercadoagroganadero.com.ar/php/hacigraf000110.chartjs.php',capture_mode:'multi_capture'};
    const descriptor={family:'livestock_price',frequency:'daily',year:'2026',rows:1};
    const row=Object.fromEntries(C.FIELDS.map(key=>[key,'']));
    Object.assign(row,{schema_version:'carnes-v1',source_id:entry.source_id,source_url:entry.source_url,family:'livestock_price',metric:'price_average',species:'bovinos',
        observation_date:'2026-11-11',period_end:'2026-11-11',frequency:'daily',category:'Novillos',category_raw:'NOVILLOS',geography:'Mercado Agroganadero de Cañuelas',
        geography_raw:'Mercado Agroganadero de Cañuelas',geography_level:'market',market:'Mercado Agroganadero de Cañuelas',entity_type:'category',currency:'ARS',unit:'ARS/kg vivo',
        unit_raw:'ARS/kg vivo',weight_basis:'live',value:'4200.5',value_raw:'4200.5',value_status:'observed',methodology:'mag_category_average_chart',quality_flags:'[]',
        source_locator:'response.json#/data/0/vals/0',capture_date:'2026-11-11T13:00:00Z',capture_id:'20261111T130000Z_0123456789ab',raw_sha256:'a'.repeat(64),
        observation_id:'b'.repeat(64),record_id:'c'.repeat(64)});
    assert.equal(C.validateRows([row],entry,descriptor).length,1);
    for(const change of [{capture_id:'invalid'},{capture_date:'not-a-date'},{raw_sha256:'x'},{observation_date:'2026-02-30'}]){
        assert.throws(()=>C.validateRows([{...row,...change}],entry,descriptor));
    }
});

test('daily price labels show the observation date rather than a monthly caption',()=>{
    assert.equal(C.caption({frequency:'daily',observation_date:'2026-11-11'}),'11/11/2026');
});
