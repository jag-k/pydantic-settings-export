from collections.abc import Sequence
from os import PathLike
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic_settings.sources import PydanticBaseSettingsSource, PyprojectTomlConfigSettingsSource

__all__ = ("SourcesMixin",)


class SourcesMixin:
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
        toml_file: PathLike | Sequence[PathLike] | None = settings_cls.model_config.get("toml_file", None)
        base_settings = (init_settings, env_settings, dotenv_settings, file_secret_settings)
        if not toml_file:
            return base_settings

        if isinstance(toml_file, Sequence):
            toml_file = toml_file[0]

        if Path(toml_file).is_file():
            return (
                init_settings,
                PyprojectTomlConfigSettingsSource(settings_cls, toml_file=Path(toml_file)),
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )

        return base_settings
