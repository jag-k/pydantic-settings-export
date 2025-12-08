"""Tests for DotEnv generator."""

import warnings

from pydantic import Field
from pydantic_settings import BaseSettings

from pydantic_settings_export import SettingsInfoModel
from pydantic_settings_export.generators.dotenv import DotEnvGenerator, DotEnvSettings


def test_dotenv_generator_basic() -> None:
    """Test basic dotenv generation."""

    class Settings(BaseSettings):
        """Test settings."""

        field: str = Field(default="value", description="Field description")

    generator = DotEnvGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

# FIELD="value"
"""
    assert result == expected


def test_dotenv_generator_without_split_by_group() -> None:
    """Test dotenv generation without group headers."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# FIELD="value"
"""
    assert result == expected


def test_dotenv_generator_required_field() -> None:
    """Test dotenv generation with required fields."""

    class Settings(BaseSettings):
        required: str = Field(description="Required field")
        optional: str = Field(default="value", description="Optional field")

    generator = DotEnvGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

REQUIRED=
# OPTIONAL="value"
"""
    assert result == expected


def test_dotenv_generator_mode_only_optional() -> None:
    """Test only-optional mode filters out required fields."""

    class Settings(BaseSettings):
        required: str = Field(description="Required field")
        optional: str = Field(default="value", description="Optional field")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(mode="only-optional"))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

# OPTIONAL="value"
"""
    assert result == expected


def test_dotenv_generator_mode_only_required() -> None:
    """Test only-required mode filters out optional fields."""

    class Settings(BaseSettings):
        required: str = Field(description="Required field")
        optional: str = Field(default="value", description="Optional field")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(mode="only-required"))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

REQUIRED=
OPTIONAL=
"""
    assert result == expected


def test_dotenv_generator_with_examples() -> None:
    """Test dotenv generation with examples."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = DotEnvGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

# FIELD="default"  # "ex1", "ex2"
"""
    assert result == expected


def test_dotenv_generator_without_examples() -> None:
    """Test dotenv generation with add_examples disabled."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = DotEnvGenerator(generator_config=DotEnvSettings(add_examples=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

# FIELD="default"
"""
    assert result == expected


def test_dotenv_generator_with_alias() -> None:
    """Test dotenv generation uses alias."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="external_name")

    generator = DotEnvGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

# EXTERNAL_NAME="value"
"""
    assert result == expected


def test_dotenv_generator_with_env_prefix() -> None:
    """Test dotenv generation with environment prefix."""

    class Settings(BaseSettings):
        model_config = {"env_prefix": "APP_"}
        field: str = "value"

    generator = DotEnvGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

# APP_FIELD="value"
"""
    assert result == expected


def test_dotenv_generator_nested_settings() -> None:
    """Test dotenv generation with nested settings."""

    class Database(BaseSettings):
        """Database config."""

        host: str = Field(default="localhost", description="Database host")
        port: int = Field(description="Required port")

    class Settings(BaseSettings):
        """Main settings."""

        database: Database = Field(default_factory=Database)

    generator = DotEnvGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings

### Database

# DATABASE_HOST="localhost"
DATABASE_PORT=
"""
    assert result == expected


def test_dotenv_generator_multiple_settings() -> None:
    """Test generating documentation for multiple settings."""

    class First(BaseSettings):
        a: str = "a"

    class Second(BaseSettings):
        b: str = "b"

    generator = DotEnvGenerator()
    result = generator.generate(
        SettingsInfoModel.from_settings_model(First),
        SettingsInfoModel.from_settings_model(Second),
    )

    expected = """\
### First

# A="a"

### Second

# B="b"
"""
    assert result == expected


def test_dotenv_generator_warns_when_no_matching_fields() -> None:
    """Test warning when no fields match the selected mode."""

    class Settings(BaseSettings):
        required: str = Field(description="Required field")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(mode="only-optional"))

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
### Settings
"""
    assert result == expected
    assert len(w) == 1
    assert "No environment variables found for Settings" in str(w[0].message)
    assert "mode='only-optional'" in str(w[0].message)
