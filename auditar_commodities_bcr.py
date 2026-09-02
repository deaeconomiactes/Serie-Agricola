"""Audita la base independiente de commodities agrícolas BCR.

No cruza commodities con cantidades ni precios frutihortícolas. Genera
resúmenes reproducibles y un reporte metodológico en ``data/commodities_bcr``.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_DIR / "data" / "commodities_bcr" / "processed" / "COMMODITIES_BCR_INTEGRADO.csv"
REPORT_DIR = PROJECT_DIR / "data" / "commodities_bcr" / "reports"
REPORT_PATH = REPORT_DIR / "REPORTE_AUDITORIA_COMMODITIES_BCR.md"
OUTPUTS = {
    "coverage": REPORT_DIR / "RESUMEN_COBERTURA_COMMODITIES_BCR.csv",
    "commodities": REPORT_DIR / "RESUMEN_COMMODITIES_BCR.csv",
    "series": REPORT_DIR / "RESUMEN_SERIES_COMMODITIES_BCR.csv",
    "problems": REPORT_DIR / "CASOS_PROBLEMATICOS_COMMODITIES_BCR.csv",
}
EXPECTED_COLUMNS = [
    "fecha", "año", "mes", "commodity", "fuente", "mercado", "tipo_precio", "moneda", "unidad",
    "precio", "frecuencia", "condicion_comercial", "archivo_origen", "fecha_integracion", "observaciones",
]


def read_input(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            frame = pd.read_csv(path, sep=None, engine="python", dtype=str, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError("No se pudo leer el CSV con UTF-8, cp1252 ni latin-1.")
    for column in EXPECTED_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[EXPECTED_COLUMNS].fillna("")


def parse_number(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(" ", "")
    if not text or text.lower() in {"nan", "nat", "none", "null", "n/a", "na", "-", "–"}:
        return np.nan
    text = "".join(char for char in text if char.isdigit() or char in ",.-")
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        pieces = text.split(",")
        text = "".join(pieces[:-1]) + "." + pieces[-1] if len(pieces[-1]) <= 2 else "".join(pieces)
    elif "." in text:
        left, right = text.rsplit(".", 1)
        text = left.replace(".", "") + ("." + right if len(right) <= 2 else right)
    try:
        return float(text)
    except ValueError:
        return np.nan


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for column in EXPECTED_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    frame["fecha_parseada"] = pd.to_datetime(frame["fecha"], errors="coerce", format="mixed", dayfirst=True)
    frame["fecha_valida"] = frame["fecha_parseada"].notna()
    frame["precio_num"] = frame["precio"].map(parse_number)
    frame["precio_valido"] = frame["precio_num"].notna() & (frame["precio_num"] > 0)
    frame["precio_cero"] = frame["precio_num"].notna() & frame["precio_num"].eq(0)
    frame["precio_negativo"] = frame["precio_num"].notna() & frame["precio_num"].lt(0)
    frame["moneda_valida"] = frame["moneda"].ne("") & ~frame["moneda"].str.lower().isin({"sin determinar", "nan", "none"})
    frame["unidad_valida"] = frame["unidad"].ne("") & ~frame["unidad"].str.lower().isin({"sin determinar", "nan", "none"})
    frame["año_num"] = frame["fecha_parseada"].dt.year
    frame["mes_num"] = frame["fecha_parseada"].dt.month
    return frame


def add_outliers(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    frame = frame.copy()
    frame["outlier_iqr"] = False
    stats: dict[str, dict[str, float]] = {}
    for commodity, group in frame[frame["precio_valido"]].groupby("commodity", dropna=False):
        values = group["precio_num"]
        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = frame["commodity"].eq(commodity) & frame["precio_valido"] & ((frame["precio_num"] < lower) | (frame["precio_num"] > upper))
        frame.loc[mask, "outlier_iqr"] = True
        stats[str(commodity)] = {"q1": q1, "q3": q3, "iqr": iqr, "limite_inferior": lower, "limite_superior": upper, "outliers": int(mask.sum())}
    return frame, stats


def _valid_prices(group: pd.DataFrame) -> pd.Series:
    return group.loc[group["precio_valido"], "precio_num"]


def _stats(group: pd.DataFrame) -> dict[str, Any]:
    prices = _valid_prices(group)
    if prices.empty:
        return {"precio_promedio": np.nan, "precio_minimo": np.nan, "precio_maximo": np.nan, "coeficiente_variacion": np.nan}
    mean = prices.mean()
    return {
        "precio_promedio": mean, "precio_minimo": prices.min(), "precio_maximo": prices.max(),
        "coeficiente_variacion": prices.std(ddof=1) / mean if len(prices) > 1 and mean else np.nan,
    }


def _date_metrics(group: pd.DataFrame) -> dict[str, Any]:
    dated = group.loc[group["fecha_valida"]]
    if dated.empty:
        return {"fechas_distintas": 0, "fecha_minima": "", "fecha_maxima": "", "años_disponibles": "", "meses_disponibles": ""}
    dates = dated["fecha_parseada"].dt.normalize()
    years = sorted(dated["fecha_parseada"].dt.year.dropna().astype(int).unique())
    months = sorted({f"{year}-{month:02d}" for year, month in zip(dated["año_num"], dated["mes_num"])})
    return {
        "fechas_distintas": int(dates.nunique()), "fecha_minima": dates.min().date().isoformat(),
        "fecha_maxima": dates.max().date().isoformat(), "años_disponibles": ", ".join(map(str, years)),
        "meses_disponibles": ", ".join(months),
    }


def coverage_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    dated = frame[frame["fecha_valida"]]
    groups = [("general", "(todos)", "(todos)", dated.groupby(lambda _: True))]
    groups = []
    if not dated.empty:
        groups.extend(("año", "(todos)", str(int(year)), group) for year, group in dated.groupby("año_num"))
        groups.extend(("commodity", str(commodity) or "(sin informar)", "(todos)", group) for commodity, group in dated.groupby("commodity", dropna=False))
        groups.extend(("commodity_año", str(commodity) or "(sin informar)", str(int(year)), group) for (commodity, year), group in dated.groupby(["commodity", "año_num"], dropna=False))
    for level, commodity, year, group in groups:
        rows.append({"nivel": level, "commodity": commodity, "año": year, "cantidad_registros": len(group), **_date_metrics(group), "frecuencias": ", ".join(sorted(x for x in group["frecuencia"].unique() if x)), "precios_validos": int(group["precio_valido"].sum()), "porcentaje_precios_validos": 100 * group["precio_valido"].mean(), **_stats(group)})
    columns = ["nivel", "commodity", "año", "cantidad_registros", "fechas_distintas", "fecha_minima", "fecha_maxima", "años_disponibles", "meses_disponibles", "frecuencias", "precios_validos", "porcentaje_precios_validos", "precio_promedio", "precio_minimo", "precio_maximo", "coeficiente_variacion"]
    return pd.DataFrame(rows, columns=columns)


def commodity_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for commodity, group in frame.groupby("commodity", dropna=False):
        rows.append({"commodity": commodity or "(sin informar)", "cantidad_registros": len(group), "archivos_origen": group.loc[group["archivo_origen"] != "", "archivo_origen"].nunique(), "registros_con_fecha_valida": int(group["fecha_valida"].sum()), "registros_con_precio_valido": int(group["precio_valido"].sum()), "registros_con_moneda_valida": int(group["moneda_valida"].sum()), "registros_con_unidad_valida": int(group["unidad_valida"].sum()), "precios_cero": int(group["precio_cero"].sum()), "precios_negativos": int(group["precio_negativo"].sum()), "precios_faltantes": int(group["precio_num"].isna().sum()), "outliers_iqr": int(group["outlier_iqr"].sum()), **_date_metrics(group), **_stats(group)})
    columns = ["commodity", "cantidad_registros", "archivos_origen", "registros_con_fecha_valida", "registros_con_precio_valido", "registros_con_moneda_valida", "registros_con_unidad_valida", "precios_cero", "precios_negativos", "precios_faltantes", "outliers_iqr", "fechas_distintas", "fecha_minima", "fecha_maxima", "años_disponibles", "meses_disponibles", "precio_promedio", "precio_minimo", "precio_maximo", "coeficiente_variacion"]
    return pd.DataFrame(rows, columns=columns)


def series_summary(frame: pd.DataFrame) -> pd.DataFrame:
    keys = ["commodity", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia"]
    rows = []
    for values, group in frame.groupby(keys, dropna=False):
        commodity, market, price_type, currency, unit, frequency = values
        observations, valid = len(group), int(group["precio_valido"].sum())
        dates = int(group.loc[group["fecha_valida"], "fecha_parseada"].dt.normalize().nunique())
        valid_pct = 100 * valid / observations if observations else 0
        quality = "Alta" if observations >= 30 and dates >= 20 and valid_pct > 90 else "Media" if observations >= 10 and dates >= 5 and valid_pct > 70 else "Baja"
        rows.append({"commodity": commodity or "(sin informar)", "mercado": market or "(sin informar)", "tipo_precio": price_type or "(sin informar)", "moneda": currency or "(sin informar)", "unidad": unit or "(sin informar)", "frecuencia": frequency or "(sin determinar)", "observaciones": observations, "fechas_distintas": dates, **_date_metrics(group), **_stats(group), "porcentaje_precios_validos": valid_pct, "calidad_serie": quality})
    columns = ["commodity", "mercado", "tipo_precio", "moneda", "unidad", "frecuencia", "observaciones", "fechas_distintas", "fecha_minima", "fecha_maxima", "años_disponibles", "meses_disponibles", "precio_promedio", "precio_minimo", "precio_maximo", "coeficiente_variacion", "porcentaje_precios_validos", "calidad_serie"]
    return pd.DataFrame(rows, columns=columns)


def problem_cases(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for index, row in frame.iterrows():
        issues = []
        if not row["fecha_valida"]: issues.append("fecha_faltante_o_invalida")
        if pd.isna(row["precio_num"]): issues.append("precio_faltante_o_invalido")
        if row["precio_cero"]: issues.append("precio_cero")
        if row["precio_negativo"]: issues.append("precio_negativo")
        if not row["moneda_valida"]: issues.append("moneda_faltante")
        if not row["unidad_valida"]: issues.append("unidad_faltante")
        if row["outlier_iqr"]: issues.append("outlier_iqr")
        if issues:
            rows.append({"fila_origen_integrada": index + 2, "fecha": row["fecha"], "commodity": row["commodity"], "mercado": row["mercado"], "tipo_precio": row["tipo_precio"], "moneda": row["moneda"], "unidad": row["unidad"], "precio": row["precio"], "archivo_origen": row["archivo_origen"], "problemas": "; ".join(issues), "observaciones": row["observaciones"]})
    columns = ["fila_origen_integrada", "fecha", "commodity", "mercado", "tipo_precio", "moneda", "unidad", "precio", "archivo_origen", "problemas", "observaciones"]
    return pd.DataFrame(rows, columns=columns)


def _fmt(value: Any, decimals: int = 2) -> str:
    if value is None or pd.isna(value): return "n/d"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def markdown_table(frame: pd.DataFrame) -> str:
    """Renderiza una tabla Markdown sin depender de tabulate."""
    if frame.empty:
        return "No hay registros para resumir."
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in frame.iterrows():
        values = []
        for value in row.tolist():
            if pd.isna(value):
                values.append("n/d")
            elif isinstance(value, float):
                values.append(_fmt(value))
            else:
                values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_report(frame: pd.DataFrame, coverage: pd.DataFrame, commodities: pd.DataFrame, series: pd.DataFrame, problems: pd.DataFrame, input_path: Path) -> str:
    dated = frame.loc[frame["fecha_valida"], "fecha_parseada"]
    years = sorted(dated.dt.year.astype(int).unique()) if not dated.empty else []
    frequencies = sorted(x for x in frame["frecuencia"].unique() if x)
    quality_counts = series["calidad_serie"].value_counts().to_dict() if not series.empty else {}
    return "\n".join([
        "# Auditoría de commodities agrícolas BCR", "", "## 1. Resumen ejecutivo", "",
        f"Se auditaron **{len(frame):,} registros** de `{input_path}`. Se detectaron **{frame['commodity'].replace('', pd.NA).dropna().nunique():,} commodities**, **{frame['archivo_origen'].replace('', pd.NA).dropna().nunique():,} archivos de origen** y **{int(frame['precio_valido'].sum()):,} precios válidos**.", "",
        f"El rango de fechas válidas es **{dated.min().date().isoformat() if not dated.empty else 'n/d'}** a **{dated.max().date().isoformat() if not dated.empty else 'n/d'}**. Años disponibles: **{', '.join(map(str, years)) or 'n/d'}**. Frecuencias detectadas: **{', '.join(frequencies) or 'Sin determinar'}**.", "",
        "La auditoría corresponde exclusivamente a la capa exploratoria de BCR/Cámara Arbitral. No se cruza con cantidades ni precios frutihortícolas.", "", "## 2. Fuente y alcance", "",
        "La fuente piloto es BCR / Cámara Arbitral de Cereales, específicamente descargas manuales de precios de pizarra. El alcance esperado son commodities agrícolas/granos, no precios frutihortícolas. El integrador no realiza scraping ni llamadas de red.", "", "## 3. Cobertura temporal", "",
        f"- Filas totales: {len(frame):,}.", f"- Archivos origen: {frame['archivo_origen'].replace('', pd.NA).dropna().nunique():,}.", f"- Registros con fecha válida: {int(frame['fecha_valida'].sum()):,}.", f"- Rango: {dated.min().date().isoformat() if not dated.empty else 'n/d'} a {dated.max().date().isoformat() if not dated.empty else 'n/d'}.", f"- Años: {', '.join(map(str, years)) or 'n/d'}.", f"- Meses distintos: {int(frame.loc[frame['fecha_valida'], ['año_num', 'mes_num']].drop_duplicates().shape[0])}.", "", "El detalle por año y por commodity-año se encuentra en `RESUMEN_COBERTURA_COMMODITIES_BCR.csv`.", "", "## 4. Cobertura por commodity", "",
        markdown_table(commodities), "", "## 5. Calidad de precios", "",
        f"- Precios válidos (> 0): {int(frame['precio_valido'].sum()):,}.", f"- Precios cero: {int(frame['precio_cero'].sum()):,}.", f"- Precios negativos: {int(frame['precio_negativo'].sum()):,}.", f"- Precios faltantes o no numéricos: {int(frame['precio_num'].isna().sum()):,}.", f"- Registros con moneda válida: {int(frame['moneda_valida'].sum()):,}.", f"- Registros con unidad válida: {int(frame['unidad_valida'].sum()):,}.", f"- Outliers por commodity usando IQR (1,5 × IQR), conservados y no eliminados: {int(frame['outlier_iqr'].sum()):,}.", "", "Los casos individuales se encuentran en `CASOS_PROBLEMATICOS_COMMODITIES_BCR.csv`.", "", "## 6. Series utilizables", "",
        f"- Series Alta: {quality_counts.get('Alta', 0)}.", f"- Series Media: {quality_counts.get('Media', 0)}.", f"- Series Baja: {quality_counts.get('Baja', 0)}.", "", "La clasificación usa las claves commodity, mercado, tipo de precio, moneda, unidad y frecuencia. Alta requiere al menos 30 observaciones, 20 fechas distintas y más de 90% de precios válidos; Media requiere al menos 10 observaciones, 5 fechas distintas y más de 70%; el resto es Baja.", "", "## 7. Problemas detectados", "",
        f"Se detectaron **{len(problems):,} registros problemáticos**. Las categorías pueden superponerse: fecha faltante/inválida, precio faltante/no numérico, cero, negativo, moneda o unidad faltante y outlier IQR. Los outliers no se eliminan automáticamente porque requieren revisión metodológica.", "", "## 8. Recomendación para futura incorporación al dashboard", "",
        "Mantener commodities como tercer módulo independiente y comenzar, si se aprueba el piloto, con una única serie homogénea de precios de pizarra BCR. Mostrar fuente, mercado Rosario, moneda, unidad, condición comercial y fecha de actualización. No publicar una serie hasta validar una muestra histórica, cobertura, permisos de uso y estabilidad del formato descargado.", "", "## 9. Limitaciones metodológicas", "",
        "- Estos datos corresponden a commodities agrícolas/granos.", "- No deben mezclarse directamente con frutas y hortalizas.", "- No representan cantidades transadas.", "- No deben cruzarse con precios frutihortícolas para inferir causalidad.", "- La unidad, moneda y condición comercial deben conservarse.", "- Precio de pizarra, FOB/FAS, disponible y futuros no deben mezclarse como si fueran el mismo tipo de precio.", "", "El valor por defecto del integrador para descargas BCR sin columnas explícitas es ARS y $/Tn, y queda anotado como supuesto pendiente de validación. Las fechas mensuales o anuales no se convierten artificialmente en fechas diarias.", "",
    ])


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, sep=";", index=False, encoding="utf-8-sig", float_format="%.6f")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", nargs="?", type=Path, default=DEFAULT_INPUT, help="CSV integrado a auditar")
    args = parser.parse_args()
    input_path = args.input_path.expanduser().resolve()
    if not input_path.exists():
        print("Primero ejecute integrar_commodities_bcr.py con archivos descargados desde BCR.")
        return 2
    source = read_input(input_path)
    if source.empty:
        print("No hay datos integrados para auditar. Primero coloque descargas BCR en raw/ y ejecute integrar_commodities_bcr.py.")
        return 0
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    frame, outlier_stats = add_outliers(prepare(source))
    coverage = coverage_summary(frame)
    commodities = commodity_summary(frame)
    series = series_summary(frame)
    problems = problem_cases(frame)
    save_csv(coverage, OUTPUTS["coverage"]); save_csv(commodities, OUTPUTS["commodities"]); save_csv(series, OUTPUTS["series"]); save_csv(problems, OUTPUTS["problems"])
    REPORT_PATH.write_text(build_report(frame, coverage, commodities, series, problems, input_path), encoding="utf-8")
    dated = frame.loc[frame["fecha_valida"], "fecha_parseada"]
    years = sorted(dated.dt.year.astype(int).unique()) if not dated.empty else []
    print(f"Filas auditadas: {len(frame)}")
    print(f"Commodities detectados: {', '.join(sorted(x for x in frame['commodity'].unique() if x)) or 'ninguno'}")
    print(f"Años disponibles: {', '.join(map(str, years)) or 'n/d'}")
    print(f"Precios válidos: {int(frame['precio_valido'].sum())}")
    print("Reportes generados:")
    print(f"- {REPORT_PATH}")
    for path in OUTPUTS.values(): print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
