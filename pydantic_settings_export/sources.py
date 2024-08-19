import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic_settings import BaseSettings
from pydantic_settings.sources import (
    DEFAULT_PATH,
    ConfigFileSourceMixin,
    InitSettingsSource,
    PathType,
    PydanticBaseSettingsSource,
    import_toml,
)

from pydantic_settings_export.utils import get_tool_name

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        tomllib = None
    import tomli
    from pydantic_settings.main import BaseSettings
else:
    tomllib = None
    tomli = None


__all__ = (
    "PyprojectTomlConfigSettingsSource",
    "SourcesMixin",
)


class PyprojectTomlConfigSettingsSource(InitSettingsSource, ConfigFileSourceMixin):
    """The pyproject.toml config file settings source."""

    # noinspection PyDefaultArgument
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        toml_file: PathType | None = DEFAULT_PATH,
        pyproject_tool_name: str | None = None,
    ):
        self.toml_file_path = toml_file if toml_file != DEFAULT_PATH else settings_cls.model_config.get("toml_file")
        self.pyproject_tool_name = pyproject_tool_name
        self.toml_data = self._read_files(self.toml_file_path)
        if self.pyproject_tool_name:
            self.toml_data = self.toml_data.get("tool", {}).get(self.pyproject_tool_name, {})
        super().__init__(settings_cls, self.toml_data)

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        import_toml()
        with open(file_path, mode="rb") as toml_file:
            if sys.version_info < (3, 11):
                return tomli.load(toml_file)  # type: ignore
            return tomllib.load(toml_file)  # type: ignore


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
        return (
            init_settings,
            PyprojectTomlConfigSettingsSource(
                settings_cls,
                toml_file=settings_cls.model_config.get("toml_file"),
                pyproject_tool_name=get_tool_name(settings_cls),
            ),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
