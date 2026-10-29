/* Build-only canonical dimensions. Input observations remain immutable. */
const fs = require('node:fs');
const path = require('node:path');
const key = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleUpperCase('es-AR').replace(/[^\p{L}\p{N}]+/gu, ' ').trim().replace(/\s+/g, ' ');

function makeNormalizer(root, views) {
    const read = name => JSON.parse(fs.readFileSync(path.join(root, 'data/mayoristas/config', name), 'utf8'));
    const origins = read('procedencia_aliases.json');
    const products = read('producto_variedad_aliases.json');
    const sources = read('fuentes.json').sources;
    const approved = new Map();
    for (const rule of origins.filter(r => r.status === 'APPROVED')) {
        for (const name of [rule.raw, rule.canonical]) {
            const k = key(name);
            if (approved.has(k) && approved.get(k) !== rule.canonical) throw Error('Alias de procedencia contradictorio');
            approved.set(k, rule.canonical);
        }
    }
    const productRules = new Map();
    for (const rule of products.filter(r => r.status === 'APPROVED')) {
        if (productRules.has(key(rule.raw))) throw Error('Alias de producto duplicado');
        productRules.set(key(rule.raw), rule);
    }
    // Only normalize spelling for identical word sequences. Prefer the accented
    // form already observed; ambiguous abbreviations are never expanded here.
    const labels = new Map();
    for (const rows of Object.values(views)) for (const row of rows) {
        const name = String(row.procedencia || '').trim(); const k = key(name);
        if (!k) continue;
        const old = labels.get(k);
        if (!old || (name.normalize('NFD').length - name.length) > (old.normalize('NFD').length - old.length)) labels.set(k, name);
    }
    return function normalize(row) {
        const sourceProduct = row.product_raw ?? row.legacy_especie_raw ?? row.especie ?? '';
        const sourceVariety = row.variety_raw ?? row.legacy_variedad_raw ?? row.variedad ?? '';
        const sourceOrigin = row.origin_raw ?? row.legacy_procedencia_raw ?? row.procedencia ?? '';
        const sourceMarket = row.legacy_mercado_raw ?? row.mercado ?? '';
        const sourcePackage = row.package_raw ?? row.legacy_envase_raw ?? row.envase ?? '';
        const sourceUnit = row.legacy_unidad_raw ?? row.price_unit ?? row.unidadPrecioObservado ?? '';
        const originalCurrency = String(row.currency ?? row.legacy_moneda_raw ?? '').trim();
        const currencyKey = key(originalCurrency);
        const confirmed = sources.find(s => s.data_source === row.data_source && s.market === row.mercado);
        const sourceCurrency = confirmed && (!currencyKey || currencyKey === confirmed.currency) ? confirmed.currency : '';
        const currency = sourceCurrency || (['ARS','USD','EUR','BRL','PYG','UYU','CLP','BOB'].includes(currencyKey) ? currencyKey : 'UNKNOWN');
        const rule = productRules.get(key(row.especie));
        // Never overwrite a distinct variety already stated by the source.
        const canSplit = rule && (!rule.variedad || !row.variedad || key(row.variedad) === key(rule.variedad) || key(row.variedad) === 'SIN VARIEDAD');
        const species = canSplit ? rule.producto : row.especie;
        const variety = canSplit && rule.variedad ? rule.variedad : row.variedad;
        const origin = approved.get(key(row.procedencia)) || labels.get(key(row.procedencia)) || row.procedencia;
        const unit = row.unidadPrecioObservado === '$/kg' ? 'kg' : row.unidadPrecioObservado === '$/bulto' ? 'bulto' : 'UNKNOWN';
        const kg = Number(row.kgBulto);
        const weight = Number.isFinite(kg) && kg > 0 ? kg : null;
        const factor = unit === 'kg' ? 1 : unit === 'bulto' && weight ? 1 / weight : null;
        const declared = /\bX\s*(\d+(?:[.,]\d+)?)\s*KG\b/i.exec(row.envase || '');
        const validated = unit === 'kg' || Boolean(unit === 'bulto' && weight && declared && Number(declared[1].replace(',','.')) === weight && !/\bMAZOS?\b/i.test(row.envase || ''));
        const {legacy_especie_raw,legacy_variedad_raw,legacy_procedencia_raw,legacy_mercado_raw,
            legacy_envase_raw,legacy_unidad_raw,legacy_moneda_raw,legacy_archivo_origen,...base} = row;
        return {...base, ...(sourceCurrency ? {currency:sourceCurrency, moneda_evidencia:'data/mayoristas/config/fuentes.json'} : {}), _normalization_schema:'v1', producto_raw:sourceProduct, variedad_raw:sourceVariety, procedencia_raw:sourceOrigin,
            mercado_raw:sourceMarket, envase_raw:sourcePackage, unidad_raw:sourceUnit,
            tamanio_raw:row.size_raw ?? row.tamanoMCBA ?? '', calidad_raw:row.quality_raw ?? row.calidadMCBA ?? '',
            grado_raw:row.grade_raw ?? row.gradoMCBA ?? '', producto_normalizado:species,
            variedad_normalizada:variety, procedencia_normalizada:origin, mercado_normalizado:row.mercado,
            envase_normalizado:row.envase, tamanio_normalizado:row.tamanoMCBA || '',
            calidad_normalizada:row.calidadMCBA || '', grado_normalizado:row.gradoMCBA || '',
            unidad_normalizada:unit, moneda_original:originalCurrency, moneda_normalizada:currency,
            factor_conversion:factor, peso_utilizado:weight, conversion_validada:validated,
            fuente_original:legacy_archivo_origen || row.fuente || '',
            especie:species, variedad:variety, procedencia:origin};
    };
}
module.exports = {key, makeNormalizer};
