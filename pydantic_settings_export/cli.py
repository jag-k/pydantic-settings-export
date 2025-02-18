import argparse
import os
import sys
import warnings
from collections.abc import Sequence
from inspect import isclass
from pathlib import Path
from tomllib import load
from typing import Any

from dotenv import dotenv_values, load_dotenv
from pydantic import Field, SkipValidation, model_validator
from pydantic_settings import BaseSettings

from pydantic_settings_export.exporter import Exporter
from pydantic_settings_export.generators import AbstractGenerator
from pydantic_settings_export.generators.simple import SimpleGenerator
from pydantic_settings_export.models import SettingsInfoModel
from pydantic_settings_export.settings import PSESettings
from pydantic_settings_export.utils import ObjectImportAction, import_settings_from_string
from pydantic_settings_export.version import __version__

CDW = Path.cwd()
PROJECT_NAME: str = "pydantic-settings-export"


self_pyproject_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
if self_pyproject_file.is_file():
    with self_pyproject_file.open("rb") as f:
        PROJECT_NAME: str = load(f).get("project", {}).get("name", PROJECT_NAME)

Generators = AbstractGenerator.create_generator_config_model(multiple_for_single=True)


class PSECLISettings(PSESettings):
    """The settings for the CLI."""

    generators: Generators = Field(
        default_factory=Generators,
        description="The configuration of generators.",
        exclude=True,
    )

    generators_list: list[SkipValidation[type["AbstractGenerator"]]] = Field(
        default_factory=list,
        description="The list of generators to use.",
        exclude=True,
    )

    env_file: Path | None = Field(
        None,
        description=(
            "he path to the .env file to load environment variables. "
            "Useful when you have a Settings class/instance, which requires values while running."
        ),
    )

    @property
    def settings(self) -> list[BaseSettings]:
        """Get the settings."""
        return [import_settings_from_string(i) for i in self.default_settings or []]

    @model_validator(mode="before")
    @classmethod
    def validate_generators(cls, data: Any) -> Any:
        """Validate the generators."""
        if not isinstance(data, dict):
            return data

        generators = data.setdefault("generators", {})

        for generator in AbstractGenerator.ALL_GENERATORS:
            config = data.pop(generator.name, None)
            if config:
                warnings.warn(
                    f"You use the old-style to set generator {generator.name} config. "
                    f"Please, use the new-style:\n"
                    f"- For toml file: `[[tool.pydantic_settings_export.generators.{generator.name}]]`"
                    f"The old-style will be removed in the future!",
                    DeprecationWarning,
                    stacklevel=1,
                )
                generators[generator.name] = [config]

        for name, gen_configs in generators.items():
            if not isinstance(gen_configs, list):
                warnings.warn(
                    f"You use the old-style to set generator {name} config. "
                    f"Please, use the new-style:\n"
                    f"- For toml file: `[[tool.pydantic_settings_export.generators.{name}]]`"
                    f"The old-style will be removed in the future!",
                    DeprecationWarning,
                    stacklevel=1,
                )
                generators[name] = [gen_configs]
        return data

    @model_validator(mode="before")
    @classmethod
    def validate_env_file(cls, data: Any) -> Any:
        """Validate the env file."""
        if isinstance(data, dict):
            file = data.get("env_file")
            if file is not None:
                f = Path(file)
                if f.is_file():
                    print("Loading env file", f)
                    load_dotenv(file)
        return data

    def get_generators(self) -> list[AbstractGenerator]:
        """Get the generators."""
        all_generators = AbstractGenerator.generators()
        result = []
        for name, gen_configs in self.generators:
            for gen_config in gen_configs:
                g = all_generators.get(name)
                if not g:
                    continue
                result.append(g(self, gen_config))
        return result


class GeneratorAction(ObjectImportAction):
    """The generator action."""

    @staticmethod
    def callback(obj: Any) -> type[AbstractGenerator]:
        """Check if the object is a settings class."""
        if isclass(obj) and issubclass(obj, AbstractGenerator):
            return obj
        elif not isclass(obj) and isinstance(obj, AbstractGenerator):
            return obj.__class__
        raise ValueError(f"The {obj!r} is not a generator class.")


def _generators_help(generators_list: list[type[AbstractGenerator]]) -> str:
    """Create the help for the generators which provide a list of generators.

    :param generators_list: The list of generators.
    :return: The help text.
    """
    s = PSESettings()
    return SimpleGenerator(s).generate(
        *(
            SettingsInfoModel.from_settings_model(g.config, s)
            # Get all available generators
            for g in generators_list
        ),
    )


def dir_type(path: str) -> Path:
    """Check if the path is a directory."""
    p = Path(path).resolve().absolute()
    if p.is_dir():
        return p
    raise argparse.ArgumentTypeError(f"The {path} is not a directory.")


def file_type(path: str) -> Path:
    """Check if the path is a file."""
    p = Path(path).resolve().absolute()
    if p.is_file():
        return p
    raise argparse.ArgumentTypeError(f"The {path} is not a file.")


def make_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser.

    This function sets up a comprehensive CLI interface that supports:
    - Multiple output formats (markdown, dotenv, etc)
    - Custom generator plugins
    - Environment variable loading
    - Project-specific configuration

    Example usage:
        pydantic-settings-export app.settings:Settings
        pydantic-settings-export --generator markdown --output docs/settings.md app.settings:Settings
        pydantic-settings-export --env-file .env.dev app.settings:Settings

    :return: Configured parser instance.
    :raises ValueError: If invalid directory/file paths are provided.
    :raises FileNotFoundError: If specified files don't exist.
    :raises ImportError: If custom generators/settings can't be imported.
    """
    parser = argparse.ArgumentParser(
        prog=PROJECT_NAME,
        description="Export pydantic settings to a file",
        add_help=False,
    )

    help_group = parser.add_argument_group("help options", "Show message and exit.")
    # I've made it because the help text not matches to the following pattern as in other commands.
    # The original help text: "show this help message and exit"
    help_group.add_argument(
        "--help",
        "-h",
        action="help",
        help="Show this help message and exit.",
    )
    help_group.add_argument(
        "--version",
        "-v",
        action="version",
        help="Show the version and exit.",
        version=f"pydantic-settings-export {__version__}",
    )

    help_group.add_argument(
        "--help-generators",
        "-G",
        action="store_true",
        help="Show all generators (from --generator), their configuration and exit.",
    )

    config_group = parser.add_argument_group(
        "configuration options",
        (
            "Configuration options of this CLI tool. "
            "NOTE: This settings has higher priority than the environment variables or pyproject.toml file."
        ),
    )

    config_group.add_argument(
        "--project-dir",
        "-d",
        default=None,
        type=dir_type,
        help="The project directory. (default: current dir)",
    )
    config_group.add_argument(
        "--config-file",
        "-c",
        default=CDW / "pyproject.toml",
        type=file_type,
        help="Path to `pyproject.toml` file. (default: ./pyproject.toml)",
    )
    config_group.add_argument(
        "--env-file",
        "-e",
        nargs="+",
        default=[],
        type=argparse.FileType("r"),
        help="Use the .env file to load environment variables. Can be used multiple times. (default: [])",
    )
    config_group.add_argument(
        "--generator",
        "-g",
        nargs="*",
        default=AbstractGenerator.ALL_GENERATORS,
        action=GeneratorAction,
        help=(
            f"The generator class or object to use. "
            f"Use `module:class` to use a custom generator. "
            f"(default: [{', '.join(g.name for g in AbstractGenerator.ALL_GENERATORS)}] (all built-in generators))"
        ),
    )

    parser.add_argument(
        "settings",
        nargs="*",
        help=(
            "The settings classes or objects to export. "
            "Use `module:class` or `module:variable` to use a custom settings."
        ),
    )

    return parser


def main(parse_args: Sequence[str] | None = None):  # noqa: D103
    parser = make_parser()
    args: argparse.Namespace = parser.parse_args(parse_args)
    for env_file in args.env_file:
        os.environ.update(dotenv_values(stream=env_file))

    if args.config_file:
        PSECLISettings.model_config["toml_file"] = args.config_file
    s = PSECLISettings()

    if args.project_dir:
        s.project_dir = Path(args.project_dir).resolve().absolute()
    sys.path.insert(0, str(s.project_dir))
    generators = args.generator

    s.generators_list = generators
    if args.help_generators:
        generators_help = _generators_help(s.generators_list)
        parser.exit(0, generators_help)

    settings = s.settings
    if not settings:
        parser.exit(1, parser.format_help())

    result = Exporter(s, s.get_generators()).run_all(*settings)
    if result:
        files = "\n".join(f"- {r}" for r in result)
        parser.exit(0, f"Generated files ({len(result)}): \n{files}\n")
    parser.exit(0, "No files generated.\n")


if __name__ == "__main__":
    main()
