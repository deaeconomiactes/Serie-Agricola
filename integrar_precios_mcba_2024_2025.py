"""Integra las listas mensuales MCBA 2024-2025 al módulo de precios.

Las fuentes sólo informan año (en el nombre del archivo) y mes (columnas
K_ENER...K_DICI). Por eso se usa el primer día de cada mes como fecha técnica
y se documenta ``fecha_precision=mensual``. No se inventan fechas diarias.

La ejecución es idempotente: antes de agregar los registros normalizados se
reemplazan únicamente las filas cuyo ``archivo_origen`` coincide exactamente
con una de las cuatro fuentes administradas por este script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import sys
import tempfile
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = Path(r"C:\Users\acer\Oficina\Info. para Serie Agricola\Precios-BS. AS")
PRIMARY_INTEGRATED = PROJECT_DIR / "PRECIOS_MAYORISTAS_INTEGRADO.csv"
FALLBACK_INTEGRATED = PROJECT_DIR / "PRECIOS_MAYORISTAS_2026_INTEGRADO.csv"
REPORT_DIR = PROJECT_DIR / "data" / "precios_mayoristas" / "reports"
REPORT_PATH = REPORT_DIR / "REPORTE_INTEGRACION_PRECIOS_MCBA_2024_2025.md"
SUMMARY_PATH = REPORT_DIR / "RESUMEN_INTEGRACION_PRECIOS_MCBA_2024_2025.csv"
PRE_SUMMARY_PATH = REPORT_DIR / "RESUMEN_PRE_INTEGRACION_MCBA_2024_2025.csv"

SOURCE_SPECS = (
    ("PHOR24_K.xlsx", "Hortalizas", 2024),
    ("PFRU24_K.xlsx", "Frutas", 2024),
    ("PHOR25_K.xlsx", "Hortalizas", 2025),
    ("PFRU25_K.xlsx", "Frutas", 2025),
)
SOURCE_NAMES = {name.lower() for name, _, _ in SOURCE_SPECS}
MONTH_COLUMNS = {
    "kener": 1,
    "kfebr": 2,
    "kmarz": 3,
    "kabri": 4,
    "kmayo": 5,
    "kjuni": 6,
    "kjuli": 7,
    "kagos": 8,
    "ksept": 9,
    "koctu": 10,
    "knovi": 11,
    "kdici": 12,
}
MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}
BASE_FIELDS = [
    "fecha", "año", "mes", "rubro", "especie", "variedad", "mercado",
    "procedencia", "localidad_corrientes", "envase", "kg_bulto", "total_kilos",
    "unidad", "precio_observado", "unidad_precio_observado", "precio_kg_estimado",
    "metodo_conversion_precio", "confianza_conversion_precio", "precio",
    "precio_min", "precio_max", "precio_promedio", "archivo_origen",
]
TRACE_FIELDS = [
    "especie_normalizada", "fuente", "mercado_fuente", "provincia_mercado",
    "pais", "origen", "procedencia_informada", "moneda", "hoja_origen",
    "fecha_precision", "periodo", "precio_cero_flag", "observaciones",
]


def ascii_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def display_text(value: Any) -> str:
    text = clean_text(value)
    return text.title() if text else ""


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


def number_text(value: float | None) -> str:
    if value is None:
        return ""
    if value.is_integer():
        return str(int(value))
    return format(value, ".10g")


def header_map(values: Iterable[Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, value in enumerate(values):
        key = ascii_key(value)
        if key and key not in result:
            result[key] = index
    return result


def cell(row: tuple[Any, ...], mapping: dict[str, int], name: str) -> Any:
    index = mapping.get(ascii_key(name))
    return row[index] if index is not None and index < len(row) else None


def source_basename(value: Any) -> str:
    text = clean_text(value).replace("\\", "/")
    return text.rsplit("/", 1)[-1].split("#", 1)[0].lower()


def is_target_source(row: dict[str, str]) -> bool:
    return source_basename(row.get("archivo_origen")) in SOURCE_NAMES


def md_escape(value: Any) -> str:
    return clean_text(value).replace("|", "\\|").replace("\n", " ")


def fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


@dataclass
class FileResult:
    filename: str
    rubro: str
    year: int
    sheet: str = ""
    source_rows: int = 0
    useful_rows: int = 0
    integrated_rows: int = 0
    excluded_rows: int = 0
    summary_rows: int = 0
    blank_rows: int = 0
    rows_without_species: int = 0
    rows_without_valid_price: int = 0
    invalid_price_cells: int = 0
    zero_or_negative_cells: int = 0
    duplicate_candidates: int = 0
    duplicate_omitted: int = 0
    months: set[int] = field(default_factory=set)
    species: set[str] = field(default_factory=set)
    rows: list[dict[str, str]] = field(default_factory=list)

    @property
    def period_min(self) -> str:
        return f"{self.year}-01" if self.months else ""

    @property
    def period_max(self) -> str:
        return f"{self.year}-12" if self.months else ""

    @property
    def main_exclusion_reason(self) -> str:
        reasons = {
            "resumen C=0": self.summary_rows,
            "fila vacía": self.blank_rows,
            "sin especie": self.rows_without_species,
            "sin precio mensual positivo": self.rows_without_valid_price,
        }
        reason, count = max(reasons.items(), key=lambda item: item[1])
        return f"{reason} ({count})" if count else "ninguno"


def locate_source(source_dir: Path, filename: str) -> Path:
    candidates = (
        source_dir / filename,
        PROJECT_DIR / filename,
        PROJECT_DIR / "data" / "precios_mayoristas" / "raw" / filename,
        PROJECT_DIR / "data" / "precios_mayoristas" / filename,
        source_dir.parent / filename,
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(f"No se encontró {filename} en las ubicaciones autorizadas.")


def read_integrated(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        fields = list(reader.fieldnames or [])
        # Preserve every historical field literally. Text normalization belongs
        # only in comparisons; applying it here would alter source paths and
        # other values outside the four managed MCBA files.
        rows = [{key: value if value is not None else "" for key, value in row.items()} for row in reader]
    missing = [field for field in BASE_FIELDS if field not in fields]
    if missing:
        raise ValueError(f"El integrado no contiene columnas requeridas: {', '.join(missing)}")
    return fields, rows


def existing_input_path() -> Path:
    if PRIMARY_INTEGRATED.is_file():
        return PRIMARY_INTEGRATED
    if FALLBACK_INTEGRATED.is_file():
        return FALLBACK_INTEGRATED
    raise FileNotFoundError("No existe PRECIOS_MAYORISTAS_INTEGRADO.csv ni su fallback 2026.")


def approximate_key(row: dict[str, str]) -> tuple[str, ...]:
    price = parse_number(row.get("precio_observado") or row.get("precio_promedio") or row.get("precio"))
    return (
        clean_text(row.get("fecha") or row.get("periodo")),
        ascii_key(row.get("mercado")),
        ascii_key(row.get("rubro")),
        ascii_key(row.get("especie_normalizada") or row.get("especie")),
        ascii_key(row.get("variedad")),
        ascii_key(row.get("unidad")),
        ascii_key(row.get("envase")),
        number_text(price),
        source_basename(row.get("archivo_origen")),
    )


def exact_source_key(row: dict[str, str]) -> tuple[str, ...]:
    return approximate_key(row) + (
        ascii_key(row.get("procedencia")),
        ascii_key(row.get("observaciones")),
    )


def build_source_row(
    filename: str,
    sheet: str,
    rubro: str,
    year: int,
    month: int,
    source_row: tuple[Any, ...],
    mapping: dict[str, int],
    price: float,
    row_number: int,
    c_value: float,
    price_column: str,
) -> dict[str, str]:
    species = display_text(cell(source_row, mapping, "ESP"))
    variety = display_text(cell(source_row, mapping, "VAR"))
    provenance = display_text(cell(source_row, mapping, "PROC"))
    package = display_text(cell(source_row, mapping, "ENV"))
    kg = parse_number(cell(source_row, mapping, "KG"))
    quality_parts = []
    for label in ("CAL", "TAM", "GRADO"):
        value = clean_text(cell(source_row, mapping, label))
        if value:
            quality_parts.append(f"{label}={value}")
    note = "Moneda interpretada como ARS por tratarse de lista local MCBA."
    if quality_parts:
        note += " Atributos fuente: " + "; ".join(quality_parts) + "."
    technical_date = date(year, month, 1).isoformat()
    price_text = number_text(price)
    return {
        "fecha": technical_date,
        "año": str(year),
        "mes": MONTH_NAMES[month],
        "rubro": rubro,
        "especie": species,
        "variedad": variety,
        "mercado": "Mercado Central de Buenos Aires",
        "procedencia": provenance,
        "localidad_corrientes": "",
        "envase": package,
        "kg_bulto": number_text(kg),
        "total_kilos": "",
        "unidad": "$/kg",
        "precio_observado": price_text,
        "unidad_precio_observado": "$/kg",
        "precio_kg_estimado": price_text,
        "metodo_conversion_precio": "precio informado por kg (columna K_mes)",
        "confianza_conversion_precio": "Alta",
        "precio": price_text,
        "precio_min": "",
        "precio_max": "",
        "precio_promedio": "",
        "archivo_origen": (
            f"{filename}#hoja={sheet};fila={row_number};C={number_text(c_value)};columna={price_column}"
        ),
        "especie_normalizada": ascii_key(species).upper(),
        "fuente": "Mercado Central de Buenos Aires",
        "mercado_fuente": "Mercado Central de Buenos Aires",
        "provincia_mercado": "Buenos Aires",
        "pais": "Argentina",
        "origen": provenance,
        "procedencia_informada": "sí" if provenance else "no",
        "moneda": "ARS",
        "hoja_origen": sheet,
        "fecha_precision": "mensual",
        "periodo": f"{year}-{month:02d}",
        "precio_cero_flag": "no",
        "observaciones": note,
    }


def inspect_and_transform(path: Path, rubro: str, year: int) -> FileResult:
    result = FileResult(filename=path.name, rubro=rubro, year=year)
    workbook = load_workbook(path, read_only=True, data_only=True)
    if len(workbook.sheetnames) != 1:
        workbook.close()
        raise ValueError(f"{path.name}: se esperaba una hoja y se encontraron {len(workbook.sheetnames)}.")
    sheet = workbook[workbook.sheetnames[0]]
    result.sheet = sheet.title
    header = tuple(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)))
    mapping = header_map(header)
    required = {"c", "esp", "var", "proc", "env", "kg", *MONTH_COLUMNS}
    missing = sorted(required - set(mapping))
    if missing:
        workbook.close()
        raise ValueError(f"{path.name}: faltan encabezados requeridos: {', '.join(missing)}")
    if ascii_key(sheet.title) != ascii_key(path.stem):
        workbook.close()
        raise ValueError(f"{path.name}: la hoja {sheet.title!r} no coincide con el nombre esperado.")

    candidate_rows: list[dict[str, str]] = []
    for row_number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not any(value not in (None, "") for value in values):
            result.blank_rows += 1
            continue
        result.source_rows += 1
        species = clean_text(cell(values, mapping, "ESP"))
        c_value = parse_number(cell(values, mapping, "C"))
        if c_value == 0:
            result.summary_rows += 1
            continue
        if c_value is None or c_value < 0:
            result.rows_without_species += 1
            continue
        if not species:
            result.rows_without_species += 1
            continue

        valid_in_row = 0
        for header_key, month in MONTH_COLUMNS.items():
            raw_price = cell(values, mapping, header_key)
            source_price_column = clean_text(header[mapping[header_key]])
            price = parse_number(raw_price)
            if raw_price not in (None, "") and price is None:
                result.invalid_price_cells += 1
                continue
            if price is None:
                continue
            if price <= 0:
                result.zero_or_negative_cells += 1
                continue
            candidate_rows.append(
                build_source_row(
                    path.name, sheet.title, rubro, year, month, values, mapping, price,
                    row_number, c_value, source_price_column,
                )
            )
            result.months.add(month)
            result.species.add(display_text(species))
            valid_in_row += 1
        if valid_in_row:
            result.useful_rows += 1
        else:
            result.rows_without_valid_price += 1

    workbook.close()
    if result.months != set(range(1, 13)):
        raise ValueError(
            f"{path.name}: cobertura mensual incompleta ({sorted(result.months)}); se detiene la integración."
        )

    approx_counts = Counter(approximate_key(row) for row in candidate_rows)
    result.duplicate_candidates = sum(count - 1 for count in approx_counts.values() if count > 1)
    seen_exact: set[tuple[str, ...]] = set()
    for row in candidate_rows:
        key = exact_source_key(row)
        if key in seen_exact:
            result.duplicate_omitted += 1
            continue
        seen_exact.add(key)
        result.rows.append(row)
    result.integrated_rows = len(result.rows)
    result.excluded_rows = result.source_rows - result.useful_rows
    return result


def coverage(rows: list[dict[str, str]], field: str) -> Counter[str]:
    return Counter(clean_text(row.get(field)) or "(sin informar)" for row in rows)


def mcba_year_coverage(rows: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        if ascii_key(row.get("mercado")) == "mercadocentraldebuenosaires":
            year = clean_text(row.get("año")) or clean_text(row.get("fecha"))[:4]
            counts[year or "(sin informar)"] += 1
    return counts


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_pre_summary_once(base_rows: list[dict[str, str]], input_path: Path) -> None:
    if PRE_SUMMARY_PATH.exists():
        return
    records: list[dict[str, Any]] = [
        {"metrica": "archivo_base", "dimension": "ruta", "valor": input_path.name, "cantidad": ""},
        {"metrica": "filas_base_sin_fuentes_objetivo", "dimension": "total", "valor": "", "cantidad": len(base_rows)},
    ]
    for field in ("año", "mercado", "rubro"):
        for value, count in sorted(coverage(base_rows, field).items()):
            records.append({"metrica": "cobertura_previa", "dimension": field, "valor": value, "cantidad": count})
    for value, count in sorted(mcba_year_coverage(base_rows).items()):
        records.append({"metrica": "cobertura_previa_mcba", "dimension": "año", "valor": value, "cantidad": count})
    write_csv(PRE_SUMMARY_PATH, ["metrica", "dimension", "valor", "cantidad"], records)


def atomic_write_integrated(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8-sig", newline="", suffix=".csv", prefix="mcba_", dir=path.parent, delete=False
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})
        temp_path.replace(path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summary_rows(results: list[FileResult]) -> list[dict[str, Any]]:
    return [
        {
            "archivo": result.filename,
            "rubro": result.rubro,
            "año": result.year,
            "filas_fuente": result.source_rows,
            "filas_utiles": result.useful_rows,
            "filas_integradas": result.integrated_rows,
            "filas_excluidas": result.excluded_rows,
            "motivo_exclusion_principal": result.main_exclusion_reason,
            "periodo_min": result.period_min,
            "periodo_max": result.period_max,
            "duplicados_potenciales": result.duplicate_candidates,
            "duplicados_omitidos": result.duplicate_omitted,
        }
        for result in results
    ]


def build_report(
    results: list[FileResult],
    base_rows: list[dict[str, str]],
    final_rows: list[dict[str, str]],
    duplicates_against_base: int,
) -> str:
    added = sum(result.integrated_rows for result in results)
    file_table = []
    for result in results:
        file_table.append(
            "| " + " | ".join([
                result.filename,
                result.rubro,
                str(result.year),
                fmt_int(result.source_rows),
                fmt_int(result.useful_rows),
                fmt_int(result.integrated_rows),
                fmt_int(result.excluded_rows),
                md_escape(result.main_exclusion_reason),
                result.period_min,
                result.period_max,
            ]) + " |"
        )

    def coverage_lines(field: str) -> list[str]:
        return [f"  - {value}: {fmt_int(count)}" for value, count in sorted(coverage(final_rows, field).items())]

    mcba = mcba_year_coverage(final_rows)
    duplicate_candidates = sum(result.duplicate_candidates for result in results)
    duplicate_omitted = sum(result.duplicate_omitted for result in results)
    lines = [
        "# Integración de precios MCBA 2024-2025",
        "",
        "## Archivos integrados",
        "",
        "| archivo | rubro | año | filas fuente | filas útiles | filas integradas | filas excluidas | motivo de exclusión principal | período mínimo | período máximo |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---|",
        *file_table,
        "",
        "## Integrado actualizado",
        "",
        f"- Filas antes (base sin las cuatro fuentes administradas): {fmt_int(len(base_rows))}.",
        f"- Filas nuevas normalizadas: {fmt_int(added)}.",
        f"- Filas después: {fmt_int(len(final_rows))}.",
        "- Cobertura por año:",
        *coverage_lines("año"),
        "- Cobertura por mercado:",
        *coverage_lines("mercado"),
        "- Cobertura por rubro:",
        *coverage_lines("rubro"),
        f"- Cobertura MCBA 2024: {fmt_int(mcba.get('2024', 0))} filas.",
        f"- Cobertura MCBA 2025: {fmt_int(mcba.get('2025', 0))} filas.",
        f"- Cobertura MCBA 2026: {fmt_int(mcba.get('2026', 0))} filas.",
        "",
        "## Duplicados",
        "",
        f"- Coincidencias contra la base previa con la clave aproximada solicitada: {fmt_int(duplicates_against_base)}.",
        f"- Duplicados potenciales dentro de las fuentes con la clave aproximada: {fmt_int(duplicate_candidates)}.",
        f"- Duplicados exactos omitidos: {fmt_int(duplicate_omitted)}.",
        "- Los potenciales se conservaron porque difieren en procedencia y/o CAL/TAM/GRADO; eliminarlos con la clave corta perdería observaciones legítimas.",
        "- En una reejecución se reemplazan sólo las filas de los cuatro `archivo_origen`; no se acumulan copias.",
        "",
        "## Metodología",
        "",
        "- Mercado y fuente: `Mercado Central de Buenos Aires`. Provincia del mercado: Buenos Aires. País: Argentina.",
        "- Período: el año se toma del archivo/hoja y el mes de `K_ENER` a `K_DICI`. `fecha` usa el primer día del mes, `fecha_precision=mensual` y `periodo=YYYY-MM`. La fecha es un ancla técnica mensual, no una observación diaria.",
        "- Precio: las columnas `K_mes` se interpretan como precio informado por kg. Se conserva `KG` como peso del bulto, pero el precio no se divide nuevamente por ese valor.",
        "- Moneda: ARS, interpretada por tratarse de listas locales MCBA; la fuente no contiene un campo monetario explícito.",
        "- Unidad: `$/kg`, siguiendo la convención del integrado y de MCBA 2026.",
        "- Procedencia: se conserva `PROC` cuando existe. No se confunde con el mercado ni se imputa cuando está vacía.",
        "- Exclusiones: filas vacías, resúmenes `C=0`, filas sin especie y celdas mensuales sin precio numérico positivo.",
        "- Trazabilidad: se preservan archivo, hoja, período, precisión temporal y atributos CAL/TAM/GRADO en observaciones.",
        "- Dashboard: las observaciones con `fecha_precision=mensual` se excluyen de la frecuencia diaria; la fecha ancla no se presenta como cotización diaria.",
        "",
        "## Conclusión",
        "",
        "Las cuatro bases quedaron incorporadas como series mensuales MCBA 2024-2025. El proceso conserva MCBA 2026 y Mercado de Corrientes, y es idempotente por reemplazo controlado según `archivo_origen`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Integra precios mensuales MCBA 2024-2025")
    parser.add_argument("source_dir", nargs="?", type=Path, default=DEFAULT_SOURCE_DIR)
    args = parser.parse_args()
    source_dir = args.source_dir.expanduser().resolve()

    input_path = existing_input_path()
    existing_fields, existing_rows = read_integrated(input_path)
    base_rows = [row for row in existing_rows if not is_target_source(row)]
    results: list[FileResult] = []
    for filename, rubro, year in SOURCE_SPECS:
        path = locate_source(source_dir, filename)
        results.append(inspect_and_transform(path, rubro, year))

    new_rows = [row for result in results for row in result.rows]
    baseline_keys = {approximate_key(row) for row in base_rows}
    duplicates_against_base = sum(approximate_key(row) in baseline_keys for row in new_rows)
    if duplicates_against_base:
        raise ValueError(
            f"Se detectaron {duplicates_against_base} coincidencias contra la base previa; no se sobrescribe el integrado."
        )
    final_rows = base_rows + new_rows
    fields = list(existing_fields)
    for field in BASE_FIELDS + TRACE_FIELDS:
        if field not in fields:
            fields.append(field)

    expected = {2024: {"Hortalizas": 2211, "Frutas": 1956}, 2025: {"Hortalizas": 2451, "Frutas": 2090}}
    actual: Counter[tuple[int, str]] = Counter()
    for result in results:
        actual[(result.year, result.rubro)] += result.integrated_rows
    for year, rubros in expected.items():
        for rubro, count in rubros.items():
            if actual[(year, rubro)] != count:
                raise RuntimeError(
                    f"Control de aceptación falló para {year}/{rubro}: {actual[(year, rubro)]} != {count}."
                )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_pre_summary_once(base_rows, input_path)
    write_csv(
        SUMMARY_PATH,
        [
            "archivo", "rubro", "año", "filas_fuente", "filas_utiles", "filas_integradas",
            "filas_excluidas", "motivo_exclusion_principal", "periodo_min", "periodo_max",
            "duplicados_potenciales", "duplicados_omitidos",
        ],
        summary_rows(results),
    )
    REPORT_PATH.write_text(
        build_report(results, base_rows, final_rows, duplicates_against_base), encoding="utf-8"
    )

    atomic_write_integrated(PRIMARY_INTEGRATED, fields, final_rows)
    shutil.copyfile(PRIMARY_INTEGRATED, FALLBACK_INTEGRATED)
    if file_sha256(PRIMARY_INTEGRATED) != file_sha256(FALLBACK_INTEGRATED):
        raise RuntimeError("El archivo principal y el fallback no quedaron idénticos.")

    print(f"Integrado de entrada: {input_path}")
    print(f"Filas base sin fuentes objetivo: {len(base_rows)}")
    print(f"Filas MCBA 2024-2025 integradas: {len(new_rows)}")
    print(f"Filas finales: {len(final_rows)}")
    for result in results:
        print(f"{result.filename}: {result.integrated_rows} observaciones, {result.period_min} a {result.period_max}")
    print(f"Principal: {PRIMARY_INTEGRATED}")
    print(f"Fallback sincronizado: {FALLBACK_INTEGRATED}")
    print(f"Reporte: {REPORT_PATH}")
    print(f"Resumen: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
