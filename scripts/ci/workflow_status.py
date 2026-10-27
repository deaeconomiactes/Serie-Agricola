"""Operational publication decisions and concise summaries; no economic calculations."""
import argparse,csv,json,os,subprocess
from pathlib import Path

VOLATILE={'attempted_at','last_attempt','requested_date','checked_at','attempt_time','duration_seconds','diagnostic_note'}
STATES={'UPDATED','NO_OP_ALREADY_CURRENT','NO_PUBLICATION','SOURCE_UNAVAILABLE','PIPELINE_ERROR'}
def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in VOLATILE}
    if isinstance(value,list):return [stable(v) for v in value]
    return value
def requires_deploy(path,before,after):
    # Audit reports and acquisition indexes are not browser payloads.
    if '/reports/' in path and not path.endswith('/PRICE_FRESHNESS_STATUS.json'):return False
    if path.endswith('/SOURCE_INDEX.json'):return False
    if path.endswith('.json'):
        try:return stable(json.loads(before or b'{}'))!=stable(json.loads(after or b'{}'))
        except (ValueError,UnicodeError):return before!=after
    return before!=after
def git(*args):return subprocess.check_output(['git',*args])
def plan():
    paths=[p for p in git('diff','--cached','--name-only','-z').decode().split('\0') if p]
    deploy=False
    for path in paths:
        before=subprocess.run(['git','show','HEAD:'+path],capture_output=True).stdout
        after=git('show',':'+path)
        deploy=requires_deploy(path,before,after) or deploy
    outputs={'changed':str(bool(paths)).lower(),'deploy_required':str(deploy).lower()}
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
            for key,value in outputs.items():stream.write(f'{key}={value}\n')
    return outputs
def summary(source,status,requested,last,changed,deploy):
    result=dict(FINAL_STATUS=status,SOURCE=source,REQUESTED_DATE=requested or 'not_requested',LAST_OBSERVATION=last or 'not_reported',OUTPUT_CHANGED=changed,DEPLOY_REQUIRED=deploy)
    text='\n'.join(f'{k}={v}' for k,v in result.items());print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:stream.write('```text\n'+text+'\n```\n')
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True);sub.add_parser('plan')
    p=sub.add_parser('summary');p.add_argument('--source',required=True);p.add_argument('--status-file',type=Path);p.add_argument('--status');p.add_argument('--requested');p.add_argument('--last');p.add_argument('--last-csv',type=Path);p.add_argument('--changed',choices=['true','false'],default='false');p.add_argument('--deploy',choices=['true','false'],default='false')
    args=parser.parse_args()
    if args.mode=='plan':print(json.dumps(plan()))
    else:
        state=json.loads(args.status_file.read_text(encoding='utf-8')) if args.status_file and args.status_file.exists() else {}
        state=state.get('run_status',state)
        if args.last_csv and args.last_csv.exists():
            with args.last_csv.open(encoding='utf-8-sig',newline='') as stream:args.last=next(csv.DictReader(stream),{}).get('date_max')
        status=args.status or state.get('result') or state.get('status') or 'PIPELINE_ERROR'
        summary(args.source,status,args.requested or state.get('requested_date'),args.last or state.get('last_observation_date'),args.changed,args.deploy)
