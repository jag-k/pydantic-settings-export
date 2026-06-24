from collections.abc import Sequence
from pathlib import Path

from pydantic_settings import BaseSettings, TomlConfigSettingsSource
from pydantic_settings.sources import PathType, PydanticBaseSettingsSource, PyprojectTomlConfigSettingsSource

__all__ = ("TomlSettings",)


class TomlSettings(BaseSettings):
    """The sources mixin."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customise the sources.

        :param settings_cls: The settings class.
        :param init_settings: The init settings source.
        :param env_settings: The env settings source.
        :param dotenv_settings: The dotenv settings source.
        :param file_secret_settings: The file secret settings source.
        :return: The customised sources.
        """
        conf = settings_cls.model_config
        toml_file: PathType | None = conf.get("toml_file", None)

        if not toml_file:
            conf.pop("toml_file", None)
            conf.pop("pyproject_toml_table_header", None)
            conf.pop("pyproject_toml_depth", None)
            return init_settings, env_settings, dotenv_settings, file_secret_settings

        if isinstance(toml_file, Sequence):
            toml_file = toml_file[0]  # type: ignore[ty:invalid-assignment]

        toml_settings_source: type[TomlConfigSettingsSource] = TomlConfigSettingsSource

        # Check if the user wants to use pyproject.toml
        if conf.get("pyproject_toml_table_header") or conf.get("pyproject_toml_depth"):
            toml_settings_source = PyprojectTomlConfigSettingsSource

        return (
            init_settings,
            toml_settings_source(
                settings_cls,
                toml_file=Path(toml_file),  # type: ignore[ty:invalid-argument-type]
            ),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
