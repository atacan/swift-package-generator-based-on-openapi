"""Exercise generated secret-scanning configuration and Git behavior offline."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from bootstrapper.generators.templates import generate_config_files, render_template

ZERO_SHA = "0" * 40
PRE_COMMIT = shutil.which("pre-commit")


@pytest.fixture
def workflow():
    # BaseLoader preserves the GitHub Actions `on` key under YAML 1.1 parsers.
    return yaml.load(render_template("secret-scan.yml.j2", {}), Loader=yaml.BaseLoader)


@pytest.fixture
def hook_config():
    return yaml.safe_load(render_template(".pre-commit-config.yaml.j2", {}))


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=20, check=True
    )
    return result.stdout.strip()


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet", "--initial-branch=main")
    git(repo, "config", "user.email", "tests@example.invalid")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "commit.gpgsign", "false")
    return repo


def commit(repo, content="clean\n", filename="history.txt"):
    (repo / filename).write_text(content, encoding="utf-8")
    git(repo, "add", filename)
    git(repo, "commit", "--quiet", "-m", "Test commit")
    return git(repo, "rev-parse", "HEAD")


def resolve_range(workflow, repo, **event):
    output = repo.parent / "range-output"
    output.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        "EVENT_NAME": "push",
        "PUSH_BEFORE": ZERO_SHA,
        "PUSH_AFTER": ZERO_SHA,
        "PUSH_DELETED": "false",
        "PR_BASE": "",
        "PR_HEAD": "",
        "DEFAULT_BRANCH": "main",
        "PUSH_REF": "refs/heads/main",
        "GITHUB_OUTPUT": str(output),
        **event,
    }
    step = workflow["jobs"]["scan_range"]["steps"][1]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
    return result, values


@pytest.mark.parametrize("file_format", [".yaml", ".yml", ".json"])
def test_generate_and_preserve_scanning_files(tmp_path, file_format):
    generated = generate_config_files(tmp_path, "TestAPI", file_format)
    paths = [".pre-commit-config.yaml", ".github/workflows/secret-scan.yml"]
    for name in paths:
        assert generated[name] is True
        yaml.load((tmp_path / name).read_text(), Loader=yaml.BaseLoader)
        (tmp_path / name).write_text("# Custom scanning configuration\n", encoding="utf-8")

    existing_workflow = tmp_path / ".github/workflows/build.yml"
    existing_workflow.write_text("# Existing build\n", encoding="utf-8")
    regenerated = generate_config_files(tmp_path, "OtherAPI", file_format)
    for name in paths:
        assert regenerated[name] is False
        assert (tmp_path / name).read_text() == "# Custom scanning configuration\n"
    assert existing_workflow.read_text() == "# Existing build\n"


def test_pinned_hooks_use_staged_scans(hook_config):
    betterleaks, trufflehog = hook_config["repos"]
    assert betterleaks["rev"] == "v1.9.0"
    assert betterleaks["hooks"][0]["id"] == "betterleaks"
    assert trufflehog["rev"] == "v3.97.9"
    hook = trufflehog["hooks"][0]
    assert hook["entry"] == (
        "trufflehog filesystem --results=verified --fail --fail-on-scan-errors --no-update"
    )
    assert hook["pass_filenames"] is True
    for repo in hook_config["repos"]:
        assert repo["hooks"][0]["stages"] == ["pre-commit"]


def test_workflow_scanners_share_range_and_fail_findings(workflow):
    assert set(workflow["on"]) == {"push", "pull_request"}
    assert workflow["on"]["push"]["branches"] == ["**"]
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        checkout = job["steps"][0]
        assert checkout["uses"] == "actions/checkout@v4"
        assert checkout["with"]["fetch-depth"] == "0"
        assert checkout["with"]["persist-credentials"] == "false"
    for scanner in ["betterleaks", "trufflehog"]:
        job = workflow["jobs"][scanner]
        assert job["needs"] == "scan_range"
        assert job["if"] == "needs.scan_range.outputs.scan == 'true'"
    betterleaks = workflow["jobs"]["betterleaks"]["steps"]
    assert "sha256sum --check --ignore-missing" in betterleaks[1]["run"]
    assert '--log-opts="$SCAN_LOG_OPTS" --redact' in betterleaks[2]["run"]
    trufflehog = workflow["jobs"]["trufflehog"]["steps"][-1]
    assert trufflehog["uses"] == "trufflesecurity/trufflehog@v3.97.9"
    assert trufflehog["with"] == {
        "version": "3.97.9",
        "base": "${{ needs.scan_range.outputs.base }}",
        "head": "${{ needs.scan_range.outputs.head }}",
        "extra_args": "--results=verified --fail-on-scan-errors",
    }


def test_push_excludes_older_findings_and_includes_every_incoming_commit(workflow, git_repo):
    base = commit(git_repo, "TEST_SECRET older finding\n")
    introduced = commit(git_repo, "TEST_SECRET incoming finding\n")
    head = commit(git_repo, "clean again\n")
    result, values = resolve_range(workflow, git_repo, PUSH_BEFORE=base, PUSH_AFTER=head)
    assert result.returncode == 0, result.stderr
    assert values["base"] == base
    assert values["head"] == head
    assert values["scan"] == "true"
    scanned = git(git_repo, "rev-list", *values["log_opts"].split()).splitlines()
    assert set(scanned) == {introduced, head}


def test_pull_request_uses_merge_base(workflow, git_repo):
    common = commit(git_repo)
    git(git_repo, "checkout", "--quiet", "-b", "feature")
    head = commit(git_repo, "feature\n")
    git(git_repo, "checkout", "--quiet", "main")
    base_head = commit(git_repo, "main advanced\n")
    result, values = resolve_range(
        workflow, git_repo, EVENT_NAME="pull_request", PR_BASE=base_head, PR_HEAD=head
    )
    assert result.returncode == 0, result.stderr
    assert values["base"] == common
    assert git(git_repo, "rev-list", *values["log_opts"].split()) == head


def test_new_branch_uses_default_branch(workflow, git_repo):
    base = commit(git_repo)
    git(git_repo, "update-ref", "refs/remotes/origin/main", base)
    git(git_repo, "checkout", "--quiet", "-b", "feature")
    head = commit(git_repo, "feature\n")
    result, values = resolve_range(
        workflow, git_repo, PUSH_AFTER=head, PUSH_REF="refs/heads/feature"
    )
    assert result.returncode == 0, result.stderr
    assert values["base"] == base
    assert git(git_repo, "rev-list", *values["log_opts"].split()) == head


@pytest.mark.parametrize("default_ref_exists", [False, True])
def test_initial_push_includes_root_commit(workflow, git_repo, default_ref_exists):
    root = commit(git_repo)
    head = commit(git_repo, "next\n")
    if default_ref_exists:
        git(git_repo, "update-ref", "refs/remotes/origin/main", head)
    result, values = resolve_range(workflow, git_repo, PUSH_AFTER=head)
    assert result.returncode == 0, result.stderr
    assert values["base"] == ""
    assert set(git(git_repo, "rev-list", *values["log_opts"].split()).splitlines()) == {
        root,
        head,
    }


def test_deleted_branch_is_skipped_without_resolving_head(workflow, git_repo):
    result, values = resolve_range(workflow, git_repo, PUSH_DELETED="true")
    assert result.returncode == 0, result.stderr
    assert values == {"scan": "false"}
    assert "!github.event.deleted" in workflow["jobs"]["scan_range"]["if"]


def test_empty_push_range_is_skipped(workflow, git_repo):
    head = commit(git_repo)
    result, values = resolve_range(workflow, git_repo, PUSH_BEFORE=head, PUSH_AFTER=head)
    assert result.returncode == 0, result.stderr
    assert values == {"scan": "false"}


def test_unresolvable_push_base_fails(workflow, git_repo):
    head = commit(git_repo)
    result, values = resolve_range(workflow, git_repo, PUSH_BEFORE="f" * 40, PUSH_AFTER=head)
    assert result.returncode != 0
    assert "Cannot resolve required scan commit" in result.stderr
    assert values == {}


@pytest.fixture
def offline_hooks(git_repo, hook_config, monkeypatch):
    """Run real pre-commit staging behavior with fake, offline scanner binaries."""
    if PRE_COMMIT is None:
        pytest.skip("pre-commit executable is needed for hook smoke tests")
    fake_bin = git_repo.parent / "bin"
    fake_bin.mkdir()
    log = git_repo.parent / "scanner-log"
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SCANNER_LOG", str(log))
    script = """#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

scanner = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['SCANNER_LOG'], 'a') as log:
    log.write(json.dumps({'scanner': scanner, 'args': args}) + '\\n')
if os.environ.get('FAKE_SCANNER_FAILURE') == scanner:
    sys.exit(2)
if scanner == 'betterleaks':
    diff = subprocess.run(['git', 'diff', '--cached', '--no-ext-diff', '--unified=0'],
                          capture_output=True, text=True, check=True).stdout
    added = '\\n'.join(line for line in diff.splitlines()
                      if line.startswith('+') and not line.startswith('+++'))
    sys.exit(1 if 'TEST_SECRET' in added else 0)
paths = [arg for arg in args[1:] if not arg.startswith('--')]
sys.exit(183 if any('TRUFFLEHOG_VERIFIED' in Path(path).read_text() for path in paths) else 0)
"""
    for scanner in ["betterleaks", "trufflehog"]:
        executable = fake_bin / scanner
        executable.write_text(script, encoding="utf-8")
        executable.chmod(0o755)
    betterleaks, trufflehog = [repo["hooks"][0] for repo in hook_config["repos"]]
    # Substitute upstream Go installation only; preserve the generated hook settings.
    config = {
        **hook_config,
        "repos": [
            {
                "repo": "local",
                "hooks": [
                    {
                        **betterleaks,
                        "name": "Betterleaks",
                        "language": "system",
                        "entry": "betterleaks git --pre-commit --redact --staged --verbose",
                        "pass_filenames": False,
                    },
                    {**trufflehog, "name": "TruffleHog", "language": "system"},
                ],
            }
        ],
    }
    config_path = git_repo / ".pre-commit-config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    # Install actual hooks, with isolated caches and no scanner/provider downloads.
    monkeypatch.setenv("PRE_COMMIT_HOME", str(git_repo.parent / "pre-commit-cache"))
    subprocess.run([PRE_COMMIT, "install"], cwd=git_repo, check=True, capture_output=True)
    return log


@pytest.mark.parametrize("initial", [False, True])
@pytest.mark.parametrize(
    "content,allowed",
    [
        ("clean\n", True),
        ("TEST_SECRET\n", False),
        ("TRUFFLEHOG_VERIFIED\n", False),
    ],
)
def test_hook_blocks_findings_on_first_and_later_commits(
    git_repo, offline_hooks, initial, content, allowed
):
    if not initial:
        commit(git_repo)
    (git_repo / "api example.txt").write_text(content, encoding="utf-8")
    git(git_repo, "add", "api example.txt")
    result = subprocess.run(
        ["git", "commit", "-m", "Check secrets"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (result.returncode == 0) is allowed, result.stdout + result.stderr
    logs = [json.loads(line) for line in offline_hooks.read_text().splitlines()]
    assert {entry["scanner"] for entry in logs} == {"betterleaks", "trufflehog"}
    assert "api example.txt" in logs[-1]["args"]


def test_hook_hides_and_restores_unstaged_secrets(git_repo, offline_hooks):
    commit(git_repo, filename="api example.txt")
    path = git_repo / "api example.txt"
    path.write_text("staged clean edit\n", encoding="utf-8")
    git(git_repo, "add", path.name)
    path.write_text("staged clean edit\nTEST_SECRET TRUFFLEHOG_VERIFIED\n", encoding="utf-8")
    result = subprocess.run(
        ["git", "commit", "-m", "Only staged clean edit"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert git(git_repo, "show", f"HEAD:{path.name}") == "staged clean edit"
    assert path.read_text() == "staged clean edit\nTEST_SECRET TRUFFLEHOG_VERIFIED\n"


def test_hook_fails_on_scanner_execution_error(git_repo, offline_hooks, monkeypatch):
    (git_repo / "clean.txt").write_text("clean\n", encoding="utf-8")
    git(git_repo, "add", "clean.txt")
    monkeypatch.setenv("FAKE_SCANNER_FAILURE", "trufflehog")
    result = subprocess.run(
        ["git", "commit", "-m", "Scanner error"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0


def test_generated_config_validates_with_pre_commit(tmp_path):
    if PRE_COMMIT is None:
        pytest.skip("pre-commit executable is needed for configuration validation")
    generate_config_files(tmp_path, "TestAPI")
    result = subprocess.run(
        [PRE_COMMIT, "validate-config", str(tmp_path / ".pre-commit-config.yaml")],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
