from pydantic import ConfigDict

from pydantic_settings_export.models import SettingsInfoModel

from .abstract import AbstractGenerator, BaseGeneratorSettings

__all__ = ("SimpleGenerator",)


class SimpleSettings(BaseGeneratorSettings):
    """Settings for the simple generator."""

    model_config = ConfigDict(title="Generator: Simple configuration")


class SimpleGenerator(AbstractGenerator):
    """The Simple generator."""

    name = "simple"
    config = SimpleSettings
    generator_config: SimpleSettings

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:  # noqa: C901
        """Generate Markdown documentation for a pydantic settings class.

        :param settings_info: The settings class to generate documentation for.
        :param level: The level of nesting. Used for indentation.
        :return: The generated documentation.
        """
        docs = settings_info.docs.rstrip()

        # Generate header
        name = settings_info.name
        hash_len = len(name)
        result = f"{name}\n{'#' * hash_len}\n"
        if docs:
            result += f"\n{docs}\n"

        for field in settings_info.fields:
            field_name = f"`{field.full_name}`"
            if field.deprecated:
                field_name += " (⚠️ Deprecated)"

            h = f"{field_name}: {field.types}"
            result += f"\n{h}\n{'-' * len(h)}\n"

            if field.description:
                result += f"\n{field.description}\n\n"

            if field.default:
                result += f"Default: {field.default}\n"

            if field.has_examples():
                result += f"Examples: {', '.join(field.examples)}\n"

        return result
