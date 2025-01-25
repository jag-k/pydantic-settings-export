import warnings
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self, TypedDict

from pydantic import ConfigDict, Field, model_validator

from pydantic_settings_export.models import FieldInfoModel, SettingsInfoModel
from pydantic_settings_export.utils import make_pretty_md_table_from_dict, q

from .abstract import AbstractGenerator, BaseGeneratorSettings

__all__ = ("MarkdownGenerator",)


class TableRowDict(TypedDict):
    """The table row dictionary."""

    Name: str
    Type: str
    Default: str
    Description: str
    Example: str | None


TableHeadersEnum = StrEnum("TableHeaders", [(h, h) for h in TableRowDict.__annotations__.keys()])
TableHeaders: list[TableHeadersEnum] = list(TableHeadersEnum.__members__.values())
UNION_SEPARATOR = " \\| "


class MarkdownSettings(BaseGeneratorSettings):
    """Settings for the Markdown file."""

    model_config = ConfigDict(title="Generator: Markdown Configuration File Settings")

    name: str = Field(
        "Configuration.md",
        description="The name of the configuration file.",
        deprecated=True,
    )
    save_dirs: list[Path] = Field(
        default_factory=list,
        description="The directories to save configuration files to.",
        deprecated=True,
    )

    paths: list[Path] = Field(
        default_factory=list,
        description="The paths to the resulting files.",
        examples=[
            Path("Configuration.md"),
            Path("docs/Configuration.md"),
            Path("wiki/project_config.md"),
        ],
    )

    file_prefix: str = Field(
        "# Configuration\n\nHere you can find all available configuration options using ENV variables.\n\n",
        description="The prefix of the result configuration file.",
        examples=[""],
    )

    to_upper_case: bool = Field(
        True,
        description="Convert the field names to upper case.",
    )

    table_headers: list[TableHeadersEnum] = Field(
        default_factory=lambda: TableHeaders,
        ge=1,
        description=(
            "The headers of the table. Can be rearranged and/or removed.\n"
            "Must be at least one element and possible are:\n"
            f"{', '.join(q(h.value) for h in TableHeaders)}"
        ),
        examples=[[TableHeadersEnum["Name"], TableHeadersEnum["Description"]]],
    )
    table_only: bool | Literal["with-header"] = Field(
        False,
        description=(
            "Only generate the table of the ALL settings (including sub-settings).\n"
            "If `with-header`, will be generated with the header of top-level settings."
        ),
        examples=[True, False, "with-header"],
    )

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        """Validate the paths."""
        if self.save_dirs and self.name:
            warnings.warn(
                (
                    "The `save_dirs` and `name` attributes are deprecated and will be removed in the future. "
                    "Use `paths` instead."
                ),
                DeprecationWarning,
                stacklevel=1,
            )
            self.paths = [path / self.name for path in self.save_dirs]
        self.paths = [p.absolute().resolve() for p in self.paths]
        return self

    def __bool__(self) -> bool:
        """Check if the configuration file is set."""
        return self.enabled and bool(self.paths)


def _make_table_row(
    settings_info: SettingsInfoModel,
    field: FieldInfoModel,
    md_settings: MarkdownSettings,
) -> TableRowDict:
    """Make a table row dictionary from a field."""
    name = q(settings_info.env_prefix + field.name)

    if field.aliases:
        name = UNION_SEPARATOR.join(q(a) for a in field.aliases)

    if md_settings.to_upper_case:
        name = name.upper()

    if field.deprecated:
        name += " (⚠️ Deprecated)"

    default = "*required*"
    if not field.is_required:
        default = q(field.default)

    example: str | None = None
    if field.examples:
        example = ", ".join(q(example) for example in field.examples)
    types = UNION_SEPARATOR.join(q(t) for t in field.types)

    return TableRowDict(
        Name=name,
        Type=types,
        Default=default,
        Description=field.description,
        Example=example,
    )


class MarkdownGenerator(AbstractGenerator):
    """The Markdown configuration file generator."""

    name = "markdown"
    config = MarkdownSettings
    generator_config: MarkdownSettings

    def _make_table(self, rows: list[TableRowDict]) -> str:
        return make_pretty_md_table_from_dict(rows, headers=[h.value for h in self.generator_config.table_headers])

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:  # noqa: C901
        """Generate Markdown documentation for a pydantic settings class.

        :param settings_info: The settings class to generate documentation for.
        :param level: The level of nesting. Used for indentation.
        :return: The generated documentation.
        """
        # Generate header
        result = ""
        if not self.generator_config.table_only:
            docs = ("\n\n" + settings_info.docs).rstrip()
            result = f"{'#' * level} {settings_info.name}{docs}\n\n"

            # Add an environment prefix if it exists
            if settings_info.env_prefix:
                result += f"**Environment Prefix**: `{settings_info.env_prefix}`\n\n"

        # Generate fields
        rows: list[TableRowDict] = [
            _make_table_row(settings_info, field, self.generator_config) for field in settings_info.fields
        ]

        if rows:
            result += self._make_table(rows) + "\n\n"

        # Generate child settings
        result += "\n\n".join(self.generate_single(child, level + 1).strip() for child in settings_info.child_settings)

        return result

    def _single_table(self, settings_info: SettingsInfoModel) -> list[TableRowDict]:
        rows: list[TableRowDict] = []
        rows.extend(_make_table_row(settings_info, field, self.generator_config) for field in settings_info.fields)
        for child in settings_info.child_settings:
            rows.extend(self._single_table(child))
        return rows

    def generate(self, *settings_infos: SettingsInfoModel) -> str:
        """Generate Markdown documentation for a pydantic settings class.

        :param settings_infos: The settings class to generate documentation for.
        :return: The generated documentation.
        """
        content = ""
        if self.generator_config.file_prefix:
            content = self.generator_config.file_prefix
            if not content.endswith("\n\n"):
                content += "\n\n"
        if self.generator_config.table_only:
            content += self._make_table([row for s in settings_infos for row in self._single_table(s)])
        else:
            content += "\n\n".join(self.generate_single(s, 2).strip() for s in settings_infos)
        return content.strip() + "\n"
