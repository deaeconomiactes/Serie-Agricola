"""Lectura y validación de CSV MCBA publicados, sin dependencias de adquisición/XLSX."""
from __future__ import annotations
import csv
import io
import json
from datetime import date, datetime
from pathlib import Path
from scripts.magyp.common.platform import PipelineError, sha256

DAILY = "MCBA_MAGYP_DAILY.csv"
DIMENSIONS = ("source", "market_normalized", "type", "product_normalized", "variety_normalized",
    "origin_normalized", "package_normalized", "quality", "size", "grade", "currency", "price_unit",
    "record_kind", "observation_level")
REQUIRED = set(DIMENSIONS) | {"date", "price", "observation_id", "raw_sha256", "capture_id",
    "product_raw", "variety_raw", "origin_raw", "package_raw", "kg_raw", "volume",
    "capture_timestamp", "source_url", "data_source", "source_status", "last_update"}


def read_bundle(folder):
    """Valida todos los hashes del conjunto; ningún CSV sin marcador se acepta como fallback."""
    try:
        marker = json.loads((folder / "_SUCCESS.json").read_text(encoding="utf-8"))
        for name, digest in marker["files"].items():
            if Path(name).name != name or sha256((folder / name).read_bytes()) != digest:
                raise PipelineError("Bundle previo inconsistente")
        payload = (folder / DAILY).read_text(encoding="utf-8")
        rows = list(csv.DictReader(io.StringIO(payload)))
        validate_daily(rows)
        if marker["record_count"] != len(rows):
            raise PipelineError("Conteo del bundle inconsistente")
        return rows
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise PipelineError("Bundle ausente o incompleto") from error


def validate_daily(rows):
    if not rows:
        raise PipelineError("Salida diaria vacía")
    ids = set()
    for r in rows:
        try:
            day = date.fromisoformat(r["date"])
            stamp = datetime.fromisoformat(r["capture_timestamp"].replace("Z", "+00:00"))
            price = float(r["price"])
            if (not REQUIRED.issubset(r) or day.isoformat() != r["date"] or
                not 0 < price < float("inf") or r["currency"] != "ARS" or r["price_unit"] != "kg" or
                not r["product_normalized"] or r["observation_level"] not in {"detail", "species_summary"} or
                not r["capture_id"] or stamp.utcoffset().total_seconds() != 0 or
                r["source_url"] != "https://ssma.magyp.gob.ar/frutas.precios.aspx" or
                len(r["raw_sha256"]) != 64 or any(c not in "0123456789abcdef" for c in r["raw_sha256"]) or
                r["volume"] not in ("", None) or r["observation_id"] in ids or
                r["data_source"] != "MAGYP" or r["source_status"] != "MAGYP" or
                (r["observation_level"] == "detail" and r["variety_normalized"] == "PROM.ESP.")):
                raise ValueError()
            ids.add(r["observation_id"])
        except (KeyError, ValueError, TypeError, AttributeError) as error:
            raise PipelineError("Contrato diario inválido") from error
