import argparse
import importlib
import re
import sys
from collections.abc import Sequence
from typing import Any, Optional, Union

from pydantic import ImportString, TypeAdapter
from pydantic_core import ValidationError
from pydantic_settings import BaseSettings

from pydantic_settings_export.generators import AbstractGenerator

__all__ = (
    "make_pretty_md_table",
    "make_pretty_md_table_from_dict",
)

MARKDOWN_PIPE_RE = re.compile(r"(?<!\\)\|")


def make_pretty_md_table(headers: list[str], rows: list[list[str]]) -> str:  # noqa: C901
    """Make a pretty Markdown table with column alignment.

    :param headers: The header of the table.
    :param rows: The rows of the table.
    :return: The prettied Markdown table.
    """
    col_sizes = [len(h) for h in headers]

    # Escape pipes in the cells to avoid table formatting issues
    rows = [[MARKDOWN_PIPE_RE.sub(r"\\|", r) for r in row] for row in rows]

    for row in rows:
        for i, cell in enumerate(row):
            if cell is None:
                cell = ""
            col_sizes[i] = max(col_sizes[i], len(cell))

    result = "|"
    for i, h in enumerate(headers):
        result += f" {h}{' ' * (col_sizes[i] - len(h))} |"
    result += "\n|"
    for i, _ in enumerate(headers):
        result += f"{'-' * (col_sizes[i] + 2)}|"
    for row in rows:
        result += "\n|"
        for i, cell in enumerate(row):
            if cell is None:
                cell = ""
            result += f" {cell}{' ' * (col_sizes[i] - len(cell))} |"
    return result


def make_pretty_md_table_from_dict(data: list[dict[str, Optional[str]]], headers: Optional[list[str]] = None) -> str:
    """Make a pretty Markdown table with column alignment from a list of dictionaries.

    :param data: The rows of the table as dictionaries.
    :param headers: The headers of the table.
    :return: The prettied Markdown table.
    """
    if not headers:
        # Save unique keys from all rows and save order
        headers = list(
            {
                # We need only the keys.
                key: 0
                for row in data
                for key in row.keys()
            }.keys(),
        )

    # noinspection PyUnboundLocalVariable
    rows = [[row.get(key, None) or "" for key in headers] for row in data]
    return make_pretty_md_table(headers, rows)


def q(s: Any) -> str:
    """Add quotes around the string."""
    return f"`{s}`"


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
        builtin_generators = AbstractGenerator.generators()
        builtin_generator_names = {g.__name__: g for g in builtin_generators.values()}

        obj: Optional[type[AbstractGenerator]] = builtin_generators.get(value, None)
        if obj:
            return obj

        obj = builtin_generator_names.get(value, None)
        if obj:
            return obj

        if ":" not in value:
            raise ValueError(f"The {value!r} is not in the format 'module:class'.")

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
        values: Optional[Union[str, Sequence[Any]]],
        option_string: Optional[str] = None,
    ) -> None:
        """Import the object from the module."""
        if values is None:
            return

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
            if not isinstance(value, str):
                continue
            try:
                result.append(self.callback(self.import_obj(value)))
            except (ValueError, ModuleNotFoundError) as e:
                parser.print_usage(sys.stderr)
                parser.exit(2, f"{parser.prog}: error: {argparse.ArgumentError(self, str(e))}\n")

        setattr(namespace, self.dest, result)


class MissingSettingsError(ValueError):
    """Raised when the settings are missing."""

    def __init__(self, missing: dict[Union[str, int], str], settings_path: str = "Settings") -> None:
        missing_as_str = "\n".join(
            f"  - `{key if '.' in key else settings_path + '.' + key}`: {v}"
            #
            for k, v in missing.items()
            if (key := str(k))
        )
        super().__init__(
            f"You have {len(missing)} missing settings:\n{missing_as_str}\n\n"
            f"Please, set this required ENV Vars into your .env files.\n"
            f"This can be happened if you call the {settings_path} directly in your settings file."
        )


def import_settings_from_string(value: str) -> BaseSettings:
    """Import the settings from the string."""
    obj: BaseSettings
    try:
        obj = TypeAdapter(ImportString).validate_python(value)
    except ValidationError as err:
        missing: dict[Union[str, int], str] = {}
        for details in err.errors():
            if details["type"] == "missing":
                missing[details["loc"][0]] = details["msg"]
        if missing:
            raise MissingSettingsError(missing=missing, settings_path=value) from err
        raise err from None

    if isinstance(obj, type) and not issubclass(obj, BaseSettings) and not isinstance(obj, BaseSettings):
        raise ValueError(f"The {obj!r} is not a settings class.")
    return obj
