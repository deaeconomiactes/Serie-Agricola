"""Verified SSPM series 40 and archived SAGyP bovine indicators. No conversions."""
import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from scripts.carnes.model import DataError, observation

SSPM_COLUMNS=['indice_tiempo','vacunos_cabezas','vacunos_toneladas','ovinos_cabezas',
    'porcinos_cabezas','porcinos_toneladas','aves_cabezas','aves_toneladas']
INDICATOR_COLUMNS=['indice_tiempo','faena_total_pais','porcentaje_hembras',
    'produccion_en_miles_de_toneladas_res_con_hueso','peso_promedio_res',
    'novillos_precio_kilo_vivo_pesos','novillo_precio_kilo_vivo_dolares','novillos_peso_kilo_vivo',
    'consumo_interno_aparente_en_miles_de_toneladas_res_c_hueso','consumo_interno_per_capita_kg_por_habitante',
    'consumo_interno_per_capita_kg_por_habitante_por_anio',
    'exportacion_volumen_en_toneladas_equivalentes_res_con_hueso','exportacion_valor_en_miles_de_dolares',
    'exportacion_precio_dolares_por_toneladas_res_con_hueso']
# Explicit source dictionary; meanings verified against the resource's data dictionary.
INDICATORS={
 'faena_total_pais':('slaughter','slaughter_heads','TOTAL','cabezas','NOT_APPLICABLE','NOT_APPLICABLE'),
 'porcentaje_hembras':('slaughter','female_share','Hembras','percent','NOT_APPLICABLE','NOT_APPLICABLE'),
 'produccion_en_miles_de_toneladas_res_con_hueso':('production','carcass_production','TOTAL','miles de toneladas res con hueso','NOT_APPLICABLE','carcass_with_bone'),
 'peso_promedio_res':('carcass_weight','mean_carcass_weight','TOTAL','kg gancho','NOT_APPLICABLE','carcass'),
 'novillos_precio_kilo_vivo_pesos':('livestock_price','novillo_price_ARS','Novillo','ARS/kg vivo','ARS','live'),
 'novillo_precio_kilo_vivo_dolares':('livestock_price','novillo_price_USD','Novillo','USD/kg vivo','USD','live'),
 'novillos_peso_kilo_vivo':('live_weight','mean_live_weight','Novillo','kg vivo','NOT_APPLICABLE','live'),
 'exportacion_volumen_en_toneladas_equivalentes_res_con_hueso':('exports','export_volume_rch','TOTAL','toneladas equivalentes res con hueso','NOT_APPLICABLE','carcass_equivalent_with_bone'),
 'exportacion_valor_en_miles_de_dolares':('exports','export_value','TOTAL','miles USD','USD','NOT_APPLICABLE'),
 'exportacion_precio_dolares_por_toneladas_res_con_hueso':('exports','export_unit_value_rch','TOTAL','USD/tonelada equivalente res con hueso','USD','carcass_equivalent_with_bone'),
}


def decimal_value(value):
    if value is None or value=='':return None
    if isinstance(value,bool):raise DataError('Boolean is not a measure')
    try:n=Decimal(str(value))
    except InvalidOperation:raise DataError('Unparseable measure') from None
    if not n.is_finite() or n<0:raise DataError('Invalid/negative measure')
    return str(n)


def csv_rows(payload,expected):
    try:
        reader=csv.DictReader(io.StringIO(payload.decode('utf-8-sig')),strict=True)
        if reader.fieldnames!=expected:raise DataError('CSV schema changed')
        rows=list(reader)
    except (UnicodeError,csv.Error):raise DataError('Malformed CSV') from None
    if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise DataError('Empty or incomplete CSV')
    return rows


def parse_csv(payload,spec,as_of):
    historical=spec['kind']=='bovine_indicators'
    rows=csv_rows(payload,INDICATOR_COLUMNS if historical else SSPM_COLUMNS)
    output=[];seen=set();frequency=spec.get('frequency','monthly')
    for number,row in enumerate(rows,2):
        raw_day=row['indice_tiempo']
        try:day=date.fromisoformat(raw_day+'-01' if historical else raw_day)
        except ValueError:raise DataError('Invalid observation date') from None
        if day>as_of or day.day!=1 or (frequency=='annual' and day.month!=1):raise DataError('Invalid/future period')
        if day in seen:raise DataError('Duplicate period')
        seen.add(day)
        for column in INDICATORS if historical else SSPM_COLUMNS[1:]:
            raw=row[column];value=decimal_value(raw);flags=[]
            if historical:
                family,metric,category,unit,currency,basis=INDICATORS[column]
                species='bovino';market='Mercado de Liniers' if family in {'livestock_price','live_weight'} else 'NOT_APPLICABLE'
                flags=['historical_series_ended_2019_08']
            else:
                species,measure=column.split('_');species={'vacunos':'bovino','porcinos':'porcino','ovinos':'ovino','aves':'aviar'}[species]
                family='slaughter' if measure=='cabezas' else 'production';metric=column;category='TOTAL'
                unit=spec['units'][column];currency='NOT_APPLICABLE';basis='NOT_APPLICABLE' if family=='slaughter' else 'NOT_IDENTIFIED';market='NOT_APPLICABLE'
                if family=='production':flags.append('weight_basis_not_documented_in_sspm_catalog')
                if column=='aves_cabezas':flags.append('bird_count_scale_requires_validation')
                if value is not None and family=='slaughter' and Decimal(value)%1:flags.append('fractional_count_published')
            if value is None:flags.append('missing_published_value')
            output.append(observation(family=family,metric=metric,species=species,observation_date=day.isoformat(),
                frequency=frequency,category=category,geography='Argentina',geography_level='national',market=market,
                entity_type='national_total' if category=='TOTAL' else 'category',table_id=spec['kind'],
                currency=currency,unit=unit,weight_basis=basis,value=value,value_raw=raw,
                methodology='SAGyP archived monthly indicators' if historical else 'SSPM faena pecuaria as published',
                quality_flags=flags,source_locator=f'CSV:row={number};column={column}'))
    return output
