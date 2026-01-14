from pathlib import Path

from cli.config import load_env_file, expand_env_vars, expand_config, discover_services


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_load_env_file_ignores_comments_and_quotes(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# comment",
                "PLAIN=value",
                "QUOTED=\"quoted value\"",
                "SINGLE='single value'",
                "export EXPORTED=ok",
                "EMPTY=",
            ]
        )
    )

    env = load_env_file(env_path)
    assert env["PLAIN"] == "value"
    assert env["QUOTED"] == "quoted value"
    assert env["SINGLE"] == "single value"
    assert env["EXPORTED"] == "ok"
    assert env["EMPTY"] == ""


def test_expand_env_vars_with_defaults() -> None:
    env = {"SET": "on", "EMPTY": ""}
    assert expand_env_vars("${SET}", env) == "on"
    assert expand_env_vars("${MISSING:-fallback}", env) == "fallback"
    assert expand_env_vars("${EMPTY:-fallback}", env) == "fallback"
    assert expand_env_vars("http://localhost:${PORT:-8080}", env) == "http://localhost:8080"


def test_expand_config_recurses() -> None:
    env = {"PORT": "9999"}
    config = {
        "port": "${PORT:-8000}",
        "healthcheck": {
            "endpoint": "http://localhost:${PORT:-8000}/health",
        },
        "command": ["echo", "${PORT:-8000}"],
    }

    expanded = expand_config(config, env)
    assert expanded["port"] == "9999"
    assert expanded["healthcheck"]["endpoint"] == "http://localhost:9999/health"
    assert expanded["command"] == ["echo", "9999"]


def test_discover_services_expands_env_and_ports(tmp_path: Path) -> None:
    write_file(tmp_path / "docker-compose.yml", "name: test\n")
    write_file(tmp_path / ".env", "APP_PORT=5555\n")
    write_file(
        tmp_path / "services" / "app" / "service.yaml",
        "\n".join(
            [
                "name: App",
                "category: other",
                "port: \"${APP_PORT:-8000}\"",
                "url: \"http://localhost:${APP_PORT:-8000}\"",
                "healthcheck:",
                "  type: http",
                "  endpoint: \"http://localhost:${APP_PORT:-8000}/health\"",
            ]
        ),
    )

    services = discover_services(tmp_path)
    service = services["app"]
    assert service.port == 5555
    assert service.url == "http://localhost:5555"
    assert service.healthcheck is not None
    assert service.healthcheck.endpoint == "http://localhost:5555/health"
