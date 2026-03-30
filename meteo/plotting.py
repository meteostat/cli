"""Plotting module for the Meteostat CLI.

Provides plot_dataframe() for generating PNG/SVG charts from weather data.
Matplotlib is lazily imported so it's only required when plotting is used.
"""

from pathlib import Path

import pandas as pd

# Pre-configured colors per parameter
PARAMETER_COLORS = {
    "temp": "#e74c3c",
    "tmin": "#3498db",
    "tmax": "#e67e22",
    "txmn": "#2980b9",
    "txmx": "#c0392b",
    "dwpt": "#1abc9c",
    "prcp": "#2ecc71",
    "pday": "#27ae60",
    "snow": "#95a5a6",
    "snwd": "#bdc3c7",
    "wspd": "#9b59b6",
    "wpgt": "#8e44ad",
    "wdir": "#34495e",
    "rhum": "#16a085",
    "pres": "#f39c12",
    "tsun": "#f1c40f",
    "cldc": "#7f8c8d",
    "vsby": "#2c3e50",
    "sghi": "#e74c3c",
    "sdni": "#e67e22",
    "sdhi": "#f39c12",
    "coco": "#7f8c8d",
}


def _get_param_label(col_str: str) -> str:
    """Get display label for a parameter column using parameter_service."""
    try:
        from meteostat.core.parameters import parameter_service
        from meteostat.enumerations import Granularity, Parameter

        param = Parameter(col_str)
        for granularity in Granularity:
            spec = parameter_service.get_parameter(param, granularity)
            if spec is not None:
                unit = spec.unit.value if spec.unit else None
                return f"{spec.name} ({unit})" if unit else spec.name
    except (ValueError, Exception):
        pass
    return col_str


# Default color cycle for unknown parameters
DEFAULT_COLORS = [
    "#e74c3c",
    "#3498db",
    "#2ecc71",
    "#f39c12",
    "#9b59b6",
    "#1abc9c",
    "#e67e22",
    "#34495e",
]


def plot_dataframe(
    df,
    output: str,
    fmt: str,
    title: str | None = None,
    width: float = 10,
    height: float = 6,
) -> None:
    """Generate a plot from a DataFrame and save to file.

    Parameters
    ----------
    df : pd.DataFrame
        The data to plot.
    output : str
        Output file path.
    fmt : str
        Output format ('png' or 'svg').
    title : str, optional
        Custom plot title.
    width : float
        Plot width in inches.
    height : float
        Plot height in inches.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        import typer

        typer.echo(
            "Error: Matplotlib is required for plot output. "
            'Install with: uv tool install "meteostat-cli[plot]"',
            err=True,
        )
        raise typer.Exit(1) from None

    # Flatten MultiIndex (e.g. normals returns a (station, month) index)
    if isinstance(df.index, pd.MultiIndex):
        try:
            df = df.droplevel(list(range(df.index.nlevels - 1)))
        except ValueError:
            df = df.reset_index(drop=True)

    # Filter out source columns (they contain provider names, not numeric data)
    # Also filter out non-numeric columns that cannot be plotted
    plot_cols = [
        col
        for col in df.columns
        if not str(col).endswith("_source") and pd.api.types.is_numeric_dtype(df[col])
    ]

    if not plot_cols:
        import typer

        typer.echo("Error: No plottable numeric data columns found.", err=True)
        raise typer.Exit(1)

    fig, ax = plt.subplots(figsize=(width, height))

    color_idx = 0
    plotted = 0
    for col in plot_cols:
        col_str = str(col)
        label = _get_param_label(col_str)
        color = PARAMETER_COLORS.get(
            col_str, DEFAULT_COLORS[color_idx % len(DEFAULT_COLORS)]
        )
        if col_str not in PARAMETER_COLORS:
            color_idx += 1

        # Drop NaN values for cleaner plots
        series = df[col].dropna()
        if series.empty:
            continue

        ax.plot(series.index, series.values, label=label, color=color, linewidth=1.2)
        plotted += 1

    if plotted == 0:
        import typer

        plt.close(fig)
        typer.echo(
            "Error: All data columns are empty (all NaN). Nothing to plot.", err=True
        )
        raise typer.Exit(1)

    ax.set_xlabel("Time")
    ax.set_ylabel("Value")

    if title:
        ax.set_title(title)

    ax.legend(loc="best", fontsize="small")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, format=fmt, dpi=150, bbox_inches="tight")
    plt.close(fig)
