"""Shared test fixtures for the Meteostat CLI test suite."""

import re

import pytest
from typer.testing import CliRunner

from meteo.cli import app

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class _StrippedResult:
    """Wrapper around CliRunner Result that strips ANSI escape codes from output."""

    def __init__(self, result):
        self._result = result
        self.output = _ANSI_RE.sub("", result.output)

    def __getattr__(self, name):
        return getattr(self._result, name)


@pytest.fixture
def runner():
    """Provide a Typer CliRunner for invoking CLI commands."""
    return CliRunner()


@pytest.fixture
def invoke(runner):
    """Shortcut to invoke CLI commands and return the result."""

    def _invoke(*args: str, catch_exceptions: bool = False):
        result = runner.invoke(app, list(args), catch_exceptions=catch_exceptions)
        return _StrippedResult(result)

    return _invoke
