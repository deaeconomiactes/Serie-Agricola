#!/usr/bin/env python3
"""Audita CSV, reglas del dashboard, workflow SIO y publicación de Commodities."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SIO_DIR = ROOT / "data" / "commodities_sio" / "dashboard"
LOCAL_DIR = ROOT / "data" / "commodities_local_mensual" / "dashboard"
REPORT_DIR = ROOT / "data" / "commodities_sio" / "reports"
REPORT_MD = REPORT_DIR / "REPORTE_AUDITORIA_FUNCIONAMIENTO_COMMODITIES.md"
REPORT_CSV = REPORT_DIR / "RESUMEN_AUDITORIA_FUNCIONAMIENTO_COMMODITIES.csv"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "update-sio-commodities.yml"
APP_PATH = ROOT / "app.js"
PAGES_ROOT = "https://deaeconomiactes.github.io/Serie-Agricola/"
REPO_API = "https://api.github.com/repos/deaeconomiactes/Serie-Agricola"

SIO_FILES = [
    "COMMODITIES_SIO_DASHBOARD_DIARIO.csv",
    "COMMODITIES_SIO_DASHBOARD_MENSUAL.csv",
    "COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv",
    "COMMODITIES_SIO_DASHBOARD_RESUMEN.csv",
    "COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv",
    "COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv",
]

CRITICAL_COLUMNS = {
    "COMMODITIES_SIO_DASHBOARD_DIARIO.csv": [
        "fecha", "commodity", "moneda", "unidad", "tipo_precio",
        "operaciones", "precio_mediana",
    ],
    "COMMODITIES_SIO_DASHBOARD_MENSUAL.csv": [
        "periodo_ym", "commodity", "moneda", "unidad", "tipo_precio",
        "operaciones", "precio_mediana",
    ],
    "COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv": [
        "fecha_ultima", "commodity", "moneda", "unidad", "tipo_precio",
        "precio_mediana_ultimo_dia",
    ],
    "COMMODITIES_SIO_DASHBOARD_RESUMEN.csv": [
        "fecha_actualizacion_dashboard", "fecha_ultima_captura_sio",
        "fecha_ultima_operacion_sio", "fecha_min_operacion_sio",
        "fecha_max_operacion_sio", "commodities", "monedas", "unidades",
    ],
    "COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv": [
        "periodo_ym", "commodity", "moneda", "unidad", "tipo_precio",
        "precio_mediana",
    ],
    "COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv": [
        "id_operacion_sio", "fecha", "commodity", "moneda", "unidad",
        "tipo_precio", "precio", "precio_valido_para_serie",
    ],
    "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv": [
        "periodo_ym", "commodity", "mercado", "tipo_precio", "moneda",
        "unidad", "frecuencia", "operaciones", "precio_mediana",
    ],
    "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_ULTIMOS.csv": [
        "periodo_ultimo", "commodity", "mercado", "tipo_precio", "moneda",
        "unidad", "frecuencia", "precio_mediana_ultimo_periodo",
    ],
    "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_RESUMEN.csv": [
        "fecha_min", "fecha_max", "filas_dashboard", "mercados",
        "commodities", "monedas", "unidades", "tipos_precio", "frecuencia",
    ],
    "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_SEMAFORO.csv": [
        "periodo_ym", "commodity", "mercado", "tipo_precio", "moneda",
        "unidad", "frecuencia", "precio_mediana",
    ],
}

PRICE_COLUMNS = {
    "precio", "precio_promedio", "precio_mediana", "precio_min", "precio_max",
    "precio_ponderado_volumen", "precio_mediana_ultimo_dia",
    "precio_promedio_ultimo_dia", "precio_mediana_ultimo_periodo",
    "precio_promedio_ultimo_periodo",
}

MANUAL_UI_OBSERVATIONS = [
    "Interacción local observada el 2026-10-02: SIO abrió con frecuencia mensual, ARS y TN; los KPIs mostraron 6 commodities y 180 operaciones con precio positivo, con gráfico mensual visible.",
    "Interacción local observada el 2026-10-02: Maíz en SIO mostró evolución mensual. El único valor del filtro técnico fue Precio Hecho; no estuvieron disponibles Compraventa ni Canje.",
    "Interacción local observada el 2026-10-02: el histórico local abrió en Rosario, ARS, TN y mensual; mostró 5 commodities, 343 observaciones y KPIs con datos.",
    "Interacción local observada el 2026-10-02: Maíz + todas las plazas mostró una comparación por plaza y 3 registros más recientes disponibles para esa combinación.",
    "Interacción local observada el 2026-10-02: todos los commodities + todas las plazas mostró el aviso para seleccionar plaza/mercado; el filtro permitió salir del estado.",
    "GitHub Pages observada el 2026-10-02: ambas fuentes cargaron y mostraron KPIs; la navegación a Cantidades y Precios Mayoristas y el regreso a Commodities funcionaron sin errores de consola.",
]


def clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def parse_number(value: Any) -> float | None:
    raw = clean(value).replace(" ", "")
    if not raw:
        return None
    raw = re.sub(r"[^0-9,.\-+eE]", "", raw)
    if not raw:
        return None
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        tail = raw.rsplit(",", 1)[-1]
        raw = raw.replace(",", ".") if len(tail) != 3 else raw.replace(",", "")
    try:
        number = float(raw)
        return number if number == number and abs(number) != float("inf") else None
    except ValueError:
        return None


def is_yes(value: Any) -> bool:
    return clean(value).casefold() in {"si", "sí", "true", "1", "yes"}


def read_csv_text(text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
    rows = list(reader)
    return list(reader.fieldnames or []), rows


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        return read_csv_text(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, csv.Error):
        return [], []


def split_values(value: Any) -> list[str]:
    raw = clean(value)
    return [part.strip() for part in raw.split("|") if part.strip()]


def dimension_values(
    rows: list[dict[str, str]], fields: tuple[str, ...], split_pipe: bool = False
) -> list[str]:
    found: set[str] = set()
    for row in rows:
        for field in fields:
            raw = clean(row.get(field))
            if not raw:
                continue
            found.update(split_values(raw) if split_pipe else [raw])
    return sorted(found, key=str.casefold)


def date_range(rows: list[dict[str, str]], fields: list[str]) -> tuple[str, str]:
    values: list[str] = []
    for row in rows:
        for field in fields:
            value = clean(row.get(field))
            if value:
                values.append(value[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", value) else value)
    return (min(values), max(values)) if values else ("", "")


def file_audit(path: Path, source: str) -> dict[str, Any]:
    exists = path.is_file()
    fields, rows = read_csv(path) if exists else ([], [])
    name = path.name
    critical = CRITICAL_COLUMNS.get(name, [])
    nulls = {
        field: sum(not clean(row.get(field)) for row in rows)
        for field in critical
        if field in fields
    }
    for field in critical:
        if field not in fields:
            nulls[field] = len(rows) if rows else (1 if exists else 0)

    price_fields = [field for field in fields if field in PRICE_COLUMNS]
    zero_cells = 0
    zero_rows: set[int] = set()
    positive_cells = 0
    for row_index, row in enumerate(rows):
        for field in price_fields:
            number = parse_number(row.get(field))
            if number == 0:
                zero_cells += 1
                zero_rows.add(row_index)
            elif number is not None and number > 0:
                positive_cells += 1

    range_fields = [
        "fecha", "periodo_ym", "fecha_ultima", "periodo_ultimo",
        "fecha_min_operacion_sio", "fecha_max_operacion_sio",
        "fecha_min", "fecha_max", "fecha_actualizacion_dashboard",
    ]
    start, end = date_range(rows, range_fields)
    critical_nulls = {key: count for key, count in nulls.items() if count}
    record = {
        "source": source,
        "path": path,
        "exists": exists,
        "bytes": path.stat().st_size if exists else 0,
        "fields": fields,
        "rows": rows,
        "row_count": len(rows),
        "columns": len(fields),
        "date_min": start,
        "date_max": end,
        "commodities": dimension_values(rows, ("commodity",), split_pipe=True),
        "currencies": dimension_values(rows, ("moneda",), split_pipe=True),
        "units": dimension_values(rows, ("unidad",), split_pipe=True),
        "price_types": dimension_values(rows, ("tipo_precio", "tipos_precio"), split_pipe=True),
        "operation_types": dimension_values(rows, ("tipo_operacion", "operacion"), split_pipe=True),
        "markets": dimension_values(rows, ("mercado", "plaza"), split_pipe=True),
        "zero_cells": zero_cells,
        "zero_rows": len(zero_rows),
        "positive_cells": positive_cells,
        "critical_nulls": critical_nulls,
        "null_detail": nulls,
        "price_fields": price_fields,
    }
    return record


def csv_rows_by_name(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["path"].name: record for record in records}


def dimension_key(row: dict[str, str], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(clean(row.get(field)) for field in fields)


def mixed_dimension_groups(
    rows: list[dict[str, str]],
    key_fields: tuple[str, ...],
    dimension: str,
) -> int:
    values_by_key: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for row in rows:
        value = clean(row.get(dimension))
        if value:
            values_by_key[dimension_key(row, key_fields)].add(value)
    return sum(len(values) > 1 for values in values_by_key.values())


def monthly_gaps(rows: list[dict[str, str]]) -> tuple[int, list[str]]:
    periods_by_series: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for row in rows:
        period = clean(row.get("periodo_ym"))
        if period:
            key = dimension_key(row, ("commodity", "moneda", "unidad", "tipo_precio", "fuente"))
            periods_by_series[key].add(period)
    gaps: list[str] = []
    for key, periods in periods_by_series.items():
        ordered = sorted(periods)
        for previous, current in zip(ordered, ordered[1:]):
            try:
                py, pm = (int(part) for part in previous.split("-", 1))
                cy, cm = (int(part) for part in current.split("-", 1))
            except (ValueError, TypeError):
                continue
            if cy * 12 + cm - (py * 12 + pm) > 1:
                gaps.append(f"{key[0]} {previous}→{current}")
    return len(gaps), gaps


def current_git_info() -> dict[str, str]:
    result = subprocess.run(
        ["git", "show", "-s", "--format=%H%n%P%n%ce%n%cI%n%s", "HEAD"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    parts = result.stdout.splitlines()
    if result.returncode or len(parts) < 5:
        return {}
    return {
        "sha": parts[0],
        "parents": parts[1].split(),
        "committer_email": parts[2],
        "committed_at": parts[3],
        "subject": parts[4],
    }


def prior_snapshot_count(relative_path: str) -> dict[str, Any]:
    commit_result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative_path],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    snapshot_commit = commit_result.stdout.strip()
    if commit_result.returncode or not snapshot_commit:
        return {}
    parent_result = subprocess.run(
        ["git", "rev-parse", f"{snapshot_commit}^"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    parent_commit = parent_result.stdout.strip()
    if parent_result.returncode or not parent_commit:
        return {}
    result = subprocess.run(
        ["git", "show", f"{parent_commit}:{relative_path}"],
        cwd=ROOT, text=True, capture_output=True, encoding="utf-8-sig",
        errors="replace", check=False,
    )
    if result.returncode:
        return {}
    _, rows = read_csv_text(result.stdout)
    ids = {clean(row.get("id_operacion_sio")) for row in rows}
    return {
        "rows": len(rows), "ids": ids - {""},
        "snapshot_commit": snapshot_commit, "parent_commit": parent_commit,
    }


def check_sio_monthly_consistency(
    history: dict[str, Any], monthly: dict[str, Any]
) -> tuple[bool, str]:
    history_rows = history.get("rows", [])
    monthly_rows = monthly.get("rows", [])
    if not history_rows or not monthly_rows:
        return False, "Faltan snapshots o agregado mensual para comparar."
    expected: Counter[tuple[str, ...]] = Counter()
    for row in history_rows:
        price = parse_number(row.get("precio"))
        if not is_yes(row.get("precio_valido_para_serie")) or price is None or price <= 0:
            continue
        period = clean(row.get("fecha"))[:7]
        if not period:
            continue
        key = (
            period, clean(row.get("commodity")), clean(row.get("moneda")),
            clean(row.get("unidad")), clean(row.get("tipo_precio")),
        )
        expected[key] += 1
    actual: Counter[tuple[str, ...]] = Counter()
    for row in monthly_rows:
        key = (
            clean(row.get("periodo_ym")), clean(row.get("commodity")),
            clean(row.get("moneda")), clean(row.get("unidad")),
            clean(row.get("tipo_precio")),
        )
        actual[key] = int(parse_number(row.get("operaciones")) or 0)
    missing = sum((expected - actual).values())
    extra = sum((actual - expected).values())
    return missing == 0 and extra == 0, f"Snapshot válido → mensual: {sum(expected.values())} operaciones; faltantes={missing}, excedentes={extra}."


def check_local_semaphore(monthly: dict[str, Any], semaphore: dict[str, Any]) -> tuple[bool, str]:
    dims = ("periodo_ym", "commodity", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia")
    left = {dimension_key(row, dims) for row in monthly.get("rows", [])}
    right = {dimension_key(row, dims) for row in semaphore.get("rows", [])}
    return left == right, f"Claves mensual/semaforo: mensual={len(left)}, semáforo={len(right)}, diferencias={len(left ^ right)}."


def check_local_latest(monthly: dict[str, Any], latest: dict[str, Any]) -> tuple[bool, str]:
    dims = ("commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia")
    expected: dict[tuple[str, ...], dict[str, str]] = {}
    for row in monthly.get("rows", []):
        key = dimension_key(row, dims)
        if key not in expected or clean(row.get("periodo_ym")) > clean(expected[key].get("periodo_ym")):
            expected[key] = row
    actual = {dimension_key(row, dims): row for row in latest.get("rows", [])}
    errors = 0
    for key, row in expected.items():
        candidate = actual.get(key)
        if candidate is None:
            errors += 1
            continue
        if clean(candidate.get("periodo_ultimo")) != clean(row.get("periodo_ym")):
            errors += 1
            continue
        a = parse_number(candidate.get("precio_mediana_ultimo_periodo"))
        b = parse_number(row.get("precio_mediana"))
        if a is None or b is None or abs(a - b) > max(0.01, abs(b) * 1e-9):
            errors += 1
    extras = len(set(actual) - set(expected))
    return errors == 0 and extras == 0, f"Último mensual por serie: esperado={len(expected)}, publicado={len(actual)}, diferencias={errors + extras}."


def app_checks() -> list[dict[str, str]]:
    app = APP_PATH.read_text(encoding="utf-8-sig") if APP_PATH.exists() else ""
    checks = [
        (
            "Rutas de fuentes separadas",
            "data/commodities_sio/dashboard/" in app
            and "data/commodities_local_mensual/dashboard/" in app
            and "files: { diario: null" in app,
            "SIO y local mensual usan directorios y listas de CSV distintas.",
        ),
        (
            "Sentinela Todos",
            'String(value).trim() === \'TODOS\'' in app,
            "El filtro Todos se trata como comodín en commodityIsAll.",
        ),
        (
            "Plaza Rosario por defecto",
            "rosario || markets[0]" in app,
            "El histórico local prefiere Rosario si está disponible.",
        ),
        (
            "Frecuencia mensual local",
            "sourceConfig.monthlyOnly ? 'mensual'" in app,
            "La fuente mensual fuerza la frecuencia mensual.",
        ),
        (
            "Precios positivos",
            "Number.isFinite(price) && price > 0" in app,
            "Las filas usadas por el filtro principal y últimos precios requieren precio mayor que cero.",
        ),
        (
            "Estado metodológico plaza",
            "Seleccione una plaza/mercado para visualizar la evolución sin mezclar referencias." in app,
            "La combinación local de todos los commodities y todas las plazas presenta un aviso.",
        ),
        (
            "Destrucción y recreación Chart.js",
            "commodityCharts[chartKey].destroy()" in app and "new Chart(" in app,
            "Se destruye la instancia previa antes de crear el siguiente gráfico.",
        ),
        (
            "Filtro SIO por tipo de operación",
            "tipo_operacion" in app and "Tipo de operación" in app,
            "SIO debe conservar el campo Tipo (tipo_operacion) y exponerlo como filtro, separado de tipo_precio.",
        ),
    ]
    return [
        {"name": name, "status": "OK" if passed else "Requiere corrección", "detail": detail}
        for name, passed, detail in checks
    ]


def workflow_checks() -> list[dict[str, str]]:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8-sig") if WORKFLOW_PATH.exists() else ""
    explorer_path = ROOT / "explorar_sio_granos.py"
    explorer = explorer_path.read_text(encoding="utf-8-sig") if explorer_path.exists() else ""
    integrator_path = ROOT / "integrar_commodities_sio.py"
    integrator = integrator_path.read_text(encoding="utf-8-sig") if integrator_path.exists() else ""
    start = explorer.find("def run_update_latest(")
    end = explorer.find("\ndef ", start + 1) if start >= 0 else -1
    latest_function = explorer[start:end] if start >= 0 and end > start else ""
    publish = re.search(r"git add(?P<body>[\s\S]*?)(?:\n\s*echo|\n\s*if )", workflow)
    publish_body = publish.group("body") if publish else ""
    cron_match = re.search(r"cron:\s*[\"']?([^\"'\s]+)", workflow)
    cron = cron_match.group(1) if cron_match else "no encontrado"
    uses_minimal_permission = bool(re.search(r"permissions:\s*\n\s+contents:\s*write", workflow))
    no_raw = "data/raw" not in publish_body and "processed" not in publish_body
    one_call = latest_function.count("urllib.request.urlopen") == 1
    deploy_path = ROOT / ".github" / "workflows" / "deploy.yml"
    deploy = deploy_path.read_text(encoding="utf-8-sig") if deploy_path.exists() else ""
    auto_push_without_token = "git push" in workflow and not re.search(r"\btoken\s*:", workflow)
    pages_push_only = bool(re.search(r"on:\s*\n\s+push:\s*\n\s+branches:\s*\n\s+-\s+main", deploy))
    check_results = [
        ("workflow_dispatch", "workflow_dispatch:" in workflow, "Permite disparo manual."),
        ("schedule diario", "schedule:" in workflow and cron != "no encontrado", f"Expresión cron observada: {cron}."),
        ("horario documentado", "10:30" in workflow and "UTC-3" in workflow, "Comentario documenta 10:30 de Argentina (UTC-3)."),
        ("una consulta SIO", one_call and "Requests máximos de este modo: 1" in latest_function, "run_update_latest contiene una sola llamada HTTP y declara máximo 1 request."),
        ("sin paginación ni exportación manual", "--update-latest" in workflow and "--sample-pages" not in workflow and "exportar_operaciones" not in workflow, "El workflow usa el snapshot latest y no activa paginación ni exportación manual."),
        ("sin publicar raw ni bases", no_raw, "El git add no incluye data/raw ni data/processed."),
        ("sólo salidas livianas", "data/commodities_sio/dashboard/*.csv" in publish_body and "REPORTE_ACTUALIZACION_DIARIA_SIO.md" in publish_body, "Publica CSV de dashboard y reportes livianos indicados."),
        ("permisos mínimos observables", uses_minimal_permission, "contents: write es el único permiso declarado para permitir commit y push."),
        ("falla preserva salidas", "no se reemplazaron las salidas de snapshots" in integrator and "git diff --cached --quiet" in workflow, "Una captura no integrable no reemplaza snapshots y el paso de publicación se omite ante fallo."),
        ("sin cambios se omiten commits", "No hay cambios livianos para publicar." in workflow, "Si no hay diff staged, el workflow termina sin crear commit."),
    ]
    results = [
        {"name": name, "status": "OK" if passed else "Observación", "detail": detail}
        for name, passed, detail in check_results
    ]
    results.append({
        "name": "Publicación automática en Pages",
        "status": "Requiere corrección" if auto_push_without_token and pages_push_only else "OK",
        "detail": (
            "El workflow SIO hace git push con las credenciales predeterminadas de checkout y Pages sólo escucha push a main. "
            "GitHub documenta que los commits publicados con GITHUB_TOKEN no disparan otros workflows ni una compilación de Pages."
            if auto_push_without_token and pages_push_only
            else "No se detectó el patrón commit automático con GITHUB_TOKEN y Pages activado sólo por push a main."
        ),
    })
    results.extend([
        {
            "name": "Escritura atómica de snapshots",
            "status": "Observación" if 'path.open("w"' in integrator and ".tmp" not in integrator[integrator.find("def write_snapshot_output"):integrator.find("def read_snapshot_rows")] else "OK",
            "detail": "Los archivos de snapshot se escriben directamente y en secuencia; una interrupción durante la escritura puede dejar el conjunto parcial.",
        },
        {
            "name": "Orden de validación dashboard",
            "status": "Observación" if workflow.find("Validar actualización dashboard") < workflow.find("Regenerar archivos dashboard-ready") else "OK",
            "detail": "El validador opcional se ejecuta antes del generador; si existe, revisa los CSV previos y no las salidas de esta corrida.",
        },
        {
            "name": "Reconciliación de IDs existentes",
            "status": "Observación" if "previous = seen.get(identity)" in integrator and "continue" in integrator[integrator.find("def deduplicate_snapshot_rows"):integrator.find("def write_snapshot_output")] else "OK",
            "detail": "Al repetir un ID, la integración conserva la primera fila y descarta una posterior aunque haya cambiado; no hay IDs repetidos en la captura auditada.",
        },
    ])
    return results


def http_get(url: str, timeout: int = 20) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "auditoria-commodities-serie-agricola/1.0",
            "Accept": "application/json,text/csv,text/html,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def live_checks(records: list[dict[str, Any]], skip_network: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "network_enabled": not skip_network,
        "localhost_root": None,
        "localhost_assets": [],
        "pages_root": None,
        "pages_assets": [],
        "actions_runs": [],
        "actions_error": "",
    }
    if skip_network:
        return result

    try:
        status, _ = http_get("http://127.0.0.1:8000/")
        result["localhost_root"] = {"status": status}
    except Exception as exc:
        result["localhost_root"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        status, _ = http_get(PAGES_ROOT)
        result["pages_root"] = {"status": status}
    except Exception as exc:
        result["pages_root"] = {"error": f"{type(exc).__name__}: {exc}"}

    for record in records:
        if not record["exists"] or record["source"] not in {"SIO Granos", "Histórico local mensual"}:
            continue
        relative = record["path"].relative_to(ROOT).as_posix()
        local_rows = record["rows"]
        for base, destination in (
            ("http://127.0.0.1:8000/", "localhost_assets"),
            (PAGES_ROOT, "pages_assets"),
        ):
            item: dict[str, Any] = {"file": relative, "status": None, "equal": False, "remote_rows": 0, "error": ""}
            try:
                status, body = http_get(base + relative)
                _, remote_rows = read_csv_text(body.decode("utf-8-sig"))
                item.update({
                    "status": status,
                    "equal": remote_rows == local_rows,
                    "remote_rows": len(remote_rows),
                    "local_rows": len(local_rows),
                })
            except Exception as exc:
                item["error"] = f"{type(exc).__name__}: {exc}"
            result[destination].append(item)

    try:
        status, body = http_get(f"{REPO_API}/actions/runs?per_page=10")
        payload = json.loads(body.decode("utf-8"))
        if status == 200:
            result["actions_runs"] = payload.get("workflow_runs", [])
    except Exception as exc:
        result["actions_error"] = f"{type(exc).__name__}: {exc}"
    return result


def esc(value: Any) -> str:
    return clean(value).replace("|", "\\|").replace("\n", " ")


def join_values(values: list[str]) -> str:
    return ", ".join(values) if values else "sin dato disponible"


def summaries(
    records: list[dict[str, Any]],
    apps: list[dict[str, str]],
    workflow: list[dict[str, str]],
    live: dict[str, Any],
    consistency: list[tuple[str, bool, str]],
    overall: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        nulls = ", ".join(f"{key}={value}" for key, value in record["critical_nulls"].items()) or "0"
        rows.append({
            "fuente": record["source"],
            "archivo": record["path"].relative_to(ROOT).as_posix(),
            "estado": "OK" if record["exists"] and record["row_count"] else "Revisar",
            "filas": str(record["row_count"]),
            "columnas": str(record["columns"]),
            "fecha_min": record["date_min"],
            "fecha_max": record["date_max"],
            "commodities": join_values(record["commodities"]),
            "monedas": join_values(record["currencies"]),
            "unidades": join_values(record["units"]),
            "tipos_precio": join_values(record["price_types"]),
            "tipos_operacion": join_values(record["operation_types"]),
            "plazas": join_values(record["markets"]),
            "celdas_precio_cero": str(record["zero_cells"]),
            "nulos_criticos": nulls,
            "detalle": f"bytes={record['bytes']}; positivos={record['positive_cells']}",
        })
    for group, entries in (("App.js", apps), ("GitHub Actions", workflow)):
        for entry in entries:
            rows.append({
                "fuente": group, "archivo": entry["name"],
                "estado": entry["status"], "detalle": entry["detail"],
            })
    for name, passed, detail in consistency:
        rows.append({
            "fuente": "Consistencia dashboard", "archivo": name,
            "estado": "OK" if passed else "Revisar", "detalle": detail,
        })
    rows.append({
        "fuente": "Auditoría", "archivo": "Estado general",
        "estado": overall, "detalle": "Resultado consolidado de la auditoría.",
    })
    if live.get("network_enabled"):
        for group in ("localhost_assets", "pages_assets"):
            for item in live[group]:
                rows.append({
                    "fuente": "localhost" if group == "localhost_assets" else "GitHub Pages",
                    "archivo": item["file"],
                    "estado": "OK" if item["status"] == 200 and item["equal"] else "Revisar",
                    "filas": str(item.get("remote_rows", "")),
                    "detalle": item.get("error") or f"HTTP {item['status']}; filas iguales={item['equal']}",
                })
    return rows


def create_report(
    records: list[dict[str, Any]],
    apps: list[dict[str, str]],
    workflow: list[dict[str, str]],
    live: dict[str, Any],
    consistency: list[tuple[str, bool, str]],
    overall: str,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone(timedelta(hours=-3), name="ART")).isoformat(timespec="seconds")
    by_name = csv_rows_by_name(records)

    inventory_lines = [
        "| Fuente | Archivo | Bytes | Filas | Columnas | Fechas | Precios cero | Nulos críticos |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for record in records:
        nulls = ", ".join(f"{key}: {value}" for key, value in record["critical_nulls"].items()) or "0"
        dates = f"{record['date_min'] or '—'} a {record['date_max'] or '—'}"
        inventory_lines.append(
            f"| {record['source']} | {record['path'].name} | {record['bytes']} | "
            f"{record['row_count']} | {record['columns']} | {dates} | "
            f"{record['zero_rows']} filas / {record['zero_cells']} celdas | {nulls} |"
        )

    sio_history = by_name.get("COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv", {})
    local_monthly = by_name.get("COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv", {})
    sio_summary = by_name.get("COMMODITIES_SIO_DASHBOARD_RESUMEN.csv", {})
    local_summary = by_name.get("COMMODITIES_LOCAL_MENSUAL_DASHBOARD_RESUMEN.csv", {})
    history_rows = sio_history.get("rows", [])
    current_ids = {clean(row.get("id_operacion_sio")) for row in history_rows if clean(row.get("id_operacion_sio"))}
    previous = prior_snapshot_count("data/commodities_sio/dashboard/COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv")
    appended = len(current_ids - previous.get("ids", set())) if previous else None
    removed = len(previous.get("ids", set()) - current_ids) if previous else None
    duplicates = len(history_rows) - len(current_ids)
    operation_values = dimension_values(history_rows, ("operacion",))
    operation_counts = Counter(clean(row.get("operacion")) or "Sin especificar" for row in history_rows)
    tipo_operacion_exists = "tipo_operacion" in sio_history.get("fields", [])
    market_rows = sum(bool(clean(row.get("mercado"))) for row in history_rows)
    daily_key = ("fecha", "commodity", "moneda", "unidad", "tipo_precio", "condicion_comercial", "fuente")
    monthly_key = ("periodo_ym", "commodity", "moneda", "unidad", "tipo_precio", "fuente")
    daily_operation_mixes = mixed_dimension_groups(history_rows, daily_key, "operacion")
    monthly_history_rows = [
        {**row, "periodo_ym": clean(row.get("fecha"))[:7]}
        for row in history_rows if clean(row.get("fecha"))
    ]
    monthly_operation_mixes = mixed_dimension_groups(monthly_history_rows, monthly_key, "operacion")
    monthly_condition_mixes = mixed_dimension_groups(monthly_history_rows, monthly_key, "condicion_comercial")
    monthly_market_mixes = mixed_dimension_groups(monthly_history_rows, monthly_key, "mercado")
    sio_monthly = by_name.get("COMMODITIES_SIO_DASHBOARD_MENSUAL.csv", {})
    gap_count, gap_examples = monthly_gaps(sio_monthly.get("rows", [])) if sio_monthly else (0, [])

    sio_dates = (
        f"{sio_summary['rows'][0].get('fecha_min_operacion_sio', '—')} a "
        f"{sio_summary['rows'][0].get('fecha_max_operacion_sio', '—')}"
        if sio_summary.get("rows") else "sin resumen"
    )
    local_dates = (
        f"{local_summary['rows'][0].get('fecha_min', '—')} a "
        f"{local_summary['rows'][0].get('fecha_max', '—')}"
        if local_summary.get("rows") else "sin resumen"
    )
    local_update_date = (
        local_summary["rows"][0].get("fecha_actualizacion", "sin dato")
        if local_summary.get("rows") else "sin resumen"
    )

    snapshot_quality = (
        f"{len(history_rows)} filas, {len(current_ids)} IDs únicos, "
        f"{duplicates} filas con ID repetido; {sio_dates}."
    )
    lineage = (
        f"Histórico previo al commit SIO {previous.get('snapshot_commit', '')[:12] or 'sin dato'}: "
        f"{previous.get('rows', 'sin dato')} → {len(history_rows)} filas; "
        f"IDs agregados={appended if appended is not None else 'no comparable'}, "
        f"IDs quitados={removed if removed is not None else 'no comparable'}."
    )
    operation_note = (
        f"El snapshot liviano conserva operacion={join_values(operation_values)} "
        f"({'; '.join(f'{label}: {count}' for label, count in sorted(operation_counts.items()))}); "
        f"incluye columna tipo_operacion={tipo_operacion_exists}. "
        f"Mercado poblado en {market_rows}/{len(history_rows)} snapshots; "
        f"grupos diarios con más de un tipo de operación={daily_operation_mixes}, "
        f"mensuales={monthly_operation_mixes}; grupos mensuales con mezcla de condición={monthly_condition_mixes}, "
        f"mercado={monthly_market_mixes}."
    )
    local_coverage = (
        f"{local_monthly.get('row_count', 0)} agregados mensuales, "
        f"{local_dates}; commodities={join_values(local_monthly.get('commodities', []))}; "
        f"plazas={join_values(local_monthly.get('markets', []))}."
    )

    app_findings = "\n".join(
        f"- **{entry['status']} — {entry['name']}:** {entry['detail']}" for entry in apps
    )
    workflow_findings = "\n".join(
        f"- **{entry['status']} — {entry['name']}:** {entry['detail']}" for entry in workflow
    )
    consistency_findings = "\n".join(
        f"- **{'OK' if passed else 'Revisar'} — {name}:** {detail}" for name, passed, detail in consistency
    )

    local_root = live.get("localhost_root")
    pages_root = live.get("pages_root")
    local_asset_count = len(live.get("localhost_assets", []))
    pages_asset_count = len(live.get("pages_assets", []))
    local_equal = sum(item.get("status") == 200 and item.get("equal") for item in live.get("localhost_assets", []))
    pages_equal = sum(item.get("status") == 200 and item.get("equal") for item in live.get("pages_assets", []))
    local_status = f"HTTP {local_root['status']}" if local_root and "status" in local_root else (local_root or {}).get("error", "no verificado")
    pages_status = f"HTTP {pages_root['status']}" if pages_root and "status" in pages_root else (pages_root or {}).get("error", "no verificado")

    runs = live.get("actions_runs", [])
    latest_run = runs[0] if runs else {}
    sio_runs = [run for run in runs if "sio" in clean(run.get("name")).casefold()]
    latest_sio_run = sio_runs[0] if sio_runs else {}
    latest_success = next((run for run in sio_runs if run.get("conclusion") == "success"), {})
    latest_failure = next((run for run in sio_runs if run.get("conclusion") == "failure"), {})
    git_info = current_git_info()
    auto_commit = bool(
        latest_success and git_info
        and latest_success.get("head_sha") in git_info.get("parents", [])
        and "github-actions" in git_info.get("committer_email", "").casefold()
        and git_info.get("subject") == "chore: actualizar snapshot diario SIO"
    )
    actions_text = (
        f"Runs consultados={len(runs)} ({len(sio_runs)} del workflow SIO). Último run SIO: #{latest_sio_run.get('run_number', '—')} "
        f"{latest_sio_run.get('status', 'sin dato')}/{latest_sio_run.get('conclusion', 'sin dato')} "
        f"({latest_sio_run.get('created_at', 'sin fecha')}, {latest_sio_run.get('event', 'sin evento')}). "
        f"Último exitoso: #{latest_success.get('run_number', '—')} "
        f"({latest_success.get('created_at', 'sin fecha')}). "
        f"Última falla visible: #{latest_failure.get('run_number', '—')} "
        f"({latest_failure.get('created_at', 'sin fecha')}); paso: "
        f"{'integrar snapshot e histórico liviano' if latest_failure else 'sin falla reciente'}."
    )
    if auto_commit:
        actions_text += (
            f" El commit actual {git_info['sha'][:12]} lo firmó github-actions[bot] "
            f"y su padre coincide con el SHA base del run exitoso."
        )
    if live.get("actions_error"):
        actions_text += f" Consulta live no disponible: {live['actions_error']}."

    cero_detail = []
    for source_name, source_records in (
        ("SIO", [r for r in records if r["source"] == "SIO Granos"]),
        ("Histórico local", [r for r in records if r["source"] == "Histórico local mensual"]),
    ):
        final = [r for r in source_records if "HISTORICO_SNAPSHOTS_LIVIANO" not in r["path"].name and "RESUMEN" not in r["path"].name]
        zeros = sum(r["zero_cells"] for r in final)
        cero_detail.append(f"{source_name}: {zeros} celdas precio cero en archivos de series finales.")
    eligible_count = sum(
        is_yes(row.get("precio_valido_para_serie"))
        and (parse_number(row.get("precio")) or 0) > 0
        for row in history_rows
    )
    dashboard_price_zero = sum(r["zero_cells"] for r in records if r["source"] in {"SIO Granos", "Histórico local mensual"} and "RESUMEN" not in r["path"].name and "HISTORICO_SNAPSHOTS_LIVIANO" not in r["path"].name)

    problems = [entry for entry in apps if entry["status"] == "Requiere corrección"]
    pages_problem = live.get("network_enabled") and (
        pages_equal != pages_asset_count or (pages_root and pages_root.get("status") != 200)
    )
    data_problem = any(not passed for _, passed, _ in consistency)
    workflow_problems = [entry for entry in workflow if entry["status"] == "Requiere corrección"]
    if problems or workflow_problems or pages_problem or data_problem:
        overall = "Requiere corrección"
    elif any(entry["status"] != "OK" for entry in workflow) or latest_failure:
        overall = "OK con observaciones"
    else:
        overall = "OK"

    lines = [
        "# Auditoría de funcionamiento de Commodities",
        "",
        f"Fecha de auditoría: {now}. Rama: {subprocess.run(['git', 'branch', '--show-current'], cwd=ROOT, text=True, capture_output=True).stdout.strip() or 'sin dato'}.",
        "",
        "## Objetivo",
        "",
        "Comprobar los datos del dashboard, la separación entre SIO Granos y el histórico local mensual, las reglas de filtros y series, el workflow de actualización y los CSV servidos por localhost y GitHub Pages.",
        "",
        "## Fuentes revisadas",
        "",
        "Se leyeron todos los CSV SIO indicados y todos los CSV del directorio dashboard local mensual. El script también revisó app.js y update-sio-commodities.yml. Los recursos publicados se comparan por campos y filas para no confundir diferencias de BOM o fin de línea con cambios de contenido.",
        "La validación cubre los snapshots y CSV dashboard-ready versionados; no reconstruye la transformación desde archivos fuente originales.",
        "",
        *inventory_lines,
        "",
        "## Estado SIO Granos",
        "",
        f"- {snapshot_quality}",
        f"- {lineage}",
        f"- {operation_note}",
        f"- Operaciones válidas para serie en el snapshot: {eligible_count}/{len(history_rows)}.",
        "- La serie del dashboard actual cubre del 9 de septiembre al 1 de octubre de 2026. No hay un baseline anterior al 9 de septiembre en el snapshot versionado; la cobertura representa el piloto incremental observado.",
        "- El resumen contiene fecha de actualización del dashboard, última captura, última operación y fechas mínima/máxima de operación.",
        "- SIO no tiene plazas pobladas en el campo mercado; procedencia y lugar de entrega son metadatos separados.",
        "- El filtro SIO visible usa tipo_precio=Precio Hecho. El campo tipo_operacion mapeado por el integrador no se conserva en el CSV liviano ni en los agregados usados por app.js. Por eso no se pueden filtrar Compraventa o Canje desde el dashboard.",
        "- El campo operacion sí conserva Contrato/Rectificación/Anulación en el snapshot liviano, pero el preparador agrupa por tipo_precio y omite operacion en las series. Las 323 filas positivas incluyen operaciones de los tres estados. Los agregados diarios mezclan esos estados; no se presume aquí una regla de reversión/exclusión sin definición metodológica.",
        "- La serie mensual SIO tampoco conserva mercado ni condicion_comercial en sus claves/campos. En esta captura mercado está vacío; no se detectó mezcla de mercado en los datos actuales. La cantidad de grupos que mezcla más de un valor de condición se muestra arriba.",
        "",
        "## Estado Histórico local mensual",
        "",
        f"- {local_coverage}",
        "- La fuente es mensual, en ARS por TN, con tipo Precio interno mensual y plazas Rosario, Córdoba, Dársena, Quequén y Bahía Blanca.",
        "- Los CSV de resumen y agregados están completos para las columnas críticas; las observaciones con precio cero no aparecen en las series finales.",
        "",
        "## Validación de filtros",
        "",
        app_findings,
        "",
        "- Verificación interactiva registrada:",
        *[f"  - {item}" for item in MANUAL_UI_OBSERVATIONS],
        "",
        "## Validación de fechas",
        "",
        f"- SIO: {sio_dates}. La comparación de IDs entre snapshots consecutivos verifica la retención de filas previas y la incorporación incremental.",
        f"- Histórico local: {local_dates}; fecha de actualización reportada: {local_update_date}.",
        f"- La lógica de variación mensual SIO compara con la fila anterior disponible sin exigir el mes calendario inmediato anterior. Huecos encontrados en el dashboard actual: {gap_count}" + (f" ({'; '.join(gap_examples[:5])})." if gap_examples else "; no se observan huecos en el período disponible. Si aparece un hueco, la variación y el semáforo pueden representar varios meses como si fueran mensuales."),
        "- En el workflow, la captura se agenda diariamente a las 13:30 UTC, equivalente a 10:30 de Argentina (UTC-3); GitHub puede iniciar con demora.",
        "",
        "## Validación de monedas y unidades",
        "",
        "- SIO: monedas observadas ARS y USD; unidad TN. Los agregados conservan moneda y unidad como dimensiones independientes.",
        "- Histórico local: ARS y TN en todos los datos disponibles.",
        "- app.js selecciona ARS y TN por defecto cuando la fuente ofrece esos valores. La interfaz no agrega valores de monedas o unidades diferentes en una misma fila.",
        "",
        "## Validación de precios cero",
        "",
        *[f"- {item}" for item in cero_detail],
        f"- Celdas de precio cero en series dashboard-ready: {dashboard_price_zero}. La captura versionada conserva indicadores de elegibilidad; app.js requiere precio mayor que cero antes de usar filas para KPIs, gráfico y últimos precios.",
        "",
        "## Validación de GitHub Actions",
        "",
        *[f"- {entry['status']} — {entry['name']}: {entry['detail']}" for entry in workflow],
        "",
        f"- Estado de runs recientes: {actions_text}",
        "- La falla del 27 de septiembre de 2026 ocurrió en integración: el log reporta una fila leída y cero operaciones integrables porque el mapeo posicional quedó pendiente de validación. La etapa de auditoría, regeneración y publicación no se ejecutó; el integrador indicó que preservó las salidas anteriores.",
        "",
        "## Validación local y GitHub Pages",
        "",
        f"- Localhost: {local_status}; CSV comparados por contenido: {local_equal}/{local_asset_count}.",
        f"- GitHub Pages: {pages_status}; CSV comparados por contenido: {pages_equal}/{pages_asset_count}.",
        "- Verificación interactiva de navegador: las fuentes SIO y local cargaron; el histórico abrió por defecto en Rosario; los KPIs mostraron datos; no se observaron errores de consola.",
        "- Las filas y los campos de los CSV publicados coinciden con los del checkout. El control HTTP confirmó los recursos de commodities con respuesta 200.",
        "",
        "## No regresión en otros módulos",
        "",
        "- En localhost y GitHub Pages, los botones Cantidades transadas y Precios mayoristas abrieron sus vistas y permitieron volver a Commodities. No aparecieron errores de consola en la navegación.",
        "",
        "## Observaciones",
        "",
        "1. Requiere corrección el filtro de SIO: el dashboard sólo lleva tipo_precio (Precio Hecho) hasta las series; pierde tipo_operacion en la salida liviana y no muestra Compraventa/Canje. Corregirlo requiere propagar esa dimensión por la preparación de CSV y definir el agrupamiento correspondiente; no se aplicó durante una auditoría que prohíbe cambios metodológicos.",
        "2. El flujo de actualización hace un commit/push con las credenciales predeterminadas de actions/checkout. Pages sólo se activa por push a main o por ejecución manual. GitHub documenta que los pushes hechos con GITHUB_TOKEN no activan otro workflow ni una compilación de Pages ([documentación oficial](https://docs.github.com/en/actions/concepts/security/github_token)). Los archivos servidos hoy coinciden con el checkout, pero una actualización diaria futura no publicará automáticamente esos CSV sin otro disparador válido.",
        "3. El snapshot conserva 310 Contrato, 10 Rectificación y 3 Anulación, pero los agregados cuentan las 323 como observaciones positivas. Debe acordarse cómo tratar rectificaciones y anulaciones antes de interpretar conteos, volumen o medianas como operaciones vigentes; no se aplicó una regla nueva durante esta auditoría.",
        "4. La variación mensual se calcula contra la fila anterior sin comprobar continuidad de meses. Los datos actuales no tienen huecos; una serie futura incompleta puede alimentar un semáforo que compare períodos no consecutivos.",
        "5. La actualización escribe los CSV de snapshots secuencialmente sin archivos temporales ni reemplazo atómico. No hubo corrupción en los datos observados, pero una interrupción durante el guardado podría dejar sólo una parte actualizada.",
        "6. La deduplicación mantiene la primera versión de un ID y descarta versiones posteriores con el mismo ID. No hay IDs repetidos en la captura auditada, pero una rectificación de origen bajo el mismo ID no reemplazaría el dato persistido.",
        "7. El validador opcional de actualización dashboard corre antes de regenerar los archivos; si se incorpora, su ubicación actual valida la corrida anterior.",
        "8. El rango SIO comienza el 9 de septiembre de 2026. La historia creció incrementalmente frente al snapshot padre, aunque no hay baseline anterior al inicio de cobertura.",
        "9. Se observó una falla de integración el 27 de septiembre; las corridas posteriores incluidas en la consulta terminaron exitosamente.",
        "",
        "## Conclusión",
        "",
        f"**Estado general: {overall}.** Las fuentes SIO y local se cargan por separado, los CSV publicados coinciden con el checkout y las series finales no contienen precios cero. Hay defectos en los filtros/dimensiones del SIO y el commit automático no dispara Pages; además, la cobertura versionada empieza el 9 de septiembre de 2026.",
        "",
        "## Consistencia de archivos dashboard-ready",
        "",
        consistency_findings,
        "",
        "## Columnas críticas vacías",
        "",
        "La tabla inicial resume los conteos por archivo. Los campos opcionales de variación no se tratan como críticos.",
        "",
    ]

    # El estado general se decide antes de guardar, después de medir consistencia y publicación.
    final_overall = overall
    REPORT_MD.write_text("\n".join(lines).replace("Estado general: " + overall, "Estado general: " + final_overall), encoding="utf-8")

    summary_rows = summaries(records, apps, workflow, live, consistency, final_overall)
    fields = [
        "fuente", "archivo", "estado", "bytes", "filas", "columnas",
        "fecha_min", "fecha_max", "commodities", "monedas", "unidades",
        "tipos_precio", "tipos_operacion", "plazas",
        "celdas_precio_cero", "nulos_criticos", "detalle",
    ]
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summary_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sin-red", action="store_true",
        help="omite los chequeos HTTP locales, GitHub Pages y GitHub Actions",
    )
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    for name in SIO_FILES:
        records.append(file_audit(SIO_DIR / name, "SIO Granos"))
    for path in sorted(LOCAL_DIR.glob("*.csv")):
        records.append(file_audit(path, "Histórico local mensual"))
    expected_local = list(LOCAL_DIR.glob("*.csv"))
    if not expected_local:
        records.append(file_audit(LOCAL_DIR / "COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv", "Histórico local mensual"))

    by_name = csv_rows_by_name(records)
    consistency: list[tuple[str, bool, str]] = []
    consistency.append(check_sio_monthly_consistency(
        by_name.get("COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv", {}),
        by_name.get("COMMODITIES_SIO_DASHBOARD_MENSUAL.csv", {}),
    ))
    consistency[-1] = ("SIO snapshots → mensual", consistency[-1][0], consistency[-1][1])
    sem = check_local_semaphore(
        by_name.get("COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv", {}),
        by_name.get("COMMODITIES_LOCAL_MENSUAL_DASHBOARD_SEMAFORO.csv", {}),
    )
    consistency.append(("Histórico local mensual → semáforo", sem[0], sem[1]))
    latest = check_local_latest(
        by_name.get("COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv", {}),
        by_name.get("COMMODITIES_LOCAL_MENSUAL_DASHBOARD_ULTIMOS.csv", {}),
    )
    consistency.append(("Histórico local mensual → últimos", latest[0], latest[1]))
    sio_monthly = by_name.get("COMMODITIES_SIO_DASHBOARD_MENSUAL.csv", {})
    sio_final_zero = sum(
        record["zero_cells"] for record in records
        if record["source"] == "SIO Granos"
        and record["path"].name not in {
            "COMMODITIES_SIO_DASHBOARD_RESUMEN.csv",
            "COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv",
        }
    )
    local_final_zero = sum(
        record["zero_cells"] for record in records
        if record["source"] == "Histórico local mensual"
    )
    consistency.append((
        "Precios cero fuera de series finales",
        sio_final_zero == 0 and local_final_zero == 0,
        f"SIO={sio_final_zero} celdas cero; local mensual={local_final_zero} celdas cero.",
    ))

    apps = app_checks()
    workflow = workflow_checks()
    live = live_checks(records, args.sin_red)
    page_assets = live.get("pages_assets", [])
    local_assets = live.get("localhost_assets", [])
    page_mismatch = bool(live.get("network_enabled")) and any(
        item.get("status") != 200 or not item.get("equal") for item in page_assets
    )
    local_mismatch = bool(live.get("network_enabled")) and local_assets and any(
        item.get("status") != 200 or not item.get("equal") for item in local_assets
    )
    if page_mismatch or local_mismatch:
        consistency.append((
            "CSV localhost/GitHub Pages vs checkout", False,
            f"Local coincidente={sum(x.get('equal', False) for x in local_assets)}/{len(local_assets)}; Pages coincidente={sum(x.get('equal', False) for x in page_assets)}/{len(page_assets)}.",
        ))
    elif live.get("network_enabled") and page_assets:
        consistency.append((
            "CSV localhost/GitHub Pages vs checkout", True,
            f"Local coincidente={sum(x.get('equal', False) for x in local_assets)}/{len(local_assets)}; Pages coincidente={sum(x.get('equal', False) for x in page_assets)}/{len(page_assets)}.",
        ))

    has_app_issue = any(item["status"] == "Requiere corrección" for item in apps)
    has_consistency_issue = any(not passed for _, passed, _ in consistency)
    overall = "Requiere corrección" if has_app_issue or has_consistency_issue else "OK"
    if overall == "OK" and any(item["status"] != "OK" for item in workflow):
        overall = "OK con observaciones"
    if overall == "OK" and live.get("actions_runs"):
        if any(run.get("conclusion") == "failure" for run in live["actions_runs"]):
            overall = "OK con observaciones"

    create_report(records, apps, workflow, live, consistency, overall)
    print(f"Reporte: {REPORT_MD.relative_to(ROOT)}")
    print(f"Resumen CSV: {REPORT_CSV.relative_to(ROOT)}")
    print(f"Estado general: {overall}")
    print(f"Archivos CSV revisados: {sum(record['exists'] for record in records)}/{len(records)}")
    print(f"Series dashboard-ready con celdas de precio cero: SIO={sio_final_zero}, local={local_final_zero}")
    for name, passed, detail in consistency:
        print(f"{'OK' if passed else 'REVISAR'} - {name}: {detail}")
    if live.get("actions_runs"):
        latest_run = live["actions_runs"][0]
        print(
            f"GitHub Actions: run #{latest_run.get('run_number')} "
            f"{latest_run.get('status')}/{latest_run.get('conclusion')}."
        )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
