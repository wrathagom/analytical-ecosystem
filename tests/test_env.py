from pathlib import Path

import pytest

from cli import env as env_utils


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_generate_env_file_includes_fragments(tmp_path: Path) -> None:
    write_file(tmp_path / "docker-compose.yml", "name: test\n")
    write_file(tmp_path / "env" / "common.env", "TIMEZONE=UTC\n")
    write_file(
        tmp_path / "services" / "app" / "service.yaml",
        "name: App\ncategory: other\n",
    )
    write_file(
        tmp_path / "services" / "app" / "env.example",
        "APP_PORT=9999\n",
    )

    output = tmp_path / ".env.example"
    selected, fragments = env_utils.generate_env_file(
        profiles=["app"],
        output_path=output,
        root=tmp_path,
    )

    content = output.read_text()
    assert selected == ["app"]
    assert fragments == [tmp_path / "env" / "common.env", tmp_path / "services" / "app" / "env.example"]
    assert "TIMEZONE=UTC" in content
    assert "APP_PORT=9999" in content


def test_generate_env_file_unknown_profile(tmp_path: Path) -> None:
    write_file(tmp_path / "docker-compose.yml", "name: test\n")
    write_file(
        tmp_path / "services" / "app" / "service.yaml",
        "name: App\ncategory: other\n",
    )

    with pytest.raises(ValueError, match="Unknown profiles"):
        env_utils.generate_env_file(
            profiles=["missing"],
            output_path=tmp_path / ".env.example",
            root=tmp_path,
        )
