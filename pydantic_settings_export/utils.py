import argparse
import importlib
import sys
import tomllib
from pathlib import Path
from typing import Any

__all__ = (
    "find_pyproject_toml",
    "make_pretty_md_table",
    "make_pretty_md_table_from_dict",
)

from pydantic_settings import BaseSettings


def make_pretty_md_table(header: list[str], rows: list[list[str]]) -> str:  # noqa: C901
    """Make a pretty Markdown table with column alignment.

    :param header: The header of the table.
    :param rows: The rows of the table.
    :return: The prettied Markdown table.
    """
    col_sizes = [len(h) for h in header]
    for row in rows:
        for i, cell in enumerate(row):
            if cell is None:
                cell = ""
            col_sizes[i] = max(col_sizes[i], len(cell))

    result = "|"
    for i, h in enumerate(header):
        result += f" {h}{' ' * (col_sizes[i] - len(h))} |"
    result += "\n|"
    for i, _ in enumerate(header):
        result += f"{'-' * (col_sizes[i] + 2)}|"
    for row in rows:
        result += "\n|"
        for i, cell in enumerate(row):
            if cell is None:
                cell = ""
            result += f" {cell}{' ' * (col_sizes[i] - len(cell))} |"
    return result


def make_pretty_md_table_from_dict(data: list[dict[str, str | None]]) -> str:
    """Make a pretty Markdown table with column alignment from a list of dictionaries.

    :param data: The rows of the table as dictionaries.
    :return: The prettied Markdown table.
    """
    # Save unique keys from all rows and save order
    header: list[str] = list(
        {
            # We need only key
            key: 0
            for row in data
            for key in row.keys()
        }.keys(),
    )
    rows = [[row.get(key, None) or "" for key in header] for row in data]
    return make_pretty_md_table(header, rows)


def find_pyproject_toml(search_from: Path | None = None) -> Path | None:
    """Find the pyproject.toml file in the current working directory or its parents.

    :param search_from: The directory to start searching from.
    :return: The path to the pyproject.toml file or None if it wasn't found.
    """
    if not search_from:
        search_from = Path.cwd()
    for parent in (search_from, *search_from.parents):
        pyproject_toml = parent / "pyproject.toml"
        if pyproject_toml.is_file():
            return pyproject_toml
    return None


def get_tool_name(settings: type[BaseSettings]) -> str | None:
    """Get the tool name from the settings.

    :param settings: The settings class to get the tool name from.
    :return: The tool name.
    """
    return settings.model_config.get("plugin_settings", {}).get("pyproject_toml", {}).get("package_name", None)


def get_config_from_pyproject_toml(settings: type[BaseSettings], base_path: Path | None = None) -> dict:
    """Get the configuration from the pyproject.toml file.

    :param base_path: The base path to search for the pyproject.toml file or this file itself.
        The current working directory is used by default.
    :param settings: The settings class to create the settings from.
    :return: The created settings.
    """
    tool_name = get_tool_name(settings)

    if not tool_name:
        raise ValueError("The tool name is not set in the settings.")

    if not base_path:
        base_path = Path.cwd()

    if not base_path.is_file():
        base_path = find_pyproject_toml(base_path)

    if not base_path:
        raise FileNotFoundError("The pyproject.toml file was not found.")

    with open(base_path, "rb") as file:
        data = tomllib.load(file)

    return data.get("tool", {}).get(tool_name, {})


class ObjectImportAction(argparse.Action):
    """Import the object from the module."""

    @staticmethod
    def callback(obj: Any) -> Any:
        """Check if the object is a settings class."""
        return obj

    @staticmethod
    def import_obj(value: str) -> Any:
        """Import the object from the module.

        :param value: The value in the format is 'module:class'.
        :raise ValueError: If the value is not in the format 'module:class'.
        :raise ValueError: If the class is not in the module.
        :raise ModuleNotFoundError: If the module is not found.
        :return: The imported object.
        """
        try:
            module_name, class_name = value.rsplit(":", 1)
        except ValueError:
            raise ValueError(f"The {value!r} is not in the format 'module:class'.") from None

        module = importlib.import_module(module_name)

        obj = getattr(module, class_name, None)
        if obj is None:
            raise ValueError(f"The {class_name!r} is not in the module {module_name!r}.")
        return obj

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: list[str],
        option_string: str | None = None,
    ) -> None:
        """Import the object from the module."""
        # Add the project directory to the sys.path
        sys.path.insert(0, str(namespace.project_dir))
        importlib.invalidate_caches()

        if isinstance(values, str):
            values = [values]

        result = getattr(namespace, self.dest, [])

        # Reset the default value
        if result == self.default:
            result = []

        for value in values:
            try:
                result.append(self.callback(self.import_obj(value)))
            except (ValueError, ModuleNotFoundError) as e:
                parser.print_usage(sys.stderr)
                parser.exit(2, f"{parser.prog}: error: {argparse.ArgumentError(self, str(e))}\n")

        setattr(namespace, self.dest, result)
