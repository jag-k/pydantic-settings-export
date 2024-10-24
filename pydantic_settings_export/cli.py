import argparse
import os
import sys
from collections.abc import Sequence
from inspect import isclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from pydantic_settings_export.exporter import Exporter
from pydantic_settings_export.generators import ALL_GENERATORS, AbstractGenerator
from pydantic_settings_export.settings import Settings, import_settings_from_string
from pydantic_settings_export.utils import ObjectImportAction
from pydantic_settings_export.version import __version__

CDW = Path.cwd()


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


parser = argparse.ArgumentParser(
    description="Export pydantic settings to a file",
)
parser.add_argument(
    "--version",
    "-v",
    action="version",
    version=f"pydantic-settings-export {__version__}",
)

parser.add_argument(
    "--project-dir",
    "-d",
    default=None,
    type=dir_type,
    help="The project directory. (default: current directory)",
)
parser.add_argument(
    "--config-file",
    "-c",
    default=CDW / "pyproject.toml",
    type=file_type,
    help="Path to `pyproject.toml` file. (default: ./pyproject.toml)",
)
parser.add_argument(
    "--generator",
    "-g",
    default=ALL_GENERATORS,
    action=GeneratorAction,
    help=f"The generator class or object to use. (default: [{', '.join(g.__name__ for g in ALL_GENERATORS)}])",
)
parser.add_argument(
    "settings",
    nargs="*",
    help="The settings classes or objects to export.",
)
parser.add_argument(
    "--env-file",
    "-e",
    default=None,
    type=argparse.FileType("r"),
    help="Use the .env file to load environment variables. (default: None)",
)


def main(parse_args: Sequence[str] | None = None):  # noqa: D103
    args: argparse.Namespace = parser.parse_args(parse_args)
    if args.env_file:
        os.environ.update(dotenv_values(stream=args.env_file))

    if args.config_file:
        Settings.model_config["toml_file"] = args.config_file
    s = Settings()

    if args.project_dir:
        s.project_dir = Path(args.project_dir).resolve().absolute()
    sys.path.insert(0, str(s.project_dir))

    s.generators = args.generator
    settings = s.settings or [import_settings_from_string(s) for s in args.settings]
    if not settings:
        parser.exit(1, parser.format_help())

    result = Exporter(s).run_all(*settings)
    if result:
        files = "\n".join(f"- {r}" for r in result)
        parser.exit(0, f"Generated files ({len(result)}): \n{files}\n")
    parser.exit(0, "No files generated.\n")


if __name__ == "__main__":
    main()
