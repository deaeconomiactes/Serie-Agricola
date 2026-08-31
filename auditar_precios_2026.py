"""Audita la base independiente de precios mayoristas.

La auditoría distingue mercado (fuente comercial/lista) de procedencia (origen
geográfico explícito del producto). No cruza esta base con cantidades.
"""

from __future__ import annotations

import re
import shutil
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_NAMES = ("PRECIOS_MAYORISTAS_INTEGRADO.csv", "PRECIOS_MAYORISTAS_2026_INTEGRADO.csv")
OUTPUT_FILES = {
    "report": "REPORTE_AUDITORIA_PRECIOS.md",
    "coverage": "RESUMEN_COBERTURA_PRECIOS.csv",
    "markets": "RESUMEN_MERCADOS_PRECIOS.csv",
    "provenances": "RESUMEN_PROCEDENCIAS_PRECIOS.csv",
    "species": "RESUMEN_ESPECIES_PRECIOS.csv",
    "series": "RESUMEN_SERIES_UTILIZABLES_PRECIOS.csv",
}
LEGACY_OUTPUT_FILES = {
    "report": "REPORTE_AUDITORIA_PRECIOS_2026.md",
    "coverage": "RESUMEN_COBERTURA_PRECIOS_2026.csv",
    "markets": "RESUMEN_MERCADOS_PRECIOS_2026.csv",
    "provenances": "RESUMEN_PROCEDENCIAS_PRECIOS_2026.csv",
    "species": "RESUMEN_ESPECIES_PRECIOS_2026.csv",
    "series": "RESUMEN_SERIES_UTILIZABLES_PRECIOS_2026.csv",
}


def read_input(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "latin1"):
        try:
            return pd.read_csv(path, sep=";", dtype=str, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise RuntimeError("No se pudo leer el archivo con UTF-8 ni latin1.")


def normalized_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def parse_number(value) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().replace("$", "").replace(" ", "")
    if not text or text.lower() in {"nan", "none", "n/a", "#n/a", "-"}:
        return np.nan
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return np.nan


def fmt_number(value, decimals: int = 2) -> str:
    if pd.isna(value):
        return "n/d"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value) -> str:
    return f"{value:.1f}%" if not pd.isna(value) else "n/d"


def value_stats(frame: pd.DataFrame) -> dict:
    prices = frame.loc[frame["precio_valido"], "precio_efectivo"]
    if prices.empty:
        return {"precio_promedio": np.nan, "precio_min": np.nan, "precio_max": np.nan, "coeficiente_variacion": np.nan}
    mean = prices.mean()
    return {"precio_promedio": mean, "precio_min": prices.min(), "precio_max": prices.max(), "coeficiente_variacion": prices.std(ddof=1) / mean if len(prices) > 1 and mean else np.nan}


def add_quality_columns(df: pd.DataFrame) -> pd.DataFrame:
    expected = ["fecha", "año", "mes", "rubro", "especie", "variedad", "mercado", "procedencia", "localidad_corrientes", "envase", "kg_bulto", "total_kilos", "unidad", "precio", "precio_min", "precio_max", "precio_promedio", "archivo_origen"]
    for column in expected:
        if column not in df.columns:
            df[column] = ""
    for column in ["fecha", "rubro", "especie", "variedad", "mercado", "procedencia", "localidad_corrientes", "envase", "kg_bulto", "total_kilos", "unidad", "archivo_origen"]:
        df[column] = clean_text(df[column])
    df["fecha_parseada"] = pd.to_datetime(df["fecha"], errors="coerce", format="mixed")
    df["fecha_valida"] = df["fecha_parseada"].notna()
    df["año_num"] = pd.to_numeric(df["año"], errors="coerce"); df["mes_num"] = pd.to_numeric(df["mes"], errors="coerce")
    df.loc[df["fecha_valida"], "año_num"] = df.loc[df["fecha_valida"], "fecha_parseada"].dt.year; df.loc[df["fecha_valida"], "mes_num"] = df.loc[df["fecha_valida"], "fecha_parseada"].dt.month
    for column in ["precio", "precio_min", "precio_max", "precio_promedio"]:
        df[f"{column}_num"] = df[column].map(parse_number)
    df["precio_efectivo"] = df["precio_promedio_num"].fillna(df["precio_num"])
    df["precio_valido"] = df["precio_efectivo"].notna() & (df["precio_efectivo"] > 0); df["precio_cero"] = df["precio_efectivo"].eq(0); df["precio_negativo"] = df["precio_efectivo"] < 0
    df["especie_normalizada"] = df["especie"].map(normalized_key); df["variedad_normalizada"] = df["variedad"].map(normalized_key)
    return df


def add_outlier_flags(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df["outlier_especie"] = False; rows = []
    for species, group in df[df["precio_valido"]].groupby("especie_normalizada"):
        prices = group["precio_efectivo"]; q1 = prices.quantile(.25); q3 = prices.quantile(.75); iqr = q3 - q1; lower = q1 - 3 * iqr; upper = q3 + 3 * iqr
        mask = df["especie_normalizada"].eq(species) & df["precio_valido"] & ((df["precio_efectivo"] < lower) | (df["precio_efectivo"] > upper)); df.loc[mask, "outlier_especie"] = True
        rows.append({"especie": species, "q1": q1, "q3": q3, "iqr": iqr, "limite_inferior": lower, "limite_superior": upper, "observaciones_validas": len(prices), "outliers": int(mask.sum())})
    return df, pd.DataFrame(rows)


def _dated_stats(group: pd.DataFrame) -> dict:
    dated = group[group["fecha_valida"]]
    return {"cantidad_fechas_disponibles": dated["fecha_parseada"].dt.date.nunique(), "fecha_minima": dated["fecha_parseada"].min().date().isoformat() if not dated.empty else "", "fecha_maxima": dated["fecha_parseada"].max().date().isoformat() if not dated.empty else "", "cantidad_meses_disponibles": dated[["año_num", "mes_num"]].drop_duplicates().shape[0]}


def _dimension_summary(df: pd.DataFrame, column: str) -> pd.DataFrame:
    report_column = f"{column}_reporte"; work = df.copy(); work[report_column] = work[column].replace("", "(sin informar)"); rows = []
    for value, group in work.groupby(report_column, dropna=False):
        rows.append({column: value, "cantidad_registros": len(group), **_dated_stats(group), "especies_unicas": group.loc[group["especie"] != "", "especie_normalizada"].nunique(), **value_stats(group), "porcentaje_precios_validos": 100 * group["precio_valido"].mean()})
    return pd.DataFrame(rows).sort_values("cantidad_registros", ascending=False)


def coverage_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, month, rubro), group in df[df["fecha_valida"]].groupby(["año_num", "mes_num", "rubro"], dropna=False):
        rows.append({"año": int(year), "mes": int(month), "rubro": rubro or "(sin informar)", "cantidad_registros": len(group), "especies_unicas": group.loc[group["especie"] != "", "especie_normalizada"].nunique(), "variedades_unicas": group.loc[group["variedad"] != "", "variedad_normalizada"].nunique(), "mercados_unicos": group.loc[group["mercado"] != "", "mercado"].nunique(), "procedencias_unicas": group.loc[group["procedencia"] != "", "procedencia"].nunique(), **value_stats(group), "porcentaje_precios_validos": 100 * group["precio_valido"].mean()})
    return pd.DataFrame(rows).sort_values(["año", "mes", "rubro"])


def species_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []; work = df.copy(); work["rubro_reporte"] = work["rubro"].replace("", "(sin informar)")
    for (species, rubro), group in work.groupby(["especie_normalizada", "rubro_reporte"], dropna=False):
        rows.append({"especie": species or "(sin informar)", "rubro": rubro, "cantidad_registros": len(group), "mercados_disponibles": group.loc[group["mercado"] != "", "mercado"].nunique(), "procedencias_disponibles": group.loc[group["procedencia"] != "", "procedencia"].nunique(), **_dated_stats(group), **value_stats(group), "porcentaje_precios_validos": 100 * group["precio_valido"].mean()})
    return pd.DataFrame(rows).sort_values("cantidad_registros", ascending=False)


def series_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []; work = df.copy(); work["mercado_reporte"] = work["mercado"].replace("", "(sin informar)"); work["procedencia_reporte"] = work["procedencia"].replace("", "(sin informar)"); work["variedad_reporte"] = work["variedad"].replace("", "(sin informar)")
    keys = ["rubro", "mercado_reporte", "procedencia_reporte", "especie_normalizada", "variedad_reporte", "unidad"]
    for values, group in work.groupby(keys, dropna=False):
        rubro, market, provenance, species, variety, unit = values; details = _dated_stats(group); observations = len(group); dates = details["cantidad_fechas_disponibles"]; months = details["cantidad_meses_disponibles"]; valid_pct = 100 * group["precio_valido"].mean()
        quality = "Alta" if observations >= 20 and dates >= 10 and months >= 3 and valid_pct > 80 else "Media" if observations >= 10 and dates >= 5 and months >= 2 and valid_pct > 60 else "Baja"
        rows.append({"rubro": rubro or "(sin informar)", "mercado": market, "procedencia": provenance, "especie": species or "(sin informar)", "variedad": variety, "unidad": unit or "(sin informar)", "cantidad_observaciones": observations, "cantidad_fechas_distintas": dates, "cantidad_meses_distintos": months, **details, **value_stats(group), "porcentaje_precios_validos": valid_pct, "indicador_serie_utilizable": quality})
    return pd.DataFrame(rows).sort_values(["indicador_serie_utilizable", "cantidad_observaciones"], ascending=[True, False])


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, sep=";", index=False, encoding="utf-8-sig", float_format="%.4f")


def build_report(df, coverage, markets, provenances, species, series, input_path) -> str:
    valid_dates = df[df["fecha_valida"]]; high = series[series["indicador_serie_utilizable"] == "Alta"]; medium = series[series["indicador_serie_utilizable"] == "Media"]; market_known = df["mercado"] != ""; provenance_known = df["procedencia"] != ""; market_inferred = df["archivo_origen"].str.contains(r"martin\s+micelli|frut|hortal", case=False, regex=True) & market_known
    market_names = ", ".join(markets.loc[markets["mercado"] != "(sin informar)", "mercado"].astype(str).tolist()) or "(ninguno)"; provenance_names = ", ".join(provenances.loc[provenances["procedencia"] != "(sin informar)", "procedencia"].astype(str).head(30).tolist()) or "(ninguna)"; month_list = ", ".join(f"{int(y)}-{int(m):02d}" for y, m in coverage[["año", "mes"]].drop_duplicates().itertuples(index=False, name=None)) or "n/d"
    return "\n".join([
        "# Auditoría de precios mayoristas", "", "## 1. Resumen ejecutivo", "", f"Se auditaron **{len(df):,} filas** de `{input_path.name}`. Esta base de precios se mantuvo separada de las cantidades 2024/2025.", "", "Los archivos de salida que conservan el sufijo `2026` son copias legacy de compatibilidad y ya no representan exclusivamente ese año.", "", f"La cobertura temporal válida va de **{valid_dates['fecha_parseada'].min().date().isoformat() if not valid_dates.empty else 'n/d'}** a **{valid_dates['fecha_parseada'].max().date().isoformat() if not valid_dates.empty else 'n/d'}**, con **{len(high)} series Alta** y **{len(medium)} series Media**.", "", "## 2. Cobertura general", "", f"- Filas totales: {len(df):,}", f"- Archivos de origen: {df['archivo_origen'].replace('', pd.NA).dropna().nunique():,}", f"- Meses: {month_list}", f"- Rubros: {', '.join(sorted(x for x in df['rubro'].unique() if x)) or 'n/d'}", f"- Especies únicas: {df.loc[df['especie'] != '', 'especie_normalizada'].nunique():,}", f"- Precios válidos (> 0): {pct(100 * df['precio_valido'].mean())}", "", "## Cobertura geográfica", "", f"- Mercado informado: **{int(market_known.sum()):,} de {len(df):,} registros ({pct(100 * market_known.mean())})**.", f"- Procedencia informada: **{int(provenance_known.sum()):,} de {len(df):,} registros ({pct(100 * provenance_known.mean())})**.", f"- Mercados detectados: {market_names}.", f"- Procedencias detectadas: {provenance_names}.", f"- Mercado inferido por fuente: **{int(market_inferred.sum()):,} registros**.", f"- Mercado proveniente de columna explícita: **{int((market_known & ~market_inferred).sum()):,} registros**.", f"- Procedencia proveniente de columnas explícitas: **{int(provenance_known.sum()):,} registros**.", "", "Los registros de listas mensuales de frutas y hortalizas se etiquetan como Mercado Central de Buenos Aires. Los registros provenientes del archivo MARTIN MICELLI 26-08-2026.xlsx se etiquetan como Mercado de Corrientes. La procedencia se conserva como origen declarado del producto cuando la fuente lo informa.", "", "Mercado representa el mercado/lista/fuente comercial de precios; procedencia representa el origen geográfico del producto. No se mezclan automáticamente.", "", "## 3. Cobertura temporal", "", "El detalle se encuentra en `RESUMEN_COBERTURA_PRECIOS.csv`.", "", "## 4. Cobertura por mercado", "", "El detalle se encuentra en `RESUMEN_MERCADOS_PRECIOS.csv`.", "", "## 5. Cobertura por procedencia", "", "El detalle se encuentra en `RESUMEN_PROCEDENCIAS_PRECIOS.csv`.", "", "## 6. Series utilizables", "", "El nivel de análisis es rubro, mercado, procedencia (si existe), especie, variedad y unidad. La procedencia no es requisito de calidad: la clasificación se basa principalmente en observaciones, fechas distintas, meses distintos y precios válidos.", "", f"- Series Alta: {len(high):,}", f"- Series Media: {len(medium):,}", f"- Series Baja: {int((series['indicador_serie_utilizable'] == 'Baja').sum()):,}", "", "## 7. Calidad y limitaciones", "", f"- Fechas inválidas o faltantes: {int((~df['fecha_valida']).sum()):,}.", f"- Precios faltantes/no numéricos: {int(df['precio_efectivo'].isna().sum()):,}.", f"- Precios cero: {int(df['precio_cero'].sum()):,}.", f"- Precios negativos: {int(df['precio_negativo'].sum()):,}.", f"- Outliers por especie (Q1 -/+ 3*IQR), no eliminados: {int(df['outlier_especie'].sum()):,}.", "", "La base sirve para monitoreo operativo de precios mayoristas. No permite inferir escasez, producción, causalidad, elasticidades ni relaciones precio-cantidad.", ""
    ])


def main() -> int:
    input_path = next((BASE_DIR / name for name in INPUT_NAMES if (BASE_DIR / name).exists()), None)
    if input_path is None:
        print(f"No existe ninguna base de precios: {', '.join(INPUT_NAMES)}. Ejecute primero integrar_precios_2026.py.", file=sys.stderr); return 2
    df, _ = add_outlier_flags(add_quality_columns(read_input(input_path))); coverage = coverage_summary(df); markets = _dimension_summary(df, "mercado"); provenances = _dimension_summary(df, "procedencia"); species = species_summary(df); series = series_summary(df)
    save_csv(coverage, BASE_DIR / OUTPUT_FILES["coverage"]); save_csv(markets, BASE_DIR / OUTPUT_FILES["markets"]); save_csv(provenances, BASE_DIR / OUTPUT_FILES["provenances"]); save_csv(species, BASE_DIR / OUTPUT_FILES["species"]); save_csv(series, BASE_DIR / OUTPUT_FILES["series"])
    report_text = build_report(df, coverage, markets, provenances, species, series, input_path)
    (BASE_DIR / OUTPUT_FILES["report"]).write_text(report_text, encoding="utf-8")
    for key, legacy_name in LEGACY_OUTPUT_FILES.items():
        if key == "report":
            (BASE_DIR / legacy_name).write_text(report_text, encoding="utf-8")
        else:
            shutil.copyfile(BASE_DIR / OUTPUT_FILES[key], BASE_DIR / legacy_name)
    print(f"Filas auditadas: {len(df):,}"); print(f"Mercados únicos: {df.loc[df['mercado'] != '', 'mercado'].nunique()}"); print(f"Procedencias únicas: {df.loc[df['procedencia'] != '', 'procedencia'].nunique()}"); print("Reportes generados:")
    for filename in OUTPUT_FILES.values(): print(f"- {BASE_DIR / filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
