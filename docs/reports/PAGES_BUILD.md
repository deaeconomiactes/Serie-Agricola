# Construcción local Pages: cierre

Construcción desde el índice Git candidato en un directorio temporal. El builder validó índice, hashes y cobertura de 19 fragmentos. `prepare_pages.py` conservó el favicon y excluyó los dos informes SIO de auditoría, sin alterar los originales. El descifrado mediante el secreto de Actions queda para el build real del PR en GitHub Actions.

Paquete anterior: 79,201,185 bytes; candidato medido: 64,896,273 bytes (895 archivos), diferencia -14,304,912 bytes. Son bytes sin comprimir; el candidato también incorpora documentación y favicon nuevos, por lo que la diferencia neta no equivale exactamente a los bytes excluidos. La medición corresponde a la copia temporal preparada antes de actualizar este propio reporte. El [listado](PAGES_CONTENTS.csv) incluye rutas presentes y ausentes.

`SIO_GRAIN_AUDIT.json` ocupa 7.849 bytes; `CASOS_PRECIOS_CERO_SIO.csv` ocupa 14.688.217 bytes. Los dos permanecen versionados para auditoría y tests; `git grep` no halló carga en el frontend.

## Mayores incluidos

| Archivo | Bytes |
| --- | ---: |
| `REGISTRO 2025 INTEGRADO.csv` | 3931671 |
| `REGISTRO 2025.csv.enc` | 2506720 |
| `data/magyp/dashboard/commodities/fob.csv` | 2349546 |
| `data/mayoristas/dashboard/mcba-anual-2026-legacy-a50df540e3e843ee.json.gz` | 1755898 |
| `data/mayoristas/dashboard/mcba-diaria-2026-legacy-3d372e177ef455f0.json.gz` | 1712132 |
| `data/magyp/reports/MCBA_CURRENT_VS_MAGYP.csv` | 1420677 |
| `data/magyp/dashboard/commodities/history/futures/daily-2024.csv-39174287ad17da81.gz` | 1267526 |
| `data/magyp/dashboard/commodities/history/futures/monthly.csv-7ec80d32b61467af.gz` | 1233771 |
| `data/magyp/dashboard/commodities/futures.csv` | 1154101 |
| `data/magyp/reports/COMMODITIES_HISTORY_LINKS.json` | 1078804 |
| `data/magyp/dashboard/commodities/history/futures/daily-2026.csv-aad93fcb3222c6a4.gz` | 1075657 |
| `data/magyp/dashboard/commodities/history/futures/daily-2021.csv-22d54e86f61b2a8d.gz` | 958603 |
| `data/magyp/dashboard/commodities/history/futures/daily-2025.csv-e106a0bfa118dad4.gz` | 727961 |
| `data/magyp/dashboard/commodities/history/futures/daily-2022.csv-c6f2d75af12e02e9.gz` | 723087 |
| `data/magyp/dashboard/commodities/history/futures/daily-2020.csv-1d7e37ffbaeb4272.gz` | 713873 |
