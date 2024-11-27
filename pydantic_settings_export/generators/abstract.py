from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, TypeVar, final

from pydantic import BaseModel, Field, create_model

if TYPE_CHECKING:
    from pydantic_settings_export.models import SettingsInfoModel
    from pydantic_settings_export.settings import PSESettings

else:
    SettingsInfoModel: TypeAlias = BaseModel
    PSESettings: TypeAlias = BaseModel


__all__ = ("AbstractGenerator",)

C = TypeVar("C", bound=BaseModel)


class AbstractGenerator(ABC):
    """The abstract class for the configuration file generator."""

    config: type[C]
    name: ClassVar[str]

    ALL_GENERATORS: ClassVar[list[type["AbstractGenerator"]]] = []

    def __init__(self, settings: PSESettings) -> None:
        """Initialize the AbstractGenerator.

        :param settings: The settings for the generator.
        """
        self.settings = settings
        self.generator_config: C = getattr(settings.generators, self.name)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize the subclass."""
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "name", None):
            raise ValueError("Generator must have a name")
        if not getattr(cls, "config", None) or not isinstance(cls.config, type):
            raise ValueError("Generator must have a config")
        if cls.name in AbstractGenerator.ALL_GENERATORS:
            raise ValueError(f"Generator {cls.name} already exists")

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

    @abstractmethod
    def file_paths(self) -> list[Path]:
        """Get the list of files which need to create/update.

        :return: The list of files to write.
        This is used to determine if the files need to be written.
        """
        raise NotImplementedError

    @classmethod
    def run(cls, settings: PSESettings, *settings_info: SettingsInfoModel) -> list[Path]:
        """Run the generator.

        :param settings: The settings for the generator.
        :param settings_info: The settings info to generate documentation for.
        :return: The list of file paths is written to.
        """
        generator = cls(settings)
        result = generator.generate(*settings_info)
        file_paths = generator.file_paths()
        updated_files: list[Path] = []
        for path in file_paths:
            if path.is_file() and path.read_text() == result:
                # No need to update the file
                continue

            path.write_text(result)
            updated_files.append(path)
        return updated_files

    @staticmethod
    @final
    def create_generator_config_model() -> type[BaseModel]:
        """Create the generator config model.

        This model contains all the generators' configuration information.
        The attribute is the generator name, the value is generator config.
        :return: The generator model.
        """
        return create_model(
            "Generators",
            **{
                generator.name: (generator.config, Field(default_factory=generator.config))
                for generator in AbstractGenerator.ALL_GENERATORS
            },
            __base__=BaseModel,
            __doc__="The configuration of generators.",
        )
