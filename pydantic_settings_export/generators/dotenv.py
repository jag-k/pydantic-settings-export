import sys
import warnings
from pathlib import Path
from typing import Literal, Optional

from pydantic import ConfigDict, Field, model_validator

from pydantic_settings_export.models import FieldInfoModel, SettingsInfoModel

from .abstract import AbstractGenerator, BaseGeneratorSettings

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

__all__ = ("DotEnvGenerator",)

# Defines the mode for .env file generation.
# Options:
#     - "all": Include both optional and required variables
#     - "only-optional": Include only optional variables
#     - "only-required": Include only required variables
DotEnvMode = Literal["all", "only-optional", "only-required"]

# Map from DotEnvMode to (is_optional, is_required)
DOTENV_MODE_MAP: dict[DotEnvMode, tuple[bool, bool]] = {
    "all": (True, True),  # Include both (optional and required)
    "only-optional": (True, False),  # Only include optional fields
    "only-required": (False, True),  # Only include required fields
}
DOTENV_MODE_MAP_DEFAULT = DOTENV_MODE_MAP["all"]


class DotEnvSettings(BaseGeneratorSettings):
    """Settings for the .env file."""

    model_config = ConfigDict(title="Generator: dotenv File Settings")

    name: Optional[Path] = Field(
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
                stacklevel=2,
            )
            self.paths = [self.name]
        return self


class DotEnvGenerator(AbstractGenerator[DotEnvSettings]):
    """The .env example generator."""

    name = "dotenv"
    config = DotEnvSettings

    def _process_field(
        self,
        settings_info: SettingsInfoModel,
        field: FieldInfoModel,
        is_optional: bool,
        is_required: bool,
    ) -> Optional[str]:
        """Process a field and return the string to add to the .env file.

        :param settings_info: The settings info model.
        :param field: The field info model.
        :param is_optional: Whether to include optional fields
        :param is_required: Whether to include required fields
        :return: The string to add to the .env file or None if the field should be skipped.
        """
        # Get the environment variable name, using alias if available
        field_name = f"{settings_info.env_prefix}{field.name.upper()}"
        if field.aliases:
            field_name = field.aliases[0].upper()

        # Skip required fields if we're only including optional ones
        if field.is_required and not is_required:
            return None

        # Format optional fields with a comment prefix
        field_string = f"{field_name}="
        if not field.is_required and is_optional:
            field_string = f"# {field_name}={field.default}"

        # Add examples as comments if available and enabled
        if field.examples and field.examples != [field.default] and self.generator_config.add_examples:
            field_string += "  # " + (", ".join(field.examples))
        return field_string

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:
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
            field_string = self._process_field(settings_info, field, is_optional, is_required)
            if not field_string:
                continue

            result += field_string + "\n"
            has_content = True

        result = result.strip() + "\n"
        if self.generator_config.split_by_group:
            result += "\n"

        child_results = [self.generate_single(child) for child in settings_info.child_settings]
        has_content = has_content or any(r.strip() for r in child_results)
        result += "".join(r for r in child_results if r.strip())

        if not has_content:
            warnings.warn(
                f"# No environment variables found for {settings_info.name} in "
                f"mode={self.generator_config.mode!r} "
                f"(looking for {'optional' if is_optional else 'required'} variables)",
                stacklevel=2,
            )

        return result
