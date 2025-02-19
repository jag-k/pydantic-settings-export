import warnings
from pathlib import Path
from typing import Literal, Self

from pydantic import ConfigDict, Field, model_validator

from pydantic_settings_export.models import SettingsInfoModel

from .abstract import AbstractGenerator, BaseGeneratorSettings

__all__ = ("DotEnvGenerator",)

# Defines the mode for .env file generation.
# Options:
#     - "all": Include both optional and required variables
#     - "only-optional": Include only optional variables
#     - "only-required": Include only required variables
DotEnvMode = Literal["all", "only-optional", "only-required"]

# Map from DotEnvMode to (is_optional, is_required)
DOTENV_MODE_MAP: dict[DotEnvMode, tuple[bool, bool]] = {
    "all": (True, True),
    "only-optional": (True, False),
    "only-required": (False, True),
}
DOTENV_MODE_MAP_DEFAULT = DOTENV_MODE_MAP["all"]


class DotEnvSettings(BaseGeneratorSettings):
    """Settings for the .env file."""

    model_config = ConfigDict(title="Generator: dotenv File Settings")

    name: Path | None = Field(
        None,
        description="The name of the .env file.",
        examples=[
            ".env.example",
            ".env.sample",
        ],
        deprecated=True,
    )

    paths: list[Path] = Field(
        default_factory=list,
        description="The paths to the resulting files.",
        examples=[
            Path(".env.example"),
            Path(".env.sample"),
        ],
    )

    split_by_group: bool = Field(True, description="Whether to split the environment variables by group (headers).")
    add_examples: bool = Field(True, description="Whether to add examples to the environment variables.")
    mode: DotEnvMode = Field(
        "all",
        description="The mode to export for the environment variables. For more information, see the README.",
    )

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        """Validate the paths."""
        if self.name:
            warnings.warn(
                "The `name` attribute is deprecated and will be removed in a future version. "
                "Please migrate to using `paths: list[Path]` instead. "
                "Example: paths=[Path('.env.example')] or `paths=['.env.example']` (for `pyproject.toml`).",
                DeprecationWarning,
                stacklevel=1,
            )
            self.paths = [self.name]
        return self


class DotEnvGenerator(AbstractGenerator):
    """The .env example generator."""

    name = "dotenv"
    config = DotEnvSettings
    generator_config: DotEnvSettings

    def generate_single(self, settings_info: SettingsInfoModel, level=1) -> str:  # noqa: C901
        """Generate a .env example for a pydantic settings class.

        Creates a formatted .env file with:
        - Optional/required variables clearly marked
        - Grouped settings with headers
        - Example values as comments
        - Proper environment variable naming

        :param settings_info: The settings class to generate examples for.
        :param level: The level of nesting for proper formatting.
        :return: Formatted .env content with variables and documentation.
        """
        result = ""
        is_optional, is_required = DOTENV_MODE_MAP.get(self.generator_config.mode, DOTENV_MODE_MAP_DEFAULT)

        has_content = False
        if self.generator_config.split_by_group:
            result = f"### {settings_info.name}\n\n"

        for field in settings_info.fields:
            field_name = f"{settings_info.env_prefix}{field.name.upper()}"
            if field.aliases:
                field_name = field.aliases[0].upper()

            field_string = f"{field_name}="
            if not field.is_required and is_optional:
                field_string = f"# {field_name}={field.default}"

            elif field.is_required and not is_required:
                continue

            if field.examples and field.examples != [field.default] and self.generator_config.add_examples:
                field_string += "  # " + (", ".join(field.examples))

            result += field_string + "\n"
            has_content = True

        result = result.strip() + "\n"
        if self.generator_config.split_by_group:
            result += "\n"

        for child in settings_info.child_settings:
            child_result = self.generate_single(child)
            if child_result.strip():
                result += child_result
                has_content = True

        if not has_content:
            warnings.warn(
                f"# No {'optional' if is_optional else 'required'} environment variables found "
                f"for {settings_info.name}",
                stacklevel=2,
            )

        return result
