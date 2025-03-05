from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import SettingsConfigDict

from pydantic_settings_export.sources import TomlSettings

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
        description=(
            "The project directory. Used for relative paths in the configuration file and .env file. "
            "If not set, will be the same as project_dir."
        ),
    )

    project_dir: Path = Field(
        Path.cwd(),
        description="The project directory. Used for importing settings.",
    )

    relative_to: RelativeToSettings = Field(
        default_factory=RelativeToSettings,
        description="The relative directory settings.",
    )
    respect_exclude: bool = Field(True, description="Respect the exclude attribute in the fields.")

    @classmethod
    @model_validator(mode="before")
    def default_for_root_dir(cls, data: dict) -> dict:
        """Set the default value for root_dir if not set."""
        if isinstance(data, dict):
            project_dir = data.get("project_dir", None)
            if project_dir is not None:
                data.setdefault("root_dir", project_dir)
        return data
