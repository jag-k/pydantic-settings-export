"""Tests for AbstractGenerator / AbstractEnvGenerator validation and file_paths."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from pydantic_settings_export.generators.abstract import (
    AbstractEnvGenerator,
    AbstractGenerator,
    BaseGeneratorSettings,
)
from pydantic_settings_export.settings import PSESettings


# fixtures
@pytest.fixture(autouse=True)
def _restore_all_generators():
    """Restore ALL_GENERATORS to its original state after each test."""
    snapshot = AbstractGenerator.ALL_GENERATORS.copy()
    yield
    AbstractGenerator.ALL_GENERATORS[:] = snapshot


@pytest.fixture
def file_paths_gen() -> type[AbstractGenerator]:  # type: ignore[type-arg]
    """A minimal concrete generator for file_paths tests.

    Defined inside a fixture so it is registered (and cleaned up) per test via
    the autouse ``_restore_all_generators`` fixture.
    """

    class FPSettings(BaseGeneratorSettings):
        pass

    class FPGenerator(AbstractGenerator[FPSettings]):
        name = "test_fp_helper_gen"
        config = FPSettings

        def generate_single(self, settings_info, level: int = 1) -> str:  # type: ignore[override]
            return ""

    return FPGenerator


# __init_subclass__: check_name kwarg
def test_check_name_kwarg_raises_without_name():
    with pytest.raises(ValueError, match="must have a name"):

        class _NoName(AbstractGenerator, check_name=True):  # type: ignore[call-arg]
            pass


# __init_subclass__: config validation
def test_missing_config_raises():
    with pytest.raises(ValueError, match="must have a config"):

        class _NoConfig(AbstractGenerator):
            name = "_no_config_gen"

            def generate_single(self, settings_info, level: int = 1) -> str:  # type: ignore[override]
                return ""


def test_config_wrong_base_raises():
    class _BadConfig(BaseModel):
        pass

    with pytest.raises(ValueError, match="not inherited from BaseGeneratorSettings"):

        class _BadBase(AbstractGenerator):
            name = "_bad_base_gen"
            config = _BadConfig  # type: ignore[assignment]

            def generate_single(self, settings_info, level: int = 1) -> str:  # type: ignore[override]
                return ""


# __init_subclass__: duplicate name
def test_duplicate_name_raises():
    class _UniqueSettings(BaseGeneratorSettings):
        pass

    class _First(AbstractGenerator[_UniqueSettings]):
        name = "dup_test_gen"
        config = _UniqueSettings

        def generate_single(self, settings_info, level: int = 1) -> str:  # type: ignore[override]
            return ""

    with pytest.raises(ValueError, match="already exists"):

        class _Second(AbstractGenerator[_UniqueSettings]):
            name = "dup_test_gen"
            config = _UniqueSettings

            def generate_single(self, settings_info, level: int = 1) -> str:  # type: ignore[override]
                return ""


# AbstractEnvGenerator: config must inherit BaseEnvGeneratorSettings
def test_env_generator_non_env_config_raises():
    class _PlainSettings(BaseGeneratorSettings):
        pass

    with pytest.raises(ValueError, match="not inherited from BaseEnvGeneratorSettings"):

        class _BadEnvGen(AbstractEnvGenerator):
            name = "bad_env_config_gen"
            config = _PlainSettings  # BaseGeneratorSettings, not BaseEnvGeneratorSettings

            def generate_single(self, settings_info, level: int = 1) -> str:  # type: ignore[override]
                return ""


# AbstractEnvGenerator.apply_env_case
@pytest.mark.parametrize(
    ("to_upper_case", "case_sensitive", "expected"),
    [
        (True, False, "MYKEY"),
        (False, False, "MyKey"),
        (True, True, "MyKey"),
        (False, True, "MyKey"),
    ],
)
def test_apply_env_case_contract(to_upper_case: bool, case_sensitive: bool, expected: str) -> None:
    result = AbstractEnvGenerator.apply_env_case(
        "MyKey",
        to_upper_case=to_upper_case,
        case_sensitive=case_sensitive,
    )
    assert result == expected


# file_paths
def test_file_paths_empty_when_no_paths(file_paths_gen: type[AbstractGenerator]) -> None:  # type: ignore[type-arg]
    gen = file_paths_gen(generator_config=file_paths_gen.config(paths=[]))
    assert gen.file_paths() == []


def test_file_paths_relative_resolved_against_root_dir(
    file_paths_gen: type[AbstractGenerator],
    tmp_path: Path,  # type: ignore[type-arg]
) -> None:
    settings = PSESettings(root_dir=tmp_path)
    gen = file_paths_gen(settings=settings, generator_config=file_paths_gen.config(paths=[Path("output.txt")]))
    assert gen.file_paths() == [tmp_path / "output.txt"]


def test_file_paths_absolute_kept_as_is(file_paths_gen: type[AbstractGenerator], tmp_path: Path) -> None:  # type: ignore[type-arg]
    abs_path = tmp_path / "abs_output.txt"
    gen = file_paths_gen(generator_config=file_paths_gen.config(paths=[abs_path]))
    assert gen.file_paths() == [abs_path]


# run(): all settings info combined into each output file
def test_run_writes_all_settings_into_file(
    file_paths_gen: type[AbstractGenerator],
    tmp_path: Path,
) -> None:  # type: ignore[type-arg]
    from pydantic_settings_export.models import SettingsInfoModel

    class _ContentGen(file_paths_gen):  # type: ignore[valid-type,misc]
        name = "_test_combined_content_gen"

        def generate_single(self, settings_info, level: int = 1) -> str:  # type: ignore[override]
            return settings_info.name

    settings = PSESettings(root_dir=tmp_path)
    gen = _ContentGen(
        settings=settings,
        generator_config=file_paths_gen.config(paths=[Path("all.txt")], per_settings=False),
    )
    si_a = SettingsInfoModel(name="Alpha", fields=[])
    si_b = SettingsInfoModel(name="Beta", fields=[])

    written = gen.run(si_a, si_b)

    assert len(written) == 1
    assert written[0] == tmp_path / "all.txt"
    content = (tmp_path / "all.txt").read_text()
    assert "Alpha" in content
    assert "Beta" in content
