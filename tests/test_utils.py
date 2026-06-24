"""Tests for utils module."""

import sys
import types
import warnings
from pathlib import Path

import pytest

from pydantic_settings_export.utils import (
    MissingSettingsError,
    ObjectImportAction,
    _find_settings_in_module,
    import_settings_from_string,
    import_settings_from_strings,
    make_pretty_md_table,
    make_pretty_md_table_from_dict,
)

# =============================================================================
# Tests for make_pretty_md_table
# =============================================================================


def test_make_pretty_md_table_simple() -> None:
    """Test creating a simple Markdown table."""
    headers = ["Name", "Value"]
    rows = [["foo", "bar"], ["baz", "qux"]]

    result = make_pretty_md_table(headers, rows)

    assert result == (
        """\
| Name | Value |
|------|-------|
| foo  | bar   |
| baz  | qux   |"""
    )


def test_make_pretty_md_table_alignment() -> None:
    """Test table columns are properly aligned."""
    headers = ["Short", "LongerHeader"]
    rows = [["a", "b"], ["longer", "x"]]

    result = make_pretty_md_table(headers, rows)

    # Check that columns are padded correctly
    lines = result.split("\n")
    # All lines should have the same length (aligned)
    assert len(set(len(line) for line in lines if line)) == 1


def test_make_pretty_md_table_escapes_pipes() -> None:
    """Test that pipes in cell content are escaped."""
    headers = ["Name", "Value"]
    rows = [["foo|bar", "baz"]]

    result = make_pretty_md_table(headers, rows)

    # Pipe should be escaped
    assert "foo\\|bar" in result


def test_make_pretty_md_table_handles_none() -> None:
    """Test that None values are handled."""
    headers = ["Name", "Value"]
    rows = [["foo", None]]

    result = make_pretty_md_table(headers, rows)

    # Should not raise and should have an empty cell
    assert "| foo" in result


def test_make_pretty_md_table_empty_rows() -> None:
    """Test table with no rows."""
    headers = ["Name", "Value"]
    rows: list[list[str]] = []

    result = make_pretty_md_table(headers, rows)

    # Should have header and separator only
    assert result == "| Name | Value |\n|------|-------|"


def test_make_pretty_md_table_single_column() -> None:
    """Test table with single column."""
    headers = ["Name"]
    rows = [["foo"], ["bar"]]

    result = make_pretty_md_table(headers, rows)

    assert "| Name |" in result
    assert "| foo  |" in result
    assert "| bar  |" in result


# =============================================================================
# Tests for make_pretty_md_table_from_dict
# =============================================================================


def test_make_pretty_md_table_from_dict_simple() -> None:
    """Test creating table from list of dicts."""
    data: list[dict[str, str | None]] = [
        {"Name": "foo", "Value": "bar"},
        {"Name": "baz", "Value": "qux"},
    ]

    result = make_pretty_md_table_from_dict(data)

    assert "| Name | Value |" in result
    assert "| foo  | bar   |" in result
    assert "| baz  | qux   |" in result


def test_make_pretty_md_table_from_dict_with_headers() -> None:
    """Test creating table from dicts with explicit headers."""
    data: list[dict[str, str | None]] = [
        {"Name": "foo", "Value": "bar", "Extra": "ignored"},
    ]
    headers = ["Name", "Value"]

    result = make_pretty_md_table_from_dict(data, headers=headers)

    assert "| Name | Value |" in result
    assert "Extra" not in result


def test_make_pretty_md_table_from_dict_missing_keys() -> None:
    """Test handling of missing keys in dicts."""
    data: list[dict[str, str | None]] = [
        {"Name": "foo", "Value": "bar"},
        {"Name": "baz"},  # Missing "Value"
    ]

    result = make_pretty_md_table_from_dict(data)

    # Should handle missing key gracefully
    assert "| baz" in result


def test_make_pretty_md_table_from_dict_preserves_order() -> None:
    """Test that column order is preserved from first dict."""
    data: list[dict[str, str | None]] = [
        {"B": "1", "A": "2", "C": "3"},
    ]

    result = make_pretty_md_table_from_dict(data)

    # Order should be B, A, C (as in first dict)
    header_line = result.split("\n")[0]
    b_pos = header_line.find("B")
    a_pos = header_line.find("A")
    c_pos = header_line.find("C")
    assert b_pos < a_pos < c_pos


# =============================================================================
# Tests for ObjectImportAction
# =============================================================================


def test_object_import_action_import_obj_builtin_generator() -> None:
    """Test importing built-in generator by name."""
    from pydantic_settings_export import MarkdownGenerator

    result = ObjectImportAction.import_obj("markdown")

    assert result == MarkdownGenerator


def test_object_import_action_import_obj_by_class_name() -> None:
    """Test importing generator by class name."""
    from pydantic_settings_export import MarkdownGenerator

    result = ObjectImportAction.import_obj("MarkdownGenerator")

    assert result == MarkdownGenerator


def test_object_import_action_import_obj_module_class() -> None:
    """Test importing object with module:class format."""
    result = ObjectImportAction.import_obj("pydantic_settings_export:MarkdownGenerator")

    from pydantic_settings_export import MarkdownGenerator

    assert result == MarkdownGenerator


def test_object_import_action_import_obj_invalid_format() -> None:
    """Test error on invalid format (no colon)."""
    with pytest.raises(ValueError, match="is not in the format 'module:class'") as exc_info:
        ObjectImportAction.import_obj("invalid_format_no_colon")

    assert "not in the format" in str(exc_info.value)


def test_object_import_action_import_obj_module_not_found() -> None:
    """Test error when module not found."""
    with pytest.raises(ModuleNotFoundError):
        ObjectImportAction.import_obj("nonexistent_module:SomeClass")


def test_object_import_action_import_obj_class_not_found() -> None:
    """Test error when class not found in module."""
    with pytest.raises(ValueError, match="is not in the module") as exc_info:
        ObjectImportAction.import_obj("pydantic_settings_export:NonexistentClass")

    assert "is not in the module" in str(exc_info.value)


# =============================================================================
# Tests for MissingSettingsError
# =============================================================================


def test_missing_settings_error_message() -> None:
    """Test MissingSettingsError message format."""
    missing = {"field1": "Field required", "field2": "Field required"}

    error = MissingSettingsError(missing, "MySettings")

    assert "2 missing settings" in str(error)
    assert "field1" in str(error)
    assert "field2" in str(error)
    assert "MySettings" in str(error)


def test_missing_settings_error_with_dotted_key() -> None:
    """Test MissingSettingsError with dotted key."""
    missing = {"nested.field": "Field required"}

    error = MissingSettingsError(missing, "MySettings")

    # Dotted key should be used as-is
    assert "nested.field" in str(error)


def test_missing_settings_error_single_field() -> None:
    """Test MissingSettingsError with single field."""
    missing = {"field": "Field required"}

    error = MissingSettingsError(missing, "Settings")

    assert "1 missing setting" in str(error)
    assert "field" in str(error)


# =============================================================================
# Tests for q (quote) function
# =============================================================================


def test_q_function() -> None:
    """Test q function adds backticks."""
    from pydantic_settings_export.utils import q

    result = q("test")

    assert result == "`test`"


def test_q_function_with_special_chars() -> None:
    """Test q function with special characters."""
    from pydantic_settings_export.utils import q

    result = q("test|value")

    assert result == "`test|value`"


# =============================================================================
# Tests for _find_settings_in_module
# =============================================================================


def _make_module_with_settings(name: str) -> types.ModuleType:
    """Create a throwaway module containing two BaseSettings subclasses."""
    from pydantic_settings import BaseSettings

    module = types.ModuleType(name)
    module.__name__ = name

    class LocalSettings(BaseSettings):
        pass

    class AnotherSettings(BaseSettings):
        pass

    LocalSettings.__module__ = name
    AnotherSettings.__module__ = name

    module.LocalSettings = LocalSettings  # type: ignore[attr-defined]
    module.AnotherSettings = AnotherSettings  # type: ignore[attr-defined]
    return module


def test_find_settings_in_module_discovers_subclasses() -> None:
    """BaseSettings subclasses defined in the module are discovered."""
    module = _make_module_with_settings("_test_find_settings_mod")
    result = _find_settings_in_module(module)
    assert len(result) == 2
    assert all(issubclass(cls, __import__("pydantic_settings").BaseSettings) for cls in result)


def test_find_settings_in_module_excludes_reimported() -> None:
    """Classes whose __module__ differs from the module name are excluded."""
    from pydantic_settings import BaseSettings

    module = types.ModuleType("_test_find_reimport_mod")
    module.__name__ = "_test_find_reimport_mod"
    module.BaseSettings = BaseSettings  # type: ignore[attr-defined]

    result = _find_settings_in_module(module)
    assert result == []


def test_find_settings_in_module_excludes_base_settings_itself() -> None:
    """BaseSettings itself is never returned."""
    from unittest.mock import patch

    from pydantic_settings import BaseSettings

    module = types.ModuleType("_test_base_mod")
    module.__name__ = "_test_base_mod"
    module.BaseSettings = BaseSettings  # type: ignore[attr-defined]

    with patch.object(BaseSettings, "__module__", "_test_base_mod"):
        result = _find_settings_in_module(module)

    assert BaseSettings not in result


# =============================================================================
# Tests for import_settings_from_string
# =============================================================================


def test_import_settings_from_string_specific_class() -> None:
    """'module:Class' format returns a single-element list with that class."""
    from pydantic_settings_export.settings import PSESettings

    result = import_settings_from_string("pydantic_settings_export.settings:PSESettings")
    assert result == [PSESettings]


def test_import_settings_from_string_module_discovers_subclasses() -> None:
    """Module-only path discovers all BaseSettings subclasses defined there."""
    from pydantic_settings_export.settings import PSESettings

    result = import_settings_from_string("pydantic_settings_export.settings")
    assert PSESettings in result


def test_import_settings_from_string_module_excludes_reimported() -> None:
    """Re-imported BaseSettings subclasses are not included in module discovery."""
    from pydantic_settings_export.sources import TomlSettings

    result = import_settings_from_string("pydantic_settings_export.settings")
    assert TomlSettings not in result


def test_import_settings_from_string_empty_module_returns_empty() -> None:
    """Module with no BaseSettings subclasses returns an empty list."""
    mod_name = "_test_empty_settings_module"
    module = types.ModuleType(mod_name)
    sys.modules[mod_name] = module
    try:
        result = import_settings_from_string(mod_name)
        assert result == []
    finally:
        del sys.modules[mod_name]


def test_import_settings_from_string_not_settings_class_raises() -> None:
    """Non-BaseSettings object imported via 'module:attr' raises ValueError."""
    with pytest.raises(ValueError, match="is not a settings class"):
        import_settings_from_string("pydantic_settings_export.utils:make_pretty_md_table")


def test_import_settings_from_string_file_discovers_settings(settings_sources_project) -> None:
    """Python file path discovers local BaseSettings subclasses."""
    result = import_settings_from_string(
        settings_sources_project.module_file_source,
        project_dir=settings_sources_project.root,
    )
    assert [cls.__name__ for cls in result] == ["AppSettings"]


def test_import_settings_from_string_standalone_file_discovers_settings(settings_sources_project) -> None:
    """Standalone Python file outside a package is supported."""
    result = import_settings_from_string(
        settings_sources_project.standalone_file_source,
        project_dir=settings_sources_project.root,
    )
    assert [cls.__name__ for cls in result] == ["StandaloneSettings"]


def test_import_settings_from_string_directory_recursively_discovers_settings(settings_sources_project) -> None:
    """Directory path recursively discovers BaseSettings subclasses."""
    result = import_settings_from_string(
        settings_sources_project.discovered_dir_source,
        project_dir=settings_sources_project.root,
    )
    assert [cls.__name__ for cls in result] == ["DatabaseSettings", "CacheSettings"]


def test_import_settings_from_string_directory_with_partial_failures_warns_and_continues(
    settings_sources_project,
) -> None:
    """Broken files inside a directory should not stop discovery for valid files."""
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        result = import_settings_from_string(
            settings_sources_project.problematic_dir_source,
            project_dir=settings_sources_project.root,
        )

    assert [cls.__name__ for cls in result] == ["ProblemSettings"]
    assert len(records) == 1
    assert "Failed to import settings from" in str(records[0].message)


def test_import_settings_from_strings_deduplicates_old_and_new_sources(settings_sources_project) -> None:
    """Module, module:attr, and file path should not duplicate the same class."""
    result = import_settings_from_strings(
        [
            settings_sources_project.module_name,
            settings_sources_project.module_attr,
            settings_sources_project.module_file_source,
            settings_sources_project.discovered_dir_source,
            settings_sources_project.standalone_file_source,
        ],
        project_dir=settings_sources_project.root,
    )
    assert [cls.__name__ for cls in result] == [
        "AppSettings",
        "DatabaseSettings",
        "CacheSettings",
        "StandaloneSettings",
    ]


def test_import_settings_from_string_resolves_relative_paths_from_project_dir(
    settings_sources_project,
) -> None:
    """Relative paths are resolved against the provided project_dir."""
    result = import_settings_from_string(
        settings_sources_project.module_file_source,
        project_dir=settings_sources_project.root,
    )
    assert [cls.__name__ for cls in result] == ["AppSettings"]


def test_import_settings_from_string_missing_path_raises_file_not_found_error(
    settings_sources_project,
) -> None:
    """Missing file-system path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="does not exist"):
        import_settings_from_string("./missing/settings.py", project_dir=settings_sources_project.root)


def test_import_settings_from_string_non_python_file_raises_value_error(
    settings_sources_project,
) -> None:
    """Non-Python file path is rejected."""
    with pytest.raises(ValueError, match="is not a Python file"):
        import_settings_from_string(
            settings_sources_project.text_file_source, project_dir=settings_sources_project.root
        )


def test_import_settings_from_string_broken_python_file_raises_syntax_error(
    settings_sources_project,
) -> None:
    """Broken Python files should raise the original import error."""
    with pytest.raises(SyntaxError):
        import_settings_from_string(
            settings_sources_project.broken_syntax_source, project_dir=settings_sources_project.root
        )


def test_import_settings_from_string_file_without_settings_returns_empty(
    settings_sources_project,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Python file without BaseSettings subclasses returns an empty list."""
    result = import_settings_from_string(
        settings_sources_project.no_settings_file_source,
        project_dir=settings_sources_project.root,
    )
    assert result == []
    assert "No BaseSettings subclasses found in file" in caplog.text


def test_import_settings_from_string_empty_directory_returns_empty(
    settings_sources_project,
) -> None:
    """Directory without Python settings files returns an empty list."""
    result = import_settings_from_string(
        f"./{Path(settings_sources_project.empty_dir).relative_to(settings_sources_project.root)!s}",
        project_dir=settings_sources_project.root,
    )
    assert result == []
