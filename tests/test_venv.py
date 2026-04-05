"""Tests for venv detection and sys.path setup."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pydantic_settings_export.venv import (
    _auto_detect_venv,
    _get_site_packages,
    _has_poetry_config,
    _has_uv_config,
    _is_poetry_project,
    _is_uv_project,
    _is_venv,
    _poetry_venv,
    _uv_venv,
    _venv_from_path,
    setup_venv_sys_path,
)

# =============================================================================
# _is_venv
# =============================================================================


def test_is_venv_true(tmp_path):
    (tmp_path / "pyvenv.cfg").write_text("home = /usr/bin\n")
    assert _is_venv(tmp_path) is True


def test_is_venv_false_missing_cfg(tmp_path):
    assert _is_venv(tmp_path) is False


def test_is_venv_false_not_dir(tmp_path):
    assert _is_venv(tmp_path / "nonexistent") is False


# =============================================================================
# _get_site_packages
# =============================================================================


def test_get_site_packages_unix(tmp_path):
    sp = tmp_path / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)
    result = _get_site_packages(tmp_path)
    assert sp in result


def test_get_site_packages_windows(tmp_path):
    sp = tmp_path / "Lib" / "site-packages"
    sp.mkdir(parents=True)
    result = _get_site_packages(tmp_path)
    assert sp in result


def test_get_site_packages_empty(tmp_path):
    assert _get_site_packages(tmp_path) == []


def test_get_site_packages_prefers_unix(tmp_path):
    unix_sp = tmp_path / "lib" / "python3.11" / "site-packages"
    unix_sp.mkdir(parents=True)
    win_sp = tmp_path / "Lib" / "site-packages"
    win_sp.mkdir(parents=True)
    result = _get_site_packages(tmp_path)
    assert unix_sp in result


# =============================================================================
# _venv_from_path
# =============================================================================


def _make_venv(path: Path) -> Path:
    """Create a minimal valid venv structure."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "pyvenv.cfg").write_text("home = /usr/bin\n")
    sp = path / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)
    return path


def test_venv_from_path_valid(tmp_path):
    venv = _make_venv(tmp_path / "venv")
    result = _venv_from_path(venv)
    assert len(result) == 1
    assert "site-packages" in str(result[0])


def test_venv_from_path_not_dir(tmp_path):
    assert _venv_from_path(tmp_path / "missing") == []


def test_venv_from_path_not_dir_explicit(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        _venv_from_path(tmp_path / "missing", explicit=True)


def test_venv_from_path_not_a_venv(tmp_path):
    (tmp_path / "notavenv").mkdir()
    assert _venv_from_path(tmp_path / "notavenv") == []


def test_venv_from_path_not_a_venv_explicit(tmp_path):
    d = tmp_path / "notavenv"
    d.mkdir()
    with pytest.raises(ValueError, match="not a valid virtual environment"):
        _venv_from_path(d, explicit=True)


def test_venv_from_path_no_site_packages_explicit(tmp_path):
    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")
    with pytest.raises(FileNotFoundError, match="No site-packages"):
        _venv_from_path(venv, explicit=True)


# =============================================================================
# _has_poetry_config / _has_uv_config
# =============================================================================


def test_has_poetry_config_true(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = 'test'\n")
    assert _has_poetry_config(pyproject) is True


def test_has_poetry_config_false(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n")
    assert _has_poetry_config(pyproject) is False


def test_has_uv_config_true(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uv]\n")
    assert _has_uv_config(pyproject) is True


def test_has_uv_config_managed_false(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uv]\nmanaged = false\n")
    assert _has_uv_config(pyproject) is False


def test_has_uv_config_no_uv_section(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n")
    assert _has_uv_config(pyproject) is False


# =============================================================================
# _is_poetry_project / _is_uv_project
# =============================================================================


def test_is_poetry_project_via_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    assert _is_poetry_project(tmp_path) is True


def test_is_poetry_project_via_lock(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
    (tmp_path / "poetry.lock").write_text("")
    assert _is_poetry_project(tmp_path) is True


def test_is_poetry_project_false(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
    assert _is_poetry_project(tmp_path) is False


def test_is_uv_project_via_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.uv]\n")
    assert _is_uv_project(tmp_path) is True


def test_is_uv_project_via_lock(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
    (tmp_path / "uv.lock").write_text("")
    assert _is_uv_project(tmp_path) is True


def test_is_uv_project_false(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
    assert _is_uv_project(tmp_path) is False


# =============================================================================
# _poetry_venv
# =============================================================================


def test_poetry_venv_no_poetry_command(tmp_path):
    with patch("pydantic_settings_export.venv.shutil.which", return_value=None):
        assert _poetry_venv(tmp_path) == []


def test_poetry_venv_no_poetry_command_explicit(tmp_path):
    with patch("pydantic_settings_export.venv.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="poetry command not found"):
            _poetry_venv(tmp_path, explicit=True)


def test_poetry_venv_not_a_poetry_project(tmp_path):
    with patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/poetry"):
        assert _poetry_venv(tmp_path) == []


def test_poetry_venv_success(tmp_path):
    venv = _make_venv(tmp_path / ".venv")
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    mock_result = MagicMock(returncode=0, stdout=str(venv) + "\n", stderr="")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/poetry"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        result = _poetry_venv(tmp_path)
    assert len(result) == 1
    assert "site-packages" in str(result[0])


def test_poetry_venv_subprocess_fails(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    mock_result = MagicMock(returncode=1, stdout="", stderr="No venv")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/poetry"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        assert _poetry_venv(tmp_path) == []


def test_poetry_venv_empty_path(tmp_path):
    """Poetry returns exit 0 but empty stdout when no venv is created (issue #7396)."""
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    mock_result = MagicMock(returncode=0, stdout="\n", stderr="")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/poetry"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        assert _poetry_venv(tmp_path) == []


def test_poetry_venv_empty_path_explicit(tmp_path):
    """Explicit mode raises when poetry returns empty path."""
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    mock_result = MagicMock(returncode=0, stdout="\n", stderr="")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/poetry"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        with pytest.raises(RuntimeError, match="No Poetry virtual environment found"):
            _poetry_venv(tmp_path, explicit=True)


def test_poetry_venv_subprocess_fails_explicit(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    mock_result = MagicMock(returncode=1, stdout="", stderr="No venv")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/poetry"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        with pytest.raises(RuntimeError, match="Failed to get Poetry venv path"):
            _poetry_venv(tmp_path, explicit=True)


# =============================================================================
# _uv_venv
# =============================================================================


def test_uv_venv_no_uv_command(tmp_path):
    with patch("pydantic_settings_export.venv.shutil.which", return_value=None):
        assert _uv_venv(tmp_path) == []


def test_uv_venv_no_uv_command_explicit(tmp_path):
    with patch("pydantic_settings_export.venv.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="uv command not found"):
            _uv_venv(tmp_path, explicit=True)


def test_uv_venv_not_a_uv_project(tmp_path):
    with patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/uv"):
        assert _uv_venv(tmp_path) == []


def test_uv_venv_detects_dot_venv(tmp_path):
    _make_venv(tmp_path / ".venv")
    (tmp_path / "uv.lock").write_text("")

    with patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/uv"):
        result = _uv_venv(tmp_path)
    assert len(result) == 1
    assert "site-packages" in str(result[0])


def test_uv_venv_fallback_via_run(tmp_path):
    sp = tmp_path / "site-packages"
    sp.mkdir()
    (tmp_path / "uv.lock").write_text("")
    mock_result = MagicMock(returncode=0, stdout=str(sp) + "\n")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/uv"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        result = _uv_venv(tmp_path)
    assert sp in result


# =============================================================================
# _auto_detect_venv
# =============================================================================


def test_auto_detect_venv_finds_venv(tmp_path):
    _make_venv(tmp_path / "venv")
    packages, method = _auto_detect_venv(tmp_path)
    assert len(packages) == 1
    assert method == "venv"


def test_auto_detect_venv_finds_dot_venv(tmp_path):
    _make_venv(tmp_path / ".venv")
    packages, method = _auto_detect_venv(tmp_path)
    assert len(packages) == 1
    assert method == ".venv"


def test_auto_detect_venv_prefers_venv_over_dot_venv(tmp_path):
    _make_venv(tmp_path / "venv")
    _make_venv(tmp_path / ".venv")
    packages, method = _auto_detect_venv(tmp_path)
    assert str(tmp_path / "venv") in str(packages[0])
    assert method == "venv"


def test_auto_detect_venv_falls_back_to_poetry(tmp_path):
    sp = tmp_path / ".poetry-venv" / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)
    poetry_venv_root = tmp_path / ".poetry-venv"
    (poetry_venv_root / "pyvenv.cfg").write_text("home = /usr/bin\n")

    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    mock_result = MagicMock(returncode=0, stdout=str(poetry_venv_root) + "\n", stderr="")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/poetry"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        packages, method = _auto_detect_venv(tmp_path)
    assert len(packages) == 1
    assert method == "poetry"


def test_auto_detect_venv_standard_venv_beats_uv(tmp_path):
    """Regression: ./venv must take precedence over uv-managed venv."""
    standard_venv = _make_venv(tmp_path / "venv")
    sp_str = str(standard_venv / "lib" / "python3.11" / "site-packages")

    uv_sp = tmp_path / ".uv-sp"
    uv_sp.mkdir()
    mock_result = MagicMock(returncode=0, stdout=str(uv_sp) + "\n")
    (tmp_path / "uv.lock").write_text("")

    with (
        patch("pydantic_settings_export.venv.shutil.which", return_value="/usr/bin/uv"),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=mock_result),
    ):
        packages, method = _auto_detect_venv(tmp_path)

    assert len(packages) == 1
    assert str(packages[0]) == sp_str
    assert method == "venv"


def test_auto_detect_venv_uv_beats_poetry(tmp_path):
    """Regression: uv must take precedence over Poetry when no ./venv exists."""
    uv_venv = _make_venv(tmp_path / ".venv")
    (tmp_path / "uv.lock").write_text("")
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")

    poetry_root = tmp_path / ".poetry-venv"
    poetry_root.mkdir()
    (poetry_root / "pyvenv.cfg").write_text("home = /usr/bin\n")
    (poetry_root / "lib" / "python3.11" / "site-packages").mkdir(parents=True)
    poetry_mock = MagicMock(returncode=0, stdout=str(poetry_root) + "\n", stderr="")

    def which_side_effect(cmd):
        return f"/usr/bin/{cmd}"

    with (
        patch("pydantic_settings_export.venv.shutil.which", side_effect=which_side_effect),
        patch("pydantic_settings_export.venv.subprocess.run", return_value=poetry_mock),
    ):
        packages, method = _auto_detect_venv(tmp_path)

    assert len(packages) == 1
    assert str(uv_venv / "lib" / "python3.11" / "site-packages") == str(packages[0])
    assert method == ".venv"


def test_auto_detect_venv_none_found(tmp_path):
    with patch("pydantic_settings_export.venv.shutil.which", return_value=None):
        packages, method = _auto_detect_venv(tmp_path)
    assert packages == []
    assert method == ""


# =============================================================================
# setup_venv_sys_path
# =============================================================================


def test_setup_venv_sys_path_none(tmp_path):
    original = sys.path.copy()
    setup_venv_sys_path(None, tmp_path)
    assert sys.path == original


def test_setup_venv_sys_path_empty_string(tmp_path):
    original = sys.path.copy()
    setup_venv_sys_path("", tmp_path)
    assert sys.path == original


def test_setup_venv_sys_path_adds_packages(tmp_path):
    _make_venv(tmp_path / "venv")
    sp_str = str(tmp_path / "venv" / "lib" / "python3.11" / "site-packages")

    original = sys.path.copy()
    try:
        setup_venv_sys_path("auto", tmp_path)
        assert sp_str in sys.path
    finally:
        sys.path[:] = original


def test_setup_venv_sys_path_no_duplicates(tmp_path):
    _make_venv(tmp_path / "venv")
    sp_str = str(tmp_path / "venv" / "lib" / "python3.11" / "site-packages")

    original = sys.path.copy()
    try:
        setup_venv_sys_path("auto", tmp_path)
        count_before = sys.path.count(sp_str)
        setup_venv_sys_path("auto", tmp_path)
        assert sys.path.count(sp_str) == count_before
    finally:
        sys.path[:] = original


def test_setup_venv_sys_path_custom_path(tmp_path):
    venv = _make_venv(tmp_path / "myvenv")
    sp_str = str(tmp_path / "myvenv" / "lib" / "python3.11" / "site-packages")

    original = sys.path.copy()
    try:
        setup_venv_sys_path(str(venv), tmp_path)
        assert sp_str in sys.path
    finally:
        sys.path[:] = original


def test_setup_venv_sys_path_relative_path(tmp_path):
    _make_venv(tmp_path / "myvenv")
    sp_str = str(tmp_path / "myvenv" / "lib" / "python3.11" / "site-packages")

    original = sys.path.copy()
    try:
        setup_venv_sys_path("myvenv", tmp_path)
        assert sp_str in sys.path
    finally:
        sys.path[:] = original


def test_setup_venv_sys_path_invalid_explicit_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        setup_venv_sys_path(str(tmp_path / "nonexistent"), tmp_path)
