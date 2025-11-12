"""TOML generator for Pydantic settings export."""

import json
import re
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import ConfigDict, Field

from pydantic_settings_export.models import FieldInfoModel, SettingsInfoModel

from .abstract import AbstractGenerator, BaseGeneratorSettings

try:
    import tomlkit
    from tomlkit import comment, document, key, nl, table

    TOMLKIT_AVAILABLE = True
except ImportError:
    TOMLKIT_AVAILABLE = False

__all__ = ("TomlGenerator", "TomlSettings")


TomlMode = Literal["all", "only-optional", "only-required"]

TOML_MODE_MAP: dict[TomlMode, tuple[bool, bool]] = {
    "all": (True, True),
    "only-optional": (True, False),
    "only-required": (False, True),
}
TOML_MODE_MAP_DEFAULT = TOML_MODE_MAP["all"]


def default_header_formatter(name: str, docstring: str) -> str:
    """Format header with name and docstring.

    Args:
        name: The name of the settings class or section
        docstring: The documentation string

    Returns:
        Formatted header with name on first line, then wrapped docstring
    """
    lines = []
    if name:
        lines.append(name)
    if docstring:
        wrapped = textwrap.fill(docstring, width=80, break_long_words=False, break_on_hyphens=False)
        lines.append(wrapped)
    return "\n".join(lines)


def default_type_formatter(key_name: str, types: list[str], required: bool, deprecated: bool) -> str:
    """Format field type information."""
    type_str = " | ".join(types)
    required_marker = " (REQUIRED)" if required else ""
    deprecated_marker = " (DEPRECATED)" if deprecated else ""
    return f"{key_name}: {type_str}{required_marker}{deprecated_marker}"


def default_description_formatter(description: str) -> str:
    """Format field description with wrapping at 80 columns."""
    return textwrap.fill(description, width=80, break_long_words=False, break_on_hyphens=False)


def default_default_formatter(default: str) -> str:
    """Format default value with 'Default: ' prefix."""
    return f"Default: {default}"


def default_examples_formatter(examples: list[str]) -> str:
    """Format examples with 'Examples: ' prefix."""
    return f"Examples: {', '.join(examples)}"


class TomlSettings(BaseGeneratorSettings):
    """Settings for the TOML file generator."""

    model_config = ConfigDict(title="Generator: TOML Configuration File Settings", arbitrary_types_allowed=True)

    paths: list[Path] = Field(
        default_factory=list,
        description="The paths to the resulting TOML files.",
        examples=[
            Path("config.toml"),
            Path("config.example.toml"),
            Path("settings.toml"),
        ],
    )

    header_formatter: Callable[[str, str], str] | None = Field(
        default_header_formatter,
        description=(
            "Formatter for header with name and docstring. If None, header is not included. "
            "Takes name and docstring as parameters."
        ),
        exclude=True,
    )

    type_formatter: Callable[[str, list[str], bool, bool], str] | None = Field(
        default_type_formatter,
        description=(
            "Formatter for field type information. If None, types are not included. "
            "Takes key_name, types, required, deprecated as parameters."
        ),
        exclude=True,
    )

    description_formatter: Callable[[str], str] | None = Field(
        default_description_formatter,
        description="Formatter for field descriptions. If None, descriptions are not included.",
        exclude=True,
    )

    default_formatter: Callable[[str], str] | None = Field(
        default_default_formatter,
        description=(
            "Formatter for default values. If None, defaults are not included. "
            "Takes the default value as string parameter."
        ),
        exclude=True,
    )

    examples_formatter: Callable[[list[str]], str] | None = Field(
        default_examples_formatter,
        description=(
            "Formatter for examples. If None, examples are not included. Takes the list of examples as parameter."
        ),
        exclude=True,
    )

    comment_defaults: bool = Field(
        True,
        description="Comment out fields that have their default value (prefix with #).",
    )

    mode: TomlMode = Field(
        "all",
        description="The mode to export for the configuration variables.",
    )

    section_depth: int | None = Field(
        None,
        description=(
            "Maximum depth for using TOML sections for nested settings. "
            "If None, all nested settings use sections. "
            "If 0, all settings use dotted keys. "
            "If 1, only first-level child settings use sections. "
            "If 2, child settings and their children use sections, etc."
        ),
    )

    prefix: str | None = Field(
        None,
        description=(
            "Prefix for all TOML sections. "
            "All fields and sections will be nested under this prefix. "
            "The prefix does not count towards section_depth."
        ),
        examples=["tool.myapp", "app.config"],
    )


class TomlGenerator(AbstractGenerator[TomlSettings]):
    """The TOML configuration file generator."""

    name = "toml"
    config = TomlSettings

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not TOMLKIT_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "tomlkit is required for TOML generation. Install it with: pip install pydantic-settings-export[toml]"
            )

    # Utility methods (naming)

    def _make_toml_key(self, field: FieldInfoModel) -> str:
        """Get the TOML key name for a field."""
        if field.aliases:
            return field.aliases[0]
        return field.name

    def _should_include_field(self, field: FieldInfoModel) -> bool:
        """Determine if a field should be included based on the mode."""
        is_optional, is_required = TOML_MODE_MAP.get(self.generator_config.mode, TOML_MODE_MAP_DEFAULT)

        if field.is_required and not is_required:
            return False

        if not field.is_required and not is_optional:
            return False

        return True

    def _should_comment_field(self, field: FieldInfoModel) -> bool:
        """Determine if a field should be commented out.

        A field is commented out if:
        - It has a None default (always commented regardless of comment_defaults)
        - It is required (always commented to force user to provide a value)
        - comment_defaults is True and the field has a default value
        """
        if field.default == "null":
            return True

        if field.is_required:
            return True

        return self.generator_config.comment_defaults

    def _add_header_comments(self, container: Any, name: str, docstring: str) -> None:
        """Add header comments to a container."""
        if not self.generator_config.header_formatter:
            return

        formatted = self.generator_config.header_formatter(name, docstring)
        if formatted:
            for line in formatted.split("\n"):
                container.add(comment(line))
            container.add(nl())

    def _format_field_comment(self, field: FieldInfoModel, key_name: str | None = None) -> list[str]:
        """Generate comment lines for a field."""
        lines: list[str] = []

        if self.generator_config.type_formatter:
            display_name = key_name if key_name else field.name
            type_line = self.generator_config.type_formatter(
                display_name, field.types, field.is_required, field.deprecated
            )
            lines.append(type_line)

        if self.generator_config.description_formatter and field.description:
            formatted_desc = self.generator_config.description_formatter(field.description)
            lines.extend(formatted_desc.split("\n"))

        if self.generator_config.default_formatter and field.default and not field.is_required:
            default_line = self.generator_config.default_formatter(field.default)
            lines.append(default_line)

        if self.generator_config.examples_formatter and field.has_examples():
            examples_line = self.generator_config.examples_formatter(field.examples)
            lines.append(examples_line)

        return lines

    def _add_field_to_container(self, container: Any, field: FieldInfoModel, prefix: str = "") -> None:
        """Add a field to a TOML document or section container."""
        field_key = self._make_toml_key(field)
        full_key = f"{prefix}{field_key}" if prefix else field_key

        comment_lines = self._format_field_comment(field, key_name=full_key if prefix else None)
        for line in comment_lines:
            container.add(comment(line))

        if not self._should_comment_field(field):
            value = json.loads(cast(str, field.default))
            if prefix:
                key_parts = full_key.split(".")
                toml_key = key(key_parts)
                container.append(toml_key, value)
            else:
                container[full_key] = value

        elif field.is_required or field.default == "null":
            container.add(comment(f"{full_key} ="))

        else:
            value = json.loads(cast(str, field.default))
            value_str = tomlkit.dumps({field_key: value}).strip()
            if prefix:
                value_str = value_str.replace(f"{field_key} =", f"{full_key} =", 1)
            container.add(comment(value_str))

        container.add(nl())

    def _add_child_as_dotted_keys(self, container: Any, child: SettingsInfoModel, dotted_prefix: str) -> None:
        """Add a child settings using dotted key syntax."""
        self._add_header_comments(container, child.name, child.docs)

        for field in child.fields:
            if self._should_include_field(field):
                self._add_field_to_container(container, field, prefix=dotted_prefix)

    def _add_settings_to_container(
        self,
        container: Any,
        settings: SettingsInfoModel,
        current_depth: int = 0,
        section_path: str = "",
    ) -> None:
        """Add settings (fields + child settings) to a container (doc or section)."""
        for field in settings.fields:
            if self._should_include_field(field):
                self._add_field_to_container(container, field)

        for child in settings.child_settings:
            next_depth = current_depth + 1
            child_section_path = f"{section_path}.{child.field_name}" if section_path else child.field_name

            use_section = (
                self.generator_config.section_depth is None or next_depth <= self.generator_config.section_depth
            )

            if use_section:
                self._add_child_as_section(container, child, child.field_name, next_depth, child_section_path)
            else:
                dotted_prefix = f"{child.field_name}."
                self._add_child_as_dotted_keys(container, child, dotted_prefix)

    def _add_child_as_section(
        self,
        container: Any,
        child: SettingsInfoModel,
        section_name: str,
        current_depth: int = 1,
        section_path: str | None = None,
    ) -> None:
        """Add a child settings as a TOML section, including nested child settings recursively."""
        self._add_header_comments(container, child.name, child.docs)

        section = table()
        container[section_name] = section
        container.add(nl())

        self._add_settings_to_container(section, child, current_depth, section_path or section_name)

    def _create_prefix_section(self, doc: Any, prefix: str) -> Any:
        """Create nested sections for a dotted prefix (e.g., 'tool.myapp')."""
        parts = prefix.split(".")
        current_section = doc

        for part in parts:
            new_section = table()
            current_section[part] = new_section
            current_section = new_section

        doc.add(nl())
        return current_section

    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:
        """Generate TOML configuration for a pydantic settings class."""
        doc = document()

        self._add_header_comments(doc, settings_info.name or "", settings_info.docs)

        if self.generator_config.prefix:
            container = self._create_prefix_section(doc, self.generator_config.prefix)
            self._add_settings_to_container(
                container, settings_info, current_depth=0, section_path=self.generator_config.prefix
            )
        else:
            self._add_settings_to_container(doc, settings_info, current_depth=0)

        result = tomlkit.dumps(doc)

        result = re.sub(r"#\s+$", "#", result, flags=re.MULTILINE)
        result = re.sub(r"\n\n+", "\n\n", result, flags=re.MULTILINE)
        return result
