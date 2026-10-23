import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.sio import grain as g
import integrar_commodities_sio as integrate


def event(key, **changes):
    row={'id_operacion_sio':key,'fecha':'2026-09-09','commodity':'Maíz','moneda':'USD','unidad':'TN',
         'tipo_precio':'Precio Hecho','condicion_comercial':'Entrega inmediata','lugar_entrega':'Rosario NEn destino',
         'precio_puesto_en':'','procedencia':'Córdoba','condicion_pago':'Contra entrega','tipo_operacion':'Compraventa',
         'operacion':'Contrato','fuente':'SIO Granos','precio':'100','volumen':'30','volumen_unidad':'TN',
         'precio_valido_para_serie':'sí','precio_cero_flag':'no','fecha_descarga_snapshot':'2026-09-09T15:00:00Z'}
    return dict(row,**changes)


def result(rows):
    events,_,_=g.normalize(rows)
    return g.views(events,'a'*64)


class GrainTests(unittest.TestCase):
    def test_single_place_statistics_and_volume_weight(self):
        row=result([event('1',precio='100',volumen='10'),event('2',precio='200',volumen='30')])['diario'][0]
        self.assertEqual(row['operaciones'],'2');self.assertEqual(row['precio_mediana'],'150')
        self.assertEqual(row['precio_ponderado_volumen'],'175');self.assertEqual(row['volumen_total'],'40')
        self.assertEqual(json.loads(row['event_ids']),['id:1','id:2'])

    def test_places_conditions_payment_origins_event_classes_and_currencies_are_separate(self):
        rows=[event('base'),event('place',lugar_entrega='Rosario SEn destino'),
              event('condition',condicion_comercial='A fijar'),event('payment',condicion_pago='A plazo'),
              event('currency',moneda='ARS'),event('origin',procedencia='Santa Fe'),
              event('basis',lugar_entrega='Rosario NEn origen'),event('event',operacion='Rectificación'),
              event('type',tipo_operacion='Canje'),event('unit',unidad='KG',volumen_unidad='KG'),
              event('quality',calidad='Otra'),event('shipment',fecha_entrega='2026-12')]
        output=result(rows)
        self.assertEqual(len(output['diario']),len(rows));self.assertEqual(len(output['mensual']),len(rows))
        self.assertEqual(len({r['series_id'] for r in output['mensual']}),len(rows))

    def test_missing_place_is_not_multiple_places(self):
        rows=result([event('missing',lugar_entrega=''),event('known')])['diario']
        missing=next(r for r in rows if r['delivery_status']=='MISSING')
        self.assertEqual(missing['lugar_entrega_raw'],'')
        self.assertIn('MISSING_LUGAR_ENTREGA',json.loads(missing['quality_flags']))

    def test_zero_missing_negative_and_nonfinite_price_are_not_observations(self):
        output=result([event('positive'),event('zero',precio='0'),event('missing',precio=''),
                       event('negative',precio='-1'),event('infinity',precio='1e309')])
        self.assertEqual(output['diario'][0]['operaciones'],'1')

    def test_unidentified_or_nonexplicit_currency_is_quarantined_without_inference(self):
        output=result([event('known'),event('missing',moneda='Sin identificar'),
                       event('unconfirmed',moneda='ARS',moneda_explicitamente_informada='no')])
        self.assertEqual(output['diario'][0]['operaciones'],'1')

    def test_zero_volume_missing_volume_and_incomparable_volume_are_different(self):
        zero=result([event('zero',volumen='0')])['diario'][0]
        self.assertEqual(zero['volumen_total'],'0');self.assertEqual(zero['precio_ponderado_volumen'],'')
        for volume,unit in [('', 'TN'),('-1','TN'),('30','KG')]:
            row=result([event('1'),event('2',volumen=volume,volumen_unidad=unit)])['diario'][0]
            self.assertEqual(row['volumen_total'],'');self.assertEqual(row['precio_ponderado_volumen'],'')
            self.assertEqual(row['volumen_conocido'],'30')

    def test_monthly_preserves_conditions_and_does_not_bridge_missing_months(self):
        output=result([event('sep'),event('oct',fecha='2026-10-01',precio='120'),
                       event('nov',fecha='2026-11-01',precio='150',condicion_pago='A plazo'),
                       event('dec',fecha='2026-12-01',precio='180')])
        monthly={r['periodo_ym']:r for r in output['mensual']}
        self.assertEqual(monthly['2026-10']['variacion_mensual_pct'],'20')
        self.assertEqual(monthly['2026-11']['variacion_mensual_pct'],'')
        self.assertEqual(monthly['2026-12']['variacion_mensual_pct'],'')
        self.assertTrue(all(r['condicion_pago'] for r in output['semaforo']))

    def test_duplicate_events_are_not_counted_twice_and_conflicts_fail_closed(self):
        self.assertEqual(result([event('1'),event('1')])['diario'][0]['operaciones'],'1')
        with self.assertRaisesRegex(ValueError,'incompatible'):
            result([event('1'),event('1',precio='200')])

    def test_reproducible_identity_independent_of_capture_and_order(self):
        a=result([event('1'),event('2')])['diario'][0]
        b=result([event('2',fecha_descarga_snapshot='2026-10-01'),event('1')])['diario'][0]
        self.assertEqual(a['series_id'],b['series_id']);self.assertEqual(a['event_ids'],b['event_ids'])

    def test_snapshot_fallback_identity_preserves_economic_conditions_when_id_missing(self):
        a=event('',condicion_pago='Contado');b=event('',condicion_pago='A plazo')
        self.assertNotEqual(integrate.snapshot_identity(a),integrate.snapshot_identity(b))
        self.assertNotEqual(integrate.snapshot_identity(a),integrate.snapshot_identity(event('',moneda='ARS')))

    def test_semantic_control_maize_19345_separates_into_four_places(self):
        places=['Zona 7En destino','Zona 5En origen','Rosario NEn destino','Rosario SEn destino']
        output=result([event(str(i),precio=str(price),lugar_entrega=place) for i,(place,price) in enumerate(zip(places,[161.73,191.9,195,195]))])
        self.assertEqual(len(output['diario']),4)
        self.assertEqual(sorted(float(r['precio_mediana']) for r in output['diario']),[161.73,191.9,195,195])
        self.assertNotIn('193.45',[r['precio_mediana'] for r in output['diario']])

    def test_publication_schema_failure_empty_and_replace_failure_preserve_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'input.csv';report=root/'report.md'
            paths={key:root/(key+'.csv') for key in ['diario','mensual','ultimos','resumen','semaforo']}
            for p in paths.values():p.write_bytes(b'LAST_VALID')
            source.write_text('unknown;schema\n1;2\n')
            with self.assertRaises(ValueError):g.build(source,paths,report)
            for p in paths.values():self.assertEqual(p.read_bytes(),b'LAST_VALID')
            source.write_bytes(g.csv_bytes([event('0',precio='0')],list(event('0'))))
            with self.assertRaises(ValueError):g.build(source,paths,report)
            source.write_bytes(g.csv_bytes([event('1')],list(event('1'))))
            real=g.os.replace;calls=0
            def fail_second(*args):
                nonlocal calls
                calls+=1
                if calls==2:raise OSError('disk failure')
                return real(*args)
            with patch.object(g.os,'replace',side_effect=fail_second):
                with self.assertRaises(OSError):g.build(source,paths,report)
            for p in paths.values():self.assertEqual(p.read_bytes(),b'LAST_VALID')
            metrics=g.build(source,paths,report)
            self.assertEqual(metrics['valid_rows'],1)
            audit=json.loads((root/'SIO_GRAIN_AUDIT.json').read_text('utf-8'))
            self.assertEqual(audit['input_sha256'],hashlib.sha256(source.read_bytes()).hexdigest())

    def test_integration_preserves_original_type_payment_quality_and_capture_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'SIO_latest_GetOperaciones_20261023_120000.json'
            row=['123','23/10/2026','999','Contrato','Canje','Precio Hecho','MAIZ','30,00',
                 'Conforme','BUENOS AIRESLIMA','U$S 195,00','Rosario NEn destino','01/11/2026-30/11/2026','Contra entrega','No']
            path.write_text(json.dumps({'d':{'Items':[{'ID':'123','Row':row}]}}),encoding='utf-8')
            rows,_=integrate.process_file(path,{},integrate.LATEST_POSITIONAL_MAPPING,1,'no_aplica')
            self.assertEqual(len(rows),1)
            light=integrate.light_history_row(rows[0])
            self.assertEqual(light['tipo_operacion'],'Canje');self.assertEqual(light['condicion_pago'],'Contra entrega')
            self.assertEqual(light['calidad'],'Conforme');self.assertEqual(light['numero_operacion'],'999')
            self.assertEqual(light['fecha_entrega'],'01/11/2026-30/11/2026')
            self.assertEqual(light['raw_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':
    unittest.main()
