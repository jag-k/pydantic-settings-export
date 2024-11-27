from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pydantic_settings_export.models import SettingsInfoModel

from .abstract import AbstractGenerator

__all__ = ("DotEnvGenerator",)


class DotEnvSettings(BaseModel):
    """Settings for the .env file."""

    model_config = ConfigDict(title="Generator: dotenv File Settings")

    enabled: bool = Field(True, description="Enable the dotenv file generation.")
    path: Path = Field(
        ".env.example",
        description="The name of the .env file.",
        examples=[
            ".env.example",
            ".env.sample",
        ],
    )


class DotEnvGenerator(AbstractGenerator):
    """The .env example generator."""

    name = __name__
    config = DotEnvSettings
    generator_config: DotEnvSettings

    def file_paths(self) -> list[Path]:
        """Get the list of files which need to create/update.

        :return: The list of files to write.
        This is used to determine if the files need to be written.
        """
        if not self.generator_config.enabled:
            return []
        return [self.settings.root_dir / self.generator_config.path]

    def generate_single(self, settings_info: SettingsInfoModel, level=1) -> str:
        """Generate a .env example for a pydantic settings class.

        :param level: The level of nesting. Used for indentation.
        :param settings_info: The settings class to generate a .env example for.
        :return: The generated .env example.
        """
        result = f"### {settings_info.name}\n\n"
        for field in settings_info.fields:
            field_name = f"{settings_info.env_prefix}{field.name.upper()}"
            if field.alias:
                field_name = field.alias.upper()

            field_string = f"{field_name}="
            if not field.is_required:
                field_string = f"# {field_name}={field.default}"

            if field.examples and field.examples != [field.default]:
                field_string += "  # " + (", ".join(field.examples))

            result += field_string + "\n"

        result = result.strip() + "\n\n"

        for child in settings_info.child_settings:
            result += self.generate_single(child)

        return result
