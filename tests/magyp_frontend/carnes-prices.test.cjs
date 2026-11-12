const test=require('node:test');
const assert=require('node:assert/strict');
const C=require('../../carnes.js');

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
