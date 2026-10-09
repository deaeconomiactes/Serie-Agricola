import json
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from contextlib import redirect_stdout
from email.message import Message
from unittest.mock import patch
from scripts.magyp.grains import references as r

DAY=date(2026,10,8)
FIXTURES=Path(__file__).parent/'fixtures'


class FobResponse:
    status=200
    headers=Message()
    headers['Content-Type']='text/html; charset=UTF-8'

    def __init__(self,body):self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,limit):return self.body[:limit]


def board(price='342,300.00'):
    return {'text':'Cotizaciones $/Tn Miércoles 07 de octubre de 2026 Cotizaciones provisorias',
        'rows':[['PRODUCTO','BUENOS AIRES','BAHIA BLANCA','QUEQUEN','ROSARIO','CORDOBA']]+
            [[product,'0.00','0.00','0.00',price,'0.00'] for product in
             ['GIRASOL','TRIGO PAN','MAIZ','SOJA','SORGO','CEBADA FORRAJERA']]}


def fob():
    return {'posts':[{'fecha':'2026-10-08 00:00:00.000','circular':'2076','posicion':'001A',
        'precio':290,'mesDesde':10,'añoDesde':2026,'mesHasta':11,'añoHasta':2026}]}


def enrich(rows,capture='c1',stamp='2026-10-09T12:00:00Z'):
    return [{**row,'capture_id':capture,'updated_at_utc':stamp,'raw_sha256':'a'*64,
        'record_id':r.identity([row['observation_id'],capture])} for row in rows]


class ReferencesTests(unittest.TestCase):
    def test_fob_legacy_and_current_published_fixtures_preserve_original_fields(self):
        for name in ['fob_legacy.json','fob_current_published.json']:
            body=(FIXTURES/name).read_bytes();original=json.loads(body)
            projected=r.project(body,'fob')
            self.assertEqual(projected,original)
            row=r.parse(projected,'fob',DAY,DAY.isoformat())[0]
            self.assertEqual(row['position_raw'],original['posts'][0]['posicion'])
            self.assertEqual(row['price_raw'],str(original['posts'][0]['precio']))
            self.assertEqual(row['circular'],original['posts'][0]['circular'])
            self.assertEqual(row['moneda'],'Sin identificar')
            self.assertEqual(row['unidad'],'Sin identificar')
            self.assertNotIn('ncm',row)

    def test_fob_current_empty_recognized_but_not_a_publishable_price_series(self):
        body=(FIXTURES/'fob_current_empty.json').read_bytes()
        self.assertEqual(r.project(body,'fob'),[])
        for obj in [[],{'posts':[]}]:
            with self.subTest(obj=obj),self.assertRaisesRegex(r.Error,'FOB sin publicación'):
                r.parse(obj,'fob',date(2026,10,9),'2026-10-09')

    def test_fob_unknown_schemas_still_rejected(self):
        published=json.loads((FIXTURES/'fob_current_published.json').read_bytes())
        unknown=[(FIXTURES/'fob_unknown.json').read_bytes(),r.encoded(published['posts']),
                 r.encoded({'posts':None}),r.encoded({'posts':[],'extra':1})]
        for change in ['extra','removed','renamed']:
            obj=json.loads(r.encoded(published));row=obj['posts'][0]
            if change=='extra':row['product']='unverified'
            elif change=='removed':del row['precio']
            else:row['price']=row.pop('precio')
            unknown.append(r.encoded(obj))
        for body in unknown:
            with self.subTest(body=body),self.assertRaises(r.Error):r.project(body,'fob')

    def test_fob_empty_weekend_preserves_last_valid_output_for_both_formats(self):
        for body in [b'[]',r.encoded({'posts':[]})]:
            with self.subTest(body=body),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);out=root/'dashboard/commodities/fob.csv'
                prior=r.bundle(enrich(r.parse(fob(),'fob',DAY,DAY.isoformat())),'fob')
                r.atomic(out,prior)
                with patch.object(r,'build_opener') as opener:
                    opener.return_value.open.return_value=FobResponse(body)
                    r.run('fob',root,date(2026,10,10),'2026-10-10',True)
                self.assertEqual(out.read_bytes(),prior)
                self.assertFalse((root/'raw').exists())

    def test_fob_failure_keeps_last_output_and_all_other_families_publish(self):
        for body,diagnostic in [(b'[]','FOB sin publicación'),
                ((FIXTURES/'fob_unknown.json').read_bytes(),'Schema FOB cambiado')]:
            with self.subTest(body=body),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);out=root/'dashboard/commodities/fob.csv'
                prior=r.bundle(enrich(r.parse(fob(),'fob',DAY,DAY.isoformat())),'fob')
                r.atomic(out,prior)
                # Valid independent snapshots: no network or changes to other family parsers.
                for source in ['internal','board','fas','futures']:
                    row=r.observation(source,'2026-10-08','Fixture','Fixture plaza',
                        'Fixture reference','Sin identificar','Sin identificar','100','json')
                    path=root/'normalized'/'commodities'/source/'fixture.json'
                    r.atomic(path,r.encoded(enrich([row])))
                real_run=r.run
                def run(source,data_root,as_of,requested,allow_web):
                    return real_run(source,data_root,as_of,requested,source=='fob')
                logs=io.StringIO()
                with patch('sys.argv',['references','--source','all','--date','2026-10-09',
                        '--data-root',str(root),'--allow-web']),patch.object(r,'build_opener') as opener,\
                        patch.object(r,'run',side_effect=run),patch.object(r.time,'sleep'),redirect_stdout(logs):
                    opener.return_value.open.return_value=FobResponse(body)
                    self.assertEqual(r.main(),1)
                self.assertIn(diagnostic,logs.getvalue())
                self.assertEqual(out.read_bytes(),prior)
                for source in ['internal','board','fas','futures']:
                    self.assertIn('[PUBLISH] '+source,logs.getvalue())
                    r.validate_bundle((root/'dashboard/commodities'/f'{source}.csv').read_bytes(),source)
                self.assertFalse((root/'raw'/'commodities'/'fob').exists())

    def test_locale_decimals_and_missing_zero_distinct(self):
        self.assertEqual(r.number('342,300.00','us'),('342300.00','positive'))
        self.assertEqual(r.number('342.300,00','ar'),('342300.00','positive'))
        self.assertEqual(r.number('0.00','us'),('0.00','zero'))
        self.assertEqual(r.number('S/C','ar'),('','missing'))
        for raw in ['NaN','Infinity','-1','12x','1,5']:
            with self.subTest(raw=raw),self.assertRaises(r.Error):r.number(raw,'json')

    def test_public_projection_excludes_session(self):
        obj=r.project(b'<script>SECRET</script><input name="__VIEWSTATE" value="PRIVATE"><table><tr><td>public</td></tr></table>','board')
        self.assertEqual(obj['rows'],[['public']])
        self.assertNotIn('SECRET',str(obj));self.assertNotIn('PRIVATE',str(obj));self.assertNotIn('VIEWSTATE',str(obj))

    def test_fob_json_valid_wrong_content_type_irrelevant(self):
        obj=r.project(r.encoded(fob()),'fob')
        row=r.parse(obj,'fob',DAY,DAY.isoformat())[0]
        self.assertEqual(row['position_raw'],'001A')
        self.assertEqual(row['shipment_window'],'2026-10/2026-11')
        self.assertEqual(row['moneda'],'Sin identificar');self.assertEqual(row['currency_evidence'],'unknown')

    def test_fob_absent_empty_html_schema_invalid_price_date_duplicates(self):
        for obj in [{},{'posts':None},{'posts':[{}]},{'posts':[]},{'posts':fob()['posts'],'extra':1}]:
            with self.subTest(obj=obj),self.assertRaises(r.Error):
                r.parse(r.project(r.encoded(obj),'fob'),'fob',DAY,DAY.isoformat())
        for field,value in [('precio','bad'),('fecha','2026-02-30'),('mesDesde',13),('posicion',None)]:
            obj=fob();obj['posts'][0][field]=value
            with self.subTest(field=field),self.assertRaises(r.Error):r.parse(obj,'fob',DAY,DAY.isoformat())
        with self.assertRaises(r.Error):r.project(b'<html>service error</html>','fob')
        obj=fob();obj['posts']*=2
        with self.assertRaises(r.Error):r.parse(obj,'fob',DAY,DAY.isoformat())

    def test_board_provisional_zero_kept_not_published_as_price(self):
        rows=r.parse(board(),'board',DAY)
        self.assertEqual(len(rows),30)
        self.assertEqual(sum(row['value_status']=='zero' for row in rows),24)
        self.assertTrue(all(row['tipo_precio']=='Pizarra provisional' for row in rows))
        body=r.bundle(enrich(rows),'board');parsed=r.validate_bundle(body,'board')
        self.assertEqual(len([x for x in parsed if x['row_kind']=='diario']),6)

    def test_board_schema_future_stale_no_positive(self):
        obj=board();obj['rows'][0][1]='NEW PLAZA'
        with self.assertRaises(r.Error):r.parse(obj,'board',DAY)
        obj=board();obj['rows'].append(['NUEVO','1','1','1','1','1'])
        with self.assertRaises(r.Error):r.parse(obj,'board',DAY)
        with self.assertRaises(r.Error):r.parse(board(),'board',date(2026,10,1))
        with self.assertRaises(r.Error):r.parse(board(),'board',date(2026,11,1))
        with self.assertRaises(r.Error):r.parse(board('0.00'),'board',DAY)

    def test_fas_regimes_separate_oil_unit_unknown(self):
        obj={'grids':{'W0031GridContainerDataV':[['08/10/2026']+['100']*9],
                      'W0039GridContainerDataV':[['31/10/2025']+['99']*9]},
             'columns':[list(x) for x in zip(r.FAS_CODES,r.FAS_LABELS)]}
        rows=r.parse(obj,'fas',DAY)
        self.assertEqual(len(rows),18)
        self.assertNotEqual(rows[0]['series_id'],rows[9]['series_id'])
        self.assertEqual(rows[7]['unidad'],'Sin identificar')
        obj['columns'][0][1]='UNKNOWN'
        with self.assertRaises(r.Error):r.parse(obj,'fas',DAY)

    def test_futures_only_named_markets_not_embedded_physical_fob(self):
        rows=[['CHICAGO *'],['POSICION','TRIGO','MAIZ','AVENA','SOJA','HARINA DE SOJA','ACEITE DE SOJA'],
              ['8/oct','7/oct']*6,['DIC2026']+['251,05']*12,['KANSAS *'],['POSICION','TRIGO'],
              ['8/oct','7/oct'],['DIC2026','270,53','271,35'],['COTIZACIONES FOB BS. AS.'],
              ['POSICION','TRIGO PAN'],['DIC2026','999,00']]
        result=r.parse({'text':'8 de octubre de 2026 Cotizaciones de cierre Dólares Estadounidenses/Ton.','rows':rows},'futures',DAY)
        self.assertEqual(len(result),14)
        self.assertEqual({x['mercado'] for x in result},{'CHICAGO','KANSAS'})
        self.assertNotIn('999.00',[x['price'] for x in result])
        self.assertTrue(all(x['condicion_comercial']=='DIC2026' for x in result))

    def test_internal_monthly_schema_and_sc_preserved(self):
        plazas=[['DARSENA','ROSARIO','B.BLANCA','CORDOBA','QUEQUEN','DARSENA','ROSARIO','B.BLANCA','QUEQUEN','DARSENA','ROSARIO','B.BLANCA'],
                ['DARSENA','ROSARIO','B.BLANCA','QUEQUEN','DARSENA','ROSARIO','B.BLANCA','QUEQUEN','B.BLANCA','QUEQUEN']]
        obj={'text':'Pesos Argentinos por Toneladas','rows':[['AÑO \\ MES','TRIGO','MAIZ','SORGO'],plazas[0],['2026'],['SEPTIEMBRE']+['S/C','100,50']*6,
             ['AÑO \\ MES','SOJA','GIRASOL','CEBADA FORRAJERA'],plazas[1],['2026'],['SEPTIEMBRE']+['S/C','99,50']*5]}
        rows=r.parse(obj,'internal',DAY)
        self.assertEqual(len(rows),22);self.assertEqual(rows[0]['frecuencia'],'mensual')
        obj['rows'][1][0]='NEW'
        with self.assertRaises(r.Error):r.parse(obj,'internal',DAY)

    def test_variations_exact_periods_not_nearest_observation(self):
        a=r.observation('board','2026-08-01','SOJA','ROSARIO','Pizarra provisional','ARS','TN','100','json')
        b={**a,'fecha':'2026-10-01','periodo_ym':'2026-10','price':'120','observation_id':r.identity([a['series_id'],'2026-10-01'])}
        rows=r.csv_read(r.bundle(enrich([a,b]),'board'))
        october=next(x for x in rows if x['row_kind']=='mensual' and x['periodo_ym']=='2026-10')
        self.assertEqual(october['variacion_mensual_pct'],'')

    def test_revision_replaces_whole_period_including_removed_position(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'normalized/commodities/board';path.mkdir(parents=True)
            old=enrich(r.parse(board(),'board',DAY),'c1','2026-10-08T10:00:00Z')
            new=enrich(old[:5],'c2','2026-10-09T10:00:00Z')
            (path/'c1.json').write_bytes(r.encoded(old));(path/'c2.json').write_bytes(r.encoded(new))
            result=r.analytical('board',root)
            self.assertEqual(len(result),5);self.assertEqual({x['capture_id'] for x in result},{'c2'})

    def test_persistent_published_memory_other_dates_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'dashboard/commodities/board.csv'
            old=enrich(r.parse(board(),'board',DAY))
            r.atomic(out,r.bundle(old,'board'))
            new=[{**x,'fecha':'2026-10-08','observation_id':r.identity([x['series_id'],'2026-10-08'])} for x in old]
            path=root/'normalized/commodities/board';path.mkdir(parents=True)
            (path/'new.json').write_bytes(r.encoded(new))
            self.assertEqual(len(r.analytical('board',root)),60)

    def test_error_preserves_last_valid_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'dashboard/commodities/board.csv'
            prior=r.bundle(enrich(r.parse(board(),'board',DAY)),'board');r.atomic(out,prior)
            with patch.object(r,'fetch',side_effect=r.Error('HTTP error')),self.assertRaises(r.Error):
                r.run('board',root,DAY,DAY.isoformat(),True)
            self.assertEqual(out.read_bytes(),prior)
            invalid=root/'raw/commodities/board/c1';invalid.mkdir(parents=True)
            (invalid/'response.json').write_bytes(b'bad');(invalid/'manifest.json').write_bytes(b'{}')
            with self.assertRaises(r.Error):r.run('board',root,DAY,DAY.isoformat())
            self.assertEqual(out.read_bytes(),prior)

    def test_real_fetch_boundary_http_error_and_size_limit(self):
        from urllib.error import HTTPError
        from email.message import Message
        class Response:
            status=200
            headers=Message()
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return b'x'*(r.MAX_BYTES+1)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(r,'build_opener') as opener:
                opener.return_value.open.side_effect=HTTPError(r.SOURCES['fob'],503,'error',{},None)
                with self.assertRaises(r.Error):r.fetch('fob',DAY.isoformat(),DAY,root)
                opener.return_value.open.side_effect=None
                opener.return_value.open.return_value=Response()
                with self.assertRaises(r.Error):r.fetch('fob',DAY.isoformat(),DAY,root)
            self.assertFalse((root/'raw').exists())

    def test_json_under_html_content_type_stored_immutably_and_replayable(self):
        from email.message import Message
        class Response:
            status=200
            headers=Message()
            headers['Content-Type']='text/html; charset=utf-8'
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return r.encoded(fob())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(r,'build_opener') as opener:
                opener.return_value.open.return_value=Response()
                first=r.fetch('fob',DAY.isoformat(),DAY,root)
                second=r.fetch('fob',DAY.isoformat(),DAY,root)
            self.assertNotEqual(first,second)
            before=(first/'response.json').read_bytes()
            a=r.normalize(first,root,DAY);b=r.normalize(first,root,DAY)
            self.assertEqual(a,b)
            self.assertEqual((first/'response.json').read_bytes(),before)
            self.assertEqual(json.loads((first/'manifest.json').read_bytes())['content_type'],'text/html; charset=utf-8')

    def test_bundle_schema_count_price_trace_integrity(self):
        valid=r.bundle(enrich(r.parse(board(),'board',DAY)),'board')
        for bad in [b'',valid.replace(b'magyp-references-v1',b'unknown'),valid.replace(b'a'*64,b'BADHASH')]:
            with self.subTest(),self.assertRaises(r.Error):r.validate_bundle(bad,'board')

    def test_atomic_replace_failure_preserves_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'file.csv';path.write_bytes(b'valid')
            with patch.object(r.os,'replace',side_effect=OSError('failure')),self.assertRaises(OSError):r.atomic(path,b'new')
            self.assertEqual(path.read_bytes(),b'valid')
            self.assertEqual(list(Path(temp).glob('.stage-*')),[])

    def test_dry_run_no_network_writes(self):
        with patch('sys.argv',['references','--date','2026-10-08','--dry-run','--allow-web']),patch.object(r,'run') as run:
            self.assertEqual(r.main(),0);run.assert_not_called()


if __name__=='__main__':unittest.main()
