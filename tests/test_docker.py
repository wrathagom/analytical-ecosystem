from pathlib import Path
from types import SimpleNamespace

import pytest

from cli import docker


def make_project_root(tmp_path: Path) -> Path:
    (tmp_path / "docker-compose.yml").write_text("name: test\n")
    services_dir = tmp_path / "services" / "svc"
    services_dir.mkdir(parents=True, exist_ok=True)
    (services_dir / "compose.yaml").write_text("services:\n  svc:\n    image: busybox\n")
    return tmp_path


def test_build_profile_args() -> None:
    assert docker.build_profile_args(["a", "b"]) == ["--profile", "a", "--profile", "b"]


def test_build_file_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = make_project_root(tmp_path)
    monkeypatch.setattr(docker, "get_project_root", lambda: root)

    args = docker.build_file_args(["svc", "missing"])
    assert args == [
        "-f",
        "docker-compose.yml",
        "-f",
        "services/svc/compose.yaml",
    ]


def test_compose_command_builds_expected_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = make_project_root(tmp_path)
    monkeypatch.setattr(docker, "get_project_root", lambda: root)

    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, capture_output=False, text=False):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(docker.subprocess, "run", fake_run)

    docker.compose_command(["ps"], profiles=["svc"])
    assert calls == [
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "-f",
            "services/svc/compose.yaml",
            "--profile",
            "svc",
            "ps",
        ]
    ]


def test_ensure_env_creates_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(docker, "get_project_root", lambda: tmp_path)
    monkeypatch.setattr(docker.os, "getuid", lambda: 4242)

    docker.ensure_env()
    env_file = tmp_path / ".env"
    assert env_file.exists()
    assert env_file.read_text() == "AIRFLOW_UID=4242\n"
