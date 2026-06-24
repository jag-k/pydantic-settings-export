import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import Field
from pydantic_settings import BaseSettings

from pydantic_settings_export import Exporter, PSESettings
from pydantic_settings_export.generators import AbstractGenerator
from pydantic_settings_export.generators.simple import SimpleGenerator, SimpleSettings


@pytest.fixture
def pse_settings(tmp_path: Path) -> PSESettings:
    """PSESettings with temp directory."""
    return PSESettings(root_dir=tmp_path, project_dir=tmp_path)


# =============================================================================
# Initialization tests
# =============================================================================


def test_exporter_init_default() -> None:
    """Test Exporter initialization with defaults."""
    exporter = Exporter()

    assert exporter.settings is not None
    assert isinstance(exporter.settings, PSESettings)
    assert len(exporter.generators) > 0


def test_exporter_init_with_settings(pse_settings: PSESettings) -> None:
    """Test Exporter initialization with custom settings."""
    exporter = Exporter(settings=pse_settings)

    assert exporter.settings == pse_settings


def test_exporter_init_default_generators() -> None:
    """Test Exporter initializes all built-in generators it can construct."""
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        exporter = Exporter()

    assert not records, [str(record.message) for record in records]

    # All initialized generators should be registered built-ins
    generator_types = [type(g) for g in exporter.generators]
    assert generator_types
    for gen_class in generator_types:
        assert gen_class in AbstractGenerator.ALL_GENERATORS


def test_exporter_init_custom_generators(pse_settings: PSESettings) -> None:
    """Test Exporter initialization with custom generators."""
    custom_generator = SimpleGenerator(pse_settings)
    exporter = Exporter(settings=pse_settings, generators=[custom_generator])

    assert len(exporter.generators) == 1
    assert exporter.generators[0] == custom_generator


def test_exporter_init_empty_generators(pse_settings: PSESettings) -> None:
    """Test Exporter initialization with empty generators list."""
    exporter = Exporter(settings=pse_settings, generators=[])

    assert len(exporter.generators) == 0


# =============================================================================
# run_all tests
# =============================================================================


def test_exporter_run_all_returns_paths(simple_settings: type[BaseSettings], tmp_path: Path) -> None:
    """Test run_all returns list of paths."""
    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    output_file = tmp_path / "output.txt"

    # Create a generator with a path
    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(paths=[output_file]),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    result = exporter.run_all(simple_settings)

    assert isinstance(result, list)
    assert output_file in result
    assert output_file.exists()


def test_exporter_run_all_multiple_settings(tmp_path: Path) -> None:
    """Test run_all with multiple settings classes."""

    class Settings1(BaseSettings):
        field1: str = Field(default="value1")

    class Settings2(BaseSettings):
        field2: str = Field(default="value2")

    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    output_file = tmp_path / "output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(paths=[output_file]),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    result = exporter.run_all(Settings1, Settings2)

    assert output_file in result
    content = output_file.read_text()
    assert "Settings1" in content
    assert "Settings2" in content


def test_exporter_run_all_no_generators(simple_settings: type[BaseSettings], pse_settings: PSESettings) -> None:
    """Test run_all with no generators returns empty list."""
    exporter = Exporter(settings=pse_settings, generators=[])

    result = exporter.run_all(simple_settings)

    assert result == []


def test_exporter_run_all_with_settings_instance(tmp_path: Path) -> None:
    """Test run_all accepts settings instance (not just class)."""

    class Settings(BaseSettings):
        field: str = Field(default="value")

    settings_instance = Settings()
    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    output_file = tmp_path / "output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(paths=[output_file]),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    result = exporter.run_all(settings_instance)

    assert output_file in result


# =============================================================================
# Generator failure handling tests
# =============================================================================


def test_exporter_handles_generator_failure(simple_settings: type[BaseSettings], pse_settings: PSESettings) -> None:
    """Test Exporter handles generator failures with warning."""
    # Create a mock generator that raises an exception
    mock_generator = MagicMock(spec=AbstractGenerator)
    mock_generator.run.side_effect = Exception("Generator failed")

    exporter = Exporter(settings=pse_settings, generators=[mock_generator])

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = exporter.run_all(simple_settings)

        # Should have a warning about the failure
        assert len(w) >= 1
        assert any("failed" in str(warning.message).lower() for warning in w)

    # Should return empty list since generator failed
    assert result == []


def test_exporter_continues_after_generator_failure(simple_settings: type[BaseSettings], tmp_path: Path) -> None:
    """Test Exporter continues with other generators after one fails."""
    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    output_file = tmp_path / "output.txt"

    # Create a failing generator
    failing_generator = MagicMock(spec=AbstractGenerator)
    failing_generator.run.side_effect = Exception("Generator failed")

    # Create a working generator
    working_generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(paths=[output_file]),
    )

    exporter = Exporter(settings=pse_settings, generators=[failing_generator, working_generator])

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = exporter.run_all(simple_settings)

    # Should still have output from working generator
    assert output_file in result


# =============================================================================
# Generator initialization failure tests
# =============================================================================


def test_exporter_handles_generator_init_failure(pse_settings: PSESettings) -> None:
    """Test Exporter handles generator initialization failures."""
    # This test verifies that if a generator fails to initialize,
    # the Exporter still works with other generators

    # Create a mock generator class that fails during __init__
    mock_generator_class = MagicMock(side_effect=RuntimeError("Init failed"))
    mock_generator_class.__name__ = "FailingGenerator"

    # Patch ALL_GENERATORS to include both a working and failing generator
    with (
        patch.object(
            AbstractGenerator,
            "ALL_GENERATORS",
            [SimpleGenerator, mock_generator_class],
        ),
        warnings.catch_warnings(record=True) as w,
    ):
        warnings.simplefilter("always")
        # Should handle init failure and continue with other generators
        exporter = Exporter(settings=pse_settings)

        # Exporter should still be created
        assert exporter is not None
        # Should have exactly one working generator (SimpleGenerator)
        assert len(exporter.generators) == 1
        assert isinstance(exporter.generators[0], SimpleGenerator)
        # Should have warning about the failed generator
        assert len(w) == 1
        assert "FailingGenerator" in str(w[0].message)
        assert "Init failed" in str(w[0].message)


# =============================================================================
# File creation tests
# =============================================================================


def test_exporter_creates_output_directory(simple_settings: type[BaseSettings], tmp_path: Path) -> None:
    """Test Exporter creates an output directory if it doesn't exist."""
    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    nested_dir = tmp_path / "nested" / "dir"
    output_file = nested_dir / "output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(paths=[output_file]),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    result = exporter.run_all(simple_settings)

    assert nested_dir.exists()
    assert output_file in result


def test_exporter_skips_unchanged_files(simple_settings: type[BaseSettings], tmp_path: Path) -> None:
    """Test Exporter skips writing if file content unchanged."""
    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    output_file = tmp_path / "output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(paths=[output_file]),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    # The first run - should create a file
    result1 = exporter.run_all(simple_settings)
    assert output_file in result1

    # The second run - should skip since content unchanged
    result2 = exporter.run_all(simple_settings)
    assert output_file not in result2  # File not in an updated list


# =============================================================================
# Per-generator settings / extend_settings tests
# =============================================================================


def test_generator_settings_override_ignores_defaults(tmp_path: Path) -> None:
    """Generator 'settings' field replaces default_settings entirely."""

    class DefaultSettings(BaseSettings):
        x: str = "default_field"

    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    output_file = tmp_path / "output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(
            paths=[output_file],
            settings=["pydantic_settings_export.settings:PSESettings"],
        ),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    result = exporter.run_all(DefaultSettings)

    assert output_file in result
    content = output_file.read_text()
    assert "Global Settings" in content
    assert "DefaultSettings" not in content


def test_generator_extend_settings_appends_to_defaults(settings_sources_project) -> None:
    """Generator 'extend_settings' appends to default_settings."""

    class DefaultSettings(BaseSettings):
        x: str = "default_field"

    pse_settings = PSESettings(
        root_dir=settings_sources_project.root,
        project_dir=settings_sources_project.root,
    )
    output_file = settings_sources_project.root / "output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(
            paths=[output_file],
            extend_settings=[
                settings_sources_project.module_attr,
                settings_sources_project.discovered_dir_source,
            ],
        ),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    result = exporter.run_all(DefaultSettings)

    assert output_file in result
    content = output_file.read_text()
    assert "DefaultSettings" in content
    assert "AppSettings" in content
    assert "DatabaseSettings" in content
    assert "CacheSettings" in content


def test_generator_no_override_uses_defaults(tmp_path: Path) -> None:
    """Generator without settings/extend_settings uses default_settings as-is."""

    class DefaultSettings(BaseSettings):
        x: str = "default_field"

    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    output_file = tmp_path / "output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(paths=[output_file]),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])
    result = exporter.run_all(DefaultSettings)

    assert output_file in result
    assert "DefaultSettings" in output_file.read_text()


def test_generator_settings_mixed_old_and_new_sources_are_deduplicated(settings_sources_project) -> None:
    """Generator settings should deduplicate repeated classes across source formats."""
    pse_settings = PSESettings(
        root_dir=settings_sources_project.root,
        project_dir=settings_sources_project.root,
    )
    output_file = settings_sources_project.root / "mixed-output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(
            paths=[output_file],
            settings=[
                settings_sources_project.module_name,
                settings_sources_project.module_attr,
                settings_sources_project.module_file_source,
                settings_sources_project.standalone_file_source,
            ],
        ),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    result = exporter.run_all()

    assert output_file in result
    content = output_file.read_text()
    app_settings_sections = [
        line for line in content.splitlines() if line == "AppSettings" or line.startswith("AppSettings [")
    ]
    assert app_settings_sections == ["AppSettings"]
    assert "StandaloneSettings" in content


def test_generator_settings_invalid_source_warns_and_continues(settings_sources_project) -> None:
    """Invalid settings source should emit a warning but keep valid sources."""
    pse_settings = PSESettings(
        root_dir=settings_sources_project.root,
        project_dir=settings_sources_project.root,
    )
    output_file = settings_sources_project.root / "warnings-output.txt"

    generator = SimpleGenerator(
        pse_settings,
        generator_config=SimpleSettings(
            paths=[output_file],
            settings=[
                "./missing/settings.py",
                settings_sources_project.module_attr,
                settings_sources_project.problematic_dir_source,
            ],
        ),
    )
    exporter = Exporter(settings=pse_settings, generators=[generator])

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        result = exporter.run_all()

    assert output_file in result
    content = output_file.read_text()
    assert "AppSettings" in content
    assert "ProblemSettings" in content
    assert any("Failed to import settings" in str(record.message) for record in records)


def test_exporter_caches_settings_info_across_generators(tmp_path: Path) -> None:
    """The same settings object is parsed into SettingsInfoModel only once."""
    from pydantic_settings_export.models import SettingsInfoModel

    class SharedSettings(BaseSettings):
        x: str = "shared"

    pse_settings = PSESettings(root_dir=tmp_path, project_dir=tmp_path)
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"

    gen_a = SimpleGenerator(pse_settings, generator_config=SimpleSettings(paths=[file_a]))
    gen_b = SimpleGenerator(pse_settings, generator_config=SimpleSettings(paths=[file_b]))
    exporter = Exporter(settings=pse_settings, generators=[gen_a, gen_b])

    with patch.object(
        SettingsInfoModel,
        "from_settings_model",
        wraps=SettingsInfoModel.from_settings_model,
    ) as mock_parse:
        exporter.run_all(SharedSettings)

    mock_parse.assert_called_once()
