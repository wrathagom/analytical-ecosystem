from types import SimpleNamespace

import pytest

from cli.config import HealthCheck, Service
from cli import commands


def make_service(
    service_id: str,
    name: str,
    url: str | None = None,
    credentials: str | None = None,
    healthcheck: HealthCheck | None = None,
) -> Service:
    return Service(
        id=service_id,
        name=name,
        category="other",
        url=url,
        credentials=credentials,
        healthcheck=healthcheck,
    )


def test_cmd_start_requires_profiles(capsys: pytest.CaptureFixture[str]) -> None:
    assert commands.cmd_start([]) is False
    out = capsys.readouterr().out
    assert "No services selected" in out


def test_cmd_start_prints_urls(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    services = {
        "postgres": make_service(
            "postgres",
            "PostgreSQL",
            url="http://localhost:5432",
            credentials="user/pass",
        )
    }

    monkeypatch.setattr(commands, "discover_services", lambda: services)
    monkeypatch.setattr(commands.docker, "start_services", lambda profiles: True)

    assert commands.cmd_start(["postgres"]) is True
    out = capsys.readouterr().out
    assert "Services started!" in out
    assert "PostgreSQL: http://localhost:5432 (user/pass)" in out


def test_container_to_service_id_handles_hyphens() -> None:
    assert (
        commands.container_to_service_id("analytical-ecosystem-big-beautiful-screens-1")
        == "big-beautiful-screens"
    )


def test_cmd_status_no_containers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(commands.docker, "get_running_containers", lambda: [])
    commands.cmd_status()
    out = capsys.readouterr().out
    assert "No services running." in out


def test_cmd_logs_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], str | None]] = []

    def fake_logs(profiles: list[str], service: str | None, follow: bool = True) -> None:
        calls.append((profiles, service))

    monkeypatch.setattr(commands.docker, "get_logs", fake_logs)
    commands.cmd_logs(["postgres"], "postgres")
    assert calls == [(["postgres"], "postgres")]


def test_cmd_test_no_containers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(commands.docker, "get_running_containers", lambda: [])
    assert commands.cmd_test() is False
    out = capsys.readouterr().out
    assert "No services running." in out


def test_cmd_test_healthchecks_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    services = {
        "postgres": make_service(
            "postgres",
            "PostgreSQL",
            healthcheck=HealthCheck(type="exec", command=["pg_isready"]),
        ),
        "grafana": make_service(
            "grafana",
            "Grafana",
            healthcheck=HealthCheck(type="http", endpoint="http://localhost:3001/api/health"),
        ),
    }

    containers = [
        {"name": "analytical-ecosystem-postgres-1", "status": "Up", "ports": ""},
        {"name": "analytical-ecosystem-grafana-1", "status": "Up", "ports": ""},
    ]

    monkeypatch.setattr(commands, "discover_services", lambda: services)
    monkeypatch.setattr(commands.docker, "get_running_containers", lambda: containers)
    monkeypatch.setattr(commands.docker, "get_container_health", lambda name: "healthy")
    monkeypatch.setattr(commands.docker, "get_container_status", lambda name: "running")
    monkeypatch.setattr(
        commands.docker,
        "exec_in_container",
        lambda name, cmd: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        commands.urllib.request,
        "urlopen",
        lambda url, timeout=5: SimpleNamespace(),
    )

    assert commands.cmd_test() is True
    out = capsys.readouterr().out
    assert "All tests passed!" in out
