from pathlib import Path

from pydantic_settings_export.models import SettingsInfoModel

from .abstract import AbstractGenerator

__all__ = ("DotEnvGenerator",)


class DotEnvGenerator(AbstractGenerator):
    """The .env example generator."""

    def write_to_files(self, generated_result: str) -> list[Path]:
        """Write the generated content to files.

        :param generated_result: The result is to write to files.
        :return: The list of file paths is written to.
        """
        file_path = self.settings.root_dir / self.settings.dotenv.name
        file_path.write_text(generated_result)
        return [file_path]

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
            field_string = f"{field_name}={field.default}\n"

            if not field.is_required:
                field_string = f"# {field_string}"
            result += field_string

        result = result.strip() + "\n\n"

        for child in settings_info.child_settings:
            result += self.generate_single(child)

        return result
