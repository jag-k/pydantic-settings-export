"""Utilities for detecting and configuring virtual environment paths for sys.path."""

import logging
import shutil
import subprocess  # noqa: S404
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    from tomli import load as toml_load
else:
    from tomllib import load as toml_load

__all__ = ("setup_venv_sys_path",)

logger = logging.getLogger(__name__)


def _is_venv(path: Path) -> bool:
    """Check if the given path is a valid virtual environment.

    :param path: Path to check.
    :return: True if the path is a valid venv directory.
    """
    return (path / "pyvenv.cfg").is_file()


def _get_site_packages(venv_path: Path) -> list[Path]:
    """Get site-packages directories from a virtual environment.

    :param venv_path: Path to the virtual environment.
    :return: List of existing site-packages directories.
    """
    packages = list(venv_path.glob("lib/python*/site-packages"))
    if not packages:
        win_path = venv_path / "Lib" / "site-packages"
        if win_path.is_dir():
            packages = [win_path]
    return packages


def _venv_from_path(venv_path: Path, *, explicit: bool = False) -> list[Path]:
    """Resolve site-packages from a venv directory.

    :param venv_path: Path to the virtual environment directory.
    :param explicit: If True, raise errors when the venv is invalid or missing.
    :return: List of site-packages directories.
    :raise FileNotFoundError: If explicit=True and the directory does not exist.
    :raise ValueError: If explicit=True and the path is not a valid venv.
    """
    if not venv_path.is_dir():
        if explicit:
            raise FileNotFoundError(f"Virtual environment not found at {venv_path}")
        return []
    if not _is_venv(venv_path):
        if explicit:
            raise ValueError(f"The path {venv_path} is not a valid virtual environment (no pyvenv.cfg found)")
        return []
    packages = _get_site_packages(venv_path)
    if not packages and explicit:
        raise FileNotFoundError(f"No site-packages found in virtual environment at {venv_path}")
    return packages


def _read_pyproject_tool(pyproject_path: Path) -> dict:
    """Read the [tool] section from a pyproject.toml file.

    :param pyproject_path: Path to pyproject.toml.
    :return: The [tool] section as a dict, or an empty dict on failure.
    """
    try:
        with pyproject_path.open("rb") as f:
            return toml_load(f).get("tool", {})
    except Exception:
        return {}


def _has_poetry_config(pyproject_path: Path) -> bool:
    """Check if pyproject.toml contains a [tool.poetry] section.

    :param pyproject_path: Path to pyproject.toml.
    :return: True if [tool.poetry] is present.
    """
    return "poetry" in _read_pyproject_tool(pyproject_path)


def _has_uv_config(pyproject_path: Path) -> bool:
    """Check if pyproject.toml has [tool.uv] without ``managed = false``.

    :param pyproject_path: Path to pyproject.toml.
    :return: True if [tool.uv] is present and ``managed`` is not False.
    """
    uv = _read_pyproject_tool(pyproject_path).get("uv")
    if uv is None:
        return False
    return uv.get("managed", True) is not False


def _is_poetry_project(project_dir: Path) -> bool:
    """Check if a directory contains a Poetry-managed project.

    :param project_dir: The project directory.
    :return: True if it's a Poetry project.
    """
    pyproject = project_dir / "pyproject.toml"
    poetry_lock = project_dir / "poetry.lock"
    return (pyproject.is_file() and _has_poetry_config(pyproject)) or poetry_lock.is_file()


def _is_uv_project(project_dir: Path) -> bool:
    """Check if a directory contains a uv-managed project.

    :param project_dir: The project directory.
    :return: True if it's a uv project.
    """
    pyproject = project_dir / "pyproject.toml"
    uv_lock = project_dir / "uv.lock"
    return (pyproject.is_file() and _has_uv_config(pyproject)) or uv_lock.is_file()


def _run_poetry_env_path(project_dir: Path, poetry_cmd: str, *, explicit: bool = False) -> str | None:
    """Run ``poetry env info --path`` and return the stripped path string.

    :param project_dir: The project directory (used as cwd).
    :param poetry_cmd: Full path to the poetry executable.
    :param explicit: If True, raise errors on failure instead of returning None.
    :return: The venv path string, or None on failure.
    :raise RuntimeError: If explicit=True and the call fails or returns no path.
    """
    try:
        result = subprocess.run(  # noqa: S603
            [poetry_cmd, "env", "info", "--path"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        if explicit:
            raise RuntimeError(f"Failed to run poetry: {e}") from e
        return None

    if result.returncode != 0:
        if explicit:
            raise RuntimeError(f"Failed to get Poetry venv path: {result.stderr.strip()}")
        return None

    venv_path_str = result.stdout.strip()
    if not venv_path_str:
        if explicit:
            raise RuntimeError(
                f"No Poetry virtual environment found for {project_dir}. "
                "Run `poetry install` or `poetry env use <python>` to create one."
            )
        return None

    return venv_path_str


def _poetry_venv(project_dir: Path, *, explicit: bool = False) -> list[Path]:
    """Get site-packages from a Poetry-managed virtual environment.

    :param project_dir: The project directory.
    :param explicit: If True, raise errors on failure instead of returning an empty list.
    :return: List of site-packages directories.
    :raise RuntimeError: If explicit=True and poetry or its venv cannot be found.
    """
    poetry_cmd = shutil.which("poetry")
    if not poetry_cmd:
        if explicit:
            raise RuntimeError("poetry command not found. Please install Poetry.")
        return []

    if not _is_poetry_project(project_dir):
        if explicit:
            raise RuntimeError(
                f"No Poetry project found in {project_dir}. "
                "Ensure [tool.poetry] is in pyproject.toml or poetry.lock exists."
            )
        return []

    venv_path_str = _run_poetry_env_path(project_dir, poetry_cmd, explicit=explicit)
    if not venv_path_str:
        return []

    return _venv_from_path(Path(venv_path_str), explicit=explicit)


def _uv_site_packages_via_run(project_dir: Path, *, explicit: bool = False) -> list[Path]:
    """Fallback: ask uv to print site-packages via ``uv run python``.

    :param project_dir: The project directory.
    :param explicit: If True, raise errors on failure.
    :return: List of site-packages directories.
    :raise RuntimeError: If explicit=True and the call fails.
    """
    uv_cmd = shutil.which("uv")
    if not uv_cmd:
        if explicit:
            raise RuntimeError("Failed to run uv: command not found")
        return []
    try:
        result = subprocess.run(  # noqa: S603
            [
                uv_cmd,
                "run",
                "--project",
                str(project_dir),
                "python",
                "-c",
                "import site; print(site.getsitepackages()[0])",
            ],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        if explicit:
            raise RuntimeError(f"Failed to run uv: {e}") from e
        return []

    if result.returncode == 0:
        site_pkg = Path(result.stdout.strip())
        if site_pkg.is_dir():
            return [site_pkg]
    return []


def _uv_venv(project_dir: Path, *, explicit: bool = False) -> list[Path]:
    """Get site-packages from a uv-managed virtual environment.

    :param project_dir: The project directory.
    :param explicit: If True, raise errors on failure instead of returning an empty list.
    :return: List of site-packages directories.
    :raise RuntimeError: If explicit=True and uv or its venv cannot be found.
    """
    if not shutil.which("uv"):
        if explicit:
            raise RuntimeError("uv command not found. Please install uv.")
        return []

    if not _is_uv_project(project_dir):
        if explicit:
            raise RuntimeError(
                f"No uv project found in {project_dir}. "
                "Ensure [tool.uv] is in pyproject.toml (without managed = false) or uv.lock exists."
            )
        return []

    packages = _venv_from_path(project_dir / ".venv")
    if packages:
        return packages

    packages = _uv_site_packages_via_run(project_dir, explicit=explicit)
    if packages:
        return packages

    if explicit:
        raise RuntimeError(f"No uv virtual environment found in {project_dir}")
    return []


def _auto_detect_venv(project_dir: Path) -> list[Path]:
    """Auto-detect a virtual environment in the project directory.

    Detection order:

    1. ``./venv``
    2. ``./.venv``
    3. uv (if the ``uv`` CLI and project config are present)
    4. Poetry (if the ``poetry`` CLI and project config are present)

    :param project_dir: The project directory.
    :return: List of site-packages directories from the detected venv.
    """
    for subdir in ("venv", ".venv"):
        packages = _venv_from_path(project_dir / subdir)
        if packages:
            logger.debug("Auto-detected venv at %s/%s", project_dir, subdir)
            return packages

    packages = _uv_venv(project_dir)
    if packages:
        logger.debug("Auto-detected uv venv for %s", project_dir)
        return packages

    packages = _poetry_venv(project_dir)
    if packages:
        logger.debug("Auto-detected Poetry venv for %s", project_dir)
        return packages

    logger.debug("No virtual environment auto-detected for %s", project_dir)
    return []


def setup_venv_sys_path(venv: str | None, project_dir: Path) -> None:
    """Add the virtual environment's site-packages to :data:`sys.path`.

    :param venv: The venv configuration value:

        - ``None`` or empty string — disabled (no-op).
        - ``"auto"`` — auto-detect from ``./venv``, ``./.venv``, uv, or Poetry.
        - ``"poetry"`` — use the Poetry-managed venv.
        - ``"uv"`` — use the uv-managed venv.
        - Any other non-empty string — treated as a path to the venv directory;
          relative paths are resolved against *project_dir*.
    :param project_dir: The project directory used for detection and resolving relative paths.
    """
    if not venv:
        return

    if venv == "auto":
        packages = _auto_detect_venv(project_dir)
    elif venv == "poetry":
        packages = _poetry_venv(project_dir, explicit=True)
    elif venv == "uv":
        packages = _uv_venv(project_dir, explicit=True)
    else:
        venv_path = Path(venv)
        if not venv_path.is_absolute():
            venv_path = project_dir / venv_path
        packages = _venv_from_path(venv_path, explicit=True)

    for pkg in packages:
        pkg_str = str(pkg)
        if pkg_str not in sys.path:
            sys.path.insert(0, pkg_str)
            logger.debug("Added %s to sys.path", pkg_str)
