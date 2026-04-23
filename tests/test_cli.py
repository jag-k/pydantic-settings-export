"""Tests for CLI module."""

import argparse
from pathlib import Path

import pytest

from pydantic_settings_export.cli import (
    dir_type,
    file_type,
    main,
    make_parser,
)

# =============================================================================
# Parser creation tests
# =============================================================================


def test_make_parser_returns_parser() -> None:
    """Test make_parser returns an ArgumentParser."""
    parser = make_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_make_parser_has_help() -> None:
    """Test parser has help option."""
    parser = make_parser()
    # Check that -h/--help is available
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])
    assert exc_info.value.code == 0


def test_make_parser_has_version() -> None:
    """Test parser has version option."""
    parser = make_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])
    assert exc_info.value.code == 0


def test_make_parser_has_help_generators() -> None:
    """Test parser has help-generators option."""
    parser = make_parser()
    args = parser.parse_args(["--help-generators"])
    assert args.help_generators is True


# =============================================================================
# Argument parsing tests
# =============================================================================


def test_parser_default_values() -> None:
    """Test parser default values."""
    parser = make_parser()
    args = parser.parse_args([])

    assert args.settings == []
    assert args.env_file == []
    assert args.project_dir is None
    assert args.venv is None


def test_parser_venv_auto() -> None:
    """Test --venv auto."""
    parser = make_parser()
    args = parser.parse_args(["--venv", "auto"])
    assert args.venv == "auto"


def test_parser_venv_uv() -> None:
    """Test --venv uv."""
    parser = make_parser()
    args = parser.parse_args(["--venv", "uv"])
    assert args.venv == "uv"


def test_parser_venv_poetry() -> None:
    """Test --venv poetry."""
    parser = make_parser()
    args = parser.parse_args(["--venv", "poetry"])
    assert args.venv == "poetry"


def test_parser_venv_custom_path() -> None:
    """Test --venv with custom path."""
    parser = make_parser()
    args = parser.parse_args(["--venv", "/some/path/.venv"])
    assert args.venv == "/some/path/.venv"


def test_parser_venv_empty_disables() -> None:
    """Test --venv '' disables venv detection."""
    parser = make_parser()
    args = parser.parse_args(["--venv", ""])
    assert args.venv == ""


def test_parser_with_settings() -> None:
    """Test parser with settings argument."""
    parser = make_parser()
    args = parser.parse_args(["module:Settings"])

    assert args.settings == ["module:Settings"]


def test_parser_with_multiple_settings() -> None:
    """Test parser with multiple settings arguments."""
    parser = make_parser()
    args = parser.parse_args(["module1:Settings1", "module2:Settings2"])

    assert args.settings == ["module1:Settings1", "module2:Settings2"]


def test_parser_with_project_dir(tmp_path: Path) -> None:
    """Test parser with project-dir option."""
    parser = make_parser()
    args = parser.parse_args(["--project-dir", str(tmp_path)])

    assert args.project_dir == tmp_path.resolve().absolute()


def test_parser_with_config_file(tmp_path: Path) -> None:
    """Test parser with config-file option."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("[tool.pydantic_settings_export]\n")

    parser = make_parser()
    args = parser.parse_args(["--config-file", str(config_file)])

    assert args.config_file == config_file.resolve().absolute()


# =============================================================================
# Type validators tests
# =============================================================================


def test_dir_type_valid_directory(tmp_path: Path) -> None:
    """Test dir_type with valid directory."""
    result = dir_type(str(tmp_path))
    assert result == tmp_path.resolve().absolute()


def test_dir_type_invalid_directory() -> None:
    """Test dir_type with invalid directory."""
    with pytest.raises(argparse.ArgumentTypeError) as exc_info:
        dir_type("/nonexistent/path")
    assert "is not a directory" in str(exc_info.value)


def test_file_type_valid_file(tmp_path: Path) -> None:
    """Test file_type with valid file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    result = file_type(str(test_file))
    assert result == test_file.resolve().absolute()


def test_file_type_invalid_file() -> None:
    """Test file_type with invalid file."""
    with pytest.raises(argparse.ArgumentTypeError) as exc_info:
        file_type("/nonexistent/file.txt")
    assert "is not a file" in str(exc_info.value)


# =============================================================================
# Generator option tests
# =============================================================================


def test_parser_generator_default() -> None:
    """Test parser has default generators."""
    from pydantic_settings_export.generators import AbstractGenerator

    parser = make_parser()
    args = parser.parse_args([])

    # Default should be all built-in generators
    assert args.generator == AbstractGenerator.ALL_GENERATORS


def test_parser_generator_by_name() -> None:
    """Test parser accepts generator by name."""
    parser = make_parser()
    args = parser.parse_args(["--generator", "markdown"])

    # Should have MarkdownGenerator
    from pydantic_settings_export import MarkdownGenerator

    assert MarkdownGenerator in args.generator


def test_parser_generator_multiple() -> None:
    """Test parser accepts multiple generators."""
    parser = make_parser()
    args = parser.parse_args(["--generator", "markdown", "dotenv"])

    from pydantic_settings_export import DotEnvGenerator, MarkdownGenerator

    assert MarkdownGenerator in args.generator
    assert DotEnvGenerator in args.generator


# =============================================================================
# Env file option tests
# =============================================================================


def test_parser_env_file(tmp_path: Path) -> None:
    """Test parser with env-file option."""
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=value\n")

    parser = make_parser()
    args = parser.parse_args(["--env-file", str(env_file)])

    assert len(args.env_file) == 1
    assert args.env_file[0].name == str(env_file)


def test_parser_multiple_env_files(tmp_path: Path) -> None:
    """Test parser with multiple env-file options."""
    env_file1 = tmp_path / ".env1"
    env_file1.write_text("KEY1=value1\n")
    env_file2 = tmp_path / ".env2"
    env_file2.write_text("KEY2=value2\n")

    parser = make_parser()
    args = parser.parse_args(["--env-file", str(env_file1), str(env_file2)])

    assert len(args.env_file) == 2


# =============================================================================
# Short option tests
# =============================================================================


def test_parser_short_options(tmp_path: Path) -> None:
    """Test parser short options work."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("[tool.pydantic_settings_export]\n")

    parser = make_parser()
    args = parser.parse_args([
        "-d",
        str(tmp_path),
        "-c",
        str(config_file),
        "-g",
        "markdown",
    ])

    assert args.project_dir == tmp_path.resolve().absolute()
    assert args.config_file == config_file.resolve().absolute()


# =============================================================================
# Integration tests
# =============================================================================


def test_parser_full_command(tmp_path: Path) -> None:
    """Test parser with full command line."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("[tool.pydantic_settings_export]\n")
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=value\n")

    parser = make_parser()
    # Note: settings arguments are stored as strings and imported later by main()
    # The parser itself doesn't validate/import settings classes
    # Use "--" to separate options from positional arguments since --generator uses nargs='*'
    args = parser.parse_args([
        "--project-dir",
        str(tmp_path),
        "--config-file",
        str(config_file),
        "--env-file",
        str(env_file),
        "--generator",
        "markdown",
        "--",  # Separator to prevent argparse from treating settings as generator args
        "my_app.config:AppSettings",  # This is just stored as a string
    ])

    assert args.project_dir == tmp_path.resolve().absolute()
    assert args.config_file == config_file.resolve().absolute()
    assert len(args.env_file) == 1
    assert args.settings == ["my_app.config:AppSettings"]


# =============================================================================
# main() integration tests (regression for issue #43)
# =============================================================================


def test_main_cli_settings_replaces_default_settings(tmp_path: Path) -> None:
    """Positional settings args from CLI must replace default_settings (regression for #43).

    Previously, args.settings was never wired to s.default_settings, so passing
    settings via CLI was silently ignored and main() exited with code 1.
    """
    output_file = tmp_path / "output.txt"
    config_file = tmp_path / "pyproject.toml"
    # No default_settings in config — proves that CLI args alone are enough
    config_file.write_text(
        "[tool.pydantic_settings_export]\n\n"
        "[[tool.pydantic_settings_export.generators.simple]]\n"
        f'paths = ["{output_file.as_posix()}"]\n'
    )

    with pytest.raises(SystemExit) as exc_info:
        main([
            "--config-file",
            str(config_file),
            "--venv",
            "",
            "--generator",
            "simple",
            "--",
            "pydantic_settings_export.settings:PSESettings",
        ])

    # 0 = settings found and processed; 1 = no settings found (the old bug)
    assert exc_info.value.code == 0
    assert output_file.exists()
    assert "Global Settings" in output_file.read_text()


def test_main_exits_when_no_settings_provided(tmp_path: Path) -> None:
    """When no settings are given via CLI or config, main() must exit with code 1."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text("[tool.pydantic_settings_export]\n")

    with pytest.raises(SystemExit) as exc_info:
        main(["--config-file", str(config_file), "--venv", ""])

    assert exc_info.value.code == 1


def test_main_supports_mixed_old_and_new_sources_from_config(settings_sources_project) -> None:
    """Config default_settings may mix module, file, and directory sources."""
    output_file = settings_sources_project.root / "config-output.txt"
    config_file = settings_sources_project.root / "pyproject.toml"
    config_file.write_text(
        "[tool.pydantic_settings_export]\n"
        "default_settings = [\n"
        f'    "{settings_sources_project.module_name}",\n'
        f'    "{settings_sources_project.standalone_file_source}",\n'
        f'    "{settings_sources_project.discovered_dir_source}",\n'
        "]\n\n"
        "[[tool.pydantic_settings_export.generators.simple]]\n"
        f'paths = ["{output_file.as_posix()}"]\n'
    )

    with pytest.raises(SystemExit) as exc_info:
        main([
            "--project-dir",
            str(settings_sources_project.root),
            "--config-file",
            str(config_file),
            "--venv",
            "",
            "--generator",
            "simple",
        ])

    assert exc_info.value.code == 0
    content = output_file.read_text()
    assert "AppSettings" in content
    assert "DatabaseSettings" in content
    assert "CacheSettings" in content
    assert "StandaloneSettings" in content


def test_main_positional_sources_replace_config_default_settings(settings_sources_project) -> None:
    """CLI positional settings should replace config default_settings with mixed sources."""
    output_file = settings_sources_project.root / "cli-output.txt"
    config_file = settings_sources_project.root / "pyproject.toml"
    config_file.write_text(
        "[tool.pydantic_settings_export]\n"
        f'default_settings = ["{settings_sources_project.standalone_file_source}"]\n\n'
        "[[tool.pydantic_settings_export.generators.simple]]\n"
        f'paths = ["{output_file.as_posix()}"]\n'
    )

    with pytest.raises(SystemExit) as exc_info:
        main([
            "--project-dir",
            str(settings_sources_project.root),
            "--config-file",
            str(config_file),
            "--venv",
            "",
            "--generator",
            "simple",
            "--",
            settings_sources_project.module_attr,
            settings_sources_project.discovered_dir_source,
        ])

    assert exc_info.value.code == 0
    content = output_file.read_text()
    assert "AppSettings" in content
    assert "DatabaseSettings" in content
    assert "CacheSettings" in content
    assert "StandaloneSettings" not in content


def test_main_invalid_settings_path_exits_with_code_2(settings_sources_project) -> None:
    """Invalid file-system path should produce a CLI error."""
    output_file = settings_sources_project.root / "invalid-output.txt"
    config_file = settings_sources_project.root / "pyproject.toml"
    config_file.write_text(
        "[tool.pydantic_settings_export]\n\n"
        "[[tool.pydantic_settings_export.generators.simple]]\n"
        f'paths = ["{output_file.as_posix()}"]\n'
    )

    with pytest.raises(SystemExit) as exc_info:
        main([
            "--project-dir",
            str(settings_sources_project.root),
            "--config-file",
            str(config_file),
            "--venv",
            "",
            "--generator",
            "simple",
            "--",
            "./missing/settings.py",
        ])

    assert exc_info.value.code == 2
