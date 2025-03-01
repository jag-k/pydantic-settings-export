from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, TypeVar, final

from pydantic import BaseModel, Field, create_model

from pydantic_settings_export.settings import PSESettings

if TYPE_CHECKING:
    from pydantic_settings_export.models import SettingsInfoModel

else:
    SettingsInfoModel: TypeAlias = BaseModel


__all__ = ("AbstractGenerator",)


class BaseGeneratorSettings(BaseModel):
    """Base model config for the generator."""

    enabled: bool = Field(
        True,
        description="Enable the configuration for file generation.",
        exclude=True,
    )

    paths: list[Path] = Field(
        default_factory=lambda: [],
        description="The paths to the resulting files.",
    )

    def __bool__(self) -> bool:
        """Check if the configuration file is set."""
        return self.enabled and bool(self.paths)


C = TypeVar("C", bound=BaseGeneratorSettings)


class AbstractGenerator(ABC):
    """The abstract class for the configuration file generator."""

    config: type[C]
    name: ClassVar[str]

    ALL_GENERATORS: ClassVar[list[type["AbstractGenerator"]]] = []

    def __init__(self, settings: PSESettings, generator_config: C | None = None) -> None:
        """Initialize the AbstractGenerator.

        :param settings: The settings for the generator.
        """
        self.settings = settings
        self.generator_config: C = generator_config if generator_config else self.config()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize the subclass."""
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "name", None):
            raise ValueError("Generator must have a name")
        if not getattr(cls, "config", None) or not isinstance(cls.config, type):
            raise ValueError("Generator must have a config")
        if cls.name in AbstractGenerator.ALL_GENERATORS:
            raise ValueError(f"Generator {cls.name} already exists")
        cls.config.__doc__ += f"\n\nGenerator name: `{cls.name}`."

        AbstractGenerator.ALL_GENERATORS.append(cls)

    @abstractmethod
    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:
        """Generate the configuration file content.

        :param settings_info: The settings class to generate documentation for.
        :param level: The level of nesting. Used for indentation.
        :return: The generated documentation.
        """
        raise NotImplementedError

    def generate(self, *settings_infos: SettingsInfoModel) -> str:
        """Generate the configuration file content.

        :param settings_infos: The settings info classes to generate documentation for.
        :return: The generated documentation.
        """
        return "\n\n".join(self.generate_single(s).strip() for s in settings_infos).strip() + "\n"

    def file_paths(self) -> list[Path]:
        """Get the list of files which need to create/update.

        :return: The list of files to write.
        This is used to determine if the files need to be written.
        """
        if not self.generator_config:
            return []
        file_paths = []
        for p in self.generator_config.paths:
            if p.is_absolute():
                file_paths.append(p)
                continue
            file_paths.append(self.settings.root_dir / p)
        return file_paths

    def run(self, *settings_info: SettingsInfoModel) -> list[Path]:
        """Run the generator.

        :param settings_info: The settings info to generate documentation for.
        :return: The list of file paths is written to.
        """
        result = self.generate(*settings_info)
        file_paths = self.file_paths()
        updated_files: list[Path] = []
        for path in file_paths:
            if path.is_file() and path.read_text() == result:
                # No need to update the file
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result)
            updated_files.append(path)
        return updated_files

    @staticmethod
    @final
    def generators() -> dict[str, type["AbstractGenerator"]]:
        """Get all generators.

        :return: The generators (key: generator name, value: generator class).
        """
        return {g.name: g for g in AbstractGenerator.ALL_GENERATORS}

    @staticmethod
    @final
    def create_generator_config_model(multiple_for_single: bool = False) -> type[BaseModel]:
        """Create the generator config model.

        This model contains all the generators' configuration information.
        The attribute is the generator name, the value is generator config.

        :param multiple_for_single: Whether to create a list of the generator config for the single generator.
        :return: The generator model.
        """

        def _make_arg(generator: type[AbstractGenerator]) -> tuple[Any, Any]:
            if multiple_for_single:
                return list[generator.config], Field(default_factory=lambda: [generator.config()])
            return generator.config, Field(default_factory=generator.config)

        fields = {name: _make_arg(generator) for name, generator in AbstractGenerator.generators().items()}
        return create_model(
            "Generators",
            **fields,
            __base__=BaseModel,
            __doc__="The configuration of generators.",
        )
