import json
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from test_mcba import row, export, normalized, DAY
from test_phase2 import current
from scripts.magyp.common.platform import PipelineError, RawManifest, sha256
from scripts.magyp.mcba.acquisition import AcquisitionResult, browser_fetch
from scripts.magyp.mcba.fetch_mcba import capture
from scripts.magyp.mcba.model import (PARSER_VERSION,SCHEMA_VERSION,ENDPOINT,normalize,
                                    parse_export,build_analytical,dashboard_rows,validate_canonical)
from scripts.magyp.mcba.validate_acquisition_mcba import attempt
from scripts.magyp.mcba.validate_readiness_mcba import (plan_month,coverage,duplicate_groups,
    audit_current,aggregate_observed,matches,matching_metrics)


def fixture_capture(start,end,records):
    body=export(records)
    manifest=RawManifest('mcba','market_price_observation',ENDPOINT,'GET',{'date_from':start,'date_to':end},
        '2026-10-06T14:00:00Z',200,None,None,len(body),sha256(body),SCHEMA_VERSION,PARSER_VERSION,
        len(records),'validated','capture-'+start,'browser_automation','ARS','kg',currency_evidence='documented')
    return body,manifest


class Phase3Tests(unittest.TestCase):
    def test_chromium_uses_bundled_engine_no_edge_and_timeout_cleanup(self):
        fake=MagicMock()
        browser=fake.return_value.__enter__.return_value.chromium.launch.return_value
        probe,context=MagicMock(),MagicMock()
        probe.new_page.return_value.evaluate.return_value='HeadlessChrome'
        browser.new_context.side_effect=[probe,context]
        context.new_page.return_value.goto.side_effect=TimeoutError('private-session-url')
        with patch.dict(sys.modules,{'playwright':MagicMock(),
               'playwright.sync_api':SimpleNamespace(sync_playwright=fake)}):
            with self.assertRaises(PipelineError) as error:
                browser_fetch(DAY,DAY,timeout=5,channel='chromium')
        fake.return_value.__enter__.return_value.chromium.launch.assert_called_once_with(headless=True)
        self.assertEqual(error.exception.diagnostics['stage'],'initial_get')
        self.assertNotIn('private-session-url',str(error.exception))
        context.close.assert_called_once();browser.close.assert_called_once()
        context.new_page.return_value.set_default_timeout.assert_called_once_with(5000)

    def test_ci_config_is_manual_readonly_one_capture_and_no_raw_artifact(self):
        text=(Path(__file__).resolve().parents[2]/'.github/workflows/magyp-mcba-pilot.yml').read_text()
        self.assertIn('workflow_dispatch:',text);self.assertNotIn('schedule:',text)
        self.assertNotIn('contents: write',text);self.assertNotIn('git commit',text)
        self.assertIn('install --with-deps chromium',text)
        self.assertEqual(text.count('validate_acquisition_mcba.py'),1)
        artifact=text.split('path: |')[-1]
        self.assertNotIn('/raw',artifact);self.assertNotIn('**/*',artifact)
        self.assertIn("default: false",text)

    def test_failed_capture_records_attempt_preserves_raw_and_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dash=root/'dashboard/mcba/last.csv';dash.parent.mkdir(parents=True);dash.write_bytes(b'valid')
            error=PipelineError('TimeoutError');error.diagnostics={'stage':'initial_get','requests':[]}
            fetch=MagicMock(side_effect=error)
            with patch('scripts.magyp.mcba.validate_acquisition_mcba.version',return_value='1.58.0'):
                result=attempt(DAY,DAY,root,'clean_smoke',fetcher=fetch)
            self.assertEqual(result['error_category'],'timeout');self.assertFalse(result['xlsx_valid'])
            self.assertEqual(dash.read_bytes(),b'valid');self.assertFalse((root/'raw').exists())
            fetch.assert_called_once()  # Nunca retry automático.

    def test_retry_requires_explicit_flag_and_third_attempt_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fetch=MagicMock(side_effect=PipelineError('controlled failure'))
            with patch('scripts.magyp.mcba.validate_acquisition_mcba.version',return_value='1.58.0'):
                attempt(DAY,DAY,root,'clean_smoke',fetcher=fetch)
                with self.assertRaises(PipelineError):attempt(DAY,DAY,root,'clean_smoke',fetcher=fetch)
                attempt(DAY,DAY,root,'clean_smoke',fetcher=fetch,explicit_retry=True)
                with self.assertRaises(PipelineError):attempt(DAY,DAY,root,'clean_smoke',fetcher=fetch,explicit_retry=True)
            self.assertEqual(fetch.call_count,2)

    def test_new_manifest_uses_currency_separate_kg_without_rewriting_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=capture(export(),DAY,Path(tmp),'browser_export_import')
            manifest=json.loads((folder/'manifest.json').read_text())
            self.assertEqual(manifest['price_unit'],'kg');self.assertEqual(manifest['currency'],'ARS')
            self.assertEqual(manifest['currency_evidence'],'documented')

    def test_month_plan_exact_calendar_nonoverlap_bounded_windows(self):
        self.assertEqual(plan_month('2025-10'),[('2025-10-01','2025-10-07'),('2025-10-08','2025-10-14'),
            ('2025-10-15','2025-10-21'),('2025-10-22','2025-10-28'),('2025-10-29','2025-10-31')])
        self.assertEqual(len(plan_month('2024-02')),5)

    def test_multiple_windows_complete_requested_does_not_claim_calendar(self):
        attempts=[];captures={}
        for start,end in plan_month('2025-10'):
            payload,m=fixture_capture(start,end,[row(Fecha=datetime.fromisoformat(start))])
            captures[m.capture_id]=(payload,m)
            attempts.append(dict(date=start,date_to=end,purpose='month_validation',result='success',
                capture_id=m.capture_id,captured_at_utc=m.captured_at_utc))
        records,metrics,rows=coverage('2025-10',attempts,captures.__getitem__)
        self.assertEqual(metrics['days_requested'],31);self.assertEqual(metrics['days_with_data'],5)
        self.assertEqual(metrics['days_without_data'],26)
        self.assertEqual(metrics['month_coverage_status'],'complete_requested_window')
        self.assertEqual(metrics['coverage_ratio_requested'],1)
        self.assertTrue(all(r['calendar_status']=='unknown' for r in records))
        self.assertFalse(metrics['official_monthly_equivalence'])

    def test_failed_window_is_unverified_not_zero_rows(self):
        att=dict(date='2025-10-01',date_to='2025-10-07',purpose='month_validation',result='failed')
        records,metrics,_=coverage('2025-10',[att],MagicMock())
        self.assertIsNone(records[0]['rows']);self.assertEqual(metrics['days_without_data'],0)
        self.assertEqual(metrics['days_unverified'],31);self.assertEqual(metrics['month_coverage_status'],'failed')

    def test_partial_window_and_no_expectation_of_weekdays(self):
        payload,m=fixture_capture('2025-10-01','2025-10-07',[row(Fecha=datetime(2025,10,4))])
        att=dict(date='2025-10-01',date_to='2025-10-07',purpose='month_validation',result='success',
             capture_id=m.capture_id,captured_at_utc=m.captured_at_utc)
        records,metrics,_=coverage('2025-10',[att],lambda _: (payload,m))
        self.assertEqual(records[3]['rows'],1);self.assertEqual(metrics['month_coverage_status'],'partial_requested_window')

    def test_latest_valid_window_zero_day_not_filled_from_old_capture(self):
        old=fixture_capture('2025-10-01','2025-10-07',[row(Fecha=datetime(2025,10,1))])
        new=fixture_capture('2025-10-01','2025-10-07',[row(Fecha=datetime(2025,10,2))])
        new=(new[0],replace(new[1],capture_id='revised',captured_at_utc='2026-10-06T15:00:00Z'))
        captures={old[1].capture_id:old,'revised':new}
        attempts=[dict(date='2025-10-01',date_to='2025-10-07',purpose='month_validation',result='success',
           capture_id=m.capture_id,captured_at_utc=m.captured_at_utc) for _,m in (old,new)]
        records,_,_=coverage('2025-10',attempts,captures.__getitem__)
        self.assertEqual(records[0]['rows'],0);self.assertEqual(records[1]['rows'],1)

    def test_detail_pilot_export_has_no_summary_and_month_groups_stay_separate(self):
        rows=build_analytical(normalized([row(),row(Variedad='Prom.Esp.',Procedencia=None)]))
        output=dashboard_rows(rows)
        self.assertEqual(len(output['DETAIL']),1)
        self.assertTrue(all(r['observation_level']=='detail' for r in output['DETAIL']))
        self.assertEqual(len(output['MONTHLY']),2)

    def test_kg_nonzero_still_not_volume_and_no_summary_mean(self):
        rows=build_analytical(normalized([row(Kg=27),row(Variedad='Prom.Esp.',**{'Promedio x Kg.':9999})]))
        self.assertTrue(all(r['volume'] is None and r['volume_unit'] is None for r in rows))
        aggregate=aggregate_observed(rows,True)
        self.assertEqual(len(aggregate),1);self.assertEqual(aggregate[0]['price'],1500)

    def test_unknown_kg_volume_zero_is_blocked(self):
        rows=normalized();rows[0]['volume']=0
        with self.assertRaises(PipelineError):validate_canonical(rows)

    def test_aggregate_never_invents_kg_for_unknown_unit(self):
        c=dict(current(),unidad='litro')
        with self.assertRaises(PipelineError):aggregate_observed([c],False)

    def test_alias_policies_have_no_semantic_promotions(self):
        from scripts.magyp.mcba.labels import normalized_label
        rule=dict(dimension='package',source_value='Ca',canonical_value='CAJA')
        for status,expected in [('validated','CAJA'),('observed','CA'),('manual_review','CA')]:
            self.assertEqual(normalized_label('package','Ca',[dict(rule,status=status)]),expected)

    def test_duplicate_audit_keeps_provenance_and_input_unchanged(self):
        a=dict(current(),fecha='2026-08-19',_current_row=2,archivo_origen='A.zip/RF190826.XLS')
        b=dict(a,_current_row=3,archivo_origen='B.zip/A.zip/RF190826.XLS')
        self.assertEqual(len(duplicate_groups([a,b])),1)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.csv';path.write_bytes(b'original')
            result=audit_current([a,b],path,Path(tmp))
            self.assertEqual(result['excess_rows'],1);self.assertEqual(path.read_bytes(),b'original')
            self.assertEqual(result['classification'],'economic_duplicate')

    def test_duplicate_key_preserves_quality_attributes_in_observations(self):
        a=current();b=dict(a,observaciones='CAL=1A')
        self.assertEqual(duplicate_groups([a,b]),[])

    def test_month_matching_price_diff_absolute_relative_and_no_false_official_equivalence(self):
        m=aggregate_observed(build_analytical(normalized()),True)
        c=dict(current(price='1000'),fecha='2026-08-01')
        result=matches([c],m,'C_historical_monthly_formula_unverified')
        self.assertEqual(result[0]['match_status'],'probable')
        self.assertEqual(result[0]['absolute_price_difference'],500)
        self.assertEqual(result[0]['relative_price_difference'],0.5)
        self.assertEqual(matching_metrics(result)['paired_price_differences_over_0_011'],1)
        self.assertIn('unverified',result[0]['comparison_kind'])

    def test_month_aggregate_means_days_not_rows(self):
        rows=build_analytical(normalized())
        rows += [dict(rows[0],observation_id='day2',observation_date='2026-08-25',price=3000)]
        result=aggregate_observed(rows,True)
        self.assertEqual(result[0]['price'],2250);self.assertEqual(result[0]['observed_days'],2)


if __name__=='__main__': unittest.main()
