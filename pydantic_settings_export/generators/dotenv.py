import warnings
from pathlib import Path
from typing import Literal, Self

from pydantic import ConfigDict, Field, model_validator

from pydantic_settings_export.models import SettingsInfoModel

from .abstract import AbstractGenerator, BaseGeneratorSettings

__all__ = ("DotEnvGenerator",)

DotEnvMode = Literal["all", "only-optional", "only-required"]


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
                "The `name` attribute is deprecated and will be removed in the future. Use `paths` instead.",
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

    def generate_single(self, settings_info: SettingsInfoModel, level=1) -> str:
        """Generate a .env example for a pydantic settings class.

        :param level: The level of nesting. Used for indentation.
        :param settings_info: The settings class to generate a .env example for.
        :return: The generated .env example.
        """
        result = ""
        is_optional, is_required = {
            "all": (True, True),
            "only-optional": (True, False),
            "only-required": (False, True),
        }.get(self.generator_config.mode, (True, True))

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

        result = result.strip() + "\n"
        if self.generator_config.split_by_group:
            result += "\n"

        for child in settings_info.child_settings:
            result += self.generate_single(child)

        return result
