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
uvx --from meteostat-cli meteo [YOUR_COMMANDS]
```

### ⚡ Shell Completion

```bash
meteo --install-completion   # Bash, Zsh, Fish, PowerShell
```

## 🚀 Usage

Want to know the hottest temperature of 2024 at Frankfurt Airport (station `10637`)? Run the following command:

```bash
meteo daily 10637 -s 2024-01-01 -e 2024-12-31 -p tmax --agg max
```

This will yield the following output:

```
         tmax
station
10637    35.9
```

## 📖 Documentation

Please refer to the [official documentation](https://dev.meteostat.net/cli) for detailed usage instructions and examples.

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
