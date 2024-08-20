from pathlib import Path

from pydantic_settings import BaseSettings

from pydantic_settings_export.generators import AbstractGenerator
from pydantic_settings_export.models import SettingsInfoModel
from pydantic_settings_export.settings import Settings

__all__ = ("Exporter",)


class Exporter:
    """The exporter for pydantic settings."""

    def __init__(
        self,
        settings: Settings | None = None,
        generators: list[type[AbstractGenerator]] | None = None,
    ) -> None:
        self.settings: Settings = settings or Settings.from_pyproject()
        self.generators: list[type[AbstractGenerator]] = settings.generators if generators is None else generators

    def run_all(self, *settings: BaseSettings | type[BaseSettings]) -> list[Path]:
        """Run all generators for the given settings.

        :param settings: The settings to generate documentation for.
        :return: The paths to generated documentation.
        """
        settings_infos: list[SettingsInfoModel] = [
            SettingsInfoModel.from_settings_model(s, self.settings) for s in settings
        ]

        return [
            # Run all generators for each setting info
            path
            for generator in self.generators
            for path in generator.run(self.settings, *settings_infos)
        ]
