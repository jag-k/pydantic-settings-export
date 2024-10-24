from abc import ABC, abstractmethod
from pathlib import Path

from pydantic_settings_export.models import SettingsInfoModel
from pydantic_settings_export.settings import Settings

__all__ = ("AbstractGenerator",)


class AbstractGenerator(ABC):
    """The abstract class for the configuration file generator."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the AbstractGenerator.

        :param settings: The settings for the generator.
        """
        self.settings = settings

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
        """Get the list of files, which need to create/update.

        :return: The list of files to write.
        This is used to determine if the files need to be written.
        """

    @classmethod
    def run(cls, settings: Settings, settings_info: SettingsInfoModel) -> list[Path]:
        """Run the generator.

        :param settings: The settings for the generator.
        :param settings_info: The settings info to generate documentation for.
        :return: The list of file paths is written to.
        """
        generator = cls(settings)
        result = generator.generate(settings_info)
        file_paths = generator.file_paths()
        updated_files: list[Path] = []
        for path in file_paths:
            if path.is_file() and path.read_text() == result:
                # No need to update the file
                continue

            path.write_text(result)
            updated_files.append(path)
        return updated_files
