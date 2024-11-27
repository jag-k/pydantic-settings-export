import argparse
import importlib
import sys
from collections.abc import Sequence
from typing import Any

from pydantic import ImportString, TypeAdapter
from pydantic_core import ValidationError
from pydantic_settings import BaseSettings

__all__ = (
    "make_pretty_md_table",
    "make_pretty_md_table_from_dict",
)


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
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
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

    def __init__(self, missing: dict[str | int, str], settings_path: str = "Settings") -> None:
        missing_as_str = "\n".join(
            f"  - `{k if '.' in k else settings_path + '.' + k}`: {v}"
            #
            for k, v in missing.items()
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
        missing: dict[str | int, str] = {}
        for details in err.errors():
            if details["type"] == "missing":
                missing[details["loc"][0]] = details["msg"]
        if missing:
            raise MissingSettingsError(missing=missing, settings_path=value) from err
        raise err from None

    if isinstance(obj, type) and not issubclass(obj, BaseSettings) and not isinstance(obj, BaseSettings):
        raise ValueError(f"The {obj!r} is not a settings class.")
    return obj
