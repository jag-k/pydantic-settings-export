import argparse
import os
import sys
import warnings
from collections.abc import Iterable, Sequence
from inspect import isclass
from pathlib import Path
from typing import Any, Optional, TextIO, cast

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

if sys.version_info < (3, 11):
    from tomli import load as toml_load
else:
    from tomllib import load as toml_load


CDW = Path.cwd()


def _make_project_name(default_name: str) -> str:
    self_pyproject_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
    try:
        if self_pyproject_file.is_file():
            with self_pyproject_file.open("rb") as f:
                project_name: Optional[str] = toml_load(f).get("project", {}).get("name", None)
                if not project_name:
                    warnings.warn(
                        f"Project name not found in {self_pyproject_file}! Will be used {default_name!r}",
                        stacklevel=2,
                    )
                    return default_name
                return project_name
    except Exception as e:
        warnings.warn(f"Failed to parse {self_pyproject_file}: {e}", stacklevel=2)
    return default_name


PROJECT_NAME: str = _make_project_name("pydantic-settings-export")
Generators = AbstractGenerator.create_generator_config_model(multiple_for_single=True)


class PSECLISettings(PSESettings):
    """The settings for the CLI."""

    generators: Generators = Field(  # type: ignore[valid-type]
        default_factory=Generators,
        description="The configuration of generators.",
        exclude=True,
    )

    generators_list: list[SkipValidation[type["AbstractGenerator"]]] = Field(
        default_factory=list,
        description="The list of generators to use.",
        exclude=True,
    )

    env_file: Optional[Path] = Field(
        None,
        description=(
            "The path to the .env file to load environment variables. "
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
                    stacklevel=2,
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
                    stacklevel=2,
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
        for name, gen_configs in self.generators:  # type: ignore[attr-defined]  # Is __iter__ really exist?
            for gen_config in gen_configs:
                g = all_generators.get(name)
                if not g:
                    warnings.warn(f"Generator {name!r} not found", stacklevel=2)
                    continue
                try:
                    result.append(g(self, gen_config))
                except Exception as e:
                    warnings.warn(f"Failed to initialize generator {name!r}: {e}", stacklevel=2)
                    continue
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
            SettingsInfoModel.from_settings_model(cast(type[BaseSettings], g.config), s)
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


def _load_env_files(env_files: Iterable[TextIO]) -> None:
    """Load environment variables from the provided env files.

    :param env_files: Iterable of file objects to load environment variables from.
    """
    for env_file in env_files:
        if not Path(env_file.name).exists():
            warnings.warn(f"Environment file {env_file.name} does not exist", stacklevel=2)
            continue
        try:
            os.environ.update({k: v for k, v in dotenv_values(stream=env_file).items() if v})
        except ValueError as e:
            warnings.warn(f"Invalid format in environment file {env_file.name}: {e}", stacklevel=2)
        except OSError as e:
            warnings.warn(f"Failed to read environment file {env_file.name}: {e}", stacklevel=2)
        except Exception as e:
            warnings.warn(f"Unexpected error loading environment file {env_file.name}: {e}", stacklevel=2)


def _setup_settings(
    config_file: Optional[Path] = None,
    project_dir: Optional[Path] = None,
) -> PSECLISettings:
    """Initialize and configure PSECLISettings.

    :param config_file: Path to the configuration file
    :param project_dir: Path to the project directory
    :return: Configured PSECLISettings instance
    """
    if config_file:
        PSECLISettings.model_config["toml_file"] = config_file
    s = PSECLISettings()

    if project_dir:
        s.project_dir = project_dir.resolve().absolute()
    sys.path.insert(0, str(s.project_dir))
    return s


def _process_generators(generators: Sequence[Optional[type[AbstractGenerator]]]) -> list[type[AbstractGenerator]]:
    """Process and validate generator arguments.

    :param generators: Sequence of generator classes
    :return: List of valid generator classes
    """
    result = []
    for g in generators:
        if not g:
            warnings.warn("Skipping unknown generator", stacklevel=2)
            continue
        result.append(g)
    return result


def main(parse_args: Optional[Sequence[str]] = None) -> None:  # noqa: D103
    parser = make_parser()
    args: argparse.Namespace = parser.parse_args(parse_args)

    # Load environment variables from files
    _load_env_files(args.env_file)

    # Setup settings
    s = _setup_settings(args.config_file, args.project_dir)

    # Process generators
    generators = _process_generators(args.generator)
    s.generators_list = generators

    if args.help_generators:
        generators_help = _generators_help(s.generators_list)
        parser.exit(0, generators_help)

    settings = s.settings
    if not settings:
        parser.exit(1, parser.format_help())

    # Run main settings export
    exporter = Exporter(s, s.get_generators())
    try:
        result = exporter.run_all(*settings)
    except Exception as e:
        parser.exit(2, f"Failed to initialize exporter: [{e.__class__.__name__}] {e}\n")

    if result:
        files = "\n".join(f"- {r}" for r in result)
        parser.exit(0, f"Generated files ({len(result)}): \n{files}\n")
    parser.exit(0, "No files generated.\n")


if __name__ == "__main__":
    main()
