/* Build-only bridge: reuse the production adapters, never reimplement prices. */
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {webcrypto} = require('node:crypto');
async function readSources(root) {
    const read = name => fs.readFileSync(path.join(root,name),'utf8');
    const mcba = require(path.join(root,'mcba-prices.js'));
    const monthly = require(path.join(root,'mcba-monthly.js'));
    global.crypto=webcrypto;global.MCBAPrices=mcba;
    const ctx=vm.createContext({console:{log(){},warn(){}},document:{addEventListener(){}},MCBAPrices:mcba,MCBAMonthly:monthly});
    vm.runInContext(read('app.js'),ctx);
    ctx.quality=read('RESUMEN_SERIES_UTILIZABLES_PRECIOS_2026.csv');
    ctx.integrated=read('PRECIOS_MAYORISTAS_INTEGRADO.csv');
    vm.runInContext(`priceSeriesData=parsePriceCSV(quality);priceQualityMap=new Map(priceSeriesData.map(row=>[priceSeriesKey(row),row.indicador_serie_utilizable||'']));
        legacyPriceData=processPriceData(parsePriceCSV(integrated),PRICE_CSV_PATH,true).map(row=>({...row,data_source:'LEGACY',source_status:'LEGACY',last_update:'',fechaPrecision:row.mercado===MCBAPrices.MCBA?String(row.fechaPrecision).toLowerCase():row.fechaPrecision,calidadMCBA:'',tamanoMCBA:'',gradoMCBA:''}));`,ctx);
    const base='data/magyp/dashboard/mcba/';
    const result=await mcba.verifyBundle({daily:read(base+'MCBA_MAGYP_DAILY.csv'),summary:read(base+'MCBA_MAGYP_SUMMARY.csv'),marker:JSON.parse(read(base+'_SUCCESS.json'))});
    const fresh=await monthly.verify(read(monthly.BASE+monthly.FILE),JSON.parse(read(monthly.BASE+'_SUCCESS.json')));
    const update=JSON.parse(read(base+'MCBA_MAGYP_UPDATE_STATUS.json'));
    ctx.dailyRows=result.rows;ctx.monthlyRows=fresh;ctx.update=update;ctx.info=result.info;
    vm.runInContext(`magypPriceInfo=info;magypUpdateMetadata=update;
        magypPriceData=MCBAPrices.adapt(dailyRows,MONTHS_FULL,update.source_status==='MAGYP_LAST_VALID'?'MAGYP_LAST_VALID':'MAGYP',formatLabel);
        mcbaMonthlyData=MCBAMonthly.adapt(monthlyRows,MONTHS_FULL,formatLabel);
        rawPriceData=legacyPriceData.concat(magypPriceData,mcbaMonthlyData);
        validPriceData=rawPriceData.filter(row=>isValidPrice(row.precioObservado));`,ctx);
    // Future dates are filtered at runtime, exactly as before; the build has no calendar-dependent output.
    const views={};
    for(const frequency of ['diaria','mensual','anual']) views[frequency]=JSON.parse(vm.runInContext(`JSON.stringify(getPriceSourceRows('${frequency}'))`,ctx));
    const normalize=require(path.join(root,'scripts/mayoristas/normalize.cjs')).makeNormalizer(root,views);
    for(const frequency of Object.keys(views)) views[frequency]=views[frequency].map(normalize);
    return {views,metadata:{magypPriceInfo:result.info,magypUpdateMetadata:update},context:ctx};
}
module.exports={readSources};
if(require.main===module) readSources(path.resolve(process.argv[2]||'.')).then(({views,metadata})=>process.stdout.write(JSON.stringify({views,metadata}))).catch(e=>{console.error(e.message);process.exitCode=1;});
