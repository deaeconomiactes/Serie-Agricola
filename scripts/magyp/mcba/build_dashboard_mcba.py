"""ANALYTICAL → cuatro CSV piloto independientes del frontend productivo."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.magyp.common.platform import PipelineError, csv_bytes, publish_bundle, read_jsonl
from scripts.magyp.mcba.model import dashboard_rows


def run(data_root):
    data = dashboard_rows(read_jsonl(data_root / "analytical/mcba/market_price_observation.jsonl"))
    outputs = {f"MCBA_MAGYP_{name}.csv": csv_bytes(rows, list(rows[0])) for name, rows in data.items()}
    result = publish_bundle(data_root / "dashboard/mcba", outputs, len(data["DAILY"]))
    print(f"[PUBLISH] {len(data['DAILY'])} precios diarios; {len(outputs)} CSV piloto")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, default=ROOT / "data/magyp")
    args = p.parse_args()
    try:
        run(args.data_root)
    except PipelineError as e:
        print(f"[PUBLISH] ERROR {e}; última salida conservada", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
