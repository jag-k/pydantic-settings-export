import argparse
import hashlib
import importlib
import importlib.util
import logging
import re
import sys
import warnings
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from inspect import getfile, isclass
from pathlib import Path
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


def _find_settings_in_module(module: ModuleType) -> list[BaseSettings | type[BaseSettings]]:
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


def _is_path_like(value: str) -> bool:
    """Check if the value looks like a file-system path."""
    return value.startswith((".", "~", "/")) or value.endswith(".py") or "/" in value or "\\" in value


def _resolve_settings_path(value: str, project_dir: Path | None = None) -> Path | None:
    """Resolve a settings path relative to *project_dir* when applicable."""
    if not _is_path_like(value):
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (project_dir or Path.cwd()) / path
    path = path.resolve().absolute()

    if not path.exists():
        raise FileNotFoundError(f"The path {value!r} does not exist.")
    if path.is_file() and path.suffix != ".py":
        raise ValueError(f"The {value!r} is not a Python file.")
    return path


@contextmanager
def _prepend_sys_path(path: Path | None) -> Iterator[None]:
    """Temporarily prepend a path to ``sys.path``."""
    if path is None:
        yield
        return

    str_path = str(path)
    sys.path.insert(0, str_path)
    try:
        yield
    finally:
        try:
            sys.path.remove(str_path)
        except ValueError:
            pass


def _make_module_name(path: Path, project_dir: Path | None = None) -> str | None:
    """Create a module name from the file path relative to *project_dir*."""
    if project_dir is None:
        return None

    try:
        relative_path = path.resolve().relative_to(project_dir.resolve().absolute())
    except ValueError:
        return None

    parts = list(relative_path.parts)
    if not parts:
        return None

    if path.name == "__init__.py":
        parts = parts[:-1]
    elif path.suffix == ".py":
        parts[-1] = path.stem
    else:
        return None

    if not parts:
        return None
    return ".".join(parts)


def _import_module_from_file(path: Path, project_dir: Path | None = None) -> ModuleType:
    """Import a module from a Python file path."""
    importlib.invalidate_caches()

    module_name = _make_module_name(path, project_dir)
    if module_name:
        with _prepend_sys_path(project_dir):
            try:
                return importlib.import_module(module_name)
            except Exception:
                logger.debug("Failed to import %s as %s", path, module_name, exc_info=True)

    synthetic_name = f"_pse_settings_{hashlib.sha256(str(path).encode()).hexdigest()}"
    spec = importlib.util.spec_from_file_location(synthetic_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create module spec for {path!s}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[synthetic_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(synthetic_name, None)
        raise
    return module


def _iter_python_files(path: Path) -> list[Path]:
    """Get all Python files in the directory recursively."""
    result = []
    for file in sorted(path.rglob("*.py")):
        if any(part == "__pycache__" or part.startswith(".") for part in file.relative_to(path).parts):
            continue
        result.append(file)
    return result


def _import_settings_from_path(
    path: Path,
    project_dir: Path | None = None,
) -> list[BaseSettings | type[BaseSettings]]:
    """Import settings classes from a file or directory path."""
    if path.is_dir():
        result: list[BaseSettings | type[BaseSettings]] = []
        for file in _iter_python_files(path):
            try:
                result.extend(_import_settings_from_path(file, project_dir=project_dir))
            except Exception as e:
                warnings.warn(f"Failed to import settings from {file!s}: {e}", stacklevel=2)
        return result

    module = _import_module_from_file(path, project_dir=project_dir)
    found = _find_settings_in_module(module)
    if not found:
        logger.warning("No BaseSettings subclasses found in file %r", str(path))
    return found


def _settings_identity(obj: BaseSettings | type[BaseSettings]) -> tuple[str, ...] | tuple[str, int]:
    """Create an identity for settings objects to deduplicate them."""
    if isinstance(obj, BaseSettings) and not isclass(obj):
        return ("instance", id(obj))

    cls = obj if isclass(obj) else obj.__class__
    try:
        file_path = str(Path(getfile(cls)).resolve().absolute())
    except (OSError, TypeError):
        file_path = cls.__module__
    return ("class", file_path, cls.__qualname__)


def import_settings_from_string(
    value: str,
    project_dir: Path | None = None,
) -> list[BaseSettings | type[BaseSettings]]:
    """Import the settings from the string.

    When *value* contains ``:``, the part before it is treated as a module
    path and the part after it as an attribute name (e.g.
    ``"app.settings:Settings"``).  The resolved object must be a
    :class:`~pydantic_settings.BaseSettings` subclass or instance.

    When *value* looks like a file-system path, it is resolved relative to
    *project_dir* (or current working directory), then imported either as a
    single Python file or as a directory recursively containing Python files.

    When *value* contains no ``:```, it is treated as a plain Python module
    path (e.g. ``"app.settings"``). In this case the module is imported and
    **all** :class:`~pydantic_settings.BaseSettings` subclasses defined in
    that module (i.e. whose ``__module__`` equals the module name) are
    returned.

    :param value: Import string in ``"module:attribute"`` or
        ``"module"`` format, or a path to a Python file/directory.
    :param project_dir: Base directory for resolving relative file-system paths.
    :return: List of resolved settings classes or instances.
    """
    path = _resolve_settings_path(value, project_dir=project_dir)
    if path is not None:
        return _import_settings_from_path(path, project_dir=project_dir)

    obj: Any
    with _prepend_sys_path(project_dir):
        importlib.invalidate_caches()
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


def import_settings_from_strings(
    values: Sequence[str],
    project_dir: Path | None = None,
    continue_on_error: bool = False,
) -> list[BaseSettings | type[BaseSettings]]:
    """Import settings from multiple strings and deduplicate them."""
    result: list[BaseSettings | type[BaseSettings]] = []
    seen: set[tuple[str, ...] | tuple[str, int]] = set()

    for value in values:
        try:
            imported = import_settings_from_string(value, project_dir=project_dir)
        except (ImportError, ValueError, ValidationError, FileNotFoundError) as e:
            if continue_on_error:
                warnings.warn(f"Failed to import settings {value!r}: {e}", stacklevel=2)
                continue
            raise

        for obj in imported:
            key = _settings_identity(obj)
            if key in seen:
                continue
            seen.add(key)
            result.append(obj)
    return result
