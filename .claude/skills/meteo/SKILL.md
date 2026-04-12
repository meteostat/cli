---
name: meteo
description: Access weather and climate data for thousands of weather stations and any place worldwide.
---

# Meteo

## Commands

Meteo is a CLI tool, run `meteo --help` to see a list of all available commands and options.

## Gotchas

- If the `meteo` command is not found, use uvx: `uvx meteostat-cli [YOUR_COMMAND]`
- `meteo nearby` requires numeric `LAT,LON` argument — city names are not accepted; use coordinates directly
- When looking for stations that match the elevation of a place, use `meteo nearby` without a radius and filter results by elevation
- Pass multiple station IDs in one call instead of looping: `meteo daily D1424 EDEV0 10635 --start 2025 --end 2025`
- Fetch only the columns you need with `--parameters` to eliminate post-processing: `--parameters tmax` or `--parameters tmax,prcp`
- Aggregate all rows with `--agg` (Pandas `.agg()`): `--agg max`, `--agg mean`, `--agg sum`
- `--start` and `--end` accept YYYY-MM-DD, YYYY-MM, YYYY
- Machine-readable output for piping: `--format json` or `--format csv`
- To get the date of extreme values, fetch the parameter without aggregation and filter with `sort` after fetching: `meteo daily D1424 --start 2025-01-01 --end 2025-12-31 --parameters tmax -f csv | awk -F',' 'NR>1' | sort -t',' -k3 -rn | head -1`