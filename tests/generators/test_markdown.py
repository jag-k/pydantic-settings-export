from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings_export import MarkdownGenerator, SettingsInfoModel
from pydantic_settings_export.generators.markdown import MarkdownSettings

# =============================================================================
# Basic generation tests
# =============================================================================


def test_markdown_simple_table(simple_settings: type[BaseSettings]) -> None:
    """Test Markdown generation with simple settings."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    assert "## Settings" in result
    assert "Test settings." in result
    assert "`FIELD`" in result
    assert "Field description" in result
    assert '`"value"`' in result


def test_markdown_with_required_field(mixed_settings: type[BaseSettings]) -> None:
    """Test Markdown generation with required fields."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(mixed_settings))

    assert "*required*" in result
    assert "Required field" in result
    assert "Optional field" in result


def test_markdown_with_nested_settings(nested_settings: type[BaseSettings]) -> None:
    """Test Markdown generation with nested settings creates proper headers."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    # Main settings should be h2
    assert "## Settings" in result
    # Nested settings should be h3
    assert "### Database" in result
    assert "Database config." in result
    assert "`DATABASE_HOST`" in result
    assert "`DATABASE_PORT`" in result


def test_markdown_with_env_prefix() -> None:
    """Test Markdown generation shows the environment prefix."""

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_")
        field: str = Field(default="value", description="A field")

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    assert "**Environment Prefix**: `APP_`" in result
    assert "`APP_FIELD`" in result


# =============================================================================
# Column visibility tests
# =============================================================================


def test_markdown_column_visibility_name_only(simple_settings: type[BaseSettings]) -> None:
    """Test showing only the Name column."""
    from pydantic_settings_export.generators.markdown import TableHeadersEnum

    generator = MarkdownGenerator(
        generator_config=MarkdownSettings(
            file_prefix="",
            table_headers=[TableHeadersEnum.Name],
        )
    )
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    assert "| Name" in result
    assert "| Type" not in result
    assert "| Default" not in result
    assert "| Description" not in result


def test_markdown_column_visibility_custom_order(simple_settings: type[BaseSettings]) -> None:
    """Test custom column order."""
    from pydantic_settings_export.generators.markdown import TableHeadersEnum

    generator = MarkdownGenerator(
        generator_config=MarkdownSettings(
            file_prefix="",
            table_headers=[
                TableHeadersEnum.Description,
                TableHeadersEnum.Name,
                TableHeadersEnum.Type,
            ],
        )
    )
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    # Check that Description comes before Name in the header
    desc_pos = result.find("| Description")
    name_pos = result.find("| Name")
    assert desc_pos < name_pos


# =============================================================================
# Deprecated field tests
# =============================================================================


def test_markdown_deprecated_field() -> None:
    """Test deprecated field is marked in Markdown."""

    class Settings(BaseSettings):
        field: str = Field(default="value", deprecated=True)

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    assert "(⚠️ Deprecated)" in result


# =============================================================================
# Table only mode tests
# =============================================================================


def test_markdown_table_only_true(nested_settings: type[BaseSettings]) -> None:
    """Test table_only=True generates only table without headers."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix="", table_only=True))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    # Should not have section headers
    assert "## Settings" not in result
    assert "### Database" not in result
    # Should have table with all fields
    assert "`DATABASE_HOST`" in result
    assert "`DATABASE_PORT`" in result


def test_markdown_table_only_with_header(nested_settings: type[BaseSettings]) -> None:
    """Test table_only='with-header' generates table with top-level header."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix="", table_only="with-header"))
    result = generator.generate(SettingsInfoModel.from_settings_model(nested_settings))

    # Should have table with all fields but no headers
    assert "## Settings" not in result
    assert "`DATABASE_HOST`" in result


# =============================================================================
# File prefix tests
# =============================================================================


def test_markdown_with_file_prefix(simple_settings: type[BaseSettings]) -> None:
    """Test Markdown generation with custom file prefix."""
    custom_prefix = "# My Configuration\n\nCustom prefix text.\n\n"
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=custom_prefix))
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    assert result.startswith("# My Configuration")
    assert "Custom prefix text." in result


def test_markdown_default_file_prefix(simple_settings: type[BaseSettings]) -> None:
    """Test Markdown generation with default file prefix."""
    generator = MarkdownGenerator()
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    assert "# Configuration" in result
    assert "available configuration options" in result


# =============================================================================
# Case conversion tests
# =============================================================================


def test_markdown_to_upper_case_true(simple_settings: type[BaseSettings]) -> None:
    """Test field names are converted to upper case by default."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix="", to_upper_case=True))
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    assert "`FIELD`" in result
    assert "`field`" not in result


def test_markdown_to_upper_case_false(simple_settings: type[BaseSettings]) -> None:
    """Test field names are not converted when to_upper_case=False."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix="", to_upper_case=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(simple_settings))

    assert "`field`" in result


# =============================================================================
# Alias tests
# =============================================================================


def test_markdown_with_alias() -> None:
    """Test field alias is used in Markdown."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="EXTERNAL_NAME")

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    assert "`EXTERNAL_NAME`" in result


# =============================================================================
# Examples tests
# =============================================================================


def test_markdown_with_examples() -> None:
    """Test examples are shown in Markdown."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Examples should be in the Example column
    assert '"ex1"' in result
    assert '"ex2"' in result


# =============================================================================
# Type display tests
# =============================================================================


def test_markdown_with_union_types() -> None:
    """Test Union types are displayed with separator."""

    class Settings(BaseSettings):
        field: str | int = Field(default="value")

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    # Pipe is escaped in Markdown tables as \|
    assert "`string` \\| `integer`" in result


# =============================================================================
# Integration tests
# =============================================================================


def test_markdown_full_settings(full_settings: type[BaseSettings]) -> None:
    """Test comprehensive Markdown generation with all features."""
    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(full_settings))

    # Check main settings
    expected = """\
## Settings

| Name         | Type                                                              | Default                                                       | Description           | Example                                                       |
|--------------|-------------------------------------------------------------------|---------------------------------------------------------------|-----------------------|---------------------------------------------------------------|
| `LOG_LEVEL`  | `"DEBUG"` \\| `"INFO"` \\| `"WARNING"` \\| `"ERROR"` \\| `"CRITICAL"` | `"INFO"`                                                      | The log level to use  | `"INFO"`                                                      |
| `LOG_FORMAT` | `string`                                                          | `"%(levelname)-8s \\| %(asctime)s \\| %(name)s \\| %(message)s"` | The log format to use | `"%(levelname)-8s \\| %(asctime)s \\| %(name)s \\| %(message)s"` |

### MongoDB settings

MongoDB connection settings.

**Environment Prefix**: `MONGODB__`

| Name                       | Type       | Default                       | Description            | Example                       |
|----------------------------|------------|-------------------------------|------------------------|-------------------------------|
| `MONGODB__MONGODB_URL`     | `MongoDsn` | `"mongodb://localhost:27017"` | MongoDB connection URL | `"mongodb://localhost:27017"` |
| `MONGODB__MONGODB_DB_NAME` | `string`   | `"test-db"`                   | MongoDB database name  | `"test-db"`                   |

### OpenRouter settings

OpenRouter models settings.

**Environment Prefix**: `OPENROUTER__`

| Name                   | Type         | Default                          | Description             | Example                          |
|------------------------|--------------|----------------------------------|-------------------------|----------------------------------|
| `OPENROUTER__API_KEY`  | `string`     | *required*                       | OpenRouter API key      |                                  |
| `OPENROUTER__MODEL`    | `string`     | `"google/gemini-2.5-flash"`      | OpenRouter model name   | `"google/gemini-2.5-flash"`      |
| `OPENROUTER__BASE_URL` | `AnyHttpUrl` | `"https://openrouter.ai/api/v1"` | OpenRouter API base URL | `"https://openrouter.ai/api/v1"` |

### APISettings

**Environment Prefix**: `API__`

| Name        | Type      | Default     | Description | Example     |
|-------------|-----------|-------------|-------------|-------------|
| `API__HOST` | `string`  | `"0.0.0.0"` | API host    | `"0.0.0.0"` |
| `API__PORT` | `integer` | `8000`      | API port    | `8000`      |
"""
    assert result == expected


def test_markdown_multiple_settings() -> None:
    """Test generating Markdown for multiple settings classes."""

    class Settings1(BaseSettings):
        """First settings."""

        field1: str = Field(default="value1")

    class Settings2(BaseSettings):
        """Second settings."""

        field2: str = Field(default="value2")

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(
        SettingsInfoModel.from_settings_model(Settings1),
        SettingsInfoModel.from_settings_model(Settings2),
    )

    assert "## Settings1" in result
    assert "First settings." in result
    assert "`FIELD1`" in result
    assert "## Settings2" in result
    assert "Second settings." in result
    assert "`FIELD2`" in result
