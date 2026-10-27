"""Transfer an MCBA capture to the current publisher without transferring freshness."""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.magyp import build_price_freshness
from scripts.magyp.common.platform import PipelineError, atomic_write, sha256
from scripts.magyp.mcba.published_bundle import read_bundle, validate_daily

BUNDLE = tuple(f"MCBA_MAGYP_{kind}.csv" for kind in ("DAILY", "DETAIL", "LATEST", "SUMMARY")) + ("_SUCCESS.json",)
PUBLISHED = Path("data/magyp/dashboard/mcba")
STATUS = "MCBA_MAGYP_UPDATE_STATUS.json"
STATES = {"UPDATED", "NO_OP_ALREADY_CURRENT", "NO_PUBLICATION", "SOURCE_UNAVAILABLE", "PIPELINE_ERROR"}
URL = "https://ssma.magyp.gob.ar/frutas.precios.aspx"


def _json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PipelineError("Invalid candidate JSON") from error


def _encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _hashes(value, names):
    if not isinstance(value, dict) or set(value) != set(names) or any(
            not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for v in value.values()):
        raise PipelineError("Invalid candidate file hashes")
    return value


def _stamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset().total_seconds() != 0:
            raise ValueError()
        return parsed
    except (TypeError, ValueError, AttributeError) as error:
        raise PipelineError("Invalid UTC timestamp") from error


def _day(value):
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except (TypeError, ValueError) as error:
        raise PipelineError("Invalid observation date") from error


def _baseline(value):
    if not isinstance(value, dict) or set(value) != {"schema_version", "files"} or value["schema_version"] != "mcba-candidate-baseline-v1":
        raise PipelineError("Invalid baseline contract")
    _hashes(value["files"], BUNDLE)
    return value


def _state(state):
    required = {"result", "source", "source_url", "source_status", "requested_date", "attempted_at",
                "last_observation_date", "last_successful_update"}
    if not isinstance(state, dict) or set(state) != required:
        raise PipelineError("Invalid run status contract")
    if state["result"] not in STATES or state["source"] != "MAGyP" or state["source_url"] != URL:
        raise PipelineError("Unknown MCBA run status")
    if state["source_status"] != ("MAGYP" if state["result"] == "UPDATED" else "MAGYP_LAST_VALID"):
        raise PipelineError("Inconsistent source status")
    _day(state["requested_date"])
    _day(state["last_observation_date"])
    if _stamp(state["attempted_at"]) < _stamp(state["last_successful_update"]):
        raise PipelineError("Attempt predates capture")
    return state


def _bundle(folder):
    """Require the public CSVs; accept the historical monthly entry only in existing bundles."""
    folder = Path(folder)
    marker = _json(folder / "_SUCCESS.json")
    files = marker.get("files") if isinstance(marker, dict) else None
    names = set(BUNDLE[:-1])
    if isinstance(files, dict) and "MCBA_MAGYP_MONTHLY.csv" in files:
        names.add("MCBA_MAGYP_MONTHLY.csv")
    _hashes(files, names)
    rows = read_bundle(folder)
    for name in BUNDLE[:-1]:
        parsed = list(csv.DictReader(io.StringIO((folder / name).read_text(encoding="utf-8"))))
        if not parsed or any(None in r or None in r.values() for r in parsed):
            raise PipelineError("Invalid public CSV")
        if name.endswith(("DETAIL.csv", "LATEST.csv")):
            validate_daily(parsed)
        if name.endswith("SUMMARY.csv"):
            if len(parsed) != 1 or parsed[0].get("date_max") != max(r["date"] for r in rows) or parsed[0].get("updated_at") != max(r["capture_timestamp"] for r in rows):
                raise PipelineError("Summary does not match daily bundle")
    return rows


def _matches(state, rows):
    if (state["last_observation_date"] != max(r["date"] for r in rows) or
            state["last_successful_update"] != max(r["capture_timestamp"] for r in rows)):
        raise PipelineError("Run status does not match final bundle")
    if state["result"] in {"UPDATED", "NO_OP_ALREADY_CURRENT"} and not any(r["date"] == state["requested_date"] for r in rows):
        raise PipelineError("Requested date absent from bundle")


def _emit(state):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"result={state['result']}\n")


def baseline(published_dir, output):
    published_dir = Path(published_dir)
    _bundle(published_dir)
    value = {"schema_version": "mcba-candidate-baseline-v1",
             "files": {name: sha256((published_dir / name).read_bytes()) for name in BUNDLE}}
    atomic_write(Path(output), _encode(value))
    return value


def pack(published_dir, baseline_path, status, destination):
    before = _baseline(_json(baseline_path))
    state = _state(_json(status))
    destination = Path(destination)
    payload = {}
    if state["result"] == "UPDATED":
        rows = _bundle(Path(published_dir))
        _matches(state, rows)
        payload = {name: (Path(published_dir) / name).read_bytes() for name in BUNDLE}
    # Exclusive directory creation avoids stale files in a reused artifact.
    destination.mkdir(parents=True, exist_ok=False)
    for name, body in payload.items():
        atomic_write(destination / "payload" / name, body)
    atomic_write(destination / "candidate.json", _encode({"schema_version": "mcba-candidate-v1",
        "baseline": before, "run_status": state, "payload": {name: sha256(body) for name, body in payload.items()}}))
    _emit(state)
    return state


def apply(root, candidate):
    root, candidate = Path(root), Path(candidate)
    manifest = _json(candidate / "candidate.json")
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "baseline", "run_status", "payload"} or manifest["schema_version"] != "mcba-candidate-v1":
        raise PipelineError("Invalid candidate contract")
    before = _baseline(manifest["baseline"])
    state = _state(manifest["run_status"])
    updated = state["result"] == "UPDATED"
    hashes = _hashes(manifest["payload"], BUNDLE if updated else ())
    expected = {"candidate.json"} | ({"payload/" + name for name in BUNDLE} if updated else set())
    actual = {p.relative_to(candidate).as_posix() for p in candidate.rglob("*") if p.is_file()}
    if actual != expected or any(p.is_symlink() for p in candidate.rglob("*")):
        raise PipelineError("Unexpected candidate files")
    payload = {name: (candidate / "payload" / name).read_bytes() for name in hashes}
    if any(sha256(payload[name]) != digest for name, digest in hashes.items()):
        raise PipelineError("Corrupt candidate payload")
    published = root / PUBLISHED
    current_rows = _bundle(published)
    if updated and any(sha256((published / name).read_bytes()) != digest for name, digest in before["files"].items()):
        raise PipelineError("Published baseline changed; capture must be retried")
    for old in ([ _json(published / STATUS) ] if (published / STATUS).exists() else []):
        if old.get("attempted_at") and _stamp(state["attempted_at"]) < _stamp(old["attempted_at"]):
            raise PipelineError("Candidate predates published MCBA status")
    freshness_path = root / build_price_freshness.REPORT
    if freshness_path.exists():
        for old in _json(freshness_path).get("sources", []):
            if old.get("source_family") == "mcba" and old.get("attempted_at") and _stamp(state["attempted_at"]) < _stamp(old["attempted_at"]):
                raise PipelineError("Candidate predates MCBA freshness")
    # Validate the exact in-memory bytes that will be installed, outside the checkout.
    if updated:
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            for name, body in payload.items():
                (stage / name).write_bytes(body)
            final_rows = _bundle(stage)
    else:
        final_rows = current_rows
    _matches(state, final_rows)
    changes = {published / name: body for name, body in payload.items()}
    changes[published / STATUS] = _encode(state)
    touched = set(changes) | {freshness_path}
    originals = {p: p.read_bytes() if p.exists() else None for p in touched}
    try:
        for path, body in changes.items():
            atomic_write(path, body)
        build_price_freshness.build(root, mcba_status=state)
    except Exception:
        for path, body in originals.items():
            if body is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, body)
        raise
    _emit(state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("baseline")
    command.add_argument("--published-dir", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("pack")
    command.add_argument("--published-dir", type=Path, required=True)
    command.add_argument("--baseline", type=Path, required=True)
    command.add_argument("--status", type=Path, required=True)
    command.add_argument("--destination", type=Path, required=True)
    command = commands.add_parser("apply")
    command.add_argument("--root", type=Path, required=True)
    command.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "baseline":
        baseline(args.published_dir, args.output)
    elif args.command == "pack":
        pack(args.published_dir, args.baseline, args.status, args.destination)
    else:
        apply(args.root, args.candidate)


if __name__ == "__main__":
    main()
