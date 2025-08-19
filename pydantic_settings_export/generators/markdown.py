import importlib.util
import sys
import warnings
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, TypedDict, Union, cast

from pydantic import ConfigDict, Field, model_validator

from pydantic_settings_export.models import FieldInfoModel, SettingsInfoModel
from pydantic_settings_export.utils import make_pretty_md_table_from_dict, q

from .abstract import AbstractGenerator, BaseGeneratorSettings

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self


if TYPE_CHECKING:
    from text_region_parser import RegionConstructor

__all__ = ("MarkdownGenerator",)


class TableRowDict(TypedDict):
    """The table row dictionary."""

    Name: str
    Type: str
    Default: str
    Description: str
    Example: Optional[str]


TableHeadersEnum = Enum(  # type: ignore[misc]
    "TableHeaders",
    [(h, h) for h in TableRowDict.__annotations__.keys()],
    type=str,
)
TableHeaders: list[TableHeadersEnum] = list(TableHeadersEnum.__members__.values())
UNION_SEPARATOR = " | "


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
    table_only: Union[bool, Literal["with-header"]] = Field(
        False,
        description=(
            "Only generate the table of the ALL settings (including sub-settings).\n"
            "If `with-header`, will be generated with the header of top-level settings."
        ),
        examples=[True, False, "with-header"],
    )

    region: Union[str, Literal[False]] = Field(
        False,
        description=(
            "The region to use for the table of the ALL settings (including sub-settings).\n"
            "If a string is provided, the generator will insert content into that named region.\n"
            "It replace all regions with the same to the same content.\n\n"
            "NOTE: This option is only available if the `regions` extra is installed.\n"
            'NOTE: For now, you cannot be able to control regions with the "region header option".'
        ),
        examples=[False, "config"],
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
                stacklevel=2,
            )
            self.paths = [path / self.name for path in self.save_dirs]
        self.paths = [p.absolute().resolve() for p in self.paths]
        return self

    @model_validator(mode="after")
    def validate_region(self) -> Self:
        """Validate the region."""
        if self.region:
            spec = importlib.util.find_spec("text_region_parser")
            if not spec or not spec.loader:
                raise ValueError("The `region` option is only available if the `regions` extra is installed.")
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

    example: Optional[str] = None
    if field.examples:
        example = ", ".join(q(example) for example in field.examples)
    types = UNION_SEPARATOR.join(q(t) for t in field.types)

    return TableRowDict(
        Name=name,
        Type=types,
        Default=default,
        Description=field.description or "",
        Example=example,
    )


class MarkdownGenerator(AbstractGenerator[MarkdownSettings]):
    """The Markdown configuration file generator."""

    name = "markdown"
    config = MarkdownSettings

    def _make_table(self, rows: list[TableRowDict]) -> str:
        return make_pretty_md_table_from_dict(
            cast(list[dict[str, Optional[str]]], rows),
            headers=[h.value for h in self.generator_config.table_headers],
        )

    @staticmethod
    def _process_region(path: Path, constructor: "RegionConstructor") -> bool:
        """Process a single region in a file.

        :param path: Path to the file
        :param constructor: Region constructor instance
        :return: True if a file was updated, False otherwise
        :raises FileNotFoundError: If the file doesn't exist
        :raises IOError: If there are issues reading/writing the file
        """
        try:
            if not path.is_file():
                raise FileNotFoundError(
                    f"The file {path} does not exist. "
                    f"Please create this file before running the generator with the `region` option."
                )

            file_content = path.read_text()
            new_content = constructor.parse_content(file_content)

            if new_content == file_content:
                return False

            path.write_text(new_content)
            return True

        except OSError as e:
            raise OSError(f"Failed to process region in {path}: {e}") from e

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:  # noqa: C901
        """Generate Markdown documentation for a pydantic settings class.

        Creates formatted Markdown with:
        - Nested headers for settings hierarchy
        - Tables for settings documentation
        - Environment variable information
        - Type annotations and defaults
        - Optional examples and deprecation notices


        :param settings_info: Settings model to document.
        :param level: Header nesting level (h1, h2, etc.).
        :return: Formatted Markdown documentation.
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

    def run(self, *settings_info: SettingsInfoModel) -> list[Path]:
        """Run the generator.

        :param settings_info: The settings info to generate documentation for.
        :return: The paths to generated documentation.
        """
        # If the region is not set, run the generator as usual
        region = self.generator_config.region
        if not region:
            return super().run(*settings_info)

        import text_region_parser

        result = f"\n{self.generate(*settings_info).strip()}\n"
        file_paths = self.file_paths()

        constructor = text_region_parser.RegionConstructor()

        # Add the region with name from the config
        # This region will be replaced with the generated content
        constructor.add_parser(cast(str, region))(lambda _: result)

        updated_files: list[Path] = []
        for path in file_paths:
            try:
                if self._process_region(path, constructor):
                    updated_files.append(path)
            except (OSError, FileNotFoundError) as e:
                warnings.warn(str(e), stacklevel=2)

        return updated_files
