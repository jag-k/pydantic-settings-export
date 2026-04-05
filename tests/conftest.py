from typing import Literal

import pytest
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, MongoDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
