"""Execute generated recipes to verify fail-fast shell settings on real Make."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from bootstrapper.generators.templates import render_template


@pytest.mark.parametrize(
    "recipe",
    [
        "false; touch continued",
        "false | true; touch continued",
        "echo $$BOOTSTRAPPER_UNSET_FOR_TEST; touch continued",
    ],
)
def test_generated_makefile_stops_after_shell_failure(tmp_path: Path, recipe: str) -> None:
    make = shutil.which("make")
    if make is None:
        pytest.skip("Make is not installed")
    content = render_template("Makefile.j2", {"project_name": "TestAPI"})
    (tmp_path / "Makefile").write_text(content + f"\ncheck-shell:\n\t@{recipe}\n")
    environment = os.environ.copy()
    environment.pop("BOOTSTRAPPER_UNSET_FOR_TEST", None)
    result = subprocess.run(
        [make, "check-shell"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert not (tmp_path / "continued").exists()
