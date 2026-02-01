"""Tests for DotEnvGenerator."""

from pydantic import Field
from pydantic_settings import BaseSettings

from pydantic_settings_export import SettingsInfoModel
from pydantic_settings_export.generators.dotenv import DotEnvGenerator


class SimpleSettings(BaseSettings):
    """Simple settings for testing."""

    host: str = Field(default="localhost", description="The host")
    port: int = Field(default=8080, description="The port")
    debug: bool = Field(default=False, description="Debug mode")


def test_dotenv_instance_shows_default_commented_and_value_uncommented() -> None:
    """Instance should show default commented and value uncommented."""
    instance = SimpleSettings(host="production.example.com", port=443, debug=True)
    info = SettingsInfoModel.from_settings_model(instance)

    generator = DotEnvGenerator()
    result = generator.generate(info)

    expected = """\
### SimpleSettings

# HOST="localhost"  # default
HOST="production.example.com"
# PORT=8080  # default
PORT=443
# DEBUG=false  # default
DEBUG=true
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


def test_dotenv_nested_instance() -> None:
    """Nested instances should propagate their values."""

    class Database(BaseSettings):
        host: str = Field(default="localhost", description="DB host")
        port: int = Field(default=5432, description="DB port")

    class AppSettings(BaseSettings):
        debug: bool = Field(default=False, description="Debug mode")
        database: Database = Field(default_factory=Database)

    db = Database(host="prod-db.example.com", port=5433)
    instance = AppSettings(debug=True, database=db)
    info = SettingsInfoModel.from_settings_model(instance)

    generator = DotEnvGenerator()
    result = generator.generate(info)

    expected = """\
### AppSettings

# DEBUG=false  # default
DEBUG=true

### Database

# DATABASE_HOST="localhost"  # default
DATABASE_HOST="prod-db.example.com"
# DATABASE_PORT=5432  # default
DATABASE_PORT=5433
"""
    assert result == expected
