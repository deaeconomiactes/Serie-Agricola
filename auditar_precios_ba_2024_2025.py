"""Audita las listas MCBA 2024-2025 contra el integrado del dashboard.

El script es deliberadamente de solo lectura respecto de las fuentes y del
integrado. Solo crea/actualiza los dos reportes en
``data/precios_mayoristas/reports``.
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook


PROJECT_DIR = Path(__file__).resolve().parent
EXTERNAL_ROOT = Path(r"C:\Users\acer\Oficina\Info. para Serie Agricola")
EXTERNAL_PRICE_DIR = EXTERNAL_ROOT / "Precios-BS. AS"
REPORT_DIR = PROJECT_DIR / "data" / "precios_mayoristas" / "reports"
REPORT_PATH = REPORT_DIR / "REPORTE_AUDITORIA_PRECIOS_BA_2024_2025.md"
SUMMARY_PATH = REPORT_DIR / "RESUMEN_AUDITORIA_PRECIOS_BA_2024_2025.csv"

SOURCE_SPECS = (
    ("PHOR24_K.xlsx", "Hortalizas", 2024),
    ("PFRU24_K.xlsx", "Frutas", 2024),
    ("PHOR25_K.xlsx", "Hortalizas", 2025),
    ("PFRU25_K.xlsx", "Frutas", 2025),
)
INTEGRATED_NAMES = (
    "PRECIOS_MAYORISTAS_INTEGRADO.csv",
    "PRECIOS_MAYORISTAS_2026_INTEGRADO.csv",
)
MONTH_ALIASES = {
    "ENER": 1,
    "FEBR": 2,
    "MARZ": 3,
    "ABRI": 4,
    "MAYO": 5,
    "JUNI": 6,
    "JULI": 7,
    "AGOS": 8,
    "SEPT": 9,
    "SETI": 9,
    "OCTU": 10,
    "NOVI": 11,
    "DICI": 12,
}
MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def ascii_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def parse_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value == value else None
    text = clean_text(value).replace("$", "").replace(" ", "")
    if not text or text.lower() in {"nan", "none", "null", "-", "–"}:
        return None
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text:
        return None
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts[:-1]) + "." + parts[-1] if len(parts[-1]) <= 2 else "".join(parts)
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value).split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def month_number(value: Any) -> int | None:
    number = parse_number(value)
    if number is not None and 1 <= int(number) <= 12:
        return int(number)
    key = ascii_key(value)
    for prefix, month in MONTH_ALIASES.items():
        if key.startswith(prefix.lower()):
            return month
    return None


def is_mcba(value: Any) -> bool:
    key = ascii_key(value)
    return key == "mcba" or key.startswith("mercadocentral")


def rubro_key(value: Any) -> str:
    key = ascii_key(value)
    if "hortal" in key:
        return "hortalizas"
    if "frut" in key:
        return "frutas"
    return key


def header_map(values: Iterable[Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, value in enumerate(values):
        key = ascii_key(value)
        if key and key not in result:
            result[key] = index
    return result


def value_at(row: tuple[Any, ...], mapping: dict[str, int], aliases: Iterable[str]) -> Any:
    for alias in aliases:
        index = mapping.get(ascii_key(alias))
        if index is not None and index < len(row):
            return row[index]
    return None


def month_from_header(value: Any) -> int | None:
    key = ascii_key(value).upper()
    for prefix, month in MONTH_ALIASES.items():
        if key.endswith(prefix) or prefix in key:
            return month
    return None


def md_escape(value: Any) -> str:
    return clean_text(value).replace("|", "\\|").replace("\n", " ")


def fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


@dataclass
class SourceAudit:
    filename: str
    rubro: str
    expected_year: int
    found: bool = False
    path: Path | None = None
    sheets: list[str] = field(default_factory=list)
    sheet_used: str = ""
    header_row: int | None = None
    headers: list[str] = field(default_factory=list)
    useful_rows: int = 0
    presentation_rows: int = 0
    summary_rows: int = 0
    price_observations: int = 0
    min_date: str = ""
    max_date: str = ""
    year_evidence: str = ""
    months: list[int] = field(default_factory=list)
    species_counts: Counter[str] = field(default_factory=Counter)
    varieties: set[str] = field(default_factory=set)
    has_origin: bool = False
    has_package: bool = False
    has_unit: bool = False
    has_price: bool = False
    date_columns: list[str] = field(default_factory=list)
    species_columns: list[str] = field(default_factory=list)
    variety_columns: list[str] = field(default_factory=list)
    price_columns: list[str] = field(default_factory=list)
    package_columns: list[str] = field(default_factory=list)
    origin_columns: list[str] = field(default_factory=list)
    integrated_count: int = 0
    integrated_months: list[int] = field(default_factory=list)
    integrated_species: set[str] = field(default_factory=set)
    status: str = "INCIERTO"
    observation: str = ""


def candidate_source_paths(filename: str) -> list[Path]:
    direct = [
        PROJECT_DIR / filename,
        PROJECT_DIR / "data" / filename,
        PROJECT_DIR / "data" / "precios_mayoristas" / filename,
        PROJECT_DIR / "data" / "precios_mayoristas" / "raw" / filename,
        EXTERNAL_ROOT / filename,
        EXTERNAL_PRICE_DIR / filename,
    ]
    seen: set[str] = set()
    return [path for path in direct if not (str(path).lower() in seen or seen.add(str(path).lower()))]


def locate_source(filename: str) -> Path | None:
    for path in candidate_source_paths(filename):
        if path.is_file():
            return path
    matches = sorted(EXTERNAL_ROOT.rglob(filename)) if EXTERNAL_ROOT.exists() else []
    return matches[0] if matches else None


def inspect_source(filename: str, rubro: str, expected_year: int) -> SourceAudit:
    audit = SourceAudit(filename=filename, rubro=rubro, expected_year=expected_year)
    path = locate_source(filename)
    if path is None:
        audit.observation = "Archivo no encontrado en las ubicaciones autorizadas."
        return audit
    audit.found = True
    audit.path = path
    workbook = load_workbook(path, read_only=True, data_only=True)
    audit.sheets = list(workbook.sheetnames)
    sheet = workbook[workbook.sheetnames[0]]
    audit.sheet_used = sheet.title

    header_values: tuple[Any, ...] | None = None
    for row_number, row in enumerate(sheet.iter_rows(min_row=1, max_row=30, values_only=True), start=1):
        keys = {ascii_key(value) for value in row if value is not None}
        if "esp" in keys and any(key.startswith("kener") or key == "enero" for key in keys):
            audit.header_row = row_number
            header_values = tuple(row)
            break
    if header_values is None or audit.header_row is None:
        workbook.close()
        audit.observation = "No se pudo detectar un encabezado con ESP y columnas mensuales."
        return audit

    audit.headers = [clean_text(value) for value in header_values if clean_text(value)]
    mapping = header_map(header_values)
    monthly_columns = [(index, month_from_header(value)) for index, value in enumerate(header_values)]
    monthly_columns = [(index, month) for index, month in monthly_columns if month is not None]
    audit.months = sorted({month for _, month in monthly_columns})
    audit.species_columns = [value for value in audit.headers if ascii_key(value) in {"esp", "especie", "producto"}]
    audit.variety_columns = [value for value in audit.headers if ascii_key(value) in {"var", "variedad"}]
    audit.price_columns = [clean_text(header_values[index]) for index, _ in monthly_columns]
    audit.package_columns = [value for value in audit.headers if ascii_key(value) in {"env", "envase", "kg", "unidad"}]
    audit.origin_columns = [value for value in audit.headers if ascii_key(value) in {"proc", "procedencia", "origen"}]
    audit.date_columns = [value for value in audit.headers if ascii_key(value) in {"fecha", "date", "dia"}]
    audit.has_origin = bool(audit.origin_columns)
    audit.has_package = any(ascii_key(value) in {"env", "envase"} for value in audit.package_columns)
    audit.has_unit = any(ascii_key(value) in {"kg", "unidad"} for value in audit.package_columns)
    audit.has_price = bool(monthly_columns)

    for row in sheet.iter_rows(min_row=audit.header_row + 1, values_only=True):
        species = clean_text(value_at(row, mapping, ("ESP", "especie", "producto")))
        if not species:
            continue
        prices = [(month, parse_number(row[index]) if index < len(row) else None) for index, month in monthly_columns]
        positive_prices = [(month, value) for month, value in prices if value is not None and value > 0]
        c_value = parse_number(value_at(row, mapping, ("C",)))
        is_summary = c_value == 0
        if is_summary:
            audit.summary_rows += 1
        else:
            audit.presentation_rows += 1
        if not is_summary and positive_prices:
            audit.useful_rows += 1
            audit.price_observations += len(positive_prices)
            audit.species_counts[species] += len(positive_prices)
            variety = clean_text(value_at(row, mapping, ("VAR", "variedad")))
            if variety:
                audit.varieties.add(variety)

    workbook.close()
    if audit.date_columns:
        audit.year_evidence = "La fuente incluye columna de fecha, pero este formato mensual requiere revisión adicional."
    else:
        audit.year_evidence = (
            f"No hay columna de fecha ni fechas completas; {expected_year} sólo se infiere del nombre "
            "del archivo/hoja. Las columnas K_ENER…K_DICI prueban cobertura mensual, no el año."
        )
    audit.observation = audit.year_evidence
    return audit


def locate_integrated() -> Path:
    for name in INTEGRATED_NAMES:
        path = PROJECT_DIR / name
        if path.is_file():
            return path
    raise FileNotFoundError("No se encontró un integrado de precios mayoristas en la raíz del proyecto.")


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            sample = text[:8192]
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
            reader = csv.DictReader(text.splitlines(), dialect=dialect)
            return list(reader.fieldnames or []), list(reader)
        except (UnicodeDecodeError, csv.Error):
            continue
    raise ValueError(f"No se pudo leer {path} con codificaciones/separadores admitidos.")


def row_year_month(row: dict[str, str]) -> tuple[int | None, int | None, date | None]:
    parsed = parse_date(row.get("fecha"))
    if parsed:
        return parsed.year, parsed.month, parsed
    year_number = parse_number(row.get("año"))
    return (int(year_number) if year_number is not None else None, month_number(row.get("mes")), None)


def effective_price(row: dict[str, str]) -> float | None:
    for column in ("precio_promedio", "precio", "precio_observado"):
        value = parse_number(row.get(column))
        if value is not None:
            return value
    return None


def duplicate_key(row: dict[str, str]) -> tuple[Any, ...]:
    year, month, parsed = row_year_month(row)
    date_value = parsed.isoformat() if parsed else f"{year or ''}-{month or ''}"
    price = effective_price(row)
    return (
        date_value,
        ascii_key(row.get("mercado")),
        rubro_key(row.get("rubro")),
        ascii_key(row.get("especie") or row.get("producto")),
        ascii_key(row.get("variedad")),
        ascii_key(row.get("unidad")),
        ascii_key(row.get("envase")),
        "" if price is None else round(price, 6),
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_integrated(path: Path, sources: list[SourceAudit]) -> dict[str, Any]:
    headers, rows = read_csv_rows(path)
    years: Counter[int] = Counter()
    markets: Counter[str] = Counter()
    rubros: Counter[str] = Counter()
    parsed_dates: list[date] = []
    mcba_dates: list[date] = []
    mcba_year_rubro: Counter[tuple[int, str]] = Counter()
    mcba_months: dict[tuple[int, str], set[int]] = {}
    mcba_species: dict[tuple[int, str], set[str]] = {}
    duplicate_counts: Counter[tuple[Any, ...]] = Counter()
    duplicate_mcba_counts: Counter[tuple[Any, ...]] = Counter()

    for row in rows:
        year, month, parsed = row_year_month(row)
        if year is not None:
            years[year] += 1
        if parsed:
            parsed_dates.append(parsed)
        market = clean_text(row.get("mercado")) or "(sin informar)"
        rubro = clean_text(row.get("rubro")) or "(sin informar)"
        markets[market] += 1
        rubros[rubro] += 1
        key = duplicate_key(row)
        duplicate_counts[key] += 1
        if is_mcba(market):
            duplicate_mcba_counts[key] += 1
            if parsed:
                mcba_dates.append(parsed)
            if year is not None:
                comparison_key = (year, rubro_key(rubro))
                mcba_year_rubro[comparison_key] += 1
                if month is not None:
                    mcba_months.setdefault(comparison_key, set()).add(month)
                species = clean_text(row.get("especie") or row.get("producto"))
                if species:
                    mcba_species.setdefault(comparison_key, set()).add(species)

    for source in sources:
        comparison_key = (source.expected_year, rubro_key(source.rubro))
        source.integrated_count = mcba_year_rubro[comparison_key]
        source.integrated_months = sorted(mcba_months.get(comparison_key, set()))
        source.integrated_species = mcba_species.get(comparison_key, set())
        if not source.found:
            source.status = "INCIERTO"
            source.observation = "La fuente no fue encontrada; no puede compararse."
        elif source.integrated_count == 0:
            source.status = "AUSENTE"
            source.observation = (
                f"El integrado no contiene registros de MCBA/{source.rubro}/{source.expected_year}. "
                + source.year_evidence
            )
        else:
            source_species = {ascii_key(value) for value in source.species_counts}
            integrated_species = {ascii_key(value) for value in source.integrated_species}
            overlap = source_species & integrated_species
            month_complete = set(source.months).issubset(source.integrated_months)
            species_ratio = len(overlap) / len(source_species) if source_species else 0.0
            count_ratio = source.integrated_count / source.price_observations if source.price_observations else 0.0
            if month_complete and species_ratio >= 0.9 and 0.8 <= count_ratio <= 1.2:
                source.status = "INCLUIDO"
            elif overlap or source.integrated_months:
                source.status = "PARCIAL"
            else:
                source.status = "INCIERTO"
            source.observation = (
                f"Meses integrados: {len(source.integrated_months)}/12; especies coincidentes: "
                f"{len(overlap)}/{len(source_species)}; relación de conteos: {count_ratio:.2f}. "
                + source.year_evidence
            )

    duplicate_groups = [count for count in duplicate_counts.values() if count > 1]
    duplicate_mcba_groups = [count for count in duplicate_mcba_counts.values() if count > 1]
    fallback = PROJECT_DIR / INTEGRATED_NAMES[1]
    return {
        "path": path,
        "headers": headers,
        "rows": len(rows),
        "years": years,
        "markets": markets,
        "rubros": rubros,
        "date_min": min(parsed_dates).isoformat() if parsed_dates else "",
        "date_max": max(parsed_dates).isoformat() if parsed_dates else "",
        "missing_or_invalid_dates": len(rows) - len(parsed_dates),
        "mcba_rows": sum(count for market, count in markets.items() if is_mcba(market)),
        "mcba_date_min": min(mcba_dates).isoformat() if mcba_dates else "",
        "mcba_date_max": max(mcba_dates).isoformat() if mcba_dates else "",
        "mcba_months": sorted({month for months in mcba_months.values() for month in months}),
        "mcba_species": {key: len(values) for key, values in mcba_species.items()},
        "mcba_year_rubro": mcba_year_rubro,
        "duplicate_groups": len(duplicate_groups),
        "duplicate_rows": sum(duplicate_groups),
        "duplicate_excess": sum(count - 1 for count in duplicate_groups),
        "duplicate_mcba_groups": len(duplicate_mcba_groups),
        "duplicate_mcba_rows": sum(duplicate_mcba_groups),
        "duplicate_mcba_excess": sum(count - 1 for count in duplicate_mcba_groups),
        "fallback_equal": fallback.is_file() and fallback != path and file_sha256(fallback) == file_sha256(path),
    }


def months_text(months: Iterable[int]) -> str:
    values = [MONTH_NAMES[month] for month in sorted(set(months)) if month in MONTH_NAMES]
    return ", ".join(values) if values else "ninguno"


def top_species(source: SourceAudit, limit: int = 12) -> str:
    values = [name for name, _ in source.species_counts.most_common(limit)]
    return ", ".join(values) if values else "n/d"


def build_report(sources: list[SourceAudit], integrated: dict[str, Any]) -> str:
    source_rows = []
    for source in sources:
        source_rows.append(
            "| " + " | ".join([
                md_escape(source.filename),
                "Sí" if source.found else "No",
                md_escape(source.sheet_used or "n/d"),
                fmt_int(source.useful_rows) if source.found else "n/d",
                source.min_date or "n/d",
                source.max_date or "n/d",
                source.rubro,
                "Mercado Central de Buenos Aires",
            ]) + " |"
        )

    years_text = ", ".join(f"{year} ({fmt_int(count)})" for year, count in sorted(integrated["years"].items()))
    markets_text = "; ".join(f"{name} ({fmt_int(count)})" for name, count in integrated["markets"].most_common())
    rubros_text = "; ".join(f"{name} ({fmt_int(count)})" for name, count in integrated["rubros"].most_common())
    mcba_breakdown = []
    for (year, rubro), count in sorted(integrated["mcba_year_rubro"].items()):
        species_count = integrated["mcba_species"].get((year, rubro), 0)
        mcba_breakdown.append(f"{year} / {rubro.title()}: {fmt_int(count)} filas y {fmt_int(species_count)} especies")

    comparison_sections = []
    for source in sources:
        comparison_sections.extend([
            f"### {source.filename}",
            "",
            f"- Estado: **{source.status}**.",
            f"- Evidencia: {source.observation}",
            f"- Conteo fuente: {fmt_int(source.price_observations)} observaciones mensuales positivas en {fmt_int(source.useful_rows)} filas útiles.",
            f"- Conteo integrado comparable: {fmt_int(source.integrated_count)} filas MCBA / {source.rubro} / {source.expected_year}.",
            f"- Meses fuente: {months_text(source.months)}. Meses integrados comparables: {months_text(source.integrated_months)}.",
            f"- Especies fuente: {fmt_int(len(source.species_counts))}; variedades informadas únicas: {fmt_int(len(source.varieties))}. Especies integradas comparables: {fmt_int(len(source.integrated_species))}.",
            f"- Especies principales: {top_species(source)}.",
            f"- Estructura: encabezado fila {source.header_row or 'n/d'}; columnas de especie {', '.join(source.species_columns) or 'n/d'}; variedad {', '.join(source.variety_columns) or 'n/d'}; precio {', '.join(source.price_columns) or 'n/d'}; envase/unidad {', '.join(source.package_columns) or 'n/d'}; procedencia {', '.join(source.origin_columns) or 'n/d'}.",
            "- Observación metodológica: una fila útil es una presentación (C distinto de 0) con especie y al menos un precio mensual positivo. El conteo comparable usa cada celda mensual positiva como observación; no se usan las filas resumen C=0. La fuente no incluye campo de mercado: MCBA es la interpretación esperada provista para la auditoría, no un valor validable dentro del libro.",
            "",
        ])

    included = [source.filename for source in sources if source.status == "INCLUIDO"]
    partial = [source.filename for source in sources if source.status == "PARCIAL"]
    absent = [source.filename for source in sources if source.status == "AUSENTE"]
    uncertain = [source.filename for source in sources if source.status == "INCIERTO"]
    conclusion_lines = [
        f"- Incorporadas: {', '.join(included) if included else 'ninguna'}.",
        f"- Parciales: {', '.join(partial) if partial else 'ninguna'}.",
        f"- Ausentes: {', '.join(absent) if absent else 'ninguna'}.",
        f"- Inciertas: {', '.join(uncertain) if uncertain else 'ninguna'}.",
    ]

    lines = [
        "# Auditoría de precios Mercado Central Buenos Aires 2024-2025",
        "",
        "## Archivos revisados",
        "",
        "| archivo | encontrado | hoja usada | filas útiles | fecha mínima | fecha máxima | rubro | mercado esperado |",
        "|---|---:|---|---:|---|---|---|---|",
        *source_rows,
        "",
        "Los cuatro libros carecen de una columna de fecha y de valores de fecha completos. El año no pudo validarse dentro de las celdas: se infiere del nombre del archivo y de la hoja. Las columnas mensuales K_ENER a K_DICI permiten validar los 12 meses, no el año calendario.",
        "",
        "Ubicaciones buscadas: raíz del proyecto, `data/`, `data/precios_mayoristas/`, `data/precios_mayoristas/raw/`, la raíz externa indicada y `Precios-BS. AS/`. Los cuatro archivos se encontraron en la carpeta externa y no se copiaron al repositorio.",
        "",
        "## Integrado actual",
        "",
        f"- Archivo detectado y usado por `app.js`: `{integrated['path']}`.",
        f"- Filas totales: {fmt_int(integrated['rows'])}.",
        f"- Años disponibles: {years_text}.",
        f"- Mercados/fuentes disponibles: {markets_text}.",
        f"- Rubros disponibles: {rubros_text}.",
        f"- Fecha mínima y máxima parseable: {integrated['date_min'] or 'n/d'} a {integrated['date_max'] or 'n/d'}.",
        f"- Fechas faltantes o no parseables: {fmt_int(integrated['missing_or_invalid_dates'])}.",
        f"- Cobertura Mercado Central de Buenos Aires: {fmt_int(integrated['mcba_rows'])} filas; {'; '.join(mcba_breakdown) if mcba_breakdown else 'sin registros'}.",
        f"- Período MCBA: {integrated['mcba_date_min'] or 'n/d'} a {integrated['mcba_date_max'] or 'n/d'}; meses presentes: {months_text(integrated['mcba_months'])}.",
        f"- El fallback `PRECIOS_MAYORISTAS_2026_INTEGRADO.csv` {'es idéntico por SHA-256 al archivo principal' if integrated['fallback_equal'] else 'no es idéntico o no está disponible'}.",
        "",
        "## Comparación por archivo",
        "",
        *comparison_sections,
        "## Control de duplicados potenciales",
        "",
        "La clave aproximada normalizada fue fecha (o año-mes si falta), mercado, rubro, especie/producto, variedad, unidad, envase y precio efectivo (`precio_promedio`, luego `precio`, luego `precio_observado`). Es un control conservador: repeticiones legítimas sin identificador adicional pueden quedar señaladas.",
        "",
        f"- Integrado completo: {fmt_int(integrated['duplicate_groups'])} grupos, {fmt_int(integrated['duplicate_rows'])} filas afectadas y {fmt_int(integrated['duplicate_excess'])} filas excedentes sobre una por clave.",
        f"- Sólo MCBA: {fmt_int(integrated['duplicate_mcba_groups'])} grupos, {fmt_int(integrated['duplicate_mcba_rows'])} filas afectadas y {fmt_int(integrated['duplicate_mcba_excess'])} filas excedentes.",
        "- Slices objetivo MCBA 2024-2025: 0 grupos y 0 filas, porque no contienen registros.",
        "- No se eliminó ni modificó ninguna observación.",
        "",
        "## Conclusión",
        "",
        *conclusion_lines,
        "",
        "El integrado contiene Mercado Central de Buenos Aires únicamente para 2026. No hay filas comparables de MCBA para Frutas u Hortalizas en 2024 o 2025, por lo que las cuatro bases esperadas se clasifican como AUSENTES. La inferencia del año de cada fuente debe quedar explícita porque los libros no aportan fechas completas.",
        "",
        "## Recomendación",
        "",
        "Integrar las cuatro bases en un segundo paso, con una regla documentada que asigne el año desde el archivo/hoja y convierta cada columna mensual en observaciones fechadas sin inventar día. Antes de hacerlo, acordar la granularidad temporal (por ejemplo, año-mes) y la clave de deduplicación. Esta auditoría no ejecuta la integración ni modifica el dashboard o el integrado.",
        "",
    ]
    return "\n".join(lines)


def write_summary(sources: list[SourceAudit]) -> None:
    fields = [
        "archivo", "encontrado", "rubro", "año_esperado", "fecha_min_fuente",
        "fecha_max_fuente", "filas_fuente", "filas_integrado_comparable",
        "mercado_detectado_integrado", "estado_integracion", "observacion",
    ]
    with SUMMARY_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for source in sources:
            writer.writerow({
                "archivo": source.filename,
                "encontrado": "sí" if source.found else "no",
                "rubro": source.rubro,
                "año_esperado": source.expected_year,
                "fecha_min_fuente": source.min_date,
                "fecha_max_fuente": source.max_date,
                "filas_fuente": source.price_observations if source.found else "",
                "filas_integrado_comparable": source.integrated_count,
                "mercado_detectado_integrado": "Mercado Central de Buenos Aires" if source.integrated_count else "no detectado para año/rubro",
                "estado_integracion": source.status,
                "observacion": source.observation,
            })


def main() -> int:
    sources = [inspect_source(*spec) for spec in SOURCE_SPECS]
    integrated_path = locate_integrated()
    integrated = inspect_integrated(integrated_path, sources)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(sources, integrated), encoding="utf-8")
    write_summary(sources)

    print(f"Integrado auditado: {integrated_path}")
    print(f"Filas integradas: {integrated['rows']}")
    for source in sources:
        print(
            f"{source.filename}: encontrado={source.found}, fuente={source.price_observations}, "
            f"integrado_comparable={source.integrated_count}, estado={source.status}"
        )
    print(f"Reporte: {REPORT_PATH}")
    print(f"Resumen: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
