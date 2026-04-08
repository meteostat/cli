# Examples

## Fetch weather data

```bash
meteo daily 10637  # Station ID for Frankfurt/Main
meteo hourly 10637 --start 2024-01-01 --end 2024-01-31
meteo daily 50.1109,8.6821 --start 2024-01-01 --end 2024-12-31  # Geo coordinates (interpolated)
meteo monthly 10637 --start 2020 --end 2024 --parameters temp,tmin,tmax,prcp
meteo normals 10637
meteo hourly 10637 10635 --start 2024-06-01 --end 2024-06-30 --timezone Europe/Berlin
meteo daily 10637 10635 --start 2025-01-01 --end 2025-12-31 --agg max  # Custom aggregation (Pandas `.agg()`) across multiple stations
```

## Export data

```bash
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --output data.csv
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --output data.json
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --output data.xlsx
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --output data.parquet
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --output chart.png
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --format csv --no-header
```

## Station discovery

```bash
meteo station 10637  # Metadata for a specific station
meteo station --country DE  # All stations in Germany
meteo station --country DE --state HE
meteo station --name "Frankfurt" # Search by name (case-insensitive, partial match)
meteo station --bbox "8.0,50.0,10.0,51.0"
meteo station --sql "SELECT * FROM stations WHERE country = 'DE' AND elevation > 500"
meteo nearby 50.1109,8.6821 --limit 10 --radius 20000
```

## Data quality & filtering

```bash
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --with-sources  # Include source provider columns
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --no-models  # Exclude model data
meteo daily 10637 10635 --start 2024-01-01 --end 2024-12-31 --agg mean
meteo daily 10637 --no-cache  # Disable cache for the latest data
meteo daily 10637 --start 2024-01-01 --end 2024-12-31 --all  # Show all rows without truncation
```

## Finding the hottest/coldest day

```bash
# Peak tmax for a station over a full year — single command, no awk needed
meteo daily D1424 --start 2025-01-01 --end 2025-12-31 --parameters tmax --agg max -f csv
# To also get the date of the peak, filter with sort after fetching tmax only
meteo daily D1424 --start 2025-01-01 --end 2025-12-31 --parameters tmax -f csv \
  | awk -F',' 'NR>1' | sort -t',' -k3 -rn | head -1
```

## Inventory

```bash
meteo inventory 10637
meteo inventory 10637 --granularity daily
meteo inventory 10637 --parameters temp,tmin,tmax
```

## Configuration

```bash
meteo config --list
meteo config cache_enable false
meteo config interpolation_radius 50000
```
