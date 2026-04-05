from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings_export import DotEnvGenerator, SettingsInfoModel
from pydantic_settings_export.generators.dotenv import DotEnvSettings


def test_dotenv_simple(simple_settings: type[BaseSettings]) -> None:
    """Test simple .env file generation."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    # Optional field should be commented
    assert result == '# FIELD="value"\n'


def test_dotenv_with_required_field(mixed_settings: type[BaseSettings]) -> None:
    """Test .env generation with required fields."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(mixed_settings))

    # Required field should not be commented
    assert result == 'REQUIRED=\n# OPTIONAL="value"\n'


# =============================================================================
# Mode tests
# =============================================================================


def test_dotenv_mode_all(mixed_settings: type[BaseSettings]) -> None:
    """Test mode='all' includes both optional and required variables."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(mode="all", split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(mixed_settings))

    assert result == 'REQUIRED=\n# OPTIONAL="value"\n'


def test_dotenv_mode_only_optional(mixed_settings: type[BaseSettings]) -> None:
    """Test mode='only-optional' includes only optional variables."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(mode="only-optional", split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(mixed_settings))

    # Should not include required field
    assert result == '# OPTIONAL="value"\n'


def test_dotenv_mode_only_required(mixed_settings: type[BaseSettings]) -> None:
    """Test mode='only-required' includes only required variables."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(mode="only-required", split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(mixed_settings))

    # Should include only the required field
    assert result == "REQUIRED=\n"


# =============================================================================
# Split by group tests
# =============================================================================


def test_dotenv_split_by_group_true(nested_settings: type[BaseSettings]) -> None:
    """Test split_by_group=True adds section headers."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=True))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    expected = """\
### Settings

### Database

# DATABASE_HOST="localhost"
DATABASE_PORT=
"""

    assert result == expected


def test_dotenv_split_by_group_false(nested_settings: type[BaseSettings]) -> None:
    """Test split_by_group=False does not add section headers."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    assert result == '# DATABASE_HOST="localhost"\nDATABASE_PORT=\n'


# =============================================================================
# Examples tests
# =============================================================================


def test_dotenv_with_examples() -> None:
    """Test examples are added as comments."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = DotEnvGenerator(generator_config=DotEnvSettings(add_examples=True, split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Examples should be in comments
    assert result == '# FIELD="default"  # "ex1", "ex2"\n'


def test_dotenv_without_examples() -> None:
    """Test examples are not added when add_examples=False."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = DotEnvGenerator(generator_config=DotEnvSettings(add_examples=False, split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Should not have example comments (only the field itself)
    assert result == '# FIELD="default"\n'


# =============================================================================
# Alias tests
# =============================================================================


def test_dotenv_with_alias() -> None:
    """Test field alias is used as the environment variable name."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="EXTERNAL_NAME")
        internal_name2: str = Field(default="value", alias="external_name2")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    assert result == '# EXTERNAL_NAME="value"\n# EXTERNAL_NAME2="value"\n'


# =============================================================================
# Env prefix tests
# =============================================================================


def test_dotenv_with_env_prefix() -> None:
    """Test env_prefix is applied to field names."""

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_")
        field: str = Field(default="value")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    assert result == '# APP_FIELD="value"\n'


# =============================================================================
# Nested settings tests
# =============================================================================


def test_dotenv_with_nested_settings(nested_settings: type[BaseSettings]) -> None:
    """Test nested settings are included in .env file."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    assert result == '# DATABASE_HOST="localhost"\nDATABASE_PORT=\n'


def test_dotenv_nested_with_env_prefix() -> None:
    """Test nested settings with env_prefix."""

    class Database(BaseSettings):
        host: str = Field(default="localhost")

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="_")
        database: Database = Field(default_factory=Database)

    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    assert result == '# APP_DATABASE_HOST="localhost"\n'


# =============================================================================
# Default value tests
# =============================================================================


def test_dotenv_optional_field_shows_default() -> None:
    """Test optional fields show their default value."""

    class Settings(BaseSettings):
        field: str = Field(default="my_default")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Optional field should be commented with default value
    assert result == '# FIELD="my_default"\n'


def test_dotenv_required_field_empty_value() -> None:
    """Test required fields have empty value."""

    class Settings(BaseSettings):
        field: str = Field(description="Required")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Required field should have empty value
    assert result == "FIELD=\n"


# =============================================================================
# Integration tests
# =============================================================================


def test_dotenv_full_settings(full_settings: type[BaseSettings]) -> None:
    """Test comprehensive .env generation with all features."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=True))
    result = generator.generate(SettingsInfoModel.from_settings_model(full_settings))

    # Check main settings
    expected = """\
### Settings

# LOG_LEVEL="INFO"
# LOG_FORMAT="%(levelname)-8s | %(asctime)s | %(name)s | %(message)s"

### MongoDB settings

# MONGODB__MONGODB_URL="mongodb://localhost:27017"
# MONGODB__MONGODB_DB_NAME="test-db"

### OpenRouter settings

OPENROUTER__API_KEY=
# OPENROUTER__MODEL="google/gemini-2.5-flash"
# OPENROUTER__BASE_URL="https://openrouter.ai/api/v1"

### APISettings

# API__HOST="0.0.0.0"
# API__PORT=8000
"""

    assert result == expected


def test_dotenv_multiple_settings() -> None:
    """Test generating .env for multiple settings classes."""

    class Settings1(BaseSettings):
        """First settings."""

        field1: str = Field(default="value1")

    class Settings2(BaseSettings):
        """Second settings."""

        field2: str = Field(default="value2")

    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=True))
    result = generator.generate(
        SettingsInfoModel.from_settings_model(Settings1),
        SettingsInfoModel.from_settings_model(Settings2),
    )

    expected = """\
### Settings1

# FIELD1="value1"

### Settings2

# FIELD2="value2"
"""
    assert result == expected


def test_dotenv_mode_only_required_nested(nested_settings: type[BaseSettings]) -> None:
    """Test mode='only-required' works with nested settings."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(mode="only-required", split_by_group=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    # Should only include the required field from nested settings
    assert result == "DATABASE_PORT=\n"
