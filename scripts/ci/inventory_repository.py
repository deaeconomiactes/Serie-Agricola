"""Inventory tracked files and literal references; absence of a match is not proof of non-use."""
from __future__ import annotations
import csv, hashlib, json, re, subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'reports'
TEXT = {'.py', '.js', '.cjs', '.html', '.css', '.md', '.yml', '.yaml', '.json', '.txt', '.toml', '.sh', '.ps1'}

def category(path):
    if path.startswith('.github/workflows/'): return 'workflow'
    if path.startswith('tests/'): return 'test'
    if path.startswith('docs/') or path.lower().endswith('.md'): return 'docs'
    if path.startswith('scripts/') or path.endswith('.py'): return 'script'
    if '/' not in path and path.endswith(('.js', '.html', '.css')): return 'frontend'
    return None

def classify(path):
    if path.startswith('tests/'): return 'TEST_FIXTURE', 'KEEP'
    if path.startswith('docs/') or path.lower().endswith('.md'): return 'DOCUMENTATION', 'KEEP'
    if path == '.github/workflows/magyp-mcba-pilot.yml': return 'MANUAL_DIAGNOSTIC', 'KEEP'
    if path.startswith('.github/workflows/'): return 'PRODUCTIVE_RUNTIME', 'KEEP'
    if path.startswith(('data/magyp/dashboard/mcba/', 'data/mercado_central/dashboard/')): return 'BUILD_INPUT', 'KEEP'
    if path.startswith(('data/mayoristas/dashboard/', 'data/carnes/dashboard/', 'data/magyp/dashboard/commodities/', 'data/commodities_sio/dashboard/')): return 'PRODUCTIVE_RUNTIME', 'KEEP'
    if path.startswith('data/'):
        if '/dashboard/' in path: return 'REVIEW_REQUIRED', 'REVIEW_REQUIRED'
        if '/reports/' in path or '/audit/' in path: return 'AUDIT_EVIDENCE', 'KEEP'
        return 'REVIEW_REQUIRED', 'REVIEW_REQUIRED'
    if path in {'PRECIOS_MAYORISTAS_INTEGRADO.csv', 'REGISTRO 2025.csv.enc'}: return 'BUILD_INPUT', 'KEEP'
    if path == 'PRECIOS_MAYORISTAS_2026_INTEGRADO.csv': return 'HISTORICAL_FALLBACK', 'REVIEW_REQUIRED'
    if path == 'REGISTRO 2025 INTEGRADO.csv' or ('/' not in path and path.endswith(('.js','.css','.html'))): return 'PRODUCTIVE_RUNTIME', 'KEEP'
    if path.startswith('scripts/') or path.endswith('.py'): return 'REVIEW_REQUIRED', 'REVIEW_REQUIRED'
    return 'REVIEW_REQUIRED', 'REVIEW_REQUIRED'

def main():
    paths = subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode('utf-8').split('\0')[:-1]
    names = Counter(Path(p).name for p in paths)
    terms = defaultdict(set)
    for path in paths:
        terms[path].add(path)
        if names[Path(path).name] == 1 and len(Path(path).name) >= 6:
            terms[Path(path).name].add(path)
    pattern = re.compile('|'.join(re.escape(k) for k in sorted(terms, key=len, reverse=True)))
    refs = defaultdict(lambda: defaultdict(set))
    for src in paths:
        kind = category(src)
        file = ROOT / src
        if not kind or src.startswith('docs/reports/REPO_') or file.suffix.lower() not in TEXT or not file.is_file() or file.stat().st_size > 2_000_000: continue
        text = file.read_text(encoding='utf-8-sig', errors='replace').replace('\\', '/')
        for hit in set(pattern.findall(text)):
            for target in terms[hit]:
                if target != src: refs[target][kind].add(src)
    hashes = defaultdict(list); rows = []
    for path in paths:
        file=ROOT/path
        if not file.is_file(): continue
        size=file.stat().st_size
        # Generated reports cannot hash themselves without a circular dependency.
        generated = path in {'docs/reports/REPO_INVENTORY.csv', 'docs/reports/REPO_DUPLICATES.json', 'docs/reports/REPO_LARGEST_50.json'}
        digest = 'GENERATED_REPORT' if generated else hashlib.sha256(file.read_bytes()).hexdigest()
        if not generated: hashes[digest].append(path)
        classification, action=classify(path)
        row={'path':path,'bytes':size,'extension':''.join(file.suffixes), 'top_level_area':path.split('/')[0] if '/' in path else '(root)', 'git_tracked':True,
             'references_count':len(set().union(*refs[path].values())) if refs[path] else 0}
        for kind in ('workflow','frontend','script','test','docs'): row['referenced_by_'+kind]=' | '.join(sorted(refs[path][kind]))
        row.update(classification=classification,proposed_action=action,sha256=digest);rows.append(row)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'REPO_INVENTORY.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    duplicates=[{'sha256':sha,'bytes':(ROOT/paths_[0]).stat().st_size,'paths':paths_, 'consumers':{p:{k:sorted(v) for k,v in refs[p].items() if v} for p in paths_},'canonical':'REVIEW_REQUIRED','action':'REVIEW_REQUIRED'} for sha,paths_ in hashes.items() if len(paths_)>1]
    for group in duplicates:
        paths_ = group['paths']
        if all('/.gitkeep' in p or p.endswith('/__init__.py') for p in paths_):
            group.update(canonical='Cada ruta cumple una función distinta', action='KEEP', reason='Marcadores de directorio o paquete; conservar.')
        elif any(p.startswith('tests/carnes/fixtures/') for p in paths_):
            group.update(canonical='data/carnes/dashboard/', action='KEEP', reason='Fixture reproducible independiente de la publicación corriente.')
        elif all(p.startswith('data/mayoristas/dashboard/') for p in paths_):
            group.update(canonical='Cada descriptor del índice', action='KEEP', reason='Rutas de vistas distintas referenciadas por el índice; bytes iguales no permiten retirar una ruta.')
        elif 'PRECIOS_MAYORISTAS_INTEGRADO.csv' in paths_:
            group.update(canonical='PRECIOS_MAYORISTAS_INTEGRADO.csv', action='REVIEW_REQUIRED', reason='La copia legacy tiene consumidores y referencias; no se ha probado su retiro seguro.')
        else:
            group.update(reason='Evidencia o salidas con rutas distintas; consumidores y significado requieren revisión.')
    (OUT/'REPO_DUPLICATES.json').write_text(json.dumps(duplicates,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    largest=[dict(r) for r in sorted(rows,key=lambda r:(-r['bytes'],r['path']))[:50]]
    for row in largest:
        if row['classification']=='AUDIT_EVIDENCE': row['classification']='AUDIT_ONLY'
        elif row['classification'] not in {'PRODUCTIVE_RUNTIME','BUILD_INPUT','HISTORICAL_FALLBACK','TEST_FIXTURE','AUDIT_ONLY'}: row['classification']='REVIEW_REQUIRED'
    (OUT/'REPO_LARGEST_50.json').write_text(json.dumps(largest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(rows)} files, {sum(r["bytes"] for r in rows)} bytes, {len(duplicates)} duplicate groups')

if __name__=='__main__': main()
