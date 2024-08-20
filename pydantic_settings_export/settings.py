from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from dotenv import load_dotenv
from pydantic import Field, ImportString, TypeAdapter, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings_export.constants import StrAsPath
from pydantic_settings_export.sources import SourcesMixin
from pydantic_settings_export.utils import get_config_from_pyproject_toml

if TYPE_CHECKING:
    from pydantic_settings_export.generators.abstract import AbstractGenerator  # noqa: F401

__all__ = (
    "MarkdownSettings",
    "DotEnvSettings",
    "RelativeToSettings",
    "Settings",
)


def import_settings_from_string(value: str) -> BaseSettings:
    """Import the settings from the string."""
    obj = TypeAdapter(ImportString).validate_python(value)
    if isinstance(obj, type) and not issubclass(obj, BaseSettings) and not isinstance(obj, BaseSettings):
        raise ValueError(f"The {obj!r} is not a settings class.")
    return obj


class RelativeToSettings(BaseSettings):
    """Settings for the relative directory."""

    model_config = SettingsConfigDict(
        title="Relative Directory Settings",
        env_prefix="RELATIVE_TO_",
    )

    replace_abs_paths: bool = Field(True, description="Replace absolute paths with relative path to project root.")
    alias: str = Field("<project_dir>", description="The alias for the relative directory.")


class MarkdownSettings(BaseSettings):
    """Settings for the Markdown file."""

    model_config = SettingsConfigDict(
        title="Configuration File Settings",
        env_prefix="CONFIG_FILE_",
    )

    enabled: bool = Field(True, description="Enable the configuration file generation.")
    name: str = Field("Configuration.md", description="The name of the configuration file.")

    save_dirs: list[StrAsPath] = Field(
        default_factory=list, description="The directories to save configuration files to."
    )

    def __bool__(self) -> bool:
        """Check if the configuration file is set."""
        return self.enabled and bool(self.save_dirs)


class DotEnvSettings(BaseSettings):
    """Settings for the .env file."""

    model_config = SettingsConfigDict(
        title=".env File Settings",
        env_prefix="DOTENV_",
    )

    name: str = Field(".env.example", description="The name of the .env file.")


class Settings(BaseSettings, SourcesMixin):
    """Global settings for pydantic_settings_export."""

    model_config = SettingsConfigDict(
        title="Global Settings",
        env_prefix="PYDANTIC_SETTINGS_EXPORT_",
        plugin_settings={
            "pyproject_toml": {
                "package_name": "pydantic_settings_export",
            }
        },
    )

    default_settings: list[str] = Field(
        default_factory=list,
        description="The default settings to use. The settings are applied in the order they are listed.",
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
    markdown: MarkdownSettings = Field(
        default_factory=MarkdownSettings,
        description="The configuration of markdown file settings.",
    )
    dotenv: DotEnvSettings = Field(
        default_factory=DotEnvSettings,
        description="The .env file settings.",
    )

    respect_exclude: bool = Field(
        True,
        description="Respect the exclude attribute in the fields.",
    )

    generators: list = Field(  # type: list[type[AbstractGenerator]]
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

    @classmethod
    def from_pyproject(cls, base_path: Path | None = None) -> Self:
        """Load settings from the pyproject.toml file.

        :param base_path: The base path to search for the pyproject.toml file or this file itself.
        The current working directory is used by default.
        :return: The loaded settings.
        """
        config = get_config_from_pyproject_toml(cls, base_path)
        config.setdefault("project_dir", str(base_path.parent))
        return cls(**config)
