"""Integra listas de precios mayoristas diarios de 2026.

Coloque los archivos fuente en ``data/precios_2026/`` para usar la carpeta
interna, o pase otra carpeta como argumento. Ejemplos::

    python integrar_precios_2026.py
    python integrar_precios_2026.py "C:\\Users\\acer\\Oficina\\Info. para Serie Agricola"

El resultado se escribe en la raíz del proyecto como
``PRECIOS_MAYORISTAS_2026_INTEGRADO.csv``.

Esta base de precios se mantiene separada de la base de cantidades 2024/2025:
los precios 2026 no se cruzan con cantidades, ni se usan para calcular
elasticidades o relaciones precio-cantidad.
"""

from __future__ import annotations

import argparse
import csv
import contextlib
import io
import re
import sys
import unicodedata
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = PROJECT_DIR / "data" / "precios_2026"
OUTPUT_PATH = PROJECT_DIR / "PRECIOS_MAYORISTAS_2026_INTEGRADO.csv"

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
MONTH_NAMES = {number: name.title() for name, number in MONTHS.items() if name != "setiembre"}
FIELDS = [
    "fecha", "año", "mes", "rubro", "especie", "variedad", "mercado",
    "unidad", "precio", "precio_min", "precio_max", "precio_promedio",
    "archivo_origen",
]
TABULAR_EXTENSIONS = {".csv", ".xlsx", ".xls"}
IGNORE_RE = re.compile(r"(?:^~\$|desktop\.ini$|registro|vfru|vhor|2024|2025)", re.I)


def _ascii(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()


def _filename_text(filename: str) -> str:
    return _ascii(Path(filename).name).replace("_", " ").replace("-", " ")


def infer_rubro_from_filename(filename: str) -> str:
    text = _filename_text(filename)
    if "hortal" in text:
        return "Hortalizas"
    if "frut" in text or re.search(r"\b rf\d", text):
        return "Frutas"
    return ""


def infer_month_from_filename(filename: str) -> str:
    text = _filename_text(filename)
    for month in MONTHS:
        if re.search(rf"\b{month}\b", text) or month in text:
            return month.title()
    # Daily files use RF020126 / RH020126 (DDMMYY).
    match = re.search(r"[rhf](\d{2})(\d{2})(\d{2})", text.replace(" ", ""), re.I)
    if match:
        return MONTH_NAMES.get(int(match.group(2)), "")
    return ""


def infer_year_from_filename(filename: str) -> int | str:
    text = _filename_text(filename)
    if re.search(r"(?:2026|26)\b", text) or re.search(r"\d{6}", text):
        return 2026
    return ""


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    # Repair common mojibake without altering valid Spanish accents.
    for bad, good in (("Ã¡", "á"), ("Ã©", "é"), ("Ã­", "í"), ("Ã³", "ó"), ("Ãº", "ú"), ("Ã±", "ñ"), ("¥", "Ñ")):
        text = text.replace(bad, good)
    return text.title()


def normalize_species(value: Any) -> str:
    return normalize_text(value).replace("Prom. Esp.", "Promedio Especie")


def normalize_variety(value: Any) -> str:
    return normalize_text(value)


def normalize_market(value: Any) -> str:
    return normalize_text(value)


def normalize_unit(value: Any) -> str:
    return normalize_text(value).replace("Por Kg", "$/Kg")


def parse_argentine_price(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value != 0 else None
    text = str(value).strip().replace("$", "").replace(" ", "")
    if not text or text in {"-", "–", "0", "0,00", "0.00"}:
        return None
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text:
        return None
    if "," in text and "." in text:
        # The last separator is the decimal separator: supports both locales.
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts[:-1]) + "." + parts[-1] if len(parts[-1]) <= 2 else "".join(parts)
    elif "." in text:
        # In Argentine notation 2.500 means 2500; a dot followed by one or
        # two digits is more likely a decimal point (1250.50).
        left, right = text.rsplit(".", 1)
        text = left.replace(".", "") + ("." + right if len(right) <= 2 else right)
    try:
        result = float(text)
        return result if result != 0 else None
    except ValueError:
        return None


def normalize_date(value: Any, fallback_month: str | None = None, fallback_year: int | str | None = None) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = normalize_text(value)
    if text:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        match = re.search(r"(\d{2})[./-](\d{2})[./-](\d{2,4})", text)
        if match:
            year = int(match.group(3)); year += 2000 if year < 100 else 0
            return f"{year:04d}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"
    # Deliberately leave the day empty when only month/year are known.
    return ""


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _ascii(value))


def read_price_file(path: Path) -> list[dict[str, Any]]:
    """Read CSV/XLSX/XLS and return rows as dictionaries.

    XLS support uses the optional ``xlrd`` package (``pip install xlrd``).
    A failure is raised to the caller so it can warn and continue.
    """
    suffix = path.suffix.lower()
    if suffix == ".csv":
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                text = raw.decode(encoding)
                sample = text[:4096]
                dialect = csv.Sniffer().sniff(sample, delimiters=",;")
                return list(csv.DictReader(io.StringIO(text), dialect=dialect))
            except (UnicodeDecodeError, csv.Error):
                continue
        raise ValueError("no se pudo detectar la codificación o el separador CSV")
    if suffix == ".xlsx":
        from openpyxl import load_workbook
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        values = list(sheet.values)
        workbook.close()
    elif suffix == ".xls":
        try:
            import xlrd
        except ImportError as exc:
            raise RuntimeError("falta xlrd para leer .xls (instalar con: pip install xlrd)") from exc
        # Some legacy BIFF files emit informational messages on stderr.
        with contextlib.redirect_stderr(io.StringIO()):
            book = xlrd.open_workbook(file_contents=path.read_bytes(), on_demand=True)
        sheet = book.sheet_by_index(0)
        values = [sheet.row_values(i) for i in range(sheet.nrows)]
        book.release_resources()
    else:
        raise ValueError(f"extensión no soportada: {suffix}")
    if not values:
        return []
    headers = [str(v).strip() if v is not None else "" for v in values[0]]
    return [dict(zip(headers, row)) for row in values[1:] if any(v not in (None, "") for v in row)]


def _find(row: dict[str, Any], names: Iterable[str]) -> Any:
    wanted = {_key(name) for name in names}
    for name, value in row.items():
        if _key(name) in wanted:
            return value
    return ""


def _date_from_source(source: str) -> str:
    match = re.search(r"[rhf](\d{2})(\d{2})(\d{2,4})", Path(source).name, re.I)
    if not match:
        return ""
    year = int(match.group(3)); year += 2000 if year < 100 else 0
    return f"{year:04d}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"


def _make_rows(raw_rows: list[dict[str, Any]], source: str, container: str) -> list[dict[str, Any]]:
    filename = f"{container} {source}"
    rubro = infer_rubro_from_filename(filename)
    month = infer_month_from_filename(source) or infer_month_from_filename(container)
    year = infer_year_from_filename(source) or infer_year_from_filename(container) or 2026
    exact_date = _date_from_source(source) or normalize_date(_find(raw_rows[0], ("fecha", "date"))) if raw_rows else ""
    output = []
    for raw in raw_rows:
        species = normalize_species(_find(raw, ("especie", "esp", "producto", "articulo")))
        if not species or _key(species) in {"total", "totales"}:
            continue
        avg = parse_argentine_price(_find(raw, ("precio_promedio", "promedio", "mopk", "precio")))
        minimum = parse_argentine_price(_find(raw, ("precio_min", "minimo", "mipk")))
        maximum = parse_argentine_price(_find(raw, ("precio_max", "maximo", "mapk")))
        if avg is None and minimum is None and maximum is None:
            continue
        row = {
            "fecha": exact_date,
            "año": year if not exact_date else exact_date[:4],
            "mes": month if not exact_date else MONTH_NAMES.get(int(exact_date[5:7]), month),
            "rubro": rubro,
            "especie": species,
            "variedad": normalize_variety(_find(raw, ("variedad", "var", "tipo"))),
            "mercado": normalize_market(_find(raw, ("mercado", "market"))),
            "unidad": normalize_unit(_find(raw, ("unidad", "unit"))) or "$/Kg",
            "precio": avg if avg is not None else (minimum if minimum is not None else maximum),
            "precio_min": minimum,
            "precio_max": maximum,
            "precio_promedio": avg,
            "archivo_origen": f"{container}/{source}" if container else source,
        }
        # PROC is origin/provenance, not a market. Keep the market independent.
        output.append(row)
    return output


def _is_ignored(name: str) -> bool:
    return bool(IGNORE_RE.search(Path(name).name))


def _iter_tabular_entries(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in TABULAR_EXTENSIONS and not _is_ignored(path.name):
            yield path, path.name, ""

    def from_zip(zip_path: Path, blob: bytes | None = None, container: str = ""):
        with zipfile.ZipFile(io.BytesIO(blob) if blob is not None else zip_path) as archive:
            for info in archive.infolist():
                if info.is_dir() or _is_ignored(info.filename):
                    continue
                name = Path(info.filename).name
                data = archive.read(info)
                if zipfile.is_zipfile(io.BytesIO(data)):
                    yield from from_zip(zip_path, data, f"{container}/{name}".strip("/"))
                elif Path(name).suffix.lower() in TABULAR_EXTENSIONS:
                    yield data, name, f"{container}/{zip_path.name}".strip("/")

    for path in sorted(root.rglob("*")):
        if path.is_file() and (path.suffix.lower() == ".zip" or zipfile.is_zipfile(path)) and not _is_ignored(path.name):
            yield from from_zip(path)


def _read_entry(entry: Any, name: str) -> list[dict[str, Any]]:
    if isinstance(entry, Path):
        return read_price_file(entry)
    suffix = Path(name).suffix.lower()
    temp = io.BytesIO(entry)
    # read_price_file uses paths to support openpyxl/xlrd; use a named temporary
    # file only for archive members and remove it immediately after reading.
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(entry); temp_path = Path(handle.name)
    try:
        return read_price_file(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Integra precios mayoristas diarios 2026")
    parser.add_argument("input_dir", nargs="?", type=Path, default=DEFAULT_INPUT_DIR,
                        help="carpeta fuente; por defecto data/precios_2026/")
    args = parser.parse_args()
    input_dir = args.input_dir.expanduser()
    if not input_dir.exists():
        print(f"ERROR: no existe la carpeta fuente: {input_dir}", file=sys.stderr)
        return 1

    found = processed = errors = 0
    rows: list[dict[str, Any]] = []
    months: set[str] = set(); rubros: set[str] = set(); species: set[str] = set()
    for entry, name, container in _iter_tabular_entries(input_dir):
        found += 1
        try:
            parsed = _make_rows(_read_entry(entry, name), name, container)
            rows.extend(parsed); processed += 1
            months.update(row["mes"] for row in parsed if row["mes"])
            rubros.update(row["rubro"] for row in parsed if row["rubro"])
            species.update(row["especie"] for row in parsed if row["especie"])
        except Exception as exc:
            errors += 1
            print(f"ADVERTENCIA: no se pudo leer {name}: {exc}", file=sys.stderr)

    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Archivos encontrados: {found}")
    print(f"Archivos procesados correctamente: {processed}")
    print(f"Archivos con error: {errors}")
    print(f"Filas integradas: {len(rows)}")
    print(f"Meses detectados: {', '.join(sorted(months)) or '(ninguno)'}")
    print(f"Rubros detectados: {', '.join(sorted(rubros)) or '(ninguno)'}")
    print(f"Especies únicas: {len(species)}")
    print(f"CSV generado: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
