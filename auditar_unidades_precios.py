"""Audita unidades, envases y conversiones de precios mayoristas.

Lee preferentemente ``PRECIOS_MAYORISTAS_INTEGRADO.csv`` y deja los datos
originales intactos. Los reportes sólo identifican conversiones posibles,
casos no comparables y cobertura temporal; no eliminan ni imputan precios.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_NAMES = ("PRECIOS_MAYORISTAS_INTEGRADO.csv", "PRECIOS_MAYORISTAS_2026_INTEGRADO.csv")
OUTPUT_NAMES = {
    "report": "REPORTE_AUDITORIA_UNIDADES_PRECIOS.md",
    "units": "RESUMEN_UNIDADES_PRECIOS.csv",
    "packages": "RESUMEN_ENVASES_PRECIOS.csv",
    "product_packages": "RESUMEN_PRODUCTO_ENVASE_PRECIOS.csv",
    "non_comparable": "CASOS_NO_COMPARABLES_PRECIOS.csv",
    "suspicious": "CASOS_SOSPECHOSOS_PRECIO_KG.csv",
    "diagnostic_2024": "DIAGNOSTICO_PRECIOS_2024.csv",
}


def key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def find_column(df: pd.DataFrame, *names: str) -> str | None:
    wanted = {key(name) for name in names}
    for column in df.columns:
        if key(column) in wanted:
            return column
    return None


def clean_number(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float, np.number)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(" ", "")
    if not text or text.lower() in {"nan", "none", "null", "-", "–"}:
        return np.nan
    text = re.sub(r"[^0-9,.-]", "", text)
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts[:-1]) + "." + parts[-1] if len(parts[-1]) <= 2 else "".join(parts)
    elif "." in text:
        left, right = text.rsplit(".", 1)
        text = left.replace(".", "") + (f".{right}" if len(right) <= 2 else right)
    try:
        return float(text)
    except ValueError:
        return np.nan


def pct(value: float, total: int) -> float:
    return round(100 * value / total, 2) if total else 0.0


def read_input(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", low_memory=False)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    expected = [
        "fecha", "año", "mes", "rubro", "especie", "variedad", "mercado", "procedencia",
        "envase", "kg_bulto", "unidad", "precio_observado", "unidad_precio_observado",
        "precio_kg_estimado", "metodo_conversion_precio", "confianza_conversion_precio", "archivo_origen",
    ]
    for column in expected:
        if column not in df.columns:
            df[column] = ""
    for column in expected:
        df[column] = df[column].fillna("").astype(str).str.strip()
    for column in ("precio_observado", "precio_kg_estimado", "kg_bulto", "total_kilos", "precio", "precio_promedio"):
        if column in df:
            df[f"__{column}"] = df[column].map(clean_number)
    df["__fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["__year"] = pd.to_numeric(df["año"], errors="coerce")
    df.loc[df["__year"].isna() & df["__fecha"].notna(), "__year"] = df.loc[df["__year"].isna() & df["__fecha"].notna(), "__fecha"].dt.year
    df["__observed_valid"] = df["__precio_observado"].notna() & (df["__precio_observado"] > 0)
    df["__estimated_valid"] = df["__precio_kg_estimado"].notna() & (df["__precio_kg_estimado"] > 0)
    df["__kg_valid"] = df["__kg_bulto"].notna() & (df["__kg_bulto"] > 0)
    df["__non_comparable"] = ~df["__estimated_valid"] & df["__observed_valid"]
    return df


def value_stats(group: pd.DataFrame) -> dict[str, object]:
    return {
        "precio_observado_promedio": round(group.loc[group["__observed_valid"], "__precio_observado"].mean(), 4) if group["__observed_valid"].any() else np.nan,
        "precio_kg_estimado_promedio": round(group.loc[group["__estimated_valid"], "__precio_kg_estimado"].mean(), 4) if group["__estimated_valid"].any() else np.nan,
        "registros_convertibles": int(group["__estimated_valid"].sum()),
        "registros_no_comparables": int(group["__non_comparable"].sum()),
    }


def unit_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(df)
    for unit, group in df.groupby("unidad_precio_observado", dropna=False):
        label = unit or "sin especificar"
        rows.append({"unidad_precio_observado": label, "cantidad_registros": len(group), "porcentaje_registros": pct(len(group), total), **value_stats(group)})
    return pd.DataFrame(rows).sort_values("cantidad_registros", ascending=False)


def package_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    work = df.copy()
    work["__package"] = work["envase"].replace("", "sin especificar")
    for package, group in work.groupby("__package", dropna=False):
        products = sorted(set(group.loc[group["especie"] != "", "especie"]))
        kg = group.loc[group["__kg_valid"], "__kg_bulto"]
        rows.append({
            "envase": package, "cantidad_registros": len(group), "productos_asociados": " | ".join(products),
            "kg_bulto_promedio": round(kg.mean(), 4) if len(kg) else np.nan,
            "kg_bulto_minimo": kg.min() if len(kg) else np.nan,
            "kg_bulto_maximo": kg.max() if len(kg) else np.nan,
            "porcentaje_convertible": pct(int(group["__estimated_valid"].sum()), len(group)),
        })
    return pd.DataFrame(rows).sort_values("cantidad_registros", ascending=False)


def non_comparable_summary(df: pd.DataFrame) -> pd.DataFrame:
    work = df.loc[df["__non_comparable"]].copy()
    if work.empty:
        return pd.DataFrame(columns=["especie", "variedad", "mercado", "envase", "unidad_precio_observado", "motivo"])
    work["motivo"] = work["metodo_conversion_precio"].replace("", "sin información suficiente para convertir")
    return work[["especie", "variedad", "mercado", "envase", "unidad_precio_observado", "motivo"]].drop_duplicates()


def product_package_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for values, group in df.groupby(["especie", "variedad", "envase", "kg_bulto", "confianza_conversion_precio"], dropna=False):
        species, variety, package, kg, confidence = values
        rows.append({
            "especie": species, "variedad": variety, "envase": package, "kg_bulto": kg,
            "precio_observado_promedio": group.loc[group["__observed_valid"], "__precio_observado"].mean() if group["__observed_valid"].any() else np.nan,
            "precio_kg_estimado_promedio": group.loc[group["__estimated_valid"], "__precio_kg_estimado"].mean() if group["__estimated_valid"].any() else np.nan,
            "confianza_conversion_precio": confidence or "Sin informar", "cantidad_registros": len(group),
        })
    return pd.DataFrame(rows).sort_values("cantidad_registros", ascending=False)


def suspicious_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        estimated = row["__precio_kg_estimado"]
        reasons = []
        if pd.notna(estimated) and estimated > 100000:
            reasons.append("precio_kg_estimado demasiado alto")
        if pd.notna(estimated) and estimated < 0.1:
            reasons.append("precio_kg_estimado demasiado bajo")
        if row["__observed_valid"] and (pd.isna(row["__kg_bulto"])):
            reasons.append("kg_bulto faltante")
        if row["__kg_bulto"] == 0:
            reasons.append("kg_bulto igual a cero")
        if row["__observed_valid"] and row["envase"] and not row["__estimated_valid"]:
            reasons.append("envase no convertible")
        if reasons:
            rows.append({"especie": row["especie"], "variedad": row["variedad"], "mercado": row["mercado"], "envase": row["envase"], "precio_observado": row["__precio_observado"], "kg_bulto": row["__kg_bulto"], "precio_kg_estimado": estimated, "motivo": " | ".join(reasons), "archivo_origen": row["archivo_origen"]})
    return pd.DataFrame(rows)


def diagnostic_2024(df: pd.DataFrame) -> pd.DataFrame:
    work = df.loc[df["__year"].eq(2024)].copy()
    rows = []
    group_fields = ["archivo_origen", "mercado", "rubro", "especie", "variedad"]
    for values, group in work.groupby(group_fields, dropna=False):
        source, market, rubro, species, variety = values
        dates = group.loc[group["__fecha"].notna(), "__fecha"]
        total = len(group)
        noncomparable = int(group["__non_comparable"].sum())
        reasons = []
        if not total:
            reasons.append("sin registros 2024")
        if not group["__fecha"].notna().any():
            reasons.append("fechas 2024 no válidas o faltantes")
        if not group["__observed_valid"].any():
            reasons.append("sin precio observado válido")
        if noncomparable:
            reasons.append("parte de los registros no tiene unidad comparable por kg")
        if not reasons:
            reasons.append("cobertura parcial según fechas y fuentes disponibles")
        rows.append({
            "año": 2024, "archivo_origen": source, "mercado": market, "rubro": rubro, "especie": species, "variedad": variety,
            "fecha_min": dates.min().date().isoformat() if len(dates) else "", "fecha_max": dates.max().date().isoformat() if len(dates) else "",
            "meses_disponibles": " | ".join(f"{month:02d}" for month in sorted(dates.dt.month.unique())) if len(dates) else "",
            "registros_totales": total, "registros_con_precio_observado": int(group["__observed_valid"].sum()), "registros_con_precio_kg_estimado": int(group["__estimated_valid"].sum()), "registros_no_comparables": noncomparable,
            "registros_excluidos_por_fecha": int(group["__fecha"].isna().sum()), "registros_excluidos_por_precio": int((~group["__observed_valid"]).sum()), "registros_excluidos_por_unidad": noncomparable,
            "motivo_probable_baja_cobertura": " | ".join(reasons),
        })
    return pd.DataFrame(rows)


def report(df: pd.DataFrame, input_path: Path, units: pd.DataFrame, packages: pd.DataFrame, non_comparable: pd.DataFrame, suspicious: pd.DataFrame, diagnostic: pd.DataFrame) -> str:
    total = len(df)
    years = sorted(int(y) for y in df["__year"].dropna().unique())
    y2024 = df.loc[df["__year"].eq(2024)]
    dates = df.loc[df["__fecha"].notna(), "__fecha"]
    market_2024 = sorted(y2024.loc[y2024["mercado"] != "", "mercado"].unique())
    sources_2024 = sorted(y2024.loc[y2024["archivo_origen"] != "", "archivo_origen"].unique())
    months_2024 = sorted(int(m) for m in y2024.loc[y2024["__fecha"].notna(), "__fecha"].dt.month.unique())
    return f"""# Auditoría de unidades y precios mayoristas

Archivo auditado: `{input_path.name}`. Filas: **{total:,}**. Años detectados: {', '.join(map(str, years)) or 'n/d'}.

## Resumen de comparabilidad

- Registros con precio observado válido (> 0): **{int(df['__observed_valid'].sum()):,} ({pct(int(df['__observed_valid'].sum()), total)}%)**.
- Registros con precio por kg estimado válido: **{int(df['__estimated_valid'].sum()):,} ({pct(int(df['__estimated_valid'].sum()), total)}%)**.
- Registros no comparables por kg: **{int(df['__non_comparable'].sum()):,} ({pct(int(df['__non_comparable'].sum()), total)}%)**.
- Fechas válidas: **{int(df['__fecha'].notna().sum()):,}**; rango: **{dates.min().date().isoformat() if len(dates) else 'n/d'}** a **{dates.max().date().isoformat() if len(dates) else 'n/d'}**.

`precio_observado` conserva el valor original. `precio_kg_estimado` sólo se calcula cuando la fuente permite identificar una unidad por kg o convertir una presentación con `kg_bulto` válido. No se borran ni imputan registros.

## Diagnóstico específico 2024

- ¿Existen registros 2024?: **{'Sí' if len(y2024) else 'No'}**, con **{len(y2024):,} filas**.
- Archivos origen: {', '.join(sources_2024) or 'n/d'}.
- Mercados: {', '.join(market_2024) or 'n/d'}.
- Meses cubiertos: {', '.join(map(str, months_2024)) or 'n/d'}.
- Especies únicas: **{y2024.loc[y2024['especie'] != '', 'especie'].nunique():,}**; variedades únicas: **{y2024.loc[y2024['variedad'] != '', 'variedad'].nunique():,}**.
- Precio observado válido: **{int(y2024['__observed_valid'].sum()):,}**; precio por kg estimado válido: **{int(y2024['__estimated_valid'].sum()):,}**.
- Registros no comparables: **{int(y2024['__non_comparable'].sum()):,}**.
- Primer y último registro válido: **{y2024['__fecha'].min().date().isoformat() if y2024['__fecha'].notna().any() else 'n/d'}** a **{y2024['__fecha'].max().date().isoformat() if y2024['__fecha'].notna().any() else 'n/d'}**.

La cobertura 2024 debe interpretarse como parcial si sólo comprende los archivos, meses o especies detallados en `DIAGNOSTICO_PRECIOS_2024.csv`. No se completan meses faltantes ni se extrapolan precios. Si 2024 aparece únicamente en Martin Micelli, la columna `archivo_origen` lo deja identificado.

## Archivos generados

- `RESUMEN_UNIDADES_PRECIOS.csv`: distribución por unidad observada y conversión posible.
- `RESUMEN_ENVASES_PRECIOS.csv`: envases, kilos por bulto y porcentaje convertible.
- `RESUMEN_PRODUCTO_ENVASE_PRECIOS.csv`: detalle por especie, variedad, envase y kilos por bulto.
- `CASOS_NO_COMPARABLES_PRECIOS.csv`: observaciones que no pueden expresarse por kg con la información disponible.
- `CASOS_SOSPECHOSOS_PRECIO_KG.csv`: valores que requieren revisión.
- `DIAGNOSTICO_PRECIOS_2024.csv`: cobertura detallada de 2024 por fuente, mercado y producto.

La base de precios permanece separada de las cantidades. Esta auditoría no calcula relaciones precio-cantidad, causalidad ni escasez.
"""


def main() -> int:
    input_path = next((BASE_DIR / name for name in INPUT_NAMES if (BASE_DIR / name).exists()), None)
    if input_path is None:
        print("No se encontró una base integrada de precios.")
        return 1
    df = prepare(read_input(input_path))
    units, packages = unit_summary(df), package_summary(df)
    non_comparable, suspicious = non_comparable_summary(df), suspicious_summary(df)
    product_packages = product_package_summary(df)
    diagnostic = diagnostic_2024(df)
    units.to_csv(BASE_DIR / OUTPUT_NAMES["units"], sep=";", index=False, encoding="utf-8-sig")
    packages.to_csv(BASE_DIR / OUTPUT_NAMES["packages"], sep=";", index=False, encoding="utf-8-sig")
    product_packages.to_csv(BASE_DIR / OUTPUT_NAMES["product_packages"], sep=";", index=False, encoding="utf-8-sig")
    non_comparable.to_csv(BASE_DIR / OUTPUT_NAMES["non_comparable"], sep=";", index=False, encoding="utf-8-sig")
    suspicious.to_csv(BASE_DIR / OUTPUT_NAMES["suspicious"], sep=";", index=False, encoding="utf-8-sig")
    diagnostic.to_csv(BASE_DIR / OUTPUT_NAMES["diagnostic_2024"], sep=";", index=False, encoding="utf-8-sig")
    (BASE_DIR / OUTPUT_NAMES["report"]).write_text(report(df, input_path, units, packages, non_comparable, suspicious, diagnostic), encoding="utf-8")
    y2024 = df.loc[df["__year"].eq(2024)]
    months = sorted(int(m) for m in y2024.loc[y2024["__fecha"].notna(), "__fecha"].dt.month.unique())
    print(f"Filas auditadas: {len(df)}")
    print(f"Registros 2024 totales: {len(y2024)}")
    print(f"Registros 2024 con precio observado válido: {int(y2024['__observed_valid'].sum())}")
    print(f"Registros 2024 con precio por kg estimado: {int(y2024['__estimated_valid'].sum())}")
    print(f"Meses 2024 detectados: {months}")
    print(f"Mercados 2024 detectados: {sorted(y2024.loc[y2024['mercado'] != '', 'mercado'].unique())}")
    print(f"Archivos origen 2024: {sorted(y2024.loc[y2024['archivo_origen'] != '', 'archivo_origen'].unique())}")
    print(f"Motivo principal de baja cobertura 2024: {diagnostic['motivo_probable_baja_cobertura'].value_counts().index[0] if not diagnostic.empty else 'sin registros 2024'}")
    print(f"Unidades únicas: {df['unidad_precio_observado'].replace('', 'sin especificar').nunique()}")
    print(f"Registros no comparables: {int(df['__non_comparable'].sum())}")
    print(f"Reportes generados en: {BASE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
