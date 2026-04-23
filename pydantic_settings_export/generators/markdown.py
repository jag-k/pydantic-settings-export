import importlib.util
import sys
import warnings
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypedDict, cast

from pydantic import ConfigDict, Field, model_validator

from pydantic_settings_export.models import FieldInfoModel, SettingsInfoModel, format_types, value_repr
from pydantic_settings_export.utils import make_pretty_md_table_from_dict, q

from .abstract import AbstractEnvGenerator, BaseEnvGeneratorSettings

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
    Example: str | None


TableHeadersEnum = Enum(  # type: ignore[misc]
    "TableHeaders",
    [(h, h) for h in TableRowDict.__annotations__.keys()],
    type=str,
)
TableHeaders: list[TableHeadersEnum] = list(TableHeadersEnum.__members__.values())
UNION_SEPARATOR = " | "


class MarkdownSettings(BaseEnvGeneratorSettings):
    """Settings for the Markdown file."""

    model_config = ConfigDict(title="Generator: Markdown Configuration File Settings")

    name: str | None = Field(
        None,
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

    table_headers: list[TableHeadersEnum] = Field(
        default_factory=lambda: TableHeaders,
        min_length=1,
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

    region: str | Literal[False] = Field(
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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            _name = self.name
            _save_dirs = self.save_dirs
        if _save_dirs and _name:
            warnings.warn(
                (
                    "The `save_dirs` and `name` attributes are deprecated and will be removed in the future. "
                    "Use `paths` instead."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            self.paths = [path / _name for path in _save_dirs]
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


class MarkdownGenerator(AbstractEnvGenerator[MarkdownSettings]):
    """The Markdown configuration file generator."""

    name = "markdown"
    config = MarkdownSettings

    def _make_table(self, rows: list[TableRowDict]) -> str:
        return make_pretty_md_table_from_dict(
            cast(list[dict[str, str | None]], rows),
            headers=[h.value for h in self.generator_config.table_headers],
        )

    def _make_table_row(
        self,
        settings_info: SettingsInfoModel,
        field: FieldInfoModel,
        md_settings: MarkdownSettings,
    ) -> TableRowDict:
        """Make a table row dictionary from a field."""
        if field.env_names:
            names = [
                self.apply_env_case(
                    n, to_upper_case=md_settings.to_upper_case, case_sensitive=settings_info.case_sensitive
                )
                for n in field.env_names
            ]
            name = UNION_SEPARATOR.join(q(n) for n in names)
        else:
            raw = f"{settings_info.env_prefix}{field.name}"
            name = q(
                self.apply_env_case(
                    raw, to_upper_case=md_settings.to_upper_case, case_sensitive=settings_info.case_sensitive
                )
            )

        if field.deprecated:
            name += " (⚠️ Deprecated)"

        default = "*required*"
        if not field.is_required:
            default = q(value_repr(field.default))

        example: str | None = None
        if field.examples:
            example = ", ".join(q(value_repr(ex)) for ex in field.examples)
        types = UNION_SEPARATOR.join(q(t) for t in format_types(field.types))

        return TableRowDict(
            Name=name,
            Type=types,
            Default=default,
            Description=field.description or "",
            Example=example,
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
                prefix_display = self.apply_env_case(
                    settings_info.env_prefix,
                    to_upper_case=self.generator_config.to_upper_case,
                    case_sensitive=settings_info.case_sensitive,
                )
                result += f"**Environment Prefix**: `{prefix_display}`\n\n"

        # Generate fields
        rows: list[TableRowDict] = [
            self._make_table_row(settings_info, field, self.generator_config) for field in settings_info.fields
        ]

        if rows:
            result += self._make_table(rows) + "\n\n"

        # Generate child settings
        result += "\n\n".join(self.generate_single(child, level + 1).strip() for child in settings_info.child_settings)

        return result

    def _single_table(self, settings_info: SettingsInfoModel) -> list[TableRowDict]:
        rows: list[TableRowDict] = []
        rows.extend(self._make_table_row(settings_info, field, self.generator_config) for field in settings_info.fields)
        for child in settings_info.child_settings:
            rows.extend(self._single_table(child))
        return rows

    def generate(self, *settings_infos: SettingsInfoModel) -> str:
        """Generate Markdown documentation for a pydantic settings class.

        :param settings_infos: The settings class to generate documentation for.
        :return: The generated documentation.
        """
        settings_infos = tuple(self._disambiguate_settings_infos(*settings_infos))
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
