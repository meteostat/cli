---
name: meteo
description: Access weather and climate data for thousands of weather stations and any place worldwide.
---

# Meteo

## Usage

If the `meteo` command is not found, install the tool using:

```bash
uv tool install meteostat-cli
```

Alternatively, you can use `uvx`:

```bash
uvx --from meteostat-cli meteo
```

## Commands

Run `meteo --help` to see a list of all available commands and options.

## Gotchas

- `meteo nearby` requires numeric `LAT,LON` argument — city names are not accepted. Use coordinates directly.
- When looking for stations that match the elevation of a place, use `meteo nearby` without a radius and filter results by elevation.
- Pass multiple station IDs in one call instead of looping: `meteo daily D1424 EDEV0 10635 --start 2025 --end 2025`
- Fetch only the columns you need with `--parameters` to eliminate post-processing: `--parameters tmax` or `--parameters tmax,prcp`
- Aggregate all rows with `--agg` (Pandas `.agg()`): `--agg max`, `--agg mean`, `--agg sum`
- `--start` and `--end` accept YYYY-MM-DD, YYYY-MM, YYYY
- Machine-readable output for piping: `--format json` or `--format csv`

## Additional resources

- For usage examples, see [examples.md](examples.md)