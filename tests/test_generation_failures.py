"""Generation failures must retain diagnostics and produce a failing CLI exit status."""

import os
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from bootstrapper.generators.swift import run_openapi_generator
from bootstrapper.main import app


@pytest.fixture
def project(tmp_path):
    (tmp_path / "original_openapi.yaml").write_text(
        "openapi: 3.1.0\ninfo: {title: Test, version: '1.0.0'}\npaths: {}\n"
    )
    return tmp_path


@pytest.mark.parametrize("failed_stages", [("types",), ("client",), ("types", "client")])
def test_cli_reports_stage_diagnostics_and_fails(project, failed_stages):
    completed = [
        subprocess.CompletedProcess(
            args=["swift"],
            returncode=42 if stage in failed_stages else 0,
            stdout=f"{stage} validation context\n",
            stderr=f"[error] {stage}: invalid webhook responses\n",
        )
        for stage in ("types", "client")
    ]
    with patch("bootstrapper.generators.swift.subprocess.run", side_effect=completed):
        result = CliRunner().invoke(app, [str(project)])

    assert result.exit_code == 1, result.stdout
    assert "Success!" not in result.stdout
    assert "is ready" not in result.stdout
    for stage in failed_stages:
        assert f"{stage.capitalize()} generation failed" in result.stdout
        assert f"{stage} validation context" in result.stdout
        assert f"[error] {stage}: invalid webhook responses" in result.stdout
        assert "42" in result.stdout
    assert not list((project / "Sources").rglob("Client+*.swift"))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (FileNotFoundError(), ["Swift executable not found"]),
        (
            subprocess.TimeoutExpired(
                ["swift"], 300, output=b"partial stdout\n", stderr=b"partial stderr\n"
            ),
            ["timed out after 300 seconds", "partial stdout", "partial stderr"],
        ),
    ],
)
def test_cli_reports_execution_failures(project, error, expected):
    with patch("bootstrapper.generators.swift.subprocess.run", side_effect=error):
        result = CliRunner().invoke(app, [str(project)])

    assert result.exit_code == 1, result.stdout
    assert "Success!" not in result.stdout
    for message in expected:
        assert message in result.stdout
    assert "b'partial" not in result.stdout


def test_missing_spec_reports_its_path(tmp_path):
    result = run_openapi_generator(tmp_path, "Test")
    assert result["types_generated"] is False
    assert result["client_generated"] is False
    assert str(tmp_path / "openapi.yaml") in result["types_error"]
    assert str(tmp_path / "openapi.yaml") in result["client_error"]


def test_nonzero_exit_without_diagnostics_still_has_an_error(project):
    (project / "openapi.yaml").write_text("openapi: 3.1.0\n")
    completed = subprocess.CompletedProcess(args=["swift"], returncode=7, stdout="", stderr="")
    with patch("bootstrapper.generators.swift.subprocess.run", return_value=completed):
        result = run_openapi_generator(project, "Test")
    assert "exited with status 7" in result["types_error"]
    assert "exited with status 7" in result["client_error"]


def test_cli_still_reports_success_when_both_steps_succeed(project):
    completed = subprocess.CompletedProcess(args=["swift"], returncode=0, stdout="", stderr="")
    with patch("bootstrapper.generators.swift.subprocess.run", return_value=completed):
        result = CliRunner().invoke(app, [str(project)])
    assert result.exit_code == 0, result.stdout
    assert "Generated Types" in result.stdout
    assert "Generated Client" in result.stdout
    assert "Success!" in result.stdout


def test_real_cli_process_propagates_generator_failure(project):
    executable_dir = project / "bin"
    executable_dir.mkdir()
    swift = executable_dir / "swift"
    swift.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'Generator validation context'\n"
        "printf '%s\\n' 'Error: empty webhook responses' >&2\nexit 9\n"
    )
    swift.chmod(0o755)
    result = subprocess.run(
        [sys.executable, "-m", "bootstrapper.main", "bootstrap", str(project)],
        env={**os.environ, "PATH": str(executable_dir) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Error: empty webhook responses" in result.stdout + result.stderr
    assert "Generator validation context" in result.stdout + result.stderr
    assert "Success!" not in result.stdout + result.stderr


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("swift") is None, reason="Swift toolchain not available")
def test_real_generator_rejects_gladia_style_empty_webhook_responses(project):
    (project / "original_openapi.yaml").write_text(
        "openapi: 3.1.0\n"
        "info: {title: Invalid webhook, version: '1.0.0'}\n"
        "paths: {}\n"
        "webhooks:\n"
        "  transcription.created:\n"
        "    post:\n"
        "      responses: {}\n"
    )
    result = CliRunner().invoke(app, ["bootstrap", str(project)])
    assert result.exit_code == 1, result.stdout
    assert "Types generation failed" in result.stdout
    assert "Client generation failed" in result.stdout
    assert "at least one response" in result.stdout
    assert "transcription.created" in result.stdout
    assert "Success!" not in result.stdout
    assert "is ready" not in result.stdout
