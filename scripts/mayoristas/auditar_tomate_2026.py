"""Matriz reproducible de los fragmentos mensuales publicados, sin alterar fuentes."""
import csv
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'data/mayoristas/dashboard'
OUTPUT = ROOT / 'data/mayoristas/reports/TOMATE_2026_MATRIZ.csv'


def main():
    index = json.loads((FOLDER / 'index.json').read_text(encoding='utf-8'))
    descriptors = [f for f in index['fragments'] if f['frequency'] == 'mensual' and f['year'] == 2026]
    fields = ['source', 'mercado', 'fecha', 'especie_raw_disponible', 'especie_actual',
              'variedad_raw_disponible', 'variedad_actual', 'procedencia_raw_disponible',
              'procedencia_actual', 'procedencia_canonica_propuesta', 'envase', 'kg_envase',
              'unidad_original', 'precio_observado', 'precio_kg', 'metodo', 'confianza',
              'conversion_verificable', 'motivo', 'fuente_url', 'fecha_actualizacion']
    result = []
    for descriptor in descriptors:
        with gzip.open(FOLDER / descriptor['path'], 'rt', encoding='utf-8') as stream:
            rows = json.load(stream)
        for row in rows:
            if 'TOMATE' not in (str(row.get('especie', '')) + ' ' + str(row.get('variedad', ''))).upper():
                continue
            origin = row.get('procedencia_raw', row.get('origin_raw', row.get('procedencia', '')))
            canonical = 'Corrientes' if str(origin).strip().upper().rstrip('.') in ('CTES', 'CORRIENTES') else row.get('procedencia', '')
            price = row.get('precioKgEstimado')
            unit = row.get('unidadPrecioObservado', '')
            package = row.get('envase', '')
            kg = row.get('kg_raw') or row.get('kgBulto') or ''
            reason = ''
            if unit == '$/kg' and price:
                status = 'Directa'
            elif unit == '$/bulto' and price and kg:
                match = re.search(r'\bX\s*(\d+(?:[.,]\d+)?)\s*KG\b', package.upper())
                if match and float(match.group(1).replace(',', '.')) == float(kg):
                    status = 'Estimada; peso informado en presentación'
                else:
                    status, reason = 'Revisar', 'Peso no corroborado por texto de presentación'
                if 'MAZO' in package.upper():
                    status, reason = 'Revisar', 'Presentación en mazos atípica para tomate; requiere fuente original'
            else:
                status, reason = 'No comparable', 'No consta precio por kg ni divisor verificable'
            result.append(dict(source=descriptor['source'], mercado=row.get('mercado'), fecha=row.get('fecha'),
                especie_raw_disponible=row.get('producto_raw', row.get('product_raw', row.get('especie', ''))),
                especie_actual=row.get('especie'), variedad_raw_disponible=row.get('variedad_raw', row.get('variety_raw', row.get('variedad', ''))),
                variedad_actual=row.get('variedad'), procedencia_raw_disponible=origin,
                procedencia_actual=row.get('procedencia'), procedencia_canonica_propuesta=canonical,
                envase=package, kg_envase=kg, unidad_original=unit, precio_observado=row.get('precioObservado'),
                precio_kg=price, metodo=row.get('metodoConversion'), confianza=row.get('confianzaConversion'),
                conversion_verificable=status, motivo=reason, fuente_url=row.get('fuente'),
                fecha_actualizacion=row.get('last_update')))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result)
    print(f'{len(result)} filas -> {OUTPUT}')


if __name__ == '__main__':
    main()
