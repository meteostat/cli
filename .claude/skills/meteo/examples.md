# Examples

## Fetch weather data

```bash
# Daily data for Frankfurt airport (last 30 days)
meteo d 10637

# Hourly data with date range
meteo h 10637 -s 2024-01-01 -e 2024-01-31

# Daily data by coordinates (interpolated)
meteo d 50.1109,8.6821 -s 2024-01-01 -e 2024-12-31

# Monthly data for specific parameters only
meteo m 10637 -s 2020 -e 2024 -p tavg,tmin,tmax,prcp

# Climate normals (1991–2020)
meteo n 10637

# Multiple stations, hourly, with timezone
meteo h 10637 10635 -s 2024-06-01 -e 2024-06-30 -t Europe/Berlin

# Apply aggregation (e.g. max)
meteo d 10637 10635 -s 2025-01-01 -e 2025-12-31 --agg max
```

## Export data

```bash
# Export to CSV
meteo d 10637 -s 2024-01-01 -e 2024-12-31 -o data.csv

# Export to JSON
meteo d 10637 -s 2024-01-01 -e 2024-12-31 -o data.json

# Export to Excel
meteo d 10637 -s 2024-01-01 -e 2024-12-31 -o data.xlsx

# Export to Parquet
meteo d 10637 -s 2024-01-01 -e 2024-12-31 -o data.parquet

# Generate PNG chart
meteo d 10637 -s 2024-01-01 -e 2024-12-31 -o chart.png

# CSV without header row
meteo d 10637 -s 2024-01-01 -e 2024-12-31 -f csv --no-header
```

## Station discovery

```bash
# Metadata for a specific station
meteo s 10637

# List all stations in Germany
meteo s -c DE

# Search by name
meteo s -n "Frankfurt"

# Filter by country and state
meteo s -c DE --state HE

# Find 10 nearest stations within 20 km
meteo n 50.1109 8.6821 -l 10 -r 20000

# Bounding box search
meteo s --bbox "8.0,50.0,10.0,51.0"

# Custom SQL
meteo s --sql "SELECT * FROM stations WHERE country = 'DE' AND elevation > 500"
```

## Data quality & filtering

```bash
# Include source provider columns
meteo d 10637 -s 2024-01-01 -e 2024-12-31 --with-sources

# Exclude model data
meteo d 10637 -s 2024-01-01 -e 2024-12-31 --no-models

# Aggregate multiple stations to single series
meteo d 10637 10635 -s 2024-01-01 -e 2024-12-31 --agg mean

# Disable cache for fresh data
meteo d 10637 --no-cache

# Show all rows without truncation
meteo d 10637 -s 2024-01-01 -e 2024-12-31 --all
```

## Inventory

```bash
# Check data availability for a station
meteo i 10637

# Filter inventory by granularity
meteo i 10637 -g daily

# Filter inventory by parameters
meteo i 10637 -p tavg,tmin,tmax
```

## Configuration

```bash
# List all configuration
meteo config --list

# Disable caching globally
meteo config cache_enable false

# Increase interpolation radius to 50 km
meteo config interpolation_radius 50000
```
