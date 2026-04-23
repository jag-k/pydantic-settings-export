from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, MongoDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class SettingsSourcesProject:
    """Temporary project tree with real settings modules for import tests."""

    root: Path
    module_name: str
    module_attr: str
    module_file: Path
    package_dir: Path
    discovered_dir: Path
    problematic_dir: Path
    empty_dir: Path
    standalone_file: Path
    no_settings_file: Path
    broken_syntax_file: Path
    broken_import_file: Path
    text_file: Path

    @property
    def module_file_source(self) -> str:
        """Path to the main settings file relative to the project root."""
        return f"./{self.module_file.relative_to(self.root)!s}"

    @property
    def discovered_dir_source(self) -> str:
        """Path to the recursive discovery directory relative to the project root."""
        return f"./{self.discovered_dir.relative_to(self.root)!s}"

    @property
    def standalone_file_source(self) -> str:
        """Path to the standalone settings file relative to the project root."""
        return f"./{self.standalone_file.relative_to(self.root)!s}"

    @property
    def problematic_dir_source(self) -> str:
        """Path to the directory with partial import failures."""
        return f"./{self.problematic_dir.relative_to(self.root)!s}"

    @property
    def no_settings_file_source(self) -> str:
        """Path to the file without settings relative to the project root."""
        return f"./{self.no_settings_file.relative_to(self.root)!s}"

    @property
    def broken_syntax_source(self) -> str:
        """Path to the file with a syntax error relative to the project root."""
        return f"./{self.broken_syntax_file.relative_to(self.root)!s}"

    @property
    def broken_import_source(self) -> str:
        """Path to the file with an import error relative to the project root."""
        return f"./{self.broken_import_file.relative_to(self.root)!s}"

    @property
    def text_file_source(self) -> str:
        """Path to the non-Python file relative to the project root."""
        return f"./{self.text_file.relative_to(self.root)!s}"


@dataclass
class CollidingSettingsProject:
    """Temporary project tree with colliding settings names across files."""

    root: Path
    sources: dict[str, list[str]]

    def get_sources(self, case_name: str) -> list[str]:
        """Get sources for a collision case."""
        return self.sources[case_name]


@pytest.fixture
def simple_settings() -> type[BaseSettings]:
    """Minimal settings with one field."""

    class Settings(BaseSettings):
        """Test settings."""

        field: str = Field(default="value", description="Field description")

    return Settings


@pytest.fixture
def mixed_settings() -> type[BaseSettings]:
    """Settings with required and optional fields."""

    class Settings(BaseSettings):
        """Mixed settings."""

        required: str = Field(description="Required field")
        optional: str = Field(default="value", description="Optional field")

    return Settings


@pytest.fixture
def nested_settings() -> type[BaseSettings]:
    """Settings with child settings."""

    class Database(BaseModel):
        """Database config."""

        host: str = Field(default="localhost", description="Database host")
        port: int = Field(description="Required port")

    class Settings(BaseSettings):
        """Main settings."""

        model_config = SettingsConfigDict(env_nested_delimiter="_")

        database: Database = Field(default_factory=Database)

    return Settings


@pytest.fixture
def full_settings() -> type[BaseSettings]:
    """Extensive configurations for integration tests.

    This is a slightly shortened version taken from the settings of an actual application.
    It contains all possible field types and is used to test the exporter against real-world settings.
    """

    class MongoSettings(BaseModel):
        """MongoDB connection settings."""

        model_config = ConfigDict(title="MongoDB settings")

        mongodb_url: MongoDsn = Field(MongoDsn("mongodb://localhost:27017"), description="MongoDB connection URL")
        mongodb_db_name: str = Field("test-db", description="MongoDB database name")

    class APISettings(BaseModel):
        host: str = Field("0.0.0.0", description="API host")  # noqa: S104
        port: int = Field(8000, description="API port")

    class OpenRouterSettings(BaseModel):
        """OpenRouter models settings."""

        model_config = ConfigDict(title="OpenRouter settings")

        api_key: SecretStr = Field(description="OpenRouter API key")
        model: str = Field("google/gemini-2.5-flash", description="OpenRouter model name")
        base_url: AnyHttpUrl = Field(AnyHttpUrl("https://openrouter.ai/api/v1"), description="OpenRouter API base URL")

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            env_nested_delimiter="__",
        )

        log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
            "INFO",
            description="The log level to use",
        )
        log_format: str = Field(
            "%(levelname)-8s | %(asctime)s | %(name)s | %(message)s",
            description="The log format to use",
        )

        mongodb: MongoSettings = Field(default_factory=MongoSettings)
        openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
        api: APISettings = Field(default_factory=APISettings)

    return Settings


@pytest.fixture
def settings_sources_project(tmp_path: Path) -> SettingsSourcesProject:
    """Create a temporary project tree with real settings modules."""
    package_name = f"sample_app_{tmp_path.name.replace('-', '_')}"
    package_dir = tmp_path / package_name
    discovered_dir = package_dir / "discovered"
    nested_dir = discovered_dir / "nested"
    problematic_dir = tmp_path / "problematic"
    empty_dir = tmp_path / "empty_settings"

    for directory in (package_dir, discovered_dir, nested_dir, problematic_dir, empty_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for directory in (package_dir, discovered_dir, nested_dir, problematic_dir):
        (directory / "__init__.py").write_text("")

    module_file = package_dir / "settings.py"
    module_file.write_text(
        'from pydantic_settings import BaseSettings\n\n\nclass AppSettings(BaseSettings):\n    app_name: str = "demo"\n'
    )

    (package_dir / "reexport.py").write_text("from .settings import AppSettings\n")

    (discovered_dir / "database.py").write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "\nclass DatabaseSettings(BaseSettings):\n"
        '    dsn: str = "sqlite"\n'
    )

    (nested_dir / "cache.py").write_text(
        "from pydantic_settings import BaseSettings\n\n\nclass CacheSettings(BaseSettings):\n    ttl: int = 60\n"
    )

    standalone_file = tmp_path / "standalone_settings.py"
    standalone_file.write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "\nclass StandaloneSettings(BaseSettings):\n"
        "    enabled: bool = True\n"
    )

    no_settings_file = tmp_path / "no_settings.py"
    no_settings_file.write_text('def make_value() -> str:\n    return "value"\n')

    broken_syntax_file = tmp_path / "broken_syntax.py"
    broken_syntax_file.write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "\nclass BrokenSettings(BaseSettings)\n"
        "    value: str = 'broken'\n"
    )

    broken_import_file = tmp_path / "broken_import.py"
    broken_import_file.write_text(
        "import definitely_missing_module\n\n"
        "from pydantic_settings import BaseSettings\n\n"
        "\nclass BrokenImportSettings(BaseSettings):\n"
        "    value: str = 'broken'\n"
    )

    (problematic_dir / "good_settings.py").write_text(
        "from pydantic_settings import BaseSettings\n\n\nclass ProblemSettings(BaseSettings):\n    retries: int = 3\n"
    )

    (problematic_dir / "broken_import.py").write_text(
        "import definitely_missing_module\n\n"
        "from pydantic_settings import BaseSettings\n\n"
        "\nclass ProblemBrokenSettings(BaseSettings):\n"
        "    value: str = 'broken'\n"
    )

    text_file = tmp_path / "notes.txt"
    text_file.write_text("not python\n")

    return SettingsSourcesProject(
        root=tmp_path,
        module_name=f"{package_name}.settings",
        module_attr=f"{package_name}.settings:AppSettings",
        module_file=module_file,
        package_dir=package_dir,
        discovered_dir=discovered_dir,
        problematic_dir=problematic_dir,
        empty_dir=empty_dir,
        standalone_file=standalone_file,
        no_settings_file=no_settings_file,
        broken_syntax_file=broken_syntax_file,
        broken_import_file=broken_import_file,
        text_file=text_file,
    )


@pytest.fixture
def colliding_settings_project(tmp_path: Path) -> CollidingSettingsProject:
    """Create real settings files with colliding class names."""
    package_name = f"collision_app_{tmp_path.name.replace('-', '_')}"
    package_dir = tmp_path / package_name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "__init__.py").write_text("")

    same_dir = package_dir / "same_impl"
    defaults_dir = package_dir / "different_defaults"
    shape_dir = package_dir / "different_shape"

    for directory in (same_dir, defaults_dir, shape_dir):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").write_text("")

    (same_dir / "first.py").write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "class DuplicateSettings(BaseSettings):\n"
        '    value: str = "same"\n'
    )
    (same_dir / "second.py").write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "class DuplicateSettings(BaseSettings):\n"
        '    value: str = "same"\n'
    )

    (defaults_dir / "first.py").write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "class DuplicateDefaultsSettings(BaseSettings):\n"
        '    value: str = "alpha"\n'
    )
    (defaults_dir / "second.py").write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "class DuplicateDefaultsSettings(BaseSettings):\n"
        '    value: str = "beta"\n'
    )

    (shape_dir / "first.py").write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "class DuplicateShapeSettings(BaseSettings):\n"
        "    host: str = 'localhost'\n"
    )
    (shape_dir / "second.py").write_text(
        "from pydantic_settings import BaseSettings\n\n"
        "class DuplicateShapeSettings(BaseSettings):\n"
        "    port: int = 5432\n"
    )

    return CollidingSettingsProject(
        root=tmp_path,
        sources={
            "same_impl": [
                f"./{(same_dir / 'first.py').relative_to(tmp_path)!s}",
                f"./{(same_dir / 'second.py').relative_to(tmp_path)!s}",
            ],
            "different_defaults": [
                f"./{(defaults_dir / 'first.py').relative_to(tmp_path)!s}",
                f"./{(defaults_dir / 'second.py').relative_to(tmp_path)!s}",
            ],
            "different_shape": [
                f"./{(shape_dir / 'first.py').relative_to(tmp_path)!s}",
                f"./{(shape_dir / 'second.py').relative_to(tmp_path)!s}",
            ],
        },
    )
