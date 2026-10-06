"""RAW → NORMALIZED; reconstrucción completa y validada antes de reemplazar."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import PipelineError, load_raw, write_jsonl
from scripts.magyp.mcba.model import ACCEPTED_RAW_VERSIONS, normalize, parse_export, validate_canonical


def run(data_root):
    for folder in (data_root / "raw/mcba").glob("*"):
        if folder.is_dir() and (not (folder / "manifest.json").exists() or not (folder / "response.xlsx").exists()):
            raise PipelineError("Captura incompleta; última salida conservada")
    folders = sorted((data_root / "raw/mcba").glob("*/manifest.json"))
    if not folders:
        raise PipelineError("Sin capturas MCBA; última salida conservada")
    rows = []
    for file in folders:
        payload, manifest = load_raw(file.parent)
        if (manifest.parser_version, manifest.schema_version) not in ACCEPTED_RAW_VERSIONS:
            raise PipelineError("Versión de contrato/parser RAW no soportada")
        records = parse_export(payload, manifest.public_parameters["date_from"], manifest.public_parameters["date_to"])
        if len(records) != manifest.record_count:
            raise PipelineError("Conteo RAW no coincide con manifest")
        rows.extend(normalize(records, manifest))
    validate_canonical(rows)
    write_jsonl(data_root / "normalized/mcba/market_price_observation.jsonl", rows)
    print(f"[NORMALIZE] {len(rows)} registros; {len(folders)} capturas")
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, default=ROOT / "data/magyp")
    args = p.parse_args()
    try:
        run(args.data_root)
    except PipelineError as e:
        print(f"[NORMALIZE] ERROR {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
