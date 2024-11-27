from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SkipValidation, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings_export.generators import AbstractGenerator, Generators
from pydantic_settings_export.sources import TomlSettings
from pydantic_settings_export.utils import import_settings_from_string

__all__ = (
    "RelativeToSettings",
    "PSESettings",
)


class RelativeToSettings(BaseModel):
    """Settings for the relative directory."""

    model_config = SettingsConfigDict(title="Relative Directory Settings")

    replace_abs_paths: bool = Field(True, description="Replace absolute paths with relative path to project root.")
    alias: str = Field("<project_dir>", description="The alias for the relative directory.")


class PSESettings(TomlSettings):
    """Global settings for pydantic_settings_export."""

    model_config = SettingsConfigDict(
        title="Global Settings",
        env_prefix="PYDANTIC_SETTINGS_EXPORT__",
        env_nested_delimiter="__",
        pyproject_toml_table_header=("tool", "pydantic_settings_export"),
    )

    default_settings: list[str] = Field(
        default_factory=list,
        description="The default settings to use. The settings are applied in the order they are listed.",
        examples=[
            ["settings:settings"],
            ["app.config.settings:Settings", "app.config.settings.dev:Settings"],
        ],
    )

    root_dir: Path = Field(
        Path.cwd(),
        description="The project directory. Used for relative paths in the configuration file and .env file.",
    )

    project_dir: Path = Field(
        Path.cwd(),
        description="The project directory. Used for relative paths in the configuration file and .env file.",
    )

    relative_to: RelativeToSettings = Field(
        default_factory=RelativeToSettings,
        description="The relative directory settings.",
    )
    respect_exclude: bool = Field(True, description="Respect the exclude attribute in the fields.")

    generators: Generators = Field(
        default_factory=Generators,
        description="The configuration of generators.",
    )

    generators_list: list[SkipValidation[type["AbstractGenerator"]]] = Field(
        default_factory=list,
        description="The list of generators to use.",
        exclude=True,
    )

    env_file: Path | None = Field(
        None,
        description=(
            "The path to the `.env` file to load environment variables. "
            "Useful, then you have a Settings class/instance, which require values while running."
        ),
    )

    @property
    def settings(self) -> list[BaseSettings]:
        """Get the settings."""
        return [import_settings_from_string(i) for i in self.default_settings or []]

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @classmethod
    def validate_env_file(cls, data: Any) -> Any:
        """Validate the env file."""
        if isinstance(data, dict):
            file = data.get("env_file")
            if file is not None:
                f = Path(file)
                if f.is_file():
                    print("Loading env file", f)
                    load_dotenv(file)
        return data
