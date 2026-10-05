import argparse
import json
from pathlib import Path

from .fob import ENDPOINT, FobPipeline, PipelineError, load_calendar, parse_date


def main(stage):
    parser = argparse.ArgumentParser(description=f"MAGyP FOB: {stage}; sin integración frontend")
    parser.add_argument("--data-root", type=Path, help="Raíz de capas (default: data del repositorio)")
    parser.add_argument("--raw-root", type=Path, help="Raíz RAW magyp externa opcional; contiene fob/")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar plan sin red ni escrituras")
    if stage == "fetch":
        parser.add_argument("--date", required=True, help="Fecha ISO YYYY-MM-DD")
        parser.add_argument("--calendar", type=Path, help="Calendario de ausencias con referencia validada")
    args = parser.parse_args()
    pipeline = FobPipeline(args.data_root, args.raw_root)
    if stage == "fetch":
        try:
            parse_date(args.date)
        except ValueError:
            parser.error("--date requiere una fecha válida YYYY-MM-DD")
    if args.dry_run:
        print(json.dumps({"stage": stage, "requested_date": getattr(args, "date", None), "endpoint": ENDPOINT,
                          "raw_root": str(pipeline.raw), "data_root": str(pipeline.data),
                          "dashboard": str(pipeline.dashboard), "dry_run": True,
                          "network": False, "planned_network": stage == "fetch"}, ensure_ascii=False))
        return 0
    try:
        if stage == "fetch":
            try:
                calendar = load_calendar(args.calendar)
            except Exception:
                with pipeline.locked():
                    pipeline.set_state(stage="failed", requested_date=args.date, classification="invalid_calendar")
                raise PipelineError("Calendario inválido: captura/publicación bloqueadas")
            pipeline.fetch(args.date, calendar)
        elif stage == "normalize":
            pipeline.normalize()
        else:
            pipeline.build()
        return 0
    except PipelineError as exc:
        print(f"[VALIDATE] ERROR: {exc}; último dashboard conservado cuando no se publicó")
        return 1
    except Exception as exc:
        # No imprimir cuerpos, valores remotos o estado de sesión en tracebacks.
        print(f"[VALIDATE] ERROR interno: {type(exc).__name__}; revisar permisos/integridad local")
        return 1
