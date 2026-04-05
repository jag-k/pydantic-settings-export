"""Tests for models module."""

from pathlib import Path
from typing import Any, Literal, Optional, Union

import pytest
from pydantic import AliasChoices, AliasPath, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings_export.models import (
    FieldInfoModel,
    SettingsInfoModel,
    format_types,
    get_type_by_annotation,
    type_repr,
    value_to_jsonable,
)

# =============================================================================
# Tests for value_to_jsonable
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("hello", '"hello"'),
        (42, "42"),
        (True, "true"),
        ([1, 2, 3], "[1,2,3]"),
        ({"key": "value"}, '{"key":"value"}'),
        (None, "null"),
        (Path("/tmp/file.txt"), '"/tmp/file.txt"'),  # noqa: S108
        (SecretStr("abc"), '"**********"'),
    ],
)
def test_value_to_jsonable(value: Any, expected: str) -> None:
    """Test converting string to JSON."""
    result = value_to_jsonable(value)
    assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (str, [str]),
        (int, [int]),
        (bool, [bool]),
        (float, [float]),
        (list, [list]),
        (list[str], [list]),
        (dict, [dict]),
        (dict[str, int], [dict]),
        (None, [type(None)]),
    ],
)
def test_get_type_by_annotation_simple(value: type, expected: list[Any]) -> None:
    """Test getting type from simple annotations."""
    result = get_type_by_annotation(value)
    assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Optional[str], [str, type(None)]),
        (Union[str, int], [str, int]),
        (Union[str, None], [str, type(None)]),
        (str | None, [str, type(None)]),
        (str | Path, [str, Path]),
        (str | str, [str]),
        (str | Path | int | float | None, [str, Path, int, float, type(None)]),
    ],
)
def test_get_type_by_annotation_union(value: type, expected: list[Any]) -> None:
    """Test getting type from Union-s annotation."""
    result = get_type_by_annotation(value)
    assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Literal["a", "b", 1], ["a", "b", 1]),
        (Literal[1, 2, 3], [1, 2, 3]),
    ],
)
def test_get_type_by_annotation_literal(value: type, expected: list[Any]) -> None:
    """Test getting type from Literal annotation."""
    result = get_type_by_annotation(value)
    assert result == expected


def test_get_type_by_annotation_path() -> None:
    """Test getting type from Path annotation."""
    result = get_type_by_annotation(Path)
    assert result == [Path]


# =============================================================================
# Tests for type_repr
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (str, "string"),
        (int, "integer"),
        (bool, "boolean"),
        (float, "number"),
        (list, "array"),
        (dict, "object"),
        (type(None), "null"),
        (Path, "Path"),
        # Literal values
        ("a", '"a"'),
        (1, "1"),
        (True, "true"),
        (False, "false"),
        (1.5, "1.5"),
    ],
)
def test_type_repr(value: Any, expected: str) -> None:
    """Test type_repr converts type items to display strings."""
    assert type_repr(value) == expected


# =============================================================================
# Tests for format_types
# =============================================================================


def test_format_types_simple() -> None:
    """Test format_types on a list of type objects."""
    assert format_types([str, int]) == ["string", "integer"]


def test_format_types_with_none() -> None:
    """Test format_types includes null for NoneType."""
    assert format_types([str, type(None)]) == ["string", "null"]


def test_format_types_literal_values() -> None:
    """Test format_types formats raw Literal values."""
    assert format_types(["a", 1]) == ['"a"', "1"]


# =============================================================================
# Tests for FieldInfoModel
# =============================================================================


def test_field_info_from_simple_field() -> None:
    """Test creating FieldInfoModel from a simple field with default."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.name == "field"
    assert result.types == [str]
    assert result.default == "value"
    assert result.is_required is False


def test_field_info_from_required_field() -> None:
    """Test creating FieldInfoModel from a required field (no default)."""

    class Settings(BaseSettings):
        field: str = Field(description="Required field")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.name == "field"
    assert result.types == [str]
    assert result.default is None
    assert result.is_required is True


def test_field_info_with_alias() -> None:
    """Test creating FieldInfoModel from a field with alias."""

    class Settings(BaseSettings):
        internal_name: str = Field(default="value", alias="external_name")

    field_info = Settings.model_fields["internal_name"]
    result = FieldInfoModel.from_settings_field("internal_name", field_info)

    assert result.name == "internal_name"
    # alias is added, and pydantic also sets validation_alias to the same value
    assert "external_name" in result.aliases
    assert result.full_name == "external_name"


def test_field_info_with_validation_alias_string() -> None:
    """Test creating FieldInfoModel from a field with validation_alias as string."""

    class Settings(BaseSettings):
        field: str = Field(default="value", validation_alias="VAL_ALIAS")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert "VAL_ALIAS" in result.aliases


def test_field_info_with_validation_alias_path() -> None:
    """Test creating FieldInfoModel from a field with validation_alias as AliasPath."""

    class Settings(BaseSettings):
        field: str = Field(default="value", validation_alias=AliasPath("nested", "field"))

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.aliases == ["nested"]  # BUG-6 fixed: AliasPath uses path[0]


def test_field_info_with_validation_alias_choices() -> None:
    """Test creating FieldInfoModel from a field with validation_alias as AliasChoices."""

    class Settings(BaseSettings):
        field: str = Field(default="value", validation_alias=AliasChoices("alias1", "alias2"))

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert "alias1" in result.aliases
    assert "alias2" in result.aliases


def test_field_info_with_examples() -> None:
    """Test creating FieldInfoModel from a field with examples."""

    class Settings(BaseSettings):
        field: str = Field(default="default", examples=["example1", "example2"])

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.examples == ["example1", "example2"]
    assert result.has_examples() is True


def test_field_info_examples_same_as_default() -> None:
    """Test that has_examples returns False when examples equal default."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    # When no examples provided, default is used as example
    assert result.examples == ["value"]
    assert result.has_examples() is False


def test_field_info_deprecated() -> None:
    """Test creating FieldInfoModel from a deprecated field."""

    class Settings(BaseSettings):
        field: str = Field(default="value", deprecated=True)

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.deprecated is True


def test_field_info_not_deprecated() -> None:
    """Test creating FieldInfoModel from a non-deprecated field."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.deprecated is False


def test_field_info_with_description() -> None:
    """Test creating FieldInfoModel from a field with description."""

    class Settings(BaseSettings):
        field: str = Field(default="value", description="This is a description")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.description == "This is a description"


def test_field_info_without_description() -> None:
    """Test creating FieldInfoModel from a field without description."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.description is None


def test_field_info_with_default_factory() -> None:
    """Test creating FieldInfoModel from a field with default_factory."""

    class Settings(BaseSettings):
        items: list[str] = Field(default_factory=lambda: ["a", "b"])

    field_info = Settings.model_fields["items"]
    result = FieldInfoModel.from_settings_field("items", field_info)

    assert result.default == ["a", "b"]
    assert result.is_required is False


def test_field_info_full_name_without_alias() -> None:
    """Test full_name property returns name when no alias."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    field_info = Settings.model_fields["field"]
    result = FieldInfoModel.from_settings_field("field", field_info)

    assert result.full_name == "field"


# =============================================================================
# Tests for SettingsInfoModel
# =============================================================================


def test_settings_info_from_simple_settings() -> None:
    """Test creating SettingsInfoModel from simple BaseSettings."""

    class Settings(BaseSettings):
        """Simple settings."""

        field: str = Field(default="value", description="A field")

    result = SettingsInfoModel.from_settings_model(Settings)

    assert result.name == "Settings"
    assert result.docs == "Simple settings."
    assert len(result.fields) == 1
    assert result.fields[0].name == "field"


def test_settings_info_with_title() -> None:
    """Test creating SettingsInfoModel from settings with title in config."""

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(title="Custom Title")
        field: str = Field(default="value")

    result = SettingsInfoModel.from_settings_model(Settings)

    assert result.name == "Custom Title"


def test_settings_info_with_env_prefix() -> None:
    """Test creating SettingsInfoModel from settings with env_prefix."""

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_")
        field: str = Field(default="value")

    result = SettingsInfoModel.from_settings_model(Settings)

    assert result.env_prefix == "APP_"


def test_settings_info_with_nested_settings() -> None:
    """Test creating SettingsInfoModel with nested/child settings."""

    class Database(BaseSettings):
        """Database config."""

        host: str = Field(default="localhost")
        port: int = Field(default=5432)

    class Settings(BaseSettings):
        """Main settings."""

        model_config = SettingsConfigDict(env_nested_delimiter="__")
        database: Database = Field(default_factory=Database)

    result = SettingsInfoModel.from_settings_model(Settings)

    assert result.name == "Settings"
    assert len(result.fields) == 0  # database is a child setting, not a field
    assert len(result.child_settings) == 1
    assert result.child_settings[0].name == "Database"
    assert result.child_settings[0].field_name == "database"
    assert len(result.child_settings[0].fields) == 2


def test_settings_info_with_nested_delimiter() -> None:
    """Test creating SettingsInfoModel with custom nested_delimiter."""

    class Database(BaseSettings):
        host: str = Field(default="localhost")

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")
        database: Database = Field(default_factory=Database)

    result = SettingsInfoModel.from_settings_model(Settings)

    # Child settings should have prefix with nested delimiter
    assert result.child_settings[0].env_prefix == "APP_database__"


def test_settings_info_without_docs() -> None:
    """Test creating SettingsInfoModel from settings without docstring."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    result = SettingsInfoModel.from_settings_model(Settings)

    # Should have empty docs (base class docs are filtered out)
    assert result.docs == ""


def test_settings_info_with_optional_nested_settings() -> None:
    """Test creating SettingsInfoModel with Optional nested settings."""

    class Database(BaseSettings):
        host: str = Field(default="localhost")

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_nested_delimiter="__")
        database: Database | None = Field(default=None)

    result = SettingsInfoModel.from_settings_model(Settings)

    # Optional nested settings should still be detected as child settings
    assert len(result.child_settings) == 1
    assert result.child_settings[0].name == "Database"


def test_settings_info_multiple_fields() -> None:
    """Test creating SettingsInfoModel with multiple fields."""

    class Settings(BaseSettings):
        field1: str = Field(default="value1")
        field2: int = Field(default=42)
        field3: bool = Field(default=True)

    result = SettingsInfoModel.from_settings_model(Settings)

    assert len(result.fields) == 3
    assert result.fields[0].name == "field1"
    assert result.fields[1].name == "field2"
    assert result.fields[2].name == "field3"


def test_settings_info_deeply_nested() -> None:
    """Test creating SettingsInfoModel with deeply nested settings."""

    class Level3(BaseSettings):
        value: str = Field(default="deep")

    class Level2(BaseSettings):
        level3: Level3 = Field(default_factory=Level3)

    class Level1(BaseSettings):
        level2: Level2 = Field(default_factory=Level2)

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_nested_delimiter="__")
        level1: Level1 = Field(default_factory=Level1)

    result = SettingsInfoModel.from_settings_model(Settings)

    assert len(result.child_settings) == 1
    assert result.child_settings[0].name == "Level1"
    assert len(result.child_settings[0].child_settings) == 1
    assert result.child_settings[0].child_settings[0].name == "Level2"
    assert len(result.child_settings[0].child_settings[0].child_settings) == 1
    assert result.child_settings[0].child_settings[0].child_settings[0].name == "Level3"


def test_settings_info_env_prefix_propagation() -> None:
    """Test that env_prefix is properly propagated to nested settings."""

    class Database(BaseSettings):
        host: str = Field(default="localhost")

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="_")
        database: Database = Field(default_factory=Database)

    result = SettingsInfoModel.from_settings_model(Settings)

    assert result.env_prefix == "APP_"
    assert result.child_settings[0].env_prefix == "APP_database_"


def test_settings_info_from_instance() -> None:
    """Test creating SettingsInfoModel from settings instance (not class)."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    settings_instance = Settings()
    result = SettingsInfoModel.from_settings_model(settings_instance)

    assert result.name == "Settings"
    assert len(result.fields) == 1
