from pathlib import Path
from typing import TypedDict

from pydantic_settings_export.models import SettingsInfoModel
from pydantic_settings_export.utils import make_pretty_md_table_from_dict

from .abstract import AbstractGenerator

__all__ = ("MarkdownGenerator",)


class TableRowDict(TypedDict):
    """The table row dictionary."""

    Name: str
    Type: str
    Default: str
    Description: str
    Example: str | None


class MarkdownGenerator(AbstractGenerator):
    """The Markdown configuration file generator."""

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:  # noqa: C901
        """Generate Markdown documentation for a pydantic settings class.

        :param settings_info: The settings class to generate documentation for.
        :param level: The level of nesting. Used for indentation.
        :return: The generated documentation.
        """
        docs = ("\n\n" + settings_info.docs).rstrip()

        # Generate header
        result = f"{'#' * level} {settings_info.name}{docs}\n\n"

        # Add environment prefix if it exists
        if settings_info.env_prefix:
            result += f"**Environment Prefix**: `{settings_info.env_prefix}`\n\n"

        # Generate fields
        rows: list[TableRowDict] = [
            TableRowDict(
                Name=f"`{field.alias.upper()}`" if field.alias else f"`{settings_info.env_prefix}{field.name.upper()}`",
                Type=f"`{field.type}`",
                Default=f"`{field.default}`" if not field.is_required else "*required*",
                Description=field.description,
                Example=f"`{field.example}`" if field.example else None,
            )
            for field in settings_info.fields
        ]

        if rows:
            result += make_pretty_md_table_from_dict(rows) + "\n\n"

        # Generate child settings
        result += "\n\n".join(self.generate_single(child, level + 1).strip() for child in settings_info.child_settings)

        return result

    def generate(self, *settings_infos: SettingsInfoModel) -> str:
        """Generate Markdown documentation for a pydantic settings class.

        :param settings_infos: The settings class to generate documentation for.
        :return: The generated documentation.
        """
        return (
            "# Configuration\n\n"
            "Here you can find all available configuration options using ENV variables.\n\n"
            + "\n\n".join(self.generate_single(s, 2).strip() for s in settings_infos)
        ).strip() + "\n"

    def write_to_files(self, generated_result: str) -> list[Path]:
        """Write the generated content to files.

        :param generated_result: The result to write to files.
        :return: The list of file paths written to.
        """
        file_paths = []
        for d in self.settings.markdown.save_dirs:
            d = d.absolute().resolve()
            d.mkdir(parents=True, exist_ok=True)
            p = d / self.settings.markdown.name
            file_paths.append(p)
            p.write_text(generated_result)
        return file_paths
