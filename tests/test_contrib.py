"""Tests for the contributor commands (meteo station add/edit/delete/...)."""

import copy
import json
import shlex
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from meteo.commands.contrib.edit import launch_editor
from meteo.config import coerce_value, save_config
from meteo.contrib.duplicates import distance, find_duplicates
from meteo.contrib.repo import generate_id, serialize
from meteo.contrib.validation import fix_station, load_schema

FRANKFURT = {
    "id": "10637",
    "name": {"de": "Frankfurt Flughafen", "en": "Frankfurt Airport"},
    "country": "DE",
    "region": "HE",
    "identifiers": {"icao": "EDDF", "wmo": "10637"},
    "location": {"latitude": 50.05, "longitude": 8.6, "elevation": 111},
    "timezone": "Europe/Berlin",
}

BERLIN = {
    "id": "10384",
    "name": {"en": "Berlin Tempelhof"},
    "country": "DE",
    "region": "BE",
    "identifiers": {"wmo": "10384"},
    "location": {"latitude": 52.4667, "longitude": 13.4, "elevation": 48},
    "timezone": "Europe/Berlin",
}


def write(repo: Path, data: dict, station_id: str | None = None) -> Path:
    path = repo / "stations" / f"{station_id or data['id']}.json"
    path.write_text(serialize(data), encoding="utf-8")
    return path


def read(repo: Path, station_id: str) -> dict:
    return json.loads((repo / "stations" / f"{station_id}.json").read_text())


@pytest.fixture(autouse=True)
def config_path(tmp_path, monkeypatch):
    """Isolate the CLI config file from the user's config."""
    path = tmp_path / "config" / "cli.yml"
    monkeypatch.setattr("meteo.config._get_config_path", lambda: path)
    return path


@pytest.fixture
def repo(tmp_path):
    """A stations repository with two valid stations."""
    root = tmp_path / "weather-stations"
    (root / "stations").mkdir(parents=True)
    write(root, FRANKFURT)
    write(root, BERLIN)
    return root


@pytest.fixture
def run(invoke, repo):
    """Invoke `meteo station ...` against the test repository."""

    def _run(*args: str, input: str | None = None):
        return invoke("station", *args, "--repo", str(repo), input=input)

    return _run


class TestRouting:
    def test_lookup_still_works(self, invoke):
        with patch("meteostat.stations") as mock_stations:
            mock_stations.meta.return_value = None
            result = invoke("station", "99999")
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_lookup_without_id(self, invoke):
        with patch("meteostat.stations") as mock_stations:
            mock_stations.query.return_value = None
            result = invoke("station", "--country", "DE")
        mock_stations.query.assert_called_once()
        assert result.exit_code == 1

    def test_help_lists_contributor_commands(self, invoke):
        result = invoke("station", "--help")
        assert result.exit_code == 0
        assert "Usage: meteo station [OPTIONS]" in result.output
        assert "validate" in result.output

    @pytest.mark.parametrize(
        "command", ["add", "edit", "delete", "validate", "duplicates", "build"]
    )
    def test_subcommand_help(self, invoke, command):
        result = invoke("s", command, "--help")
        assert result.exit_code == 0
        assert f"Usage: meteo s {command}" in result.output
        assert "--repo" in result.output


class TestRepository:
    def test_config_key(self):
        assert coerce_value("stations_repo", "~/code/weather-stations") == (
            "~/code/weather-stations"
        )
        assert coerce_value("stations_repo", "123") == "123"

    def test_configured_repo(self, invoke, repo, config_path):
        save_config({"stations_repo": str(repo)})
        result = invoke("station", "validate", "10637")
        assert result.exit_code == 0

    def test_working_directory(self, invoke, repo, monkeypatch):
        monkeypatch.chdir(repo)
        result = invoke("station", "validate", "10637")
        assert result.exit_code == 0

    def test_no_repo(self, invoke, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = invoke("station", "validate")
        assert result.exit_code == 2
        assert "No stations repository found" in result.output

    def test_invalid_repo(self, invoke, tmp_path):
        result = invoke("station", "validate", "--repo", str(tmp_path))
        assert result.exit_code == 2
        assert "not a stations repository" in result.output

    def test_generate_id(self, repo):
        for _ in range(50):
            station_id = generate_id(repo)
            assert len(station_id) == 5
            assert not station_id.isdigit()
            assert not (repo / "stations" / f"{station_id}.json").exists()

    def test_missing_extra(self, run):
        with patch.dict(sys.modules, {"jsonschema": None}):
            result = run("validate")
        assert result.exit_code == 1
        assert "meteostat-cli[contrib]" in result.output


class TestValidate:
    def test_all_valid(self, run):
        result = run("validate")
        assert result.exit_code == 0
        assert "✓ 10384" in result.output
        assert "✓ 10637" in result.output
        assert "All 2 stations valid" in result.output

    def test_errors(self, run, repo):
        write(
            repo,
            FRANKFURT
            | {
                "id": "0A1B2",
                "name": {"en": "frankfurt downtown"},
                "region": "XX",
                "identifiers": {"wmo": "10637"},
                "location": {"latitude": 95.2, "longitude": 8.6, "elevation": 100},
                "timezone": "Europa/Frankfurt",
            },
        )
        result = run("validate", "0A1B2", "10384")
        assert result.exit_code == 1
        output = result.output
        assert "✗ 0A1B2  location.latitude: 95.2 is out of range (-90 to 90)" in output
        assert 'timezone: "Europa/Frankfurt" is not a valid IANA time zone' in output
        assert 'name.en: "frankfurt downtown" should be capitalized' in output
        assert 'region: "XX" is not a valid ISO 3166-2 subdivision of DE' in output
        assert 'identifiers.wmo: "10637" is also used by 10637' in output
        assert "✓ 10384" in output
        assert "1 of 2 stations invalid (5 errors)" in output

    def test_schema_errors(self, run, repo):
        data = dict(FRANKFURT)
        del data["timezone"]
        write(repo, data | {"country": "de", "foo": 1})
        result = run("validate", "10637")
        assert result.exit_code == 1
        assert "'timezone' is a required property" in result.output
        assert "country: 'de' does not match" in result.output
        assert "Additional properties are not allowed" in result.output

    def test_id_mismatch_and_invalid_json(self, run, repo):
        write(repo, FRANKFURT, "AAAAA")
        (repo / "stations" / "BBBBB.json").write_text("{")
        result = run("validate", "AAAAA", "BBBBB", "CCCCC")
        assert result.exit_code == 1
        assert 'AAAAA  id: "10637" does not match the file name' in result.output
        assert "BBBBB  Invalid JSON" in result.output
        assert "CCCCC  Station not found" in result.output

    def test_quiet_and_warnings(self, run, repo):
        (repo / "stations" / "10637.json").write_text(json.dumps(FRANKFURT))
        result = run("validate", "-q")
        assert result.exit_code == 0
        assert "! 10637  File is not formatted consistently" in result.output
        assert "10384" not in result.output
        assert "All 2 stations valid (1 warning)" in result.output

    def test_fix(self, run, repo):
        broken = FRANKFURT | {
            "name": {"en": " frankfurt Airport"},
            "country": "de",
            "region": "he",
            "identifiers": {"wmo": 10637, "icao": "EDDF"},
            "location": {
                "latitude": 50.05,
                "longitude": 8.6,
                "elevation": 111.0,
                "height": 2,
            },
            "active": True,
        }
        (repo / "stations" / "10637.json").write_text(
            json.dumps({"timezone": "Europe/Berlin"} | broken | {"id": "X"})
        )
        result = run("validate", "--fix")
        assert result.exit_code == 0, result.output
        assert "Fixed 1 station" in result.output
        raw = (repo / "stations" / "10637.json").read_text()
        assert raw == serialize(FRANKFURT | {"name": {"en": "Frankfurt Airport"}})

    def test_fix_station_keeps_valid_data(self, repo):
        assert fix_station("10637", FRANKFURT, load_schema()) == FRANKFURT

    def test_changed(self, run, repo):
        def git(*args):
            subprocess.run(
                ["git", "-C", str(repo), *args], check=True, capture_output=True
            )

        git("init", "-q", "-b", "main")
        git("add", ".")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
        git("checkout", "-qb", "feature")

        result = run("validate", "--changed")
        assert result.exit_code == 0
        assert "No changed stations" in result.output

        write(repo, BERLIN | {"name": {"en": "berlin"}})
        write(repo, FRANKFURT | {"id": "0A1B2", "identifiers": {}})
        result = run("validate", "--changed")
        assert result.exit_code == 1
        assert "✓ 0A1B2" in result.output
        assert "✗ 10384" in result.output
        assert "10637" not in result.output

    def test_changed_without_git(self, run):
        result = run("validate", "--changed")
        assert result.exit_code == 2


class TestAdd:
    ARGS = (
        "--name",
        "Frankfurt Downtown",
        "--name",
        "de=Frankfurt Innenstadt",
        "--country",
        "de",
        "--region",
        "HE",
        "--lat",
        "50.11",
        "--lon",
        "8.68",
        "--elevation",
        "100",
        "--timezone",
        "Europe/Berlin",
        "--id",
        "national=1234",
    )

    def test_non_interactive(self, run, repo):
        result = run("add", *self.ARGS, "--yes")
        assert result.exit_code == 0, result.output
        station_id = result.output.split()[2]
        assert f"(stations/{station_id}.json)" in result.output
        assert read(repo, station_id) == {
            "id": station_id,
            "name": {"de": "Frankfurt Innenstadt", "en": "Frankfurt Downtown"},
            "country": "DE",
            "region": "HE",
            "identifiers": {"national": "1234"},
            "location": {"latitude": 50.11, "longitude": 8.68, "elevation": 100},
            "timezone": "Europe/Berlin",
        }

    def test_dry_run(self, run, repo):
        result = run("add", *self.ARGS, "--yes", "--dry-run")
        assert result.exit_code == 0
        assert json.loads(result.output)["country"] == "DE"
        assert len(list((repo / "stations").iterdir())) == 2

    def test_interactive(self, run, repo):
        result = run(
            "add",
            input="Frankfurt Downtown\nDE\n\n50.11\n8.68\n100\nEurope/Berlin\nwmo=D1234\n",
        )
        assert result.exit_code == 0, result.output
        station_id = result.output.split("Created station ")[1].split()[0]
        data = read(repo, station_id)
        assert data["region"] is None
        assert data["identifiers"] == {"wmo": "D1234"}

    def test_options_are_not_prompted(self, run, repo):
        args = [a for a in self.ARGS if a not in ("--region", "HE")]
        result = run("add", *args, input="\n")
        assert result.exit_code == 0, result.output
        assert "Region" in result.output
        assert "Latitude" not in result.output
        assert "Identifiers" not in result.output

    def test_missing_options(self, run):
        result = run("add", "--name", "Test", "--yes")
        assert result.exit_code == 2
        assert "--country, --lat, --lon, --elevation, --timezone" in result.output

    def test_invalid(self, run, repo):
        args = list(self.ARGS)
        args[args.index("Europe/Berlin")] = "Europe/Frankfurt"
        result = run("add", *args, "--id", "wmo=10637", "--yes")
        assert result.exit_code == 1
        assert "not a valid IANA time zone" in result.output
        assert "is also used by 10637" in result.output
        assert len(list((repo / "stations").iterdir())) == 2

    def test_invalid_identifier(self, run):
        result = run("add", *self.ARGS, "--id", "wmo", "--yes")
        assert result.exit_code == 2

    def test_duplicate_confirmation(self, run, repo):
        args = [
            "--name",
            "Frankfurt Airport West",
            "--country",
            "DE",
            "--region",
            "HE",
            "--lat",
            "50.051",
            "--lon",
            "8.601",
            "--elevation",
            "111",
            "--timezone",
            "Europe/Berlin",
            "--id",
            "icao=EDDX",
        ]
        result = run("add", *args, input="n\n")
        assert result.exit_code == 1
        assert "10637  Frankfurt Airport (132 m, location, name)" in result.output
        assert len(list((repo / "stations").iterdir())) == 2

        result = run("add", *args, "--yes")
        assert result.exit_code == 0
        assert len(list((repo / "stations").iterdir())) == 3


EDITOR = "meteo.commands.contrib.edit.launch_editor"


class TestEdit:
    def test_set_and_unset(self, run, repo):
        result = run(
            "edit",
            "10637",
            "--set",
            "name.en=Frankfurt/Main Airport",
            "--set",
            "identifiers.wmo=10638",
            "--set",
            "location.elevation=112",
            "--unset",
            "identifiers.icao",
        )
        assert result.exit_code == 0, result.output
        assert "Updated station 10637 (stations/10637.json)" in result.output
        data = read(repo, "10637")
        assert data["name"]["en"] == "Frankfurt/Main Airport"
        assert data["identifiers"] == {"wmo": "10638"}
        assert data["location"]["elevation"] == 112

    def test_set_null(self, run, repo):
        result = run("edit", "10637", "--set", "region=null")
        assert result.exit_code == 0
        assert read(repo, "10637")["region"] is None

    def test_invalid_change_is_not_written(self, run, repo):
        result = run("edit", "10637", "--set", "location.latitude=95")
        assert result.exit_code == 1
        assert "out of range" in result.output
        assert read(repo, "10637") == FRANKFURT

    def test_id_cannot_be_changed(self, run):
        result = run("edit", "10637", "--set", "id=10638")
        assert result.exit_code == 2
        assert "cannot be changed" in result.output

    def test_unset_missing(self, run):
        result = run("edit", "10637", "--unset", "identifiers.iata")
        assert result.exit_code == 2
        assert "not set" in result.output

    def test_dry_run(self, run, repo):
        result = run("edit", "10637", "--set", "name.fr=Aéroport", "--dry-run")
        assert result.exit_code == 0
        assert json.loads(result.output)["name"]["fr"] == "Aéroport"
        assert read(repo, "10637") == FRANKFURT

    def test_not_found(self, run):
        result = run("edit", "ZZZZZ", "--set", "name.en=X")
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_editor(self, run, repo):
        edited = serialize(FRANKFURT | {"timezone": "Europe/Paris"}) + "\n"
        with patch(EDITOR, return_value=edited) as edit:
            result = run("edit", "10637", "--editor", "nano")
        assert result.exit_code == 0, result.output
        assert edit.call_args.args[1:] == ("10637.json", "nano")
        assert read(repo, "10637")["timezone"] == "Europe/Paris"

    def test_editor_no_changes(self, run):
        with patch(EDITOR, side_effect=lambda text, *_: text):
            result = run("edit", "10637")
        assert result.exit_code == 0
        assert "No changes" in result.output

    def test_editor_reopen_and_discard(self, run, repo):
        invalid = serialize(FRANKFURT | {"timezone": "Mars/Olympus"})
        with patch(EDITOR, return_value=invalid) as edit:
            result = run("edit", "10637", input="y\nn\n")
        assert result.exit_code == 1
        assert edit.call_count == 2
        # The second editor session starts with the previous edits
        assert edit.call_args.args[0] == invalid
        assert "Changes discarded" in result.output
        assert read(repo, "10637") == FRANKFURT

    def test_launch_editor(self, tmp_path):
        script = tmp_path / "editor.py"
        script.write_text(
            "import sys, pathlib\n"
            "path = pathlib.Path(sys.argv[-1])\n"
            "path.write_text(path.name + ':' + path.read_text())\n"
        )
        editor = f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"
        assert launch_editor("{}", "10637.json", editor) == "10637.json:{}"

    def test_launch_editor_fails(self):
        with pytest.raises(typer.Exit):
            launch_editor("{}", "10637.json", "/nonexistent/editor")


class TestDelete:
    def test_confirm(self, run, repo):
        result = run("delete", "10637", input="y\n")
        assert result.exit_code == 0
        assert "Frankfurt Airport" in result.output
        assert "Deleted station 10637" in result.output
        assert not (repo / "stations" / "10637.json").exists()

    def test_abort(self, run, repo):
        result = run("delete", "10637", input="n\n")
        assert result.exit_code == 1
        assert (repo / "stations" / "10637.json").exists()

    def test_yes(self, run, repo):
        result = run("delete", "10637", "--yes")
        assert result.exit_code == 0
        assert not (repo / "stations" / "10637.json").exists()


class TestDuplicates:
    @pytest.fixture
    def duplicates(self, repo):
        # Shares the WMO ID with 10637 and has a similar name
        write(repo, FRANKFURT | {"id": "0A1B2", "identifiers": {"wmo": "10637"}})
        # Close to 10637 with a similar name
        write(
            repo,
            FRANKFURT
            | {
                "id": "D4X9K",
                "name": {"en": "Frankfurt Airport (Aut)"},
                "identifiers": {},
                "location": {"latitude": 50.052, "longitude": 8.6, "elevation": 1},
            },
        )
        # Close to 10637, but with a different name
        write(
            repo,
            FRANKFURT
            | {
                "id": "E5Y0L",
                "name": {"en": "Kelsterbach"},
                "identifiers": {},
                "location": {"latitude": 50.051, "longitude": 8.6, "elevation": 1},
            },
        )

    def test_csv(self, run, duplicates):
        result = run("duplicates", "-f", "csv")
        assert result.exit_code == 1
        assert result.output.splitlines() == [
            "station_a,station_b,distance,reasons",
            '0A1B2,10637,0,"wmo, location, name"',
            '0A1B2,D4X9K,222,"location, name"',
            '10637,D4X9K,222,"location, name"',
        ]

    def test_radius(self, run, duplicates):
        result = run("duplicates", "-r", "100", "-f", "json")
        assert result.exit_code == 1
        assert json.loads(result.output) == [
            {
                "station_a": "0A1B2",
                "station_b": "10637",
                "distance": 0,
                "reasons": "wmo, location, name",
            }
        ]

    def test_filters(self, run, duplicates):
        result = run("duplicates", "--id", "d4x9k", "-f", "csv", "--no-header")
        assert len(result.output.splitlines()) == 2
        result = run("duplicates", "--country", "FR")
        assert result.exit_code == 0

    def test_none(self, run):
        result = run("duplicates")
        assert result.exit_code == 0
        assert "No potential duplicates found" in result.output

    def test_find_duplicates_same_name_far_away(self):
        far = BERLIN | {"id": "AAAAA", "identifiers": {}, "name": FRANKFURT["name"]}
        assert find_duplicates({"10637": FRANKFURT, "AAAAA": far}) == []

    def test_distance(self):
        assert distance(50.05, 8.6, 52.4667, 13.4) == pytest.approx(428_541, abs=1)


class TestBuild:
    def test_build(self, run, repo, monkeypatch):
        # Make sure the schema allows the `active` property
        schema = load_schema()
        schema["properties"]["active"] = {"type": "boolean"}
        monkeypatch.setattr(
            "meteo.contrib.validation.load_schema", lambda: copy.deepcopy(schema)
        )
        write(repo, BERLIN | {"id": "INACT", "identifiers": {}, "active": False})
        write(repo, FRANKFURT | {"id": "ACTIV", "identifiers": {}, "active": True})
        write(repo, FRANKFURT | {"id": "BAD00", "identifiers": {}, "timezone": "X"})
        result = run("build")
        assert result.exit_code == 0, result.output
        assert "✗ BAD00" in result.output
        assert "with 3 stations (1 skipped)" in result.output

        conn = sqlite3.connect(repo / "stations.db")
        ids = [row[0] for row in conn.execute("SELECT id FROM stations ORDER BY id")]
        assert ids == ["10384", "10637", "ACTIV"]
        assert conn.execute(
            "SELECT name FROM names WHERE station = '10637' AND language = 'de'"
        ).fetchone() == ("Frankfurt Flughafen",)
        assert conn.execute(
            "SELECT value FROM identifiers WHERE station = '10637' AND key = 'icao'"
        ).fetchone() == ("EDDF",)
        conn.close()

    def test_skip_validation(self, run, repo, tmp_path):
        write(repo, FRANKFURT | {"id": "BAD00", "identifiers": {}, "timezone": "X"})
        data = dict(BERLIN)
        del data["location"]
        write(repo, data | {"id": "BAD01"})
        output = tmp_path / "out" / "custom.db"
        result = run("build", "--skip-validation", "-o", str(output))
        assert result.exit_code == 0, result.output
        assert "✗ BAD01  Missing property 'location'" in result.output
        assert "with 3 stations (1 skipped)" in result.output
        assert output.exists()
        assert not (repo / "stations.db").exists()

