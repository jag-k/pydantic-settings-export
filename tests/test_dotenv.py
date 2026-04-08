"""Tests for DotEnvGenerator."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings_export import SettingsInfoModel
from pydantic_settings_export.generators.dotenv import DotEnvGenerator


class SimpleSettings(BaseSettings):
    """Simple settings for testing."""

    host: str = Field(default="localhost", description="The host")
    port: int = Field(default=8080, description="The port")
    debug: bool = Field(default=False, description="Debug mode")


def test_dotenv_instance_always_uses_defaults() -> None:
    """Instance values must NOT appear in .env.example — only defaults/examples.

    .env.example is a template. Values populated from a loaded .env file (or any
    other env source) must not leak into the generated output.
    """
    instance = SimpleSettings(host="production.example.com", port=443, debug=True)
    info = SettingsInfoModel.from_settings_model(instance)

    generator = DotEnvGenerator()
    result = generator.generate(info)

    expected = """\
### SimpleSettings

# HOST="localhost"
# PORT=8080
# DEBUG=false
"""
    assert result == expected


def test_dotenv_instance_same_as_default_behaves_like_class() -> None:
    """When value equals default, should behave like class (no duplication)."""
    instance = SimpleSettings()
    info_instance = SettingsInfoModel.from_settings_model(instance)
    info_class = SettingsInfoModel.from_settings_model(SimpleSettings)

    generator = DotEnvGenerator()
    result_instance = generator.generate(info_instance)
    result_class = generator.generate(info_class)

    assert result_instance == result_class


def test_dotenv_nested_instance_uses_defaults() -> None:
    """Nested instances should also use defaults, not instance values."""

    class Database(BaseSettings):
        host: str = Field(default="localhost", description="DB host")
        port: int = Field(default=5432, description="DB port")

    class AppSettings(BaseSettings):
        model_config = SettingsConfigDict(env_nested_delimiter="_")
        debug: bool = Field(default=False, description="Debug mode")
        database: Database = Field(default_factory=Database)

    db = Database(host="prod-db.example.com", port=5433)
    instance = AppSettings(debug=True, database=db)
    info = SettingsInfoModel.from_settings_model(instance)

    generator = DotEnvGenerator()
    result = generator.generate(info)

    expected = """\
### AppSettings

# DEBUG=false

### Database

# DATABASE_HOST="localhost"
# DATABASE_PORT=5432
"""
    assert result == expected
