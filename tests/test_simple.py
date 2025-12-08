"""Tests for Simple generator."""

from pydantic import Field
from pydantic_settings import BaseSettings

from pydantic_settings_export import SettingsInfoModel
from pydantic_settings_export.generators.simple import SimpleGenerator


def test_simple_generator_basic() -> None:
    """Test basic simple text generation."""

    class Settings(BaseSettings):
        """Test settings."""

        field: str = Field(default="value", description="Field description")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

Test settings.

`field`: ['string']
-------------------

Field description

Default: "value"
"""
    assert result == expected


def test_simple_generator_with_env_prefix() -> None:
    """Test simple text generation with environment prefix."""

    class Settings(BaseSettings):
        model_config = {"env_prefix": "APP_"}
        field: str = Field(default="value", description="A field")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

Environment Prefix: APP_

`field`: ['string']
-------------------

A field

Default: "value"
"""
    assert result == expected


def test_simple_generator_with_examples() -> None:
    """Test simple text generation with examples."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`field`: ['string']
-------------------
Default: "default"
Examples: "ex1", "ex2"
"""
    assert result == expected


def test_simple_generator_with_deprecated() -> None:
    """Test simple text generation with deprecated field."""

    class Settings(BaseSettings):
        field: str = Field(default="value", deprecated=True)

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`field` (⚠️ Deprecated): ['string']
-----------------------------------
Default: "value"
"""
    assert result == expected


def test_simple_generator_with_alias() -> None:
    """Test simple text generation uses alias as field name."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="external_name")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`external_name`: ['string']
---------------------------
Default: "value"
"""
    assert result == expected


def test_simple_generator_required_field() -> None:
    """Test simple text generation with required field."""

    class Settings(BaseSettings):
        required: str = Field(description="Required field")

    generator = SimpleGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
Settings
========

`required`: ['string']
----------------------

Required field
"""
    assert result == expected


def test_simple_generator_multiple_settings() -> None:
    """Test generating documentation for multiple settings."""

    class First(BaseSettings):
        a: str = "a"

    class Second(BaseSettings):
        b: str = "b"

    generator = SimpleGenerator()
    result = generator.generate(
        SettingsInfoModel.from_settings_model(First),
        SettingsInfoModel.from_settings_model(Second),
    )

    expected = """\
First
=====

`a`: ['string']
---------------
Default: "a"

Second
======

`b`: ['string']
---------------
Default: "b"
"""
    assert result == expected
