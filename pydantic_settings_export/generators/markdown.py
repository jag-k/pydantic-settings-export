from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

from pydantic_settings_export.models import FieldInfoModel, SettingsInfoModel
from pydantic_settings_export.utils import make_pretty_md_table_from_dict

from .abstract import AbstractGenerator

__all__ = ("MarkdownGenerator",)


class MarkdownSettings(BaseModel):
    """Settings for the Markdown file."""

    model_config = ConfigDict(title="Generator: Markdown Configuration File Settings")

    enabled: bool = Field(True, description="Enable the configuration file generation.")

    name: str = Field(
        "Configuration.md",
        description="The name of the configuration file.",
        # deprecated=True,
    )
    save_dirs: list[Path] = Field(
        default_factory=list,
        description="The directories to save configuration files to.",
        # deprecated=True,
    )

    # WIP
    # paths: list[Path] = Field(
    #     default_factory=lambda: [Path("Configuration.md")],
    #     description="The name of the configuration file.",
    # )
    #
    # @model_validator(mode="after")
    # def validate_paths(self) -> Any:
    #     """Validate the paths."""
    #     if self.save_dirs and self.name:
    #         warnings.warn(
    #             (
    #                 "The `save_dirs` and `name` attributes are deprecated and will be removed in the future. "
    #                 "Use `paths` instead."
    #             ),
    #             DeprecationWarning,
    #             stacklevel=2,
    #         )
    #         self.paths = [path / self.name for path in self.save_dirs]
    #     return self

    def __bool__(self) -> bool:
        """Check if the configuration file is set."""
        return self.enabled and bool(self.save_dirs)


class TableRowDict(TypedDict):
    """The table row dictionary."""

    Name: str
    Type: str
    Default: str
    Description: str
    Example: str | None


def q(s: str) -> str:
    """Add quotes around the string."""
    return f"`{s}`"


def _make_table_row(settings_info: SettingsInfoModel, field: FieldInfoModel) -> TableRowDict:
    """Make a table row dictionary from a field."""
    name = f"`{settings_info.env_prefix}{field.name.upper()}`"
    if field.alias:
        name = q(field.alias.upper())

    if field.deprecated:
        name += " (⚠️ Deprecated)"

    default = "*required*"
    if not field.is_required:
        default = q(field.default)

    example: str | None = None
    if field.examples:
        example = ", ".join(q(example) for example in field.examples)

    return TableRowDict(
        Name=name,
        Type=q(field.type),
        Default=default,
        Description=field.description,
        Example=example,
    )


class MarkdownGenerator(AbstractGenerator):
    """The Markdown configuration file generator."""

    name = __name__
    config = MarkdownSettings
    generator_config: MarkdownSettings

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:  # noqa: C901
        """Generate Markdown documentation for a pydantic settings class.

        :param settings_info: The settings class to generate documentation for.
        :param level: The level of nesting. Used for indentation.
        :return: The generated documentation.
        """
        docs = ("\n\n" + settings_info.docs).rstrip()

        # Generate header
        result = f"{'#' * level} {settings_info.name}{docs}\n\n"

        # Add an environment prefix if it exists
        if settings_info.env_prefix:
            result += f"**Environment Prefix**: `{settings_info.env_prefix}`\n\n"

        # Generate fields
        rows: list[TableRowDict] = [_make_table_row(settings_info, field) for field in settings_info.fields]

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

    def file_paths(self) -> list[Path]:
        """Get the list of files which need to create/update.

        :return: The list of files to write.
        This is used to determine if the files need to be written.
        """
        file_paths = []
        if not self.generator_config.enabled:
            return file_paths

        for d in self.generator_config.save_dirs:
            d = d.absolute().resolve()
            d.mkdir(parents=True, exist_ok=True)
            p = d / self.generator_config.name
            file_paths.append(p)
        return file_paths
