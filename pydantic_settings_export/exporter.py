import warnings
from pathlib import Path

from pydantic_settings import BaseSettings

from pydantic_settings_export.generators.abstract import AbstractGenerator
from pydantic_settings_export.models import SettingsInfoModel
from pydantic_settings_export.settings import PSESettings
from pydantic_settings_export.utils import import_settings_from_strings

__all__ = ("Exporter",)


class Exporter:
    """The exporter for pydantic settings."""

    def __init__(
        self,
        settings: PSESettings | None = None,
        generators: list[AbstractGenerator] | None = None,
    ) -> None:
        self.settings: PSESettings = settings or PSESettings()
        if generators is None:
            generators = []
            for generator_class in AbstractGenerator.ALL_GENERATORS:
                try:
                    generators.append(generator_class(self.settings))
                except Exception as e:
                    warnings.warn(f"Failed to initialize generator {generator_class.__name__}: {e}", stacklevel=2)
        self.generators: list[AbstractGenerator] = generators

    def run_all(self, *settings: BaseSettings | type[BaseSettings]) -> list[Path]:
        """Run all generators for the given settings.

        Each generator config can override or extend the global *settings* via its
        ``settings`` (full override) or ``extend_settings`` (appended) fields.
        All unique settings objects are parsed into
        :class:`~pydantic_settings_export.models.SettingsInfoModel` exactly once.

        :param settings: The default settings to generate documentation for.
        :return: The paths to generated documentation.
        """
        cache: dict[int, SettingsInfoModel] = {}

        def _parse(s: BaseSettings | type[BaseSettings]) -> SettingsInfoModel:
            key = id(s)
            if key not in cache:
                cache[key] = SettingsInfoModel.from_settings_model(s, self.settings)
            return cache[key]

        def _import_all(strings: list[str]) -> list[BaseSettings | type[BaseSettings]]:
            return import_settings_from_strings(
                strings,
                project_dir=self.settings.project_dir,
                continue_on_error=True,
            )

        default_infos = [_parse(s) for s in settings]
        paths: list[Path] = []

        for generator in self.generators:
            try:
                config = generator.generator_config
                if config.settings:
                    gen_infos = [_parse(s) for s in _import_all(config.settings)]
                elif config.extend_settings:
                    gen_infos = default_infos + [_parse(s) for s in _import_all(config.extend_settings)]
                else:
                    gen_infos = default_infos

                paths.extend(generator.run(*gen_infos))
            except Exception as e:
                warnings.warn(f"Generator {generator.__class__.__name__} failed: {e}", stacklevel=2)

        return paths
