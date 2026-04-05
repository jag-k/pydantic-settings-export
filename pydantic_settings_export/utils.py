import argparse
import importlib
import logging
import re
import sys
from collections.abc import Sequence
from inspect import isclass
from types import ModuleType
from typing import Any

from pydantic import ImportString, TypeAdapter
from pydantic_core import ValidationError
from pydantic_settings import BaseSettings

from pydantic_settings_export.generators import AbstractGenerator

__all__ = (
    "make_pretty_md_table",
    "make_pretty_md_table_from_dict",
)

logger = logging.getLogger(__name__)

MARKDOWN_PIPE_RE = re.compile(r"(?<!\\)\|")


def make_pretty_md_table(headers: list[str], rows: list[list[str]]) -> str:  # noqa: C901
    """Make a pretty Markdown table with column alignment.

    :param headers: The header of the table.
    :param rows: The rows of the table.
    :return: The prettied Markdown table.
    """
    col_sizes = [len(h) for h in headers]

    # Escape pipes in the cells to avoid table formatting issues (be None-safe)
    rows = [
        [MARKDOWN_PIPE_RE.sub(r"\\|", cell) if isinstance(cell, str) else "" for cell in row] for row in rows if row
    ]

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


def make_pretty_md_table_from_dict(data: list[dict[str, str | None]], headers: list[str] | None = None) -> str:
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

        obj: type[AbstractGenerator] | None = builtin_generators.get(value, None)
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


def _find_settings_in_module(module: ModuleType) -> list[type[BaseSettings]]:
    """Discover all BaseSettings subclasses defined in a module.

    Only classes whose ``__module__`` matches the module's ``__name__`` are
    returned, so re-imported classes from other modules are excluded.

    :param module: The imported module to inspect.
    :return: List of BaseSettings subclasses defined in the module.
    """
    module_name = module.__name__
    return [
        obj
        for obj in vars(module).values()
        if (
            isclass(obj)  # If it's a class
            and issubclass(obj, BaseSettings)  # and it's a subclass of BaseSettings
            and obj is not BaseSettings  # and it's not BaseSettings itself
            and obj.__module__ == module_name  # and it's defined in this module
        )
    ]


def import_settings_from_string(value: str) -> list[BaseSettings | type[BaseSettings]]:
    """Import the settings from the string.

    When *value* contains ``:``, the part before it is treated as a module
    path and the part after it as an attribute name (e.g.
    ``"app.settings:Settings"``).  The resolved object must be a
    :class:`~pydantic_settings.BaseSettings` subclass or instance.

    When *value* contains no ``:``, it is treated as a plain Python module
    path (e.g. ``"app.settings"``).  In this case the module is imported and
    **all** :class:`~pydantic_settings.BaseSettings` subclasses defined in
    that module (i.e. whose ``__module__`` equals the module name) are
    returned.

    :param value: Import string in ``"module:attribute"`` or
        ``"module"`` format.
    :return: List of resolved settings classes or instances.
    """
    obj: Any
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

    if isinstance(obj, ModuleType):
        found = _find_settings_in_module(obj)
        if not found:
            logger.warning("No BaseSettings subclasses found in module %r", value)
        return found  # type: ignore[return-value]

    if (isinstance(obj, type) and issubclass(obj, BaseSettings)) or isinstance(obj, BaseSettings):
        return [obj]
    raise ValueError(f"The {obj!r} is not a settings class.")
