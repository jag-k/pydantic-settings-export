import argparse
import importlib
import sys
from collections.abc import Sequence
from typing import Any

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
