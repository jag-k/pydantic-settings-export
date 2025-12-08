"""Tests for Markdown generator."""

from pydantic import Field
from pydantic_settings import BaseSettings

from pydantic_settings_export import SettingsInfoModel
from pydantic_settings_export.generators.markdown import MarkdownGenerator, MarkdownSettings, TableHeadersEnum


def test_markdown_generator_basic() -> None:
    """Test basic markdown generation."""

    class Settings(BaseSettings):
        """Test settings."""

        field: str = Field(default="value", description="Field description")

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

Test settings.

| Name    | Type     | Default   | Description       | Example   |
|---------|----------|-----------|-------------------|-----------|
| `FIELD` | `string` | `"value"` | Field description | `"value"` |
"""
    assert result == expected


def test_markdown_generator_with_file_prefix() -> None:
    """Test markdown generation with custom file prefix."""

    class Settings(BaseSettings):
        field: str = "value"

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix="# Custom Title\n\n"))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
# Custom Title

## Settings

| Name    | Type     | Default   | Description | Example   |
|---------|----------|-----------|-------------|-----------|
| `FIELD` | `string` | `"value"` |             | `"value"` |
"""
    assert result == expected


def test_markdown_generator_with_env_prefix() -> None:
    """Test markdown generation with environment prefix."""

    class Settings(BaseSettings):
        model_config = {"env_prefix": "APP_"}
        field: str = "value"

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

**Environment Prefix**: `APP_`

| Name        | Type     | Default   | Description | Example   |
|-------------|----------|-----------|-------------|-----------|
| `APP_FIELD` | `string` | `"value"` |             | `"value"` |
"""
    assert result == expected


def test_markdown_generator_required_field() -> None:
    """Test markdown generation marks required fields."""

    class Settings(BaseSettings):
        required: str = Field(description="Required field")
        optional: str = Field(default="value", description="Optional field")

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

| Name       | Type     | Default    | Description    | Example   |
|------------|----------|------------|----------------|-----------|
| `REQUIRED` | `string` | *required* | Required field |           |
| `OPTIONAL` | `string` | `"value"`  | Optional field | `"value"` |
"""
    assert result == expected


def test_markdown_generator_to_upper_case_false() -> None:
    """Test markdown generation without uppercase conversion."""

    class Settings(BaseSettings):
        field: str = "value"

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix="", to_upper_case=False))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

| Name    | Type     | Default   | Description | Example   |
|---------|----------|-----------|-------------|-----------|
| `field` | `string` | `"value"` |             | `"value"` |
"""
    assert result == expected


def test_markdown_generator_with_examples() -> None:
    """Test markdown generation with examples."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["ex1", "ex2"])

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

| Name    | Type     | Default     | Description | Example          |
|---------|----------|-------------|-------------|------------------|
| `FIELD` | `string` | `"default"` |             | `"ex1"`, `"ex2"` |
"""
    assert result == expected


def test_markdown_generator_with_deprecated() -> None:
    """Test markdown generation with deprecated field."""

    class Settings(BaseSettings):
        field: str = Field(default="value", deprecated=True)

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

| Name                    | Type     | Default   | Description | Example   |
|-------------------------|----------|-----------|-------------|-----------|
| `FIELD` (⚠️ Deprecated) | `string` | `"value"` |             | `"value"` |
"""
    assert result == expected


def test_markdown_generator_with_alias() -> None:
    """Test markdown generation uses alias."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="external_name")

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

| Name                               | Type     | Default   | Description | Example   |
|------------------------------------|----------|-----------|-------------|-----------|
| `EXTERNAL_NAME` \\| `EXTERNAL_NAME` | `string` | `"value"` |             | `"value"` |
"""
    assert result == expected


def test_markdown_generator_nested_settings() -> None:
    """Test markdown generation with nested settings."""

    class Database(BaseSettings):
        """Database config."""

        host: str = Field(default="localhost", description="Database host")

    class Settings(BaseSettings):
        """Main settings."""

        debug: bool = Field(default=False, description="Debug mode")
        database: Database = Field(default_factory=Database)

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

Main settings.

| Name    | Type      | Default | Description | Example |
|---------|-----------|---------|-------------|---------|
| `DEBUG` | `boolean` | `false` | Debug mode  | `false` |

### Database

Database config.

**Environment Prefix**: `DATABASE_`

| Name            | Type     | Default       | Description   | Example       |
|-----------------|----------|---------------|---------------|---------------|
| `DATABASE_HOST` | `string` | `"localhost"` | Database host | `"localhost"` |
"""
    assert result == expected


def test_markdown_generator_table_only() -> None:
    """Test markdown generation with table_only option."""

    class Settings(BaseSettings):
        field: str = "value"

    generator = MarkdownGenerator(generator_config=MarkdownSettings(table_only=True, file_prefix=""))
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
| Name    | Type     | Default   | Description | Example   |
|---------|----------|-----------|-------------|-----------|
| `FIELD` | `string` | `"value"` |             | `"value"` |
"""
    assert result == expected


def test_markdown_generator_custom_table_headers() -> None:
    """Test markdown generation with custom table headers."""

    class Settings(BaseSettings):
        field: str = Field(default="value", description="Field description")

    generator = MarkdownGenerator(
        generator_config=MarkdownSettings(
            table_headers=[TableHeadersEnum["Name"], TableHeadersEnum["Description"]],
            file_prefix="",
        )
    )
    result = generator.generate(SettingsInfoModel.from_settings_model(Settings))

    expected = """\
## Settings

| Name    | Description       |
|---------|-------------------|
| `FIELD` | Field description |
"""
    assert result == expected


def test_markdown_generator_multiple_settings() -> None:
    """Test generating documentation for multiple settings."""

    class First(BaseSettings):
        a: str = "a"

    class Second(BaseSettings):
        b: str = "b"

    generator = MarkdownGenerator(generator_config=MarkdownSettings(file_prefix=""))
    result = generator.generate(
        SettingsInfoModel.from_settings_model(First),
        SettingsInfoModel.from_settings_model(Second),
    )

    expected = """\
## First

| Name | Type     | Default | Description | Example |
|------|----------|---------|-------------|---------|
| `A`  | `string` | `"a"`   |             | `"a"`   |

## Second

| Name | Type     | Default | Description | Example |
|------|----------|---------|-------------|---------|
| `B`  | `string` | `"b"`   |             | `"b"`   |
"""
    assert result == expected
