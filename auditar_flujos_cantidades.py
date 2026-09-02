"""Audita origen, destino y productos agregados de la base de cantidades.

La auditoría no modifica la base integrada: produce resúmenes reproducibles y
deja cada registro con destino no clasificable en un CSV de casos.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
INPUT_PATH = PROJECT / "REGISTRO 2025 INTEGRADO.csv"
INVALID_VALUES = {
    "", "#REF!", "#N/A", "#VALUE!", "#DIV/0!", "#NAME?", "#NULL!", "#NUM!",
    "UNDEFINED", "NAN", "NULL", "NONE",
}
VALID_DESTINATIONS = {"Buenos Aires", "Corrientes"}


def clean(value: object) -> str:
    text = "" if value is None else str(value).replace("\ufeff", "").strip()
    return "" if text.upper() in INVALID_VALUES else re.sub(r"\s+", " ", text)


def raw(value: object) -> str:
    return "" if value is None else re.sub(r"\s+", " ", str(value).replace("\ufeff", "").strip())


def key(value: object) -> str:
    text = clean(value).replace("�", "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"[^A-Z0-9]", "", text.upper())


LOCATION_ALIASES = {
    "BUENOSAIRES": "Buenos Aires", "BSAS": "Buenos Aires", "CABA": "Ciudad Autónoma de Buenos Aires",
    "CAPITALFEDERAL": "Ciudad Autónoma de Buenos Aires", "CIUDADAUTONOMADEBUENOSAIRES": "Ciudad Autónoma de Buenos Aires",
    "CORRIENTES": "Corrientes", "CTES": "Corrientes", "MENDOZA": "Mendoza", "SALTA": "Salta", "MDPLAT": "Mar del Plata",
    "JUJUY": "Jujuy", "SANJUAN": "San Juan", "SANTAFE": "Santa Fe",
    "ENTRERIOS": "Entre Ríos", "ERIOS": "Entre Ríos", "RNEGRO": "Río Negro", "RONEGRO": "Río Negro", "RIONEGRO": "Río Negro", "NEUQUEN": "Neuquén",
    "CORDOBA": "Córdoba", "CRDOBA": "Córdoba", "TUCUMAN": "Tucumán", "MISIONES": "Misiones",
    "FORMOSA": "Formosa", "CHACO": "Chaco", "CHUBUT": "Chubut", "SANLUIS": "San Luis",
    "LARIOJA": "La Rioja", "LAPAMPA": "La Pampa", "CATAMARCA": "Catamarca", "CATAMARC": "Catamarca",
    "SANTIAGODELESTERO": "Santiago del Estero", "SGOEST": "Santiago del Estero", "SGODELESTERO": "Santiago del Estero", "STACRUZ": "Santa Cruz",
    "SANTACRUZ": "Santa Cruz", "MARDELPLATA": "Mar del Plata", "MDP": "Mar del Plata",
    "SANPEDRO": "San Pedro", "SPEDRO": "San Pedro", "PTO RICO": "Puerto Rico", "PTORICO": "Puerto Rico",
    "BRASIL": "Brasil", "CHILE": "Chile", "BOLIVIA": "Bolivia", "PARAGUAY": "Paraguay",
    "URUGUAY": "Uruguay", "PERU": "Perú", "ECUADOR": "Ecuador", "COLOMBIA": "Colombia",
    "MEXICO": "México", "ESPANA": "España", "ITALIA": "Italia", "GRECIA": "Grecia",
}

DESTINATION_ALIASES = {
    "BUENOSAIRES": "Buenos Aires", "BSAS": "Buenos Aires", "CABA": "Buenos Aires",
    "CAPITALFEDERAL": "Buenos Aires", "CIUDADAUTONOMADEBUENOSAIRES": "Buenos Aires",
    "MERCADOCENTRAL": "Buenos Aires", "MERCADOCENTRALDEBUENOSAIRES": "Buenos Aires",
    "CORRIENTES": "Corrientes", "CTES": "Corrientes", "MERCADODECORRIENTES": "Corrientes",
}


def normalize_location(value: object) -> str:
    raw = clean(value)
    if not raw:
        return ""
    return LOCATION_ALIASES.get(key(raw), raw.title())


def normalize_origin(value: object) -> str:
    return normalize_location(value)


def normalize_destination(value: object) -> str:
    raw = clean(value)
    return DESTINATION_ALIASES.get(key(raw), "") if raw else ""


def parse_weight(value: object) -> float:
    raw = clean(value).replace(" ", "")
    if not raw:
        return 0.0
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def normalize_tomato_product(species: object, variety: object) -> tuple[str, str]:
    species_key = key(species)
    variety_text = clean(variety)
    variety_key = key(variety_text)
    is_tomato = species_key.startswith("TOMATE") or variety_key.startswith("TOMATE")
    if not is_tomato:
        return "", "no_aplica"
    species_specific = clean(species)
    if key(species).startswith("TOMATE") and species_key != "TOMATE":
        species_specific = re.sub(r"^tomate\s+", "", species_specific, flags=re.I)
    variety_specific = re.sub(r"^tomate\s+", "", variety_text, flags=re.I)
    generic = {"", "TOMATE", "SINVARIEDAD", "SINVARIED"}
    specific = species_specific if key(species_specific) not in generic else ""
    if not specific and key(species) == "TOMATE" and key(variety_specific) not in generic:
        specific = variety_specific
    if specific:
        return f"Tomate {specific.title()}", "tomate_especifico"
    if not variety_text or key(variety_text) in generic:
        return "Tomate sin variedad especificada", "tomate_sin_variedad"
    return "Tomate sin variedad especificada", "tomate_generico"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value).replace("|", "/") for value in row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> None:
    with INPUT_PATH.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))

    origin_counts: Counter[str] = Counter()
    destination_counts: Counter[tuple[str, str]] = Counter()
    combinations: Counter[tuple[str, str, str]] = Counter()
    origin_weights: Counter[str] = Counter()
    destination_weights: Counter[tuple[str, str]] = Counter()
    combination_weights: Counter[tuple[str, str, str]] = Counter()
    origin_raw: defaultdict[str, Counter[str]] = defaultdict(Counter)
    destination_raw: defaultdict[str, Counter[str]] = defaultdict(Counter)
    suspicious_rows: list[dict[str, object]] = []
    tomato_rows: list[dict[str, object]] = []
    tomato_generic_records = 0
    tomato_without_variety_records = 0
    invalid_fields: Counter[str] = Counter()

    for number, row in enumerate(rows, start=2):
        origin_raw_value = raw(row.get("PROCEDENCIA"))
        destination_raw_value = raw(row.get("MERCADO"))
        origin = normalize_origin(origin_raw_value)
        destination = normalize_destination(destination_raw_value)
        weight = parse_weight(row.get("PESO"))
        origin_counts[origin or "(vacío / inválido)"] += 1
        origin_raw[origin or "(vacío / inválido)"][origin_raw_value or "(vacío / inválido)"] += 1
        destination_counts[(destination or "(sospechoso / inválido)", destination_raw_value or "(vacío / inválido)")] += 1
        destination_raw[destination or "(sospechoso / inválido)"][destination_raw_value or "(vacío / inválido)"] += 1
        combinations[(origin or "(vacío / inválido)", destination or "(sospechoso / inválido)", destination_raw_value or "(vacío / inválido)")] += 1
        origin_weights[origin or "(vacío / inválido)"] += weight
        destination_weights[(destination or "(sospechoso / inválido)", destination_raw_value or "(vacío / inválido)")] += weight
        combination_weights[(origin or "(vacío / inválido)", destination or "(sospechoso / inválido)", destination_raw_value or "(vacío / inválido)")] += weight

        for field in ("PROCEDENCIA", "MERCADO", "ESPECIE", "VARIEDAD", "MUNICIPIO", "SERIE"):
            if not clean(row.get(field)):
                invalid_fields[field] += 1

        if not destination:
            reason = "vacío o inválido" if not clean(destination_raw_value) else "valor no reconocido como mercado de cantidades"
            if normalize_origin(destination_raw_value) in set(origin_counts) or key(destination_raw_value) in {"MENDOZA", "SALTA", "JUJUY", "CORDOBA", "RONEGRO", "SANTAFE", "ENTRERIOS", "BRASIL", "CHILE", "PARAGUAY"}:
                reason += "; parece origen/procedencia"
            suspicious_rows.append({
                "fila_csv": number, "destino_original": destination_raw_value,
                "destino_normalizado": "", "motivo": reason,
                "origen_original": origin_raw_value, "origen_normalizado": origin,
                "especie_original": raw(row.get("ESPECIE")), "variedad_original": raw(row.get("VARIEDAD")),
                "peso": raw(row.get("PESO")), "unidad": raw(row.get("UNIDAD")),
            })

        product, case_type = normalize_tomato_product(row.get("ESPECIE"), row.get("VARIEDAD"))
        if product:
            if key(row.get("ESPECIE")) == "TOMATE":
                tomato_generic_records += 1
            if case_type == "tomate_sin_variedad":
                tomato_without_variety_records += 1
            tomato_rows.append({
                "fila_csv": number, "especie_original": raw(row.get("ESPECIE")),
                "variedad_original": raw(row.get("VARIEDAD")), "producto_normalizado": product,
                "tipo_caso": case_type, "origen": origin, "destino_original": destination_raw_value,
                "destino_normalizado": destination, "peso": raw(row.get("PESO")), "fecha": raw(row.get("FECHA")),
            })

    origin_summary = []
    for origin, count in sorted(origin_counts.items(), key=lambda item: (-item[1], item[0])):
        origin_summary.append({"origen_normalizado": origin, "registros": count, "peso_tn": round(origin_weights[origin], 3), "valores_originales": ", ".join(f"{raw} ({n})" for raw, n in origin_raw[origin].most_common())})

    destination_summary = []
    for (destination, raw_destination), count in sorted(destination_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])):
        destination_summary.append({"destino_normalizado": destination if destination in VALID_DESTINATIONS else "", "destino_original": raw_destination, "clasificacion": "válido" if destination in VALID_DESTINATIONS else "sospechoso", "registros": count, "peso_tn": round(destination_weights[(destination, raw_destination)], 3)})

    combination_summary = []
    for (origin, destination, raw_destination), count in sorted(combinations.items(), key=lambda item: (-item[1], item[0])):
        combination_summary.append({"origen_normalizado": origin, "destino_normalizado": destination if destination in VALID_DESTINATIONS else "", "destino_original": raw_destination, "clasificacion_destino": "válido" if destination in VALID_DESTINATIONS else "sospechoso", "registros": count, "peso_tn": round(combination_weights[(origin, destination, raw_destination)], 3)})

    write_csv(PROJECT / "RESUMEN_ORIGENES_CANTIDADES.csv", origin_summary, ["origen_normalizado", "registros", "peso_tn", "valores_originales"])
    write_csv(PROJECT / "RESUMEN_DESTINOS_CANTIDADES.csv", destination_summary, ["destino_normalizado", "destino_original", "clasificacion", "registros", "peso_tn"])
    write_csv(PROJECT / "RESUMEN_ORIGEN_DESTINO_CANTIDADES.csv", combination_summary, ["origen_normalizado", "destino_normalizado", "destino_original", "clasificacion_destino", "registros", "peso_tn"])
    write_csv(PROJECT / "CASOS_DESTINO_SOSPECHOSO_CANTIDADES.csv", suspicious_rows, list(suspicious_rows[0]) if suspicious_rows else ["fila_csv", "destino_original", "destino_normalizado", "motivo"])
    write_csv(PROJECT / "CASOS_PRODUCTO_AGREGADO_CANTIDADES.csv", tomato_rows, list(tomato_rows[0]) if tomato_rows else ["fila_csv", "especie_original", "variedad_original", "producto_normalizado", "tipo_caso"])

    valid_destination_records = sum(count for (destination, _), count in destination_counts.items() if destination in VALID_DESTINATIONS)
    tomato_generic = tomato_generic_records
    tomato_without_variety = tomato_without_variety_records
    top_destinations = sorted(destination_counts.items(), key=lambda item: -item[1])[:20]
    top_combinations = sorted(combinations.items(), key=lambda item: -item[1])[:30]
    origin_rows = [[row["origen_normalizado"], row["registros"], row["peso_tn"]] for row in origin_summary]
    destination_rows = [[row["destino_original"], row["destino_normalizado"] or "—", row["clasificacion"], row["registros"]] for row in destination_summary]
    combination_rows = [[origin, destination if destination in VALID_DESTINATIONS else "—", raw_destination, count, round(combination_weights[(origin, destination, raw_destination)], 3)] for (origin, destination, raw_destination), count in top_combinations]

    report = f"""# Auditoría de flujos de cantidades

## 1. Resumen ejecutivo

- Archivo auditado: `REGISTRO 2025 INTEGRADO.csv`.
- Registros leídos: **{len(rows):,}**.
- Destinos válidos para el filtro ejecutivo: **Buenos Aires** y **Corrientes**.
- Registros con destino válido: **{valid_destination_records:,}**.
- Registros con destino sospechoso, vacío o inválido: **{len(suspicious_rows):,}**.
- Registros identificados como tomate: **{len(tomato_rows):,}**; genéricos: **{tomato_generic:,}**; sin variedad: **{tomato_without_variety:,}**.

La auditoría es no destructiva. Los valores originales se conservan en los CSV de casos y no se reescribe la base integrada.

## 2. Orígenes detectados

{markdown_table(["Origen normalizado", "Registros", "Peso tn"], origin_rows)}

Las variantes de escritura se detallan en `RESUMEN_ORIGENES_CANTIDADES.csv`.

## 3. Destinos detectados

{markdown_table(["Destino original", "Destino normalizado", "Clasificación", "Registros"], destination_rows)}

{len(destination_summary)} valores originales de destino fueron detectados.

## 4. Combinaciones origen-destino

Principales combinaciones por cantidad de registros:

{markdown_table(["Origen", "Destino normalizado", "Destino original", "Registros", "Peso tn"], combination_rows)}

El detalle completo está en `RESUMEN_ORIGEN_DESTINO_CANTIDADES.csv`.

## 5. Destinos sospechosos

Se detectaron **{len(suspicious_rows):,}** registros fuera de las equivalencias válidas. No se eliminan: se excluyen del filtro visible de destino y se conservan en `CASOS_DESTINO_SOSPECHOSO_CANTIDADES.csv`.

Principales valores observados:

{markdown_table(["Destino original", "Normalización", "Clasificación", "Registros"], [[raw_destination, destination if destination in VALID_DESTINATIONS else "—", "válido" if destination in VALID_DESTINATIONS else "sospechoso", count] for (destination, raw_destination), count in top_destinations])}

Campos vacíos o inválidos: {", ".join(f"{field}={count}" for field, count in sorted(invalid_fields.items()))}.

## 6. Revisión de productos agregados

La regla derivada `producto_normalizado` separa `Tomate Redondo`, `Tomate Perita`, `Tomate Cherry`, `Tomate Larga Vida`, `Tomate Platense` y otros tipos existentes. Los casos sin variedad se etiquetan como `Tomate sin variedad especificada`; ningún registro original se elimina.

El detalle de los {len(tomato_rows):,} registros relacionados con tomate está en `CASOS_PRODUCTO_AGREGADO_CANTIDADES.csv`.

## 7. Recomendaciones de corrección

1. Mantener `Buenos Aires` y `Corrientes` como únicas opciones visibles del filtro Destino de cantidades.
2. Mantener los destinos sospechosos para auditoría, sin sumarlos a una opción ejecutiva válida.
3. Mantener Origen amplio, normalizando tildes, abreviaturas y errores de planilla.
4. Usar `producto_normalizado` para filtros, rankings y tablas; conservar `ESPECIE` y `VARIEDAD` originales.
5. Cuando se selecciona un producto específico y Origen es `Todos`, desagregar la tabla de cantidades por origen.
6. Revisar en la fuente de integración la asignación de `MERCADO` para los registros cuyo valor coincide con una procedencia.
"""
    (PROJECT / "REPORTE_AUDITORIA_FLUJOS_CANTIDADES.md").write_text(report, encoding="utf-8")
    print(f"Leídos {len(rows)} registros; destinos sospechosos={len(suspicious_rows)}; casos tomate={len(tomato_rows)}")


if __name__ == "__main__":
    main()
