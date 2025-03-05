from pydantic import ConfigDict

from pydantic_settings_export.models import SettingsInfoModel

from .abstract import AbstractGenerator, BaseGeneratorSettings

__all__ = ("SimpleGenerator",)

INDENT_CHAR = "  "
HEADER_UNDERLINE_CHAR = "="


class SimpleSettings(BaseGeneratorSettings):
    """Settings for the simple generator."""

    model_config = ConfigDict(title="Generator: Simple configuration")


class SimpleGenerator(AbstractGenerator[SimpleSettings]):
    """The Simple generator."""

    name = "simple"
    config = SimpleSettings

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:  # noqa: C901
        """Generate simple text documentation for settings.

        Produces a clean, readable text format with:
        - Section headers with underlines
        - Field descriptions and types
        - Default values and examples
        - Proper spacing and indentation

        :param settings_info: Settings model to document.
        :param level: Nesting level for indentation.
        :return: Formatted text documentation with consistent styling.
        """
        indent = INDENT_CHAR * (level - 1)
        docs = settings_info.docs.rstrip()

        # Generate section header
        name = settings_info.name
        header_line = HEADER_UNDERLINE_CHAR * len(name)
        result = f"{indent}{name}\n{indent}{header_line}\n"

        # Add environment prefix if present
        if settings_info.env_prefix:
            result += f"\n{indent}Environment Prefix: {settings_info.env_prefix}\n"

        # Add documentation if present
        if docs:
            result += f"\n{indent}{docs}\n"

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
