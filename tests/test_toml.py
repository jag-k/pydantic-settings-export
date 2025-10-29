"""Tests for TOML generator."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import Field
from pydantic_settings import BaseSettings

from pydantic_settings_export import SettingsInfoModel, TomlGenerator, TomlSettings


@pytest.fixture
def simple_settings() -> type[BaseSettings]:
    """Minimal settings with one field."""

    class Settings(BaseSettings):
        """Test settings."""

        field: str = Field(default="value", description="Field description")

    return Settings


@pytest.fixture
def mixed_settings() -> type[BaseSettings]:
    """Settings with required and optional fields."""

    class Settings(BaseSettings):
        """Mixed settings."""

        required: str = Field(description="Required field")
        optional: str = Field(default="value", description="Optional field")

    return Settings


@pytest.fixture
def nested_settings() -> type[BaseSettings]:
    """Settings with child settings."""

    class Database(BaseSettings):
        """Database config."""

        host: str = Field(default="localhost", description="Database host")
        port: int = Field(description="Required port")

    class Settings(BaseSettings):
        """Main settings."""

        database: Database = Field(default_factory=Database)

    return Settings


@pytest.fixture
def full_settings() -> type[BaseSettings]:
    """Comprehensive settings for integration tests."""

    class Database(BaseSettings):
        """Database configuration."""

        host: str = Field(default="localhost", description="Database host")
        port: int = Field(default=5432, description="Database port")
        username: str = Field(description="Database username")

    class App(BaseSettings):
        """Application settings."""

        debug: bool = Field(default=False, description="Debug mode")
        api_key: str = Field(description="API key")
        database: Database = Field(default_factory=Database)

    return App


def test_toml_generator_with_comment_defaults(simple_settings: Any) -> None:
    """Test TOML generation with comment_defaults option."""
    generator = TomlGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    expected = """\
# Settings
# Test settings.

# field: string
# Field description
# Default: "value"
# field = "value"
"""
    assert result == expected


def test_toml_generator_without_comment_defaults(simple_settings: Any) -> None:
    """Test TOML generation without commenting defaults."""
    generator = TomlGenerator(generator_config=TomlSettings(comment_defaults=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    expected = """\
# Settings
# Test settings.

# field: string
# Field description
# Default: "value"
field = "value"
"""
    assert result == expected


def test_toml_generator_with_none_and_comment_defaults_false() -> None:
    """Test that None values are always commented, even with comment_defaults=False."""

    class Settings(BaseSettings):
        nullable: str | None = None
        regular: str = "value"

    generator = TomlGenerator(generator_config=TomlSettings(comment_defaults=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# nullable: string | NoneType
# Default: null
# nullable =

# regular: string
# Default: "value"
regular = "value"
"""
    assert result == expected


def test_toml_generator_with_long_descriptions() -> None:
    """Test that long descriptions are wrapped at 80 columns."""

    class Settings(BaseSettings):
        field: str = Field(
            default="value",
            description=(
                "This is a very long field description that should be wrapped "
                "automatically when it exceeds the 80 column limit"
            ),
        )

    generator = TomlGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# field: string
# This is a very long field description that should be wrapped automatically when
# it exceeds the 80 column limit
# Default: "value"
# field = "value"
"""
    assert result == expected


def test_toml_generator_with_description_transformer() -> None:
    """Test description formatter callback."""

    def uppercase(desc: str) -> str:
        return desc.upper()

    class Settings(BaseSettings):
        field: str = Field(default="value", description="lowercase text")

    generator = TomlGenerator(generator_config=TomlSettings(description_formatter=uppercase))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# field: string
# LOWERCASE TEXT
# Default: "value"
# field = "value"
"""
    assert result == expected


def test_toml_generator_without_formatters(simple_settings: Any) -> None:
    """Test TOML generation without any formatters."""
    generator = TomlGenerator(
        generator_config=TomlSettings(
            header_formatter=None,
            type_formatter=None,
            description_formatter=None,
            default_formatter=None,
        )
    )
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    expected = """\
# field = "value"
"""
    assert result == expected


def test_toml_generator_mode_only_optional(mixed_settings: Any) -> None:
    """Test only-optional mode filters out required fields."""
    generator = TomlGenerator(generator_config=TomlSettings(mode="only-optional"))
    result = generator.generate(SettingsInfoModel.from_settings_model(mixed_settings))

    expected = """\
# Settings
# Mixed settings.

# optional: string
# Optional field
# Default: "value"
# optional = "value"
"""
    assert result == expected


def test_toml_generator_mode_only_required(mixed_settings: Any) -> None:
    """Test only-required mode filters out optional fields."""
    generator = TomlGenerator(generator_config=TomlSettings(mode="only-required"))
    result = generator.generate(SettingsInfoModel.from_settings_model(mixed_settings))

    expected = """\
# Settings
# Mixed settings.

# required: string (REQUIRED)
# Required field
# required =
"""
    assert result == expected


def test_toml_generator_mode_filter_in_nested_sections(nested_settings: Any) -> None:
    """Test mode filtering works in nested settings with sections."""
    generator = TomlGenerator(generator_config=TomlSettings(mode="only-required"))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    expected = """\
# Settings
# Main settings.

# Database
# Database config.

[database]
# port: integer (REQUIRED)
# Required port
# port =
"""
    assert result == expected


def test_toml_generator_with_dotted_keys(nested_settings: Any) -> None:
    """Test section_depth=0 generates dotted keys instead of sections."""
    generator = TomlGenerator(generator_config=TomlSettings(section_depth=0))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    expected = """\
# Settings
# Main settings.

# Database
# Database config.

# database.host: string
# Database host
# Default: "localhost"
# database.host = "localhost"

# database.port: integer (REQUIRED)
# Required port
# database.port =
"""
    assert result == expected


def test_toml_generator_with_examples() -> None:
    """Test examples formatter."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = TomlGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# field: string
# Default: "default"
# Examples: "ex1", "ex2"
# field = "default"
"""
    assert result == expected


def test_toml_generator_with_alias() -> None:
    """Test field alias is used as TOML key."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="external_name")

    generator = TomlGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# internal_name: string
# Default: "value"
# external_name = "value"
"""
    assert result == expected


def test_toml_generator_with_deprecated() -> None:
    """Test deprecated field is marked."""

    class Settings(BaseSettings):
        field: str = Field(default="value", deprecated=True)

    generator = TomlGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# field: string (DEPRECATED)
# Default: "value"
# field = "value"
"""
    assert result == expected


def test_toml_generator_with_types() -> None:
    """Test various Python types."""

    class Settings(BaseSettings):
        flag: bool = True
        count: int = 42
        items: list[str] = ["a", "b"]

    generator = TomlGenerator(generator_config=TomlSettings(comment_defaults=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# flag: boolean
# Default: true
flag = true

# count: integer
# Default: 42
count = 42

# items: array
# Default: ["a","b"]
items = ["a", "b"]
"""
    assert result == expected


def test_toml_generator_with_path() -> None:
    """Test Path type serialization."""

    class Settings(BaseSettings):
        path: Path = Path("/tmp/file.txt")  # noqa: S108

    generator = TomlGenerator(generator_config=TomlSettings(comment_defaults=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Settings

# path: Path
# Default: "/tmp/file.txt"
path = "/tmp/file.txt"
"""
    assert result == expected


def test_toml_generator_with_nested_union_types(full_settings: Any) -> None:
    """Test nested settings with Union types are recognized as child settings."""
    generator = TomlGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(full_settings))

    expected = """\
# App
# Application settings.

# debug: boolean
# Debug mode
# Default: false
# debug = false

# api_key: string (REQUIRED)
# API key
# api_key =

# Database
# Database configuration.

[database]
# host: string
# Database host
# Default: "localhost"
# host = "localhost"

# port: integer
# Database port
# Default: 5432
# port = 5432

# username: string (REQUIRED)
# Database username
# username =
"""
    assert result == expected


def test_toml_generator_dotted_keys_without_comment_defaults(nested_settings: Any) -> None:
    """Test dotted keys with comment_defaults=False to cover uncommented field path."""
    generator = TomlGenerator(generator_config=TomlSettings(section_depth=0, comment_defaults=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    expected = """\
# Settings
# Main settings.

# Database
# Database config.

# database.host: string
# Database host
# Default: "localhost"
database.host = "localhost"

# database.port: integer (REQUIRED)
# Required port
# database.port =
"""
    assert result == expected


def test_toml_generator_dotted_keys_with_mode_filter(nested_settings: Any) -> None:
    """Test dotted keys with mode filtering to cover continue path in _add_child_as_dotted_keys."""
    generator = TomlGenerator(generator_config=TomlSettings(section_depth=0, mode="only-required"))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    expected = """\
# Settings
# Main settings.

# Database
# Database config.

# database.port: integer (REQUIRED)
# Required port
# database.port =
"""
    assert result == expected


def test_toml_generator_with_section_depth() -> None:
    """Test section_depth limits nesting level for sections."""

    class SMTP(BaseSettings):
        host: str = "localhost"

    class Core(BaseSettings):
        name: str = "app"
        smtp: SMTP = Field(default_factory=SMTP)

    class App(BaseSettings):
        core: Core = Field(default_factory=Core)

    settings_info = SettingsInfoModel.from_settings_model(App)

    generator = TomlGenerator(generator_config=TomlSettings(section_depth=1, comment_defaults=False))
    result = generator.generate(settings_info)

    expected = """\
# App

# Core

[core]
# name: string
# Default: "app"
name = "app"

# SMTP

# smtp.host: string
# Default: "localhost"
smtp.host = "localhost"
"""
    assert result == expected

    generator = TomlGenerator(generator_config=TomlSettings(section_depth=2, comment_defaults=False))
    result = generator.generate(settings_info)

    expected = """\
# App

# Core

[core]
# name: string
# Default: "app"
name = "app"

# SMTP

[core.smtp]
# host: string
# Default: "localhost"
host = "localhost"
"""
    assert result == expected


def test_toml_generator_with_deeply_nested_child_settings() -> None:
    """Test deeply nested child settings create proper section hierarchy."""

    class SMTP(BaseSettings):
        host: str = "localhost"

    class Core(BaseSettings):
        name: str = "app"
        smtp: SMTP = Field(default_factory=SMTP)

    class App(BaseSettings):
        core: Core = Field(default_factory=Core)

    generator = TomlGenerator(generator_config=TomlSettings(comment_defaults=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(App))

    expected = """\
# App

# Core

[core]
# name: string
# Default: "app"
name = "app"

# SMTP

[core.smtp]
# host: string
# Default: "localhost"
host = "localhost"
"""
    assert result == expected


def test_toml_generator_creates_intermediate_tables() -> None:
    """Test that intermediate tables are created when skipping nesting levels."""

    class Level4(BaseSettings):
        value: str = "deep"

    class Level3(BaseSettings):
        level4: Level4 = Field(default_factory=Level4)

    class Level2(BaseSettings):
        level3: Level3 = Field(default_factory=Level3)

    class Level1(BaseSettings):
        name: str = "root"
        level2: Level2 = Field(default_factory=Level2)

    class Root(BaseSettings):
        level1: Level1 = Field(default_factory=Level1)

    generator = TomlGenerator(generator_config=TomlSettings(comment_defaults=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Root))

    expected = """\
# Root

# Level1

[level1]
# name: string
# Default: "root"
name = "root"

# Level2

[level1.level2]
# Level3

[level1.level2.level3]
# Level4

[level1.level2.level3.level4]
# value: string
# Default: "deep"
value = "deep"
"""
    assert result == expected


def test_toml_generator_with_prefix(simple_settings: Any) -> None:
    """Test TOML generation with prefix option."""
    generator = TomlGenerator(generator_config=TomlSettings(prefix="tool.myapp"))
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    expected = """\
# Settings
# Test settings.

[tool.myapp]
# field: string
# Field description
# Default: "value"
# field = "value"
"""
    assert result == expected
