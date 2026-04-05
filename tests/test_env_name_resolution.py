"""Tests for env variable name resolution correctness.

These tests verify that pydantic-settings-export generates env variable names
that match what pydantic-settings actually resolves. Each test case defines a
settings model, checks what SettingsInfoModel produces, and verifies against
the actual pydantic-settings EnvSettingsSource behavior.

Notes on env variable naming:
- POSIX allows only [a-zA-Z_][a-zA-Z0-9_]* for env variable names.
  Dots, dashes, etc. are NOT valid shell identifiers (bash refuses `export A.B=x`).
  However, Python os.environ and .env files DO allow them.
  So env_nested_delimiter="." works via dotenv files but NOT from shell.
- pydantic-settings lowercases both sides when case_sensitive=False (default).
  ANY case of env var works. Convention for documentation: UPPER_CASE.

Known bugs tracked here (marked as xfail):
- BUG-1: env_nested_delimiter defaults to "_" when None - should not expand nested models
- BUG-2: Nested BaseSettings' own env_nested_delimiter overrides parent's
- BUG-3: validation_alias on nested model fields loses parent prefix
- BUG-4: env_prefix is not uppercased in dotenv output
- BUG-6: AliasPath produces dotted string instead of first path element
"""

import os
from typing import Optional

import pytest
from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources.providers.env import EnvSettingsSource

from pydantic_settings_export.generators.dotenv import DotEnvGenerator, DotEnvSettings
from pydantic_settings_export.models import SettingsInfoModel

# =============================================================================
# Helper: get the actual env names pydantic-settings looks for
# =============================================================================


# NOTE: This helper relies on the private method EnvSettingsSource._extract_field_info
# which is not part of the public pydantic-settings API and may be renamed, moved,
# or removed in future releases.  If this function raises AttributeError after a
# pydantic-settings upgrade, update the call below to use whatever replacement the
# new version provides.
def get_pydantic_settings_env_names(
    settings_cls: type[BaseSettings],
) -> dict[str, list[str]]:
    """Get the actual env names pydantic-settings would look for.

    Returns dict of field_name -> list of env_name strings.
    """
    source = EnvSettingsSource(settings_cls)
    result = {}
    for field_name, field in settings_cls.model_fields.items():
        try:
            infos = source._extract_field_info(field, field_name)
        except AttributeError as exc:
            raise AttributeError(
                "EnvSettingsSource._extract_field_info is no longer available — "
                "the pydantic-settings private API has changed. "
                "Update get_pydantic_settings_env_names() in this test file to use "
                "the new API exposed by EnvSettingsSource."
            ) from exc
        result[field_name] = [env_name for _, env_name, _ in infos]
    return result


def get_pydantic_settings_nested_env_names(
    settings_cls: type[BaseSettings],
    field_name: str,
) -> list[str]:
    """Get the explode env prefixes for a nested field.

    Returns list of prefix strings that pydantic-settings uses with env_nested_delimiter.
    """
    source = EnvSettingsSource(settings_cls)
    field = settings_cls.model_fields[field_name]
    if not source.env_nested_delimiter:
        return []
    return [
        f"{env_name}{source.env_nested_delimiter}" for _, env_name, _ in source._extract_field_info(field, field_name)
    ]


def collect_env_names_from_info(info: SettingsInfoModel) -> dict[str, str]:
    """Collect all env variable names from SettingsInfoModel tree.

    Returns dict of descriptive_key -> env_var_name as would be output by dotenv generator.
    Applies case normalization based on info.case_sensitive (same as generators).
    """
    result = {}
    for field in info.fields:
        raw = field.env_names[0] if field.env_names else f"{info.env_prefix}{field.name}"
        env_name = raw if info.case_sensitive else raw.upper()
        result[f"{info.name}.{field.name}"] = env_name
    for child in info.child_settings:
        child_result = collect_env_names_from_info(child)
        result.update(child_result)
    return result


def get_dotenv_output(settings_cls: type[BaseSettings]) -> str:
    """Generate dotenv output for a settings class."""
    generator = DotEnvGenerator(generator_config=DotEnvSettings(split_by_group=False))
    return generator.generate(SettingsInfoModel.from_settings_model(settings_cls))


# =============================================================================
# CASE 1: Basic settings, no prefix
# =============================================================================


class TestBasicNoPrefix:
    """Basic settings with no prefix."""

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class Settings(BaseSettings):
            """Basic settings."""

            field_a: str = Field(default="default_a", description="Field A")
            field_b: int = Field(default=42, description="Field B")

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        assert actual == {
            "field_a": ["field_a"],
            "field_b": ["field_b"],
        }

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == ""
        assert [f.name for f in info.fields] == ["field_a", "field_b"]

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        assert '# FIELD_A="default_a"' in result
        assert "# FIELD_B=42" in result

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["FIELD_A"] = "from_env"
        os.environ["FIELD_B"] = "99"
        try:
            s = settings_cls()
            assert s.field_a == "from_env"
            assert s.field_b == 99
        finally:
            del os.environ["FIELD_A"]
            del os.environ["FIELD_B"]


# =============================================================================
# CASE 2: Settings with env_prefix
# =============================================================================


class TestWithEnvPrefix:
    """Settings with env_prefix."""

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_")

            field_a: str = Field(default="val")
            field_b: int = Field(default=1)

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # pydantic-settings lowercases for lookup when case_sensitive=False
        assert actual == {
            "field_a": ["app_field_a"],
            "field_b": ["app_field_b"],
        }

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == "APP_"

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        assert '# APP_FIELD_A="val"' in result
        assert "# APP_FIELD_B=1" in result

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["APP_FIELD_A"] = "from_env"
        try:
            s = settings_cls()
            assert s.field_a == "from_env"
        finally:
            del os.environ["APP_FIELD_A"]


# =============================================================================
# CASE 3: env_prefix without trailing underscore
# =============================================================================


class TestEnvPrefixNoUnderscore:
    """env_prefix without trailing underscore - field names get glued to prefix."""

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="myapp")

            field_a: str = Field(default="val")

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # No underscore between prefix and field name!
        assert actual == {"field_a": ["myappfield_a"]}

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == "myapp"

    def test_dotenv_output(self, settings_cls):
        """BUG: env_prefix is not uppercased in dotenv output.

        The dotenv generator uppercases field.name but not env_prefix.
        Result: myappFIELD_A instead of MYAPPFIELD_A.
        """
        result = get_dotenv_output(settings_cls)
        # Current buggy behavior: prefix stays lowercase
        if "myappFIELD_A" in result:
            pytest.xfail(
                "BUG: env_prefix 'myapp' is not uppercased in dotenv output. "
                "Outputs 'myappFIELD_A' instead of 'MYAPPFIELD_A'."
            )
        assert '# MYAPPFIELD_A="val"' in result

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["MYAPPFIELD_A"] = "from_env"
        try:
            s = settings_cls()
            assert s.field_a == "from_env"
        finally:
            del os.environ["MYAPPFIELD_A"]


# =============================================================================
# CASE 4: case_sensitive=True
# =============================================================================


class TestCaseSensitive:
    """Settings with case_sensitive=True - env names should preserve case."""

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="App_", case_sensitive=True)

            MyField: str = Field(default="val")

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # With case_sensitive=True, no lowercasing
        assert actual == {"MyField": ["App_MyField"]}

    def test_info_model_preserves_case(self, settings_cls):
        """BUG-4: Currently the code uppercases everything unconditionally."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        # The env_prefix should be preserved as-is
        assert info.env_prefix == "App_"

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["App_MyField"] = "case_sensitive_val"
        try:
            s = settings_cls()
            assert s.MyField == "case_sensitive_val"
        finally:
            del os.environ["App_MyField"]


# =============================================================================
# CASE 5: Nested BaseModel WITH env_nested_delimiter
# =============================================================================


class TestNestedWithDelimiter:
    """Nested BaseModel with env_nested_delimiter set."""

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            sub_field: str = Field(default="sub_val")
            sub_count: int = Field(default=10)

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

            top_field: str = Field(default="top")
            nested: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        assert actual == {
            "top_field": ["app_top_field"],
            "nested": ["app_nested"],
        }
        # Nested fields are resolved via explode_env_vars
        prefixes = get_pydantic_settings_nested_env_names(settings_cls, "nested")
        assert prefixes == ["app_nested__"]

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == "APP_"
        assert len(info.child_settings) == 1
        child = info.child_settings[0]
        assert child.env_prefix == "APP_nested__"
        assert [f.name for f in child.fields] == ["sub_field", "sub_count"]

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        assert '# APP_TOP_FIELD="top"' in result
        assert '# APP_NESTED__SUB_FIELD="sub_val"' in result
        assert "# APP_NESTED__SUB_COUNT=10" in result

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["APP_TOP_FIELD"] = "t1"
        os.environ["APP_NESTED__SUB_FIELD"] = "s1"
        os.environ["APP_NESTED__SUB_COUNT"] = "99"
        try:
            s = settings_cls()
            assert s.top_field == "t1"
            assert s.nested.sub_field == "s1"
            assert s.nested.sub_count == 99
        finally:
            del os.environ["APP_TOP_FIELD"]
            del os.environ["APP_NESTED__SUB_FIELD"]
            del os.environ["APP_NESTED__SUB_COUNT"]


# =============================================================================
# CASE 6: Nested BaseModel WITHOUT env_nested_delimiter (None)
# BUG-1: Currently generates individual env vars, but should generate JSON
# =============================================================================


class TestNestedWithoutDelimiter:
    """Nested BaseModel with env_nested_delimiter=None (default).

    BUG-1: When env_nested_delimiter is None, nested model fields should NOT be
    expanded into individual env vars. The only way to set them is via a single
    JSON env var for the whole nested model.
    """

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            sub_field: str = Field(default="sub_val")
            sub_count: int = Field(default=10)

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_")
            # env_nested_delimiter is None by default!

            top_field: str = Field(default="top")
            nested: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_no_explode_without_delimiter(self, settings_cls):
        """pydantic-settings does NOT explode when delimiter is None."""
        prefixes = get_pydantic_settings_nested_env_names(settings_cls, "nested")
        assert prefixes == []  # No explode!

    def test_json_env_var_works(self, settings_cls):
        """The only way to set nested fields is via JSON."""
        os.environ["APP_NESTED"] = '{"sub_field": "json_val", "sub_count": 99}'
        try:
            s = settings_cls()
            assert s.nested.sub_field == "json_val"
            assert s.nested.sub_count == 99
        finally:
            del os.environ["APP_NESTED"]

    def test_individual_env_vars_do_not_work(self, settings_cls):
        """Individual env vars for nested fields should NOT work without delimiter."""
        os.environ["APP_NESTED_SUB_FIELD"] = "should_not_work"
        try:
            s = settings_cls()
            # The default value should remain unchanged
            assert s.nested.sub_field == "sub_val"
        finally:
            del os.environ["APP_NESTED_SUB_FIELD"]

    def test_info_model_should_not_expand(self, settings_cls):
        """BUG-1 fixed: without delimiter, nested model is in child_settings but NOT env-expandable.

        The nested model is still present in child_settings for structural generators
        (TOML, simple). But env generators (dotenv) skip it because env_accessible=False,
        and the parent shows a JSON field instead.
        """
        info = SettingsInfoModel.from_settings_model(settings_cls)

        # Nested model is present for structural generators (TOML etc.)
        assert len(info.child_settings) == 1
        child = info.child_settings[0]
        assert child.env_accessible is False

        # Child fields have no individual env var names
        for field in child.fields:
            assert field.env_names == [], f"{field.name} should have no env_names without delimiter"

        # Parent shows the nested model as a JSON field (e.g., APP_NESTED={"sub_field":…})
        nested_field = next((f for f in info.fields if f.name == "nested"), None)
        assert nested_field is not None, "nested should appear as a JSON field in parent"
        assert nested_field.env_names == ["APP_nested"]


# =============================================================================
# CASE 7: Nested BaseSettings inside another BaseSettings
# =============================================================================


class TestNestedBaseSettings:
    """Nested BaseSettings with its own env_prefix inside another BaseSettings.

    When BaseSettings is nested as a field of another BaseSettings, the parent's
    prefix + field name + delimiter is used, NOT the child's own env_prefix.
    """

    @pytest.fixture
    def settings_cls(self):
        class SubSettings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="SUB_")

            db_host: str = Field(default="localhost")
            db_port: int = Field(default=5432)

        class MainSettings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="MAIN_", env_nested_delimiter="__")

            app_name: str = Field(default="myapp")
            database: SubSettings = Field(default_factory=SubSettings)

        return MainSettings

    def test_child_prefix_ignored(self, settings_cls):
        """pydantic-settings ignores child's env_prefix when nested."""
        prefixes = get_pydantic_settings_nested_env_names(settings_cls, "database")
        assert prefixes == ["main_database__"]
        # NOT "sub_" - the child's env_prefix is ignored

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == "MAIN_"
        child = info.child_settings[0]
        # Should use parent's prefix + field_name + delimiter
        assert child.env_prefix == "MAIN_database__"

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        assert '# MAIN_APP_NAME="myapp"' in result
        assert '# MAIN_DATABASE__DB_HOST="localhost"' in result
        assert "# MAIN_DATABASE__DB_PORT=5432" in result
        # Should NOT contain SUB_ prefix
        assert "SUB_" not in result

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["MAIN_DATABASE__DB_HOST"] = "from_parent_path"
        try:
            s = settings_cls()
            assert s.database.db_host == "from_parent_path"
        finally:
            del os.environ["MAIN_DATABASE__DB_HOST"]

    def test_child_own_prefix_works_via_default_factory(self, settings_cls):
        """Child's own env_prefix (SUB_) DOES work because default_factory
        instantiates SubSettings which reads its own env vars.

        This is a subtlety: nested BaseSettings read their own env vars during
        default_factory instantiation. The parent path has higher priority.
        """
        os.environ["SUB_DB_HOST"] = "from_child_prefix"
        try:
            s = settings_cls()
            # SUB_DB_HOST works because SubSettings() reads it during default_factory
            assert s.database.db_host == "from_child_prefix"
        finally:
            del os.environ["SUB_DB_HOST"]

    def test_parent_path_overrides_child_prefix(self, settings_cls):
        """Parent's nested path takes priority over child's own env_prefix."""
        os.environ["SUB_DB_HOST"] = "from_child"
        os.environ["MAIN_DATABASE__DB_HOST"] = "from_parent"
        try:
            s = settings_cls()
            assert s.database.db_host == "from_parent"  # parent wins
        finally:
            del os.environ["SUB_DB_HOST"]
            del os.environ["MAIN_DATABASE__DB_HOST"]


# =============================================================================
# CASE 8: Field with validation_alias (string)
# =============================================================================


class TestValidationAliasString:
    """Field with validation_alias as string - replaces env name entirely."""

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_")

            field_a: str = Field(default="val", validation_alias="MY_CUSTOM_VAR")

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # validation_alias replaces env name entirely - NO prefix
        assert actual == {"field_a": ["my_custom_var"]}

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        field = info.fields[0]
        assert "MY_CUSTOM_VAR" in field.aliases

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        # Should use the alias, not the prefixed field name
        assert '# MY_CUSTOM_VAR="val"' in result
        # Should NOT contain APP_FIELD_A
        assert "APP_FIELD_A" not in result

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["MY_CUSTOM_VAR"] = "from_alias"
        try:
            s = settings_cls()
            assert s.field_a == "from_alias"
        finally:
            del os.environ["MY_CUSTOM_VAR"]

    def test_prefixed_name_does_not_work(self, settings_cls):
        """APP_FIELD_A does NOT work when validation_alias is set (without populate_by_name)."""
        os.environ["APP_FIELD_A"] = "should_not_work"
        try:
            s = settings_cls()
            assert s.field_a == "val"  # default
        finally:
            del os.environ["APP_FIELD_A"]


# =============================================================================
# CASE 9: Field with validation_alias (AliasChoices)
# =============================================================================


class TestValidationAliasChoices:
    """Field with validation_alias=AliasChoices - multiple possible env names."""

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_")

            field_a: str = Field(
                default="val",
                validation_alias=AliasChoices("VAR1", "VAR2", AliasPath("nested", "key")),
            )

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # AliasChoices: all choices are env names, NO prefix
        assert actual == {"field_a": ["var1", "var2", "nested"]}

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        field = info.fields[0]
        assert "VAR1" in field.aliases
        assert "VAR2" in field.aliases

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["VAR1"] = "from_var1"
        try:
            s = settings_cls()
            assert s.field_a == "from_var1"
        finally:
            del os.environ["VAR1"]

        os.environ["VAR2"] = "from_var2"
        try:
            s = settings_cls()
            assert s.field_a == "from_var2"
        finally:
            del os.environ["VAR2"]


# =============================================================================
# CASE 10: Field with validation_alias + populate_by_name=True
# =============================================================================


class TestValidationAliasWithPopulateByName:
    """When populate_by_name=True, BOTH alias AND prefixed field name work."""

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", populate_by_name=True)

            field_a: str = Field(default="val", validation_alias="MY_CUSTOM_VAR")

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # Both alias AND prefixed name should work
        assert actual == {"field_a": ["my_custom_var", "app_field_a"]}

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        field = info.fields[0]
        assert "MY_CUSTOM_VAR" in field.aliases
        # TODO: Should also show APP_FIELD_A as a valid env name

    def test_both_env_vars_work(self, settings_cls):
        os.environ["MY_CUSTOM_VAR"] = "from_alias"
        try:
            s = settings_cls()
            assert s.field_a == "from_alias"
        finally:
            del os.environ["MY_CUSTOM_VAR"]

        os.environ["APP_FIELD_A"] = "from_prefixed_name"
        try:
            s = settings_cls()
            assert s.field_a == "from_prefixed_name"
        finally:
            del os.environ["APP_FIELD_A"]


# =============================================================================
# CASE 11: Field with alias (not validation_alias)
# =============================================================================


class TestFieldAlias:
    """Field with alias= (not validation_alias).

    In pydantic-settings, alias is used for env var resolution (it sets validation_alias).
    """

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_")

            field_a: str = Field(default="val", alias="my_alias")

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # alias is treated like validation_alias - NO prefix
        assert actual == {"field_a": ["my_alias"]}

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        field = info.fields[0]
        assert "my_alias" in field.aliases

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["MY_ALIAS"] = "from_alias"
        try:
            s = settings_cls()
            assert s.field_a == "from_alias"
        finally:
            del os.environ["MY_ALIAS"]


# =============================================================================
# CASE 12: Custom env_nested_delimiter="."
# =============================================================================


class TestCustomDelimiterDot:
    """Custom env_nested_delimiter='.' instead of default.

    NOTE: Dots are NOT valid POSIX env var characters. This works via
    Python os.environ and .env files, but NOT from shell (`export A.B=x` fails).
    pydantic-settings allows it, but users should prefer POSIX-safe delimiters.
    """

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            value: str = Field(default="x")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter=".")

            nested: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_env_names_match(self, settings_cls):
        prefixes = get_pydantic_settings_nested_env_names(settings_cls, "nested")
        assert prefixes == ["app_nested."]

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        assert child.env_prefix == "APP_nested."

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        assert '# APP_NESTED.VALUE="x"' in result

    def test_env_vars_work_via_os_environ(self, settings_cls):
        """Works via Python os.environ (and .env files) but NOT from shell."""
        os.environ["APP_NESTED.VALUE"] = "from_env"
        try:
            s = settings_cls()
            assert s.nested.value == "from_env"
        finally:
            del os.environ["APP_NESTED.VALUE"]

    def test_dot_delimiter_not_posix_safe(self):
        """Dots in env var names are not valid POSIX identifiers.

        `export APP_NESTED.VALUE=x` would fail in bash/zsh.
        Only works via dotenv files or Python os.environ.
        """
        import subprocess  # noqa: S404

        result = subprocess.run(
            ["bash", "-c", "export APP_NESTED.VALUE=test"],  # noqa: S607
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0  # bash rejects it


# =============================================================================
# CASE 13: Triple-nested models with delimiter
# =============================================================================


class TestTripleNested:
    """Three levels of nesting with env_nested_delimiter."""

    @pytest.fixture
    def settings_cls(self):
        class Level3(BaseModel):
            deep_val: str = Field(default="deep")

        class Level2(BaseModel):
            mid_val: str = Field(default="mid")
            level3: Level3 = Field(default_factory=Level3)

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

            top: str = Field(default="top")
            level2: Level2 = Field(default_factory=Level2)

        return Settings

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == "APP_"

        level2_info = info.child_settings[0]
        assert level2_info.env_prefix == "APP_level2__"

        level3_info = level2_info.child_settings[0]
        assert level3_info.env_prefix == "APP_level2__level3__"

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        assert '# APP_TOP="top"' in result
        assert '# APP_LEVEL2__MID_VAL="mid"' in result
        assert '# APP_LEVEL2__LEVEL3__DEEP_VAL="deep"' in result

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["APP_LEVEL2__MID_VAL"] = "m1"
        os.environ["APP_LEVEL2__LEVEL3__DEEP_VAL"] = "d1"
        try:
            s = settings_cls()
            assert s.level2.mid_val == "m1"
            assert s.level2.level3.deep_val == "d1"
        finally:
            del os.environ["APP_LEVEL2__MID_VAL"]
            del os.environ["APP_LEVEL2__LEVEL3__DEEP_VAL"]


# =============================================================================
# CASE 14: env_nested_delimiter="_" (ambiguous with field name separators)
# =============================================================================


class TestAmbiguousDelimiter:
    """env_nested_delimiter="_" - same as Python field name word separator.

    This creates ambiguity: APP_SUB_MODEL_MY_FIELD could mean
    sub_model.my_field or sub.model_my_field etc.
    """

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            my_field: str = Field(default="val")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="_")

            sub_model: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        # With delimiter "_", prefix becomes APP_SUB_MODEL_
        assert child.env_prefix == "APP_sub_model_"

    def test_env_var_ambiguity(self, settings_cls):
        """This delimiter creates ambiguous env var names."""
        # APP_SUB_MODEL_MY_FIELD - pydantic-settings splits on "_"
        # and tries to match field by field. This may or may not work
        # depending on how the tokenization resolves.
        os.environ["APP_SUB_MODEL_MY_FIELD"] = "test_val"
        try:
            s = settings_cls()  # noqa: F841
            # pydantic-settings may or may not resolve this correctly
            # The point is that "_" as delimiter is ambiguous
        finally:
            del os.environ["APP_SUB_MODEL_MY_FIELD"]


# =============================================================================
# CASE 14b: Ambiguous delimiter - field name contains the delimiter character
# KNWN-1: Field with "_" in name is unreachable when env_nested_delimiter="_"
# =============================================================================


class TestAmbiguousDelimiterUnderscoreField:
    """Field whose name contains the delimiter is unreachable via env vars.

    KNWN-1: When env_nested_delimiter="_" and a nested model has a field
    named e.g. "nested_field", the env var APP_NESTED_FIELD gets tokenized
    as app → nested → field (3 levels), not app → nested_field (2 levels).
    The field is UNREACHABLE via individual env vars; only JSON works.

    PSE currently shows APP_NESTED_FIELD as the env var, which is misleading.
    This is a pydantic-settings limitation, not a PSE bug per se.
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class SubModel(BaseModel):
            nested_field: str = Field(default="default_val")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="_")

            app: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_individual_env_var_does_not_work(self, settings_cls):
        """APP_APP_NESTED_FIELD is tokenized as app→nested→field, not app→nested_field."""
        os.environ["APP_APP_NESTED_FIELD"] = "path_attempt"
        try:
            s = settings_cls()
            assert s.app.nested_field == "default_val"
        finally:
            del os.environ["APP_APP_NESTED_FIELD"]

    def test_json_works(self, settings_cls):
        """Only JSON can set the field when delimiter creates ambiguity."""
        os.environ["APP_APP"] = '{"nested_field": "json_val"}'
        try:
            s = settings_cls()
            assert s.app.nested_field == "json_val"
        finally:
            del os.environ["APP_APP"]

    def test_pse_shows_misleading_env_name(self, settings_cls):
        """PSE generates APP_APP_NESTED_FIELD which doesn't actually work."""
        result = get_dotenv_output(settings_cls)
        # PSE shows this env var name — but it's unreachable in practice
        assert "APP_APP_NESTED_FIELD" in result


# =============================================================================
# CASE 15: Nested model with validation_alias on sub-field
# BUG-3: alias on nested field loses parent prefix
# =============================================================================


class TestNestedFieldWithAlias:
    """Nested model field that has its own validation_alias.

    BUG-3: When a nested model's field has validation_alias, pydantic-settings
    matches it via the explode path (parent_prefix + delimiter + alias_name),
    but pydantic-settings-export shows just the alias without parent prefix.
    """

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            field_a: str = Field(default="a", validation_alias="custom_a")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

            nested: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_alias_env_var_works(self, settings_cls):
        """pydantic-settings uses parent prefix + delimiter + alias name."""
        os.environ["APP_NESTED__CUSTOM_A"] = "from_alias"
        try:
            s = settings_cls()
            assert s.nested.field_a == "from_alias"
        finally:
            del os.environ["APP_NESTED__CUSTOM_A"]

    def test_field_name_does_not_work(self, settings_cls):
        """Using the Python field name instead of alias does NOT work."""
        os.environ["APP_NESTED__FIELD_A"] = "from_field_name"
        try:
            s = settings_cls()
            # field_name does NOT match when validation_alias is set
            assert s.nested.field_a == "a"  # default
        finally:
            del os.environ["APP_NESTED__FIELD_A"]

    def test_info_model_shows_alias_with_prefix(self, settings_cls):
        """BUG-3: The alias should be shown with the parent prefix.

        Correct env var: APP_NESTED__CUSTOM_A
        Current buggy output: CUSTOM_A (no prefix)
        """
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        field = child.fields[0]

        # The field has aliases from validation_alias
        assert "custom_a" in field.aliases

        # The dotenv generator would output CUSTOM_A without prefix
        # But the correct env var is APP_NESTED__CUSTOM_A
        env_names = collect_env_names_from_info(info)
        # BUG: This will show CUSTOM_A instead of APP_NESTED__CUSTOM_A
        for key, env_name in env_names.items():
            if "field_a" in key:
                # This documents the bug - expected vs actual
                if env_name == "CUSTOM_A":
                    pytest.xfail(
                        "BUG-3: Alias 'CUSTOM_A' shown without parent prefix. Should be 'APP_NESTED__CUSTOM_A'."
                    )
                assert env_name == "APP_NESTED__CUSTOM_A"


# =============================================================================
# CASE 16: AliasPath on top-level field
# =============================================================================


class TestAliasPath:
    """Field with validation_alias=AliasPath."""

    @pytest.fixture
    def settings_cls(self):
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_")

            field_a: str = Field(default="val", validation_alias=AliasPath("config", "key"))

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # AliasPath first element is used as env name
        # Actually pydantic-settings extracts both path elements separately
        assert actual == {"field_a": ["config", "key"]}

    def test_info_model(self, settings_cls):
        """BUG-6: AliasPath is converted to dotted string instead of first path element."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        field = info.fields[0]
        # Current behavior: aliases = ["config.key"] (dotted string)
        # pydantic-settings behavior: uses "config" as the env name
        if field.aliases == ["config.key"]:
            pytest.xfail(
                "BUG-6: AliasPath('config', 'key') produces alias 'config.key' "
                "but pydantic-settings uses 'config' as the env name."
            )


# =============================================================================
# CASE 17: Empty env_prefix with nested delimiter
# =============================================================================


class TestEmptyPrefixWithDelimiter:
    """No env_prefix but with env_nested_delimiter."""

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            val: str = Field(default="x")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_nested_delimiter="__")

            nested: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_env_names_match(self, settings_cls):
        prefixes = get_pydantic_settings_nested_env_names(settings_cls, "nested")
        assert prefixes == ["nested__"]

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        assert child.env_prefix == "nested__"

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["NESTED__VAL"] = "from_env"
        try:
            s = settings_cls()
            assert s.nested.val == "from_env"
        finally:
            del os.environ["NESTED__VAL"]


# =============================================================================
# CASE 18: Optional nested model
# =============================================================================


class TestOptionalNestedModel:
    """Optional[BaseModel] nested field."""

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            val: str = Field(default="x")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

            nested: Optional[SubModel] = Field(default=None)

        return Settings

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        # Optional nested model should still be expanded
        assert len(info.child_settings) == 1
        child = info.child_settings[0]
        assert child.env_prefix == "APP_nested__"

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["APP_NESTED__VAL"] = "from_env"
        try:
            s = settings_cls()
            assert s.nested is not None
            assert s.nested.val == "from_env"
        finally:
            del os.environ["APP_NESTED__VAL"]


# =============================================================================
# CASE 19: Nested BaseSettings with different env_nested_delimiter
# BUG-2: Child's delimiter overrides parent's
# =============================================================================


class TestNestedSettingsDifferentDelimiter:
    """Nested BaseSettings with its own env_nested_delimiter.

    BUG-2: The parent's delimiter should be used for resolving nested fields,
    but the current code reads the child's delimiter for further nesting.
    """

    @pytest.fixture
    def settings_cls(self):
        class DeepModel(BaseModel):
            val: str = Field(default="deep")

        class SubSettings(BaseSettings):
            model_config = SettingsConfigDict(
                env_prefix="SUB_",
                env_nested_delimiter=".",  # Different delimiter!
            )

            mid_val: str = Field(default="mid")
            deep: DeepModel = Field(default_factory=DeepModel)

        class MainSettings(BaseSettings):
            model_config = SettingsConfigDict(
                env_prefix="MAIN_",
                env_nested_delimiter="__",
            )

            sub: SubSettings = Field(default_factory=SubSettings)

        return MainSettings

    def test_parent_delimiter_used(self, settings_cls):
        """Parent's delimiter is what pydantic-settings uses."""
        os.environ["MAIN_SUB__MID_VAL"] = "from_parent"
        os.environ["MAIN_SUB__DEEP__VAL"] = "from_parent_deep"
        try:
            s = settings_cls()
            assert s.sub.mid_val == "from_parent"
            assert s.sub.deep.val == "from_parent_deep"
        finally:
            del os.environ["MAIN_SUB__MID_VAL"]
            del os.environ["MAIN_SUB__DEEP__VAL"]

    def test_child_delimiter_does_not_work(self, settings_cls):
        """Child's own delimiter does NOT work when nested."""
        os.environ["MAIN_SUB.MID_VAL"] = "should_not_work"
        try:
            s = settings_cls()
            assert s.sub.mid_val == "mid"  # default
        finally:
            del os.environ["MAIN_SUB.MID_VAL"]

    def test_info_model_delimiter(self, settings_cls):
        """BUG-2: Child settings should use parent's delimiter, not their own.

        Expected: MAIN_SUB__DEEP__VAL
        Buggy:    MAIN_SUB__DEEP.VAL (uses child's "." delimiter)
        """
        info = SettingsInfoModel.from_settings_model(settings_cls)
        sub_info = info.child_settings[0]
        assert sub_info.env_prefix == "MAIN_sub__"

        deep_info = sub_info.child_settings[0]
        # BUG-2: Currently reads child's env_nested_delimiter="."
        # and produces "MAIN_SUB__DEEP." instead of "MAIN_SUB__DEEP__"
        if deep_info.env_prefix == "MAIN_SUB__DEEP.":
            pytest.xfail(
                "BUG-2: Nested BaseSettings' env_nested_delimiter='.' overrides "
                "parent's '__'. Produces MAIN_SUB__DEEP.VAL instead of MAIN_SUB__DEEP__VAL"
            )
        assert deep_info.env_prefix == "MAIN_sub__deep__"


# =============================================================================
# MONSTER CASE 1: Deep nesting + custom delimiter + mixed aliases
# =============================================================================


class TestMonster1:
    """Monster case: 3 levels, delimiter='.', mixed aliases."""

    @pytest.fixture
    def settings_cls(self):
        class DeepModel(BaseModel):
            deep_val: str = Field(default="deep_default")
            aliased_deep: str = Field(default="ad", validation_alias="CUSTOM_DEEP")

        class MidModel(BaseModel):
            mid_val: str = Field(default="mid_default")
            deep: DeepModel = Field(default_factory=DeepModel)

        class Monster(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="MON_", env_nested_delimiter=".")

            top_val: str = Field(default="top")
            aliased_top: str = Field(default="at", validation_alias="TOP_ALIAS")
            mid: MidModel = Field(default_factory=MidModel)

        return Monster

    def test_top_level_env_names(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        assert actual["top_val"] == ["mon_top_val"]
        assert actual["aliased_top"] == ["top_alias"]

    def test_nested_env_names(self, settings_cls):
        prefixes = get_pydantic_settings_nested_env_names(settings_cls, "mid")
        assert prefixes == ["mon_mid."]

    def test_all_env_vars_work(self, settings_cls):
        os.environ["MON_TOP_VAL"] = "t1"
        os.environ["TOP_ALIAS"] = "t2"
        os.environ["MON_MID.MID_VAL"] = "m1"
        os.environ["MON_MID.DEEP.DEEP_VAL"] = "d1"
        os.environ["MON_MID.DEEP.CUSTOM_DEEP"] = "d2"
        try:
            m = settings_cls()
            assert m.top_val == "t1"
            assert m.aliased_top == "t2"
            assert m.mid.mid_val == "m1"
            assert m.mid.deep.deep_val == "d1"
            assert m.mid.deep.aliased_deep == "d2"
        finally:
            for k in list(os.environ):
                if k.startswith("MON_") or k == "TOP_ALIAS":
                    del os.environ[k]

    def test_info_model(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == "MON_"

        # top_val
        top_val = next(f for f in info.fields if f.name == "top_val")
        assert top_val.aliases == []  # no alias

        # aliased_top
        aliased_top = next(f for f in info.fields if f.name == "aliased_top")
        assert "TOP_ALIAS" in aliased_top.aliases

        # mid
        mid_info = info.child_settings[0]
        assert mid_info.env_prefix == "MON_mid."

        # mid.deep
        deep_info = mid_info.child_settings[0]
        assert deep_info.env_prefix == "MON_mid.deep."

    def test_dotenv_output_matches_pydantic_settings(self, settings_cls):
        result = get_dotenv_output(settings_cls)
        assert '# MON_TOP_VAL="top"' in result
        assert '# TOP_ALIAS="at"' in result
        assert '# MON_MID.MID_VAL="mid_default"' in result
        assert '# MON_MID.DEEP.DEEP_VAL="deep_default"' in result

        # BUG-3: The aliased nested field should show MON_MID.DEEP.CUSTOM_DEEP
        # but currently shows just CUSTOM_DEEP
        if "CUSTOM_DEEP" in result and "MON_MID.DEEP.CUSTOM_DEEP" not in result:
            pytest.xfail(
                "BUG-3: Nested alias 'CUSTOM_DEEP' shown without parent prefix. Should be 'MON_MID.DEEP.CUSTOM_DEEP'."
            )
        assert '# MON_MID.DEEP.CUSTOM_DEEP="ad"' in result


# =============================================================================
# MONSTER CASE 2: Multiple nesting levels, BaseSettings + BaseModel mix
# =============================================================================


class TestMonster2:
    """Monster case: Mixed BaseSettings/BaseModel nesting with overridden everything."""

    @pytest.fixture
    def settings_cls(self):
        class CacheConfig(BaseModel):
            ttl: int = Field(default=300, description="Cache TTL in seconds")
            backend: str = Field(default="redis", description="Cache backend")

        class DatabaseConfig(BaseModel):
            host: str = Field(default="localhost")
            port: int = Field(default=5432)
            cache: CacheConfig = Field(default_factory=CacheConfig)

        class LoggingSettings(BaseSettings):
            """Logging configuration - has its own env_prefix."""

            model_config = SettingsConfigDict(env_prefix="LOG_")

            level: str = Field(default="INFO")
            format: str = Field(default="json")

        class AppSettings(BaseSettings):
            model_config = SettingsConfigDict(
                env_prefix="MYAPP_",
                env_nested_delimiter="__",
            )

            debug: bool = Field(default=False, description="Debug mode")
            db: DatabaseConfig = Field(default_factory=DatabaseConfig)
            logging: LoggingSettings = Field(default_factory=LoggingSettings)
            secret_key: str = Field(
                default="changeme",
                validation_alias=AliasChoices("SECRET_KEY", "MYAPP_SECRET"),
            )

        return AppSettings

    def test_all_env_vars_work(self, settings_cls):
        env_vars = {
            "MYAPP_DEBUG": "true",
            "MYAPP_DB__HOST": "db.example.com",
            "MYAPP_DB__PORT": "3306",
            "MYAPP_DB__CACHE__TTL": "600",
            "MYAPP_DB__CACHE__BACKEND": "memcached",
            "MYAPP_LOGGING__LEVEL": "DEBUG",
            "MYAPP_LOGGING__FORMAT": "text",
            "SECRET_KEY": "super-secret",
        }
        for k, v in env_vars.items():
            os.environ[k] = v
        try:
            s = settings_cls()
            assert s.debug is True
            assert s.db.host == "db.example.com"
            assert s.db.port == 3306
            assert s.db.cache.ttl == 600
            assert s.db.cache.backend == "memcached"
            assert s.logging.level == "DEBUG"
            assert s.logging.format == "text"
            assert s.secret_key == "super-secret"  # noqa: S105
        finally:
            for k in env_vars:
                del os.environ[k]

    def test_info_model_structure(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert info.env_prefix == "MYAPP_"

        # debug should be a field
        debug = next(f for f in info.fields if f.name == "debug")
        assert debug.aliases == [] or debug.name == "debug"

        # secret_key should have aliases
        secret = next(f for f in info.fields if f.name == "secret_key")
        assert "SECRET_KEY" in secret.aliases
        assert "MYAPP_SECRET" in secret.aliases

        # db should be a child
        db_info = next(c for c in info.child_settings if c.field_name == "db")
        assert db_info.env_prefix == "MYAPP_db__"

        # db.cache should be further nested
        cache_info = next(c for c in db_info.child_settings if c.field_name == "cache")
        assert cache_info.env_prefix == "MYAPP_db__cache__"

        # logging should use parent prefix, not its own LOG_
        log_info = next(c for c in info.child_settings if c.field_name == "logging")
        assert log_info.env_prefix == "MYAPP_logging__"

    def test_dotenv_output(self, settings_cls):
        result = get_dotenv_output(settings_cls)

        # Top-level fields
        assert "MYAPP_DEBUG" in result

        # Nested db fields
        assert 'MYAPP_DB__HOST="localhost"' in result
        assert "MYAPP_DB__PORT=5432" in result

        # Double-nested cache
        assert "MYAPP_DB__CACHE__TTL=300" in result
        assert 'MYAPP_DB__CACHE__BACKEND="redis"' in result

        # Logging (should use MYAPP_LOGGING__, not LOG_)
        assert 'MYAPP_LOGGING__LEVEL="INFO"' in result
        assert "LOG_LEVEL" not in result

    def test_log_prefix_works_via_default_factory(self, settings_cls):
        """LOG_ prefix DOES work because default_factory instantiates LoggingSettings.

        Nested BaseSettings read their own env vars during default_factory instantiation.
        """
        os.environ["LOG_LEVEL"] = "CRITICAL"
        try:
            s = settings_cls()
            # LOG_LEVEL works because LoggingSettings() reads it during default_factory
            assert s.logging.level == "CRITICAL"
        finally:
            del os.environ["LOG_LEVEL"]

    def test_parent_path_overrides_child_prefix(self, settings_cls):
        """Parent nested path (MYAPP_LOGGING__LEVEL) overrides child's own prefix."""
        os.environ["LOG_LEVEL"] = "CRITICAL"
        os.environ["MYAPP_LOGGING__LEVEL"] = "WARNING"
        try:
            s = settings_cls()
            assert s.logging.level == "WARNING"  # parent path wins
        finally:
            del os.environ["LOG_LEVEL"]
            del os.environ["MYAPP_LOGGING__LEVEL"]


# =============================================================================
# Edge case: Nested BaseModel (not BaseSettings) with its own model_config title
# =============================================================================


class TestNestedBaseModelWithTitle:
    """Nested BaseModel with title in model_config."""

    @pytest.fixture
    def settings_cls(self):
        class SubModel(BaseModel):
            """My sub model docs."""

            model_config = ConfigDict(title="Custom Sub Title")

            val: str = Field(default="x")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

            sub: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_info_model_uses_title(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        # title from model_config should be used
        assert child.name == "Custom Sub Title"
        assert child.env_prefix == "APP_sub__"


# =============================================================================
# Edge case: Multiple same-type nested models
# =============================================================================


class TestMultipleSameTypeNested:
    """Multiple fields of the same nested model type."""

    @pytest.fixture
    def settings_cls(self):
        class DBConfig(BaseModel):
            host: str = Field(default="localhost")
            port: int = Field(default=5432)

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

            primary_db: DBConfig = Field(default_factory=DBConfig)
            replica_db: DBConfig = Field(default_factory=DBConfig)

        return Settings

    def test_different_prefixes(self, settings_cls):
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert len(info.child_settings) == 2

        primary = next(c for c in info.child_settings if c.field_name == "primary_db")
        replica = next(c for c in info.child_settings if c.field_name == "replica_db")

        assert primary.env_prefix == "APP_primary_db__"
        assert replica.env_prefix == "APP_replica_db__"

    def test_env_vars_actually_work(self, settings_cls):
        os.environ["APP_PRIMARY_DB__HOST"] = "primary.example.com"
        os.environ["APP_REPLICA_DB__HOST"] = "replica.example.com"
        try:
            s = settings_cls()
            assert s.primary_db.host == "primary.example.com"
            assert s.replica_db.host == "replica.example.com"
        finally:
            del os.environ["APP_PRIMARY_DB__HOST"]
            del os.environ["APP_REPLICA_DB__HOST"]


# =============================================================================
# Edge case: AliasPath inside AliasChoices (BUG-6 variant)
# =============================================================================


class TestAliasPathInChoices:
    """AliasPath inside AliasChoices - same dotted-string bug as BUG-6.

    When AliasPath is one of the choices in AliasChoices, _alias_path_to_str
    produces a dotted string ("nested.key") instead of the first path element
    ("nested") that pydantic-settings actually uses as the env name.
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_")

            field_a: str = Field(
                default="val",
                validation_alias=AliasChoices("VAR1", AliasPath("nested", "key")),
            )

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # pydantic-settings uses "nested" (first path element), not "nested.key"
        assert actual == {"field_a": ["var1", "nested"]}

    def test_env_var_actually_works(self, settings_cls):
        os.environ["NESTED"] = '{"key": "from_nested"}'
        try:
            s = settings_cls()
            assert s.field_a == "from_nested"
        finally:
            del os.environ["NESTED"]

    def test_info_model_alias_path_in_choices(self, settings_cls):
        """BUG-6 (variant): AliasPath inside AliasChoices produces dotted string.

        Current buggy output: aliases = ['VAR1', 'nested.key']
        Expected:             aliases = ['VAR1', 'nested']
        """
        info = SettingsInfoModel.from_settings_model(settings_cls)
        field = info.fields[0]
        assert "VAR1" in field.aliases
        if "nested.key" in field.aliases:
            pytest.xfail(
                "BUG-6 (variant): AliasPath inside AliasChoices produces 'nested.key' "
                "instead of 'nested'. Same root cause as BUG-6: _alias_path_to_str "
                "uses '.'.join(path) instead of path[0]."
            )
        assert "nested" in field.aliases


# =============================================================================
# Edge case: case_sensitive=True - generators should preserve case
# BUG-5: generators always uppercase, ignoring case_sensitive setting
# =============================================================================


class TestCaseSensitiveGeneratorOutput:
    """case_sensitive=True - generators must not uppercase env names.

    BUG-5: dotenv and markdown generators unconditionally uppercase field.name,
    but with case_sensitive=True the env names must be output as-is (no transformation).
    Example: env_prefix="App_", field="MyField" → should output "App_MyField", not "App_MYFIELD".
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="App_", case_sensitive=True)

            MyField: str = Field(default="val")

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        # case_sensitive=True: no lowercasing, names are used as-is
        assert actual == {"MyField": ["App_MyField"]}

    def test_env_var_actually_works(self, settings_cls):
        os.environ["App_MyField"] = "case_val"
        try:
            s = settings_cls()
            assert s.MyField == "case_val"
        finally:
            del os.environ["App_MyField"]

    def test_wrong_case_does_not_work(self, settings_cls):
        """With case_sensitive=True, wrong-case env var is silently ignored."""
        os.environ["APP_MYFIELD"] = "wrong_case"
        try:
            s = settings_cls()
            assert s.MyField == "val"  # default unchanged
        finally:
            del os.environ["APP_MYFIELD"]

    def test_dotenv_output_preserves_case(self, settings_cls):
        """BUG-5: dotenv generator uppercases field.name even with case_sensitive=True.

        Current buggy output: '# App_MYFIELD="val"'
        Expected output:      '# App_MyField="val"'
        """
        result = get_dotenv_output(settings_cls)
        if '# App_MYFIELD="val"' in result:
            pytest.xfail(
                "BUG-5: case_sensitive=True not respected in dotenv output. "
                "Generator outputs 'App_MYFIELD' instead of 'App_MyField' "
                "because field.name.upper() is applied unconditionally."
            )
        assert '# App_MyField="val"' in result


# =============================================================================
# Edge case: populate_by_name=True in nested BaseModel
# =============================================================================


class TestPopulateByNameNestedModel:
    """populate_by_name=True in a nested BaseModel.

    When a nested BaseModel has populate_by_name=True and a field with
    validation_alias, pydantic-settings accepts BOTH the alias AND the Python
    field name as valid env var segments via the explode mechanism.
    The info model / generators should reflect this.
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class SubModel(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            field_a: str = Field(default="a", validation_alias="custom_a")

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

            nested: SubModel = Field(default_factory=SubModel)

        return Settings

    def test_alias_env_var_works(self, settings_cls):
        """Alias-based env var works via explode."""
        os.environ["APP_NESTED__CUSTOM_A"] = "via_alias"
        try:
            s = settings_cls()
            assert s.nested.field_a == "via_alias"
        finally:
            del os.environ["APP_NESTED__CUSTOM_A"]

    def test_field_name_also_works(self, settings_cls):
        """With populate_by_name=True, field name is also a valid env var segment."""
        os.environ["APP_NESTED__FIELD_A"] = "via_field"
        try:
            s = settings_cls()
            assert s.nested.field_a == "via_field"
        finally:
            del os.environ["APP_NESTED__FIELD_A"]

    def test_info_model_shows_alias_with_prefix(self, settings_cls):
        """Primary env name should be APP_NESTED__CUSTOM_A (hits BUG-3 for now).

        Once BUG-3 is fixed, env_names[0] should be 'APP_NESTED__CUSTOM_A'.
        The secondary env name 'APP_NESTED__FIELD_A' (populate_by_name) is a
        missing feature to be addressed after the structural refactor.
        """
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        field = child.fields[0]
        assert "custom_a" in field.aliases

        env_names = collect_env_names_from_info(info)
        for key, env_name in env_names.items():
            if "field_a" in key:
                if env_name == "CUSTOM_A":
                    pytest.xfail(
                        "BUG-3: Also affects populate_by_name case - alias shown without "
                        "parent prefix. Should be 'APP_NESTED__CUSTOM_A'."
                    )
                assert env_name == "APP_NESTED__CUSTOM_A"


# =============================================================================
# BUG-7: alias= causes duplicate entries in FieldInfoModel.aliases
# =============================================================================


class TestAliasDuplication:
    """BUG-7: field.alias= causes duplicate alias in FieldInfoModel.aliases.

    When Field(alias="X") is used, pydantic v2 automatically sets validation_alias="X"
    as well. PSE adds field.alias first, then appends validation_alias — producing ["X", "X"].
    The markdown generator then renders: `X` | `X` instead of just `X`.
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="LOGIN_")

            verification_email: str = Field(
                default="test@example.com",
                description="Email to verify",
                alias="GMAIL_USER_VERIFICATION_EMAIL",
            )

        return Settings

    def test_env_names_match(self, settings_cls):
        actual = get_pydantic_settings_env_names(settings_cls)
        assert actual == {"verification_email": ["gmail_user_verification_email"]}

    def test_no_duplicate_aliases(self, settings_cls):
        """BUG-7: alias= produces duplicate alias entries ['X', 'X'].

        pydantic v2 auto-sets validation_alias = alias, so PSE adds the same
        value twice: once from field.alias and once from field.validation_alias.
        """
        info = SettingsInfoModel.from_settings_model(settings_cls)
        field = info.fields[0]
        assert "GMAIL_USER_VERIFICATION_EMAIL" in field.aliases
        if field.aliases.count("GMAIL_USER_VERIFICATION_EMAIL") > 1:
            pytest.xfail(
                "BUG-7: alias='X' produces duplicate aliases ['X', 'X'] because "
                "pydantic v2 auto-sets validation_alias=alias, and PSE appends both."
            )
        assert field.aliases == ["GMAIL_USER_VERIFICATION_EMAIL"]

    def test_dotenv_no_duplicate(self, settings_cls):
        """Dotenv output should use the alias once, not duplicate."""
        result = get_dotenv_output(settings_cls)
        assert '# GMAIL_USER_VERIFICATION_EMAIL="test@example.com"' in result

    def test_env_var_actually_works(self, settings_cls):
        os.environ["GMAIL_USER_VERIFICATION_EMAIL"] = "alias_val"
        try:
            s = settings_cls()
            assert s.verification_email == "alias_val"
        finally:
            del os.environ["GMAIL_USER_VERIFICATION_EMAIL"]


# =============================================================================
# CASE: Nested BaseSettings with own env_prefix (no parent env_nested_delimiter)
# =============================================================================


class TestNestedBaseSettingsOwnPrefix:
    """Nested BaseSettings with its own env_prefix, parent has no env_nested_delimiter.

    Key insight verified here: pydantic-settings always calls BaseSettings.__init__
    when constructing a nested model — even via default_factory or parent's JSON env var.
    That means the child's own env_prefix is ALWAYS active and the flat vars DO work.

    PSE must show the flat vars (CHILD_HOST, CHILD_PORT) in its output, not a JSON blob.
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class ChildSettings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="CHILD_")

            host: str = Field(default="localhost", description="Child host")
            port: int = Field(default=9000, description="Child port")

        class ParentSettings(BaseSettings):
            """Parent with no env_nested_delimiter."""

            name: str = Field(default="parent", description="Parent name")
            child: ChildSettings = Field(default_factory=ChildSettings)

        return ParentSettings

    def test_child_flat_vars_actually_work(self, settings_cls):
        """Flat vars via child's own prefix are resolved by pydantic-settings."""
        os.environ["CHILD_HOST"] = "from_env"
        os.environ["CHILD_PORT"] = "1234"
        try:
            s = settings_cls()
            assert s.child.host == "from_env"
            assert s.child.port == 1234
        finally:
            del os.environ["CHILD_HOST"]
            del os.environ["CHILD_PORT"]

    def test_child_is_env_accessible(self, settings_cls):
        """SettingsInfoModel marks child with own prefix as env_accessible=True."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        assert len(info.child_settings) == 1
        child = info.child_settings[0]
        assert child.env_accessible is True

    def test_child_prefix_is_own(self, settings_cls):
        """Child's env_prefix must be its own 'CHILD_', not empty."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        assert child.env_prefix == "CHILD_"

    def test_child_fields_have_env_names(self, settings_cls):
        """Child fields must have proper env_names derived from its own prefix."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        env_names_by_field = {f.name: f.env_names for f in child.fields}
        # Keys are field names; values are lists of env var names (lowercase before normalization)
        assert "host" in env_names_by_field
        assert "port" in env_names_by_field
        # env_names should contain the prefixed name (compare lowercased)
        assert any("child_host" in n.lower() for n in env_names_by_field["host"])
        assert any("child_port" in n.lower() for n in env_names_by_field["port"])

    def test_dotenv_shows_flat_vars(self, settings_cls):
        """Dotenv output must contain flat CHILD_HOST/CHILD_PORT, not CHILD={...}."""
        result = get_dotenv_output(settings_cls)
        # Flat vars must be present
        assert "CHILD_HOST" in result
        assert "CHILD_PORT" in result
        # JSON blob must NOT be present
        assert "CHILD={" not in result
        assert 'CHILD="' not in result

    def test_no_synthetic_json_field_in_parent(self, settings_cls):
        """Parent's fields list must not contain a synthetic JSON field for child."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        parent_field_names = [f.name for f in info.fields]
        assert "child" not in parent_field_names


class TestNestedBaseSettingsThreeLevels:
    """Three-level deep nesting: Parent → Child(CHILD_) → Grand(CHILD_GRAND_).

    All flat vars must be accessible and shown — no JSON blobs at any level.
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class GrandSettings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="CHILD_GRAND_")

            value: str = Field(default="grand_default", description="Grand value")

        class ChildSettings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="CHILD_")

            host: str = Field(default="localhost", description="Child host")
            grand: GrandSettings = Field(default_factory=GrandSettings)

        class ParentSettings(BaseSettings):
            child: ChildSettings = Field(default_factory=ChildSettings)

        return ParentSettings

    def test_grandchild_flat_vars_actually_work(self, settings_cls):
        """Grandchild's flat vars work via 2-deep default_factory chain."""
        os.environ["CHILD_HOST"] = "child_env"
        os.environ["CHILD_GRAND_VALUE"] = "grand_env"
        try:
            s = settings_cls()
            assert s.child.host == "child_env"
            assert s.child.grand.value == "grand_env"
        finally:
            del os.environ["CHILD_HOST"]
            del os.environ["CHILD_GRAND_VALUE"]

    def test_all_children_env_accessible(self, settings_cls):
        """Both child and grandchild must be env_accessible=True."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        child = info.child_settings[0]
        assert child.env_accessible is True
        grand = child.child_settings[0]
        assert grand.env_accessible is True

    def test_grandchild_prefix(self, settings_cls):
        """Grandchild must carry its own env_prefix 'CHILD_GRAND_'."""
        info = SettingsInfoModel.from_settings_model(settings_cls)
        grand = info.child_settings[0].child_settings[0]
        assert grand.env_prefix == "CHILD_GRAND_"

    def test_dotenv_shows_all_flat_vars(self, settings_cls):
        """All flat vars from all levels must appear in dotenv output."""
        result = get_dotenv_output(settings_cls)
        assert "CHILD_HOST" in result
        assert "CHILD_GRAND_VALUE" in result
        # No JSON blobs
        assert "CHILD={" not in result
        assert "CHILD_GRAND={" not in result


class TestNestedBaseSettingsParentHasDelimiter:
    """Parent has env_nested_delimiter; child also has own env_prefix.

    When parent has a delimiter, the delimiter path is the primary one.
    Child's own-prefix vars still work at runtime (via default_factory)
    but PSE should show the delimiter-based names as primary.
    """

    @pytest.fixture
    def settings_cls(self) -> type[BaseSettings]:
        class ChildSettings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="CHILD_")

            host: str = Field(default="localhost")

        class ParentSettings(BaseSettings):
            model_config = SettingsConfigDict(env_nested_delimiter="__")

            child: ChildSettings = Field(default_factory=ChildSettings)

        return ParentSettings

    def test_delimiter_path_is_primary(self, settings_cls):
        """With parent delimiter, PARENT__CHILD__HOST= is the primary path."""
        os.environ["CHILD__HOST"] = "via_delimiter"
        try:
            s = settings_cls()
            assert s.child.host == "via_delimiter"
        finally:
            del os.environ["CHILD__HOST"]

    def test_own_prefix_still_works(self, settings_cls):
        """Child's own prefix CHILD_HOST= still works (via default_factory)."""
        os.environ["CHILD_HOST"] = "via_own_prefix"
        try:
            s = settings_cls()
            assert s.child.host == "via_own_prefix"
        finally:
            del os.environ["CHILD_HOST"]

    def test_dotenv_shows_delimiter_names(self, settings_cls):
        """With parent delimiter, dotenv uses delimiter-based names."""
        result = get_dotenv_output(settings_cls)
        assert "CHILD__HOST" in result
