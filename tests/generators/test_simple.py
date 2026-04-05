from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings_export import SettingsInfoModel, SimpleGenerator

# =============================================================================
# Basic generation tests
# =============================================================================


def test_simple_with_env_prefix() -> None:
    """Test simple output shows env_prefix."""

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_")
        field: str = Field(default="value", description="A field")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

Environment Prefix: APP_

`field`: string
---------------

A field

Default: "value"
"""
    assert result == expected


def test_simple_without_env_prefix(simple_settings: type[BaseSettings]) -> None:
    """Test simple output without env_prefix."""
    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    assert "Environment Prefix:" not in result


# =============================================================================
# Field display tests
# =============================================================================


def test_simple_with_default(simple_settings: type[BaseSettings]) -> None:
    """Test default value is displayed."""
    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    expected = """\
Settings
========

Test settings.

`field`: string
---------------

Field description

Default: "value"
"""
    assert result == expected


def test_simple_without_default() -> None:
    """Test required field without a default."""

    class Settings(BaseSettings):
        field: str = Field(description="Required field")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Should not have a Default line for required field
    assert "Default:" not in result


def test_simple_with_deprecated() -> None:
    """Test deprecated field is marked."""

    class Settings(BaseSettings):
        field: str = Field(default="value", deprecated=True)

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`field` (⚠️ Deprecated): string
-------------------------------
Default: "value"
"""

    assert result == expected


def test_simple_with_examples() -> None:
    """Test examples are displayed."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`field`: string
---------------
Default: "default"
Examples: "ex1", "ex2"
"""
    assert result == expected


def test_simple_without_examples() -> None:
    """Test no examples line when examples equal default."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Should not have an Examples line when examples equal default
    assert "Examples:" not in result


def test_simple_with_description(simple_settings: type[BaseSettings]) -> None:
    """Test description is displayed."""
    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    expected = """\
Settings
========

Test settings.

`field`: string
---------------

Field description

Default: "value"
"""
    assert result == expected


def test_simple_without_description() -> None:
    """Test field without description."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Field should still be present
    expected = """\
Settings
========

`field`: string
---------------
Default: "value"
"""
    assert result == expected


# =============================================================================
# Type display tests
# =============================================================================


def test_simple_with_various_types() -> None:
    """Test various Python types are displayed."""

    class Settings(BaseSettings):
        str_field: str = Field(default="value")
        int_field: int = Field(default=42)
        bool_field: bool = Field(default=True)
        list_field: list[str] = Field(default_factory=list)

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`str_field`: string
-------------------
Default: "value"

`int_field`: integer
--------------------
Default: 42

`bool_field`: boolean
---------------------
Default: true

`list_field`: array
-------------------
Default: []
"""
    assert result == expected


# =============================================================================
# Alias tests
# =============================================================================


def test_simple_with_alias() -> None:
    """Test field alias is used as full_name."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="external_name")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`external_name`: string
-----------------------
Default: "value"
"""
    assert result == expected


# =============================================================================
# Documentation tests
# =============================================================================


def test_simple_with_docstring(simple_settings: type[BaseSettings]) -> None:
    """Test settings docstring is displayed."""
    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    expected = """\
Settings
========

Test settings.

`field`: string
---------------

Field description

Default: "value"
"""
    assert result == expected


def test_simple_without_docstring() -> None:
    """Test settings without docstring."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Should still have a header
    expected = """\
Settings
========

`field`: string
---------------
Default: "value"
"""
    assert result == expected


# =============================================================================
# Integration tests
# =============================================================================


def test_simple_full_settings(full_settings: type[BaseSettings]) -> None:
    """Test comprehensive simple output with all features."""
    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(full_settings))

    # Check main settings
    expected = """\
Settings
========

`log_level`: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
----------------------------------------------------------------

The log level to use

Default: "INFO"

`log_format`: string
--------------------

The log format to use

Default: "%(levelname)-8s | %(asctime)s | %(name)s | %(message)s"
"""
    assert result == expected


def test_simple_multiple_settings() -> None:
    """Test generating simple output for multiple settings classes."""

    class Settings1(BaseSettings):
        """First settings."""

        field1: str = Field(default="value1")

    class Settings2(BaseSettings):
        """Second settings."""

        field2: str = Field(default="value2")

    generator = SimpleGenerator()
    result = generator.generate(
        SettingsInfoModel.from_settings_model(Settings1),
        SettingsInfoModel.from_settings_model(Settings2),
    )

    expected = """\
Settings1
=========

First settings.

`field1`: string
----------------
Default: "value1"

Settings2
=========

Second settings.

`field2`: string
----------------
Default: "value2"
"""
    assert result == expected


def test_simple_multiple_fields() -> None:
    """Test settings with multiple fields."""

    class Settings(BaseSettings):
        field1: str = Field(default="value1", description="First field")
        field2: int = Field(default=42, description="Second field")
        field3: bool = Field(default=True, description="Third field")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`field1`: string
----------------

First field

Default: "value1"

`field2`: integer
-----------------

Second field

Default: 42

`field3`: boolean
-----------------

Third field

Default: true
"""
    assert result == expected
