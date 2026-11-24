import warnings
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TypeVar

from pydantic import ValidationError
from pydantic_settings import BaseSettings

from pydantic_settings_export.exceptions import ExportWarning
from pydantic_settings_export.generators.abstract import AbstractGenerator, FileChange
from pydantic_settings_export.models import SettingsInfoModel
from pydantic_settings_export.settings import PSESettings
from pydantic_settings_export.utils import import_settings_from_string

__all__ = ("Exporter",)

T = TypeVar("T")


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

    def _for_each_generator(
        self,
        settings: tuple[BaseSettings | type[BaseSettings], ...],
        action: Callable[[AbstractGenerator, list[SettingsInfoModel]], list[T]],
    ) -> Iterator[T]:
        """Call *action* for each generator with its resolved settings info and yield the results.

        :param settings: The default settings.
        :param action: The callable to run for each generator.
        :return: An iterator over all items returned by *action*.
        """
        cache: dict[int, SettingsInfoModel] = {}

        def _parse(s: BaseSettings | type[BaseSettings]) -> SettingsInfoModel:
            key = id(s)
            if key not in cache:
                cache[key] = SettingsInfoModel.from_settings_model(s, self.settings)
            return cache[key]

        def _import_all(strings: list[str]) -> list[BaseSettings | type[BaseSettings]]:
            result: list[BaseSettings | type[BaseSettings]] = []
            for string in strings:
                try:
                    result.extend(import_settings_from_string(string))
                except (ImportError, ValueError, ValidationError) as e:
                    warnings.warn(f"Failed to import settings {string!r}: {e}", ExportWarning, stacklevel=4)
            return result

        default_infos = [_parse(s) for s in settings]

        for generator in self.generators:
            try:
                config = generator.generator_config
                if config.settings:
                    gen_infos = [_parse(s) for s in _import_all(config.settings)]
                elif config.extend_settings:
                    gen_infos = default_infos + [_parse(s) for s in _import_all(config.extend_settings)]
                else:
                    gen_infos = default_infos

                yield from action(generator, gen_infos)
            except Exception as e:
                warnings.warn(f"Generator {generator.__class__.__name__} failed: {e}", ExportWarning, stacklevel=3)

    def run_all(self, *settings: BaseSettings | type[BaseSettings]) -> list[Path]:
        """Run all generators for the given settings.

        Each generator config can override or extend the global *settings* via its
        ``settings`` (full override) or ``extend_settings`` (appended) fields.
        All unique settings objects are parsed into
        :class:`~pydantic_settings_export.models.SettingsInfoModel` exactly once.

        :param settings: The default settings to generate documentation for.
        :return: The paths to generated documentation.
        """
        return list(self._for_each_generator(settings, lambda generator, infos: generator.run(*infos)))

    def changes_all(self, *settings: BaseSettings | type[BaseSettings]) -> list[FileChange]:
        """Compute the changes of all generators for the given settings without writing any files.

        Uses the same settings resolution as :meth:`run_all`.

        :param settings: The default settings to generate documentation for.
        :return: The changes for files that are missing or out of date.
        """
        return list(self._for_each_generator(settings, lambda generator, infos: generator.changes(*infos)))
