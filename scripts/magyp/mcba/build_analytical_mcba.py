"""NORMALIZED → ANALYTICAL, manteniendo el grano y seleccionando revisiones completas."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import PipelineError, read_jsonl, write_jsonl
from scripts.magyp.mcba.model import build_analytical


def run(data_root):
    rows = build_analytical(read_jsonl(data_root / "normalized/mcba/market_price_observation.jsonl"))
    write_jsonl(data_root / "analytical/mcba/market_price_observation.jsonl", rows)
    print(f"[VALIDATE] {len(rows)} observaciones analíticas; grano original conservado")
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, default=ROOT / "data/magyp")
    args = p.parse_args()
    try:
        run(args.data_root)
    except PipelineError as e:
        print(f"[VALIDATE] ERROR {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
