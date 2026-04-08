<!-- PROJECT SHIELDS -->
<div align="center">

[![PyPI Version][pypi-shield]][pypi-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

</div>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/meteostat/cli">
    <img src="https://media.meteostat.net/icon.svg" alt="Meteostat Logo" width="80" height="80">
  </a>

  <h3 align="center">Meteostat CLI</h3>

  <p align="center">
    Access weather and climate data through the terminal.
    <p>
      <a href="https://dev.meteostat.net/cli"><strong>Explore the docs »</strong></a>
    </p>
    <p>
      <a href="https://meteostat.net">Visit Website</a>
      &middot;
      <a href="https://github.com/meteostat/cli/issues">Report Bug</a>
      &middot;
      <a href="https://github.com/orgs/meteostat/discussions">Request Feature</a>
    </p>
  </p>
</div>

![](demo.gif)

## 📚 Installation

```bash
uv tool install meteostat-cli
```

For plotting capabilities (`png` and `svg` output), install the `plot` extra:

```bash
uv tool install "meteostat-cli[plot]"
```

Alternatively, you can use `uvx`:

```bash
uvx --from meteostat-cli meteo
```

## 🚀 Usage

Let's get daily weather data for Frankfurt, Germany (station ID `10637`) for the year 2024:

```bash
meteo daily 10637 --start 2024-01-01 --end 2024-12-31
```

## 📖 Commands

### `meteo station` — Browse weather stations

```bash
meteo station 10637                        # Metadata for a specific station
meteo station --country DE                 # List stations by country
meteo station --country DE --state HE      # Filter by country and state
meteo station --name "Frankfurt"           # Search by name
```

| Option        | Short | Description                                      |
| ------------- | ----- | ------------------------------------------------ |
| `--country`   | `-c`  | ISO 3166-1 alpha-2 country code                  |
| `--state`     |       | State or region code                             |
| `--name`      | `-n`  | Station name (partial match)                     |
| `--wmo`       | `-w`  | WMO station ID                                   |
| `--icao`      | `-i`  | ICAO station ID                                  |
| `--iata`      |       | IATA station ID                                  |
| `--national`  | `-N`  | National station ID                              |
| `--bbox`      |       | Bounding box (`lon_min,lat_min,lon_max,lat_max`) |
| `--sql`       |       | Arbitrary SQL query                              |
| `--format`    | `-f`  | Output format: `csv`, `json`, `xlsx`, `parquet`  |
| `--output`    | `-o`  | Output file path (defaults to stdout)            |
| `--no-header` |       | Omit CSV header row                              |
| `--all`       | `-A`  | Print full table without truncation              |

### `meteo nearby` — Find stations near a location

```bash
meteo nearby 50.1109 8.6821                        # Nearest stations (default: 5 within 5 km)
meteo nearby 50.1109 8.6821 --limit 10             # Return up to 10 stations
meteo nearby 50.1109 8.6821 --radius 20000         # Search within 20 km
meteo nearby 50.1109 8.6821 --format json          # JSON output
```

| Option        | Short | Description                                     |
| ------------- | ----- | ----------------------------------------------- |
| `--limit`     | `-l`  | Maximum number of stations (default: 5)         |
| `--radius`    | `-r`  | Search radius in meters (default: 5000)         |
| `--format`    | `-f`  | Output format: `csv`, `json`, `xlsx`, `parquet` |
| `--output`    | `-o`  | Output file path (defaults to stdout)           |
| `--no-header` |       | Omit CSV header row                             |
| `--all`       | `-A`  | Print full table without truncation             |

### `meteo inventory` — Check data availability

```bash
meteo inventory 10637
meteo inventory 10637 --granularity daily --parameters tavg,tmin,tmax
```

| Option          | Short | Description                                                     |
| --------------- | ----- | --------------------------------------------------------------- |
| `--granularity` | `-g`  | Filter by granularity: `hourly`/`h`, `daily`/`d`, `monthly`/`m` |
| `--parameters`  | `-p`  | Comma-separated parameters (e.g. `tavg,tmin,tmax`)              |
| `--providers`   | `-P`  | Comma-separated data providers                                  |
| `--format`      | `-f`  | Output format: `csv`, `json`, `xlsx`, `parquet`                 |
| `--output`      | `-o`  | Output file path (defaults to stdout)                           |
| `--no-header`   |       | Omit CSV header row                                             |
| `--all`         | `-A`  | Print full table without truncation                             |

### `meteo hourly` — Hourly weather data

```bash
meteo hourly 10637 --start 2024-01-01 --end 2024-01-31
meteo h 10637 -s 2024-01-01 -e 2024-01-31                    # Short form
meteo hourly 10637 10635 -s 2024-01-01 -e 2024-01-31         # Multiple stations
meteo hourly 10637 --agg max -s 2024-01-01 -e 2024-01-31     # Aggregate by station and time
```

See [Common options](#common-options-hourly--daily--monthly--normals) below. Hourly also supports `--timezone`/`-t` (e.g. `Europe/Berlin`).

### `meteo daily` — Daily weather data

```bash
meteo daily 10637 --start 2024-01-01 --end 2024-12-31
meteo d 10637 -s 2024-01-01 -e 2024-12-31    # Short form
```

See [Common options](#common-options-hourly--daily--monthly--normals) below.

### `meteo monthly` — Monthly weather data

```bash
meteo monthly 10637 --start 2020 --end 2024
meteo m 10637 -s 2020 -e 2024               # Short form
```

See [Common options](#common-options-hourly--daily--monthly--normals) below.

### `meteo normals` — Climate normals

```bash
meteo normals 10637 --start 1991 --end 2020
meteo n 10637 -s 1991 -e 2020               # Short form
```

See [Common options](#common-options-hourly--daily--monthly--normals) below.

### Common options (hourly / daily / monthly / normals)

| Option           | Short | Description                                                   |
| ---------------- | ----- | ------------------------------------------------------------- |
| `--start`        | `-s`  | Start date (`YYYY-MM-DD`, `YYYY-MM`, `YYYY`)                  |
| `--end`          | `-e`  | End date (same formats)                                       |
| `--parameters`   | `-p`  | Comma-separated parameters (e.g. `tavg,tmin,tmax,prcp`)       |
| `--providers`    | `-P`  | Comma-separated data providers                                |
| `--format`       | `-f`  | Output format: `csv`, `json`, `xlsx`, `parquet`, `png`, `svg` |
| `--output`       | `-o`  | Output file path (defaults to stdout)                         |
| `--timezone`     | `-t`  | Timezone for timestamps (e.g. `Europe/Berlin`) — hourly only  |
| `--with-sources` | `-S`  | Include data source column in output                          |
| `--no-models`    |       | Exclude model data (e.g. MOSMIX)                              |
| `--no-header`    |       | Omit CSV header row                                           |
| `--no-cache`     |       | Disable result caching                                        |
| `--all`          | `-A`  | Print full table without truncation                           |
| `--agg`          |       | Aggregation function: `mean`, `sum`, `min`, `max`             |

### `meteo config` — Manage configuration

```bash
meteo config --list                        # List all settings
meteo config cache_enable false            # Set a value
meteo config interpolation_radius 25000
```

Configuration is stored in `cli.yml` under `typer.get_app_dir("meteostat")`.

### Shell completion

```bash
meteo --install-completion   # Bash, Zsh, Fish, PowerShell
```

## 🤝 Contributing

Please read our [contributing guidelines](https://dev.meteostat.net/contributing) for details on how to contribute to Meteostat.

## 📄 License

The Meteostat CLI is licensed under the [**MIT License**](https://github.com/meteostat/cli/blob/main/LICENSE). Data provided by Meteostat is licensed under [**Creative Commons Attribution 4.0 International (CC BY 4.0)**](https://creativecommons.org/licenses/by/4.0). See the [documentation](https://dev.meteostat.net/license) for details.

<!-- MARKDOWN LINKS & IMAGES -->

[pypi-shield]: https://img.shields.io/pypi/v/meteostat-cli
[pypi-url]: https://pypi.org/project/meteostat-cli/
[issues-shield]: https://img.shields.io/github/issues/meteostat/cli.svg
[issues-url]: https://github.com/meteostat/cli/issues
[license-shield]: https://img.shields.io/github/license/meteostat/cli.svg
[license-url]: https://github.com/meteostat/cli/blob/main/LICENSE
