import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeAlias, TypeVar, cast, final

from pydantic import BaseModel, Field, create_model

from pydantic_settings_export.settings import PSESettings

if TYPE_CHECKING:
    from pydantic_settings_export.models import SettingsInfoModel

else:
    SettingsInfoModel: TypeAlias = BaseModel


__all__ = (
    "AbstractEnvGenerator",
    "AbstractGenerator",
    "BaseEnvGeneratorSettings",
    "BaseGeneratorSettings",
)


class BaseGeneratorSettings(BaseModel):
    """Base model config for the generator."""

    enabled: bool = Field(
        True,
        description="Enable the configuration for file generation.",
        exclude=True,
    )

    paths: list[Path] = Field(
        default_factory=lambda: [],
        description="The paths to the resulting files.",
    )

    settings: list[str] = Field(
        default_factory=list,
        description=(
            "Override the global ``default_settings`` for this generator configuration. "
            "When non-empty, only these settings are exported — ``default_settings`` and "
            "``extend_settings`` are ignored for this generator."
        ),
        examples=[["app.settings:MySettings"]],
    )

    extend_settings: list[str] = Field(
        default_factory=list,
        description=(
            "Additional settings to include alongside the global ``default_settings`` "
            "for this generator configuration. Ignored when ``settings`` is non-empty."
        ),
        examples=[["app.extra_settings:ExtraSettings"]],
    )

    def __bool__(self) -> bool:
        """Check if the configuration file is set."""
        return self.enabled and bool(self.paths)


class BaseEnvGeneratorSettings(BaseGeneratorSettings):
    """Base settings for env-variable-centric generators (dotenv, markdown).

    Structural generators (TOML, simple, JSON, YAML) do *not* inherit from this class.
    """

    to_upper_case: bool = Field(
        True,
        description=(
            "Convert env variable names to upper case in the output. "
            "Has no effect when the settings model has ``case_sensitive=True`` — "
            "names are always kept as-is in that case to avoid misleading output."
        ),
    )


C = TypeVar("C", bound=BaseGeneratorSettings)
CE = TypeVar("CE", bound=BaseEnvGeneratorSettings)


class AbstractGenerator(ABC, Generic[C]):
    """The abstract class for the configuration file generator."""

    name: ClassVar[str]
    config: ClassVar[type[BaseGeneratorSettings]]

    ALL_GENERATORS: ClassVar[list[type["AbstractGenerator"]]] = []

    def __init__(self, settings: PSESettings | None = None, generator_config: C | None = None) -> None:
        """Initialize the AbstractGenerator.

        :param settings: The settings for the generator.
        """
        self.settings = settings or PSESettings()
        self.generator_config: C = generator_config if generator_config is not None else cast(C, self.config())

    @classmethod
    def _extra_subclass_checks(cls, **kwargs: Any) -> None:
        """Extra checks, when subclass is created."""
        return None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize the subclass."""
        check_name = kwargs.pop("check_name", False)
        super().__init_subclass__(**kwargs)
        if "name" not in cls.__dict__:
            if check_name:
                raise ValueError("Generator must have a name")
            # Allow explicitly abstract helpers to opt out of registration.
            # Use an explicit ``__abstract__ = True`` attribute or rely on
            # Python's ABC machinery (inspect.isabstract) to detect classes
            # that still carry unimplemented abstract methods.  Any other
            # subclass that simply forgot to declare ``name`` is a
            # misconfigured concrete generator and should fail fast.
            if getattr(cls, "__abstract__", False) or inspect.isabstract(cls):
                return
            raise ValueError("Generator must have a name")
        conf = getattr(cls, "config", None)
        if not conf or not isinstance(conf, type):
            raise ValueError(f"Generator {cls.name!r} must have a config")
        if not issubclass(conf, BaseGeneratorSettings):
            raise ValueError(
                f"Generator {cls.name!r} have config, which is not inherited from {BaseGeneratorSettings.__name__}"
            )
        if any(g.name == cls.name for g in AbstractGenerator.ALL_GENERATORS):
            raise ValueError(f"Generator {cls.name!r} already exists")

        cls._extra_subclass_checks(**kwargs)

        conf.__doc__ = conf.__doc__ or ""
        conf.__doc__ += f"\n\nGenerator name: `{cls.name}`."

        AbstractGenerator.ALL_GENERATORS.append(cls)

    @abstractmethod
    def generate_single(self, settings_info: SettingsInfoModel, level: int = 1) -> str:
        """Generate the configuration file content.

        :param settings_info: The settings class to generate documentation for.
        :param level: The level of nesting. Used for indentation.
        :return: The generated documentation.
        """
        raise NotImplementedError

    def generate(self, *settings_infos: SettingsInfoModel) -> str:
        """Generate the configuration file content.

        :param settings_infos: The settings info classes to generate documentation for.
        :return: The generated documentation.
        """
        return "\n\n".join(self.generate_single(s).strip() for s in settings_infos).strip() + "\n"

    def file_paths(self) -> list[Path]:
        """Get the list of files which need to create/update.

        :return: The list of files to write.
        """
        if not self.generator_config:
            return []
        file_paths = []
        for p in self.generator_config.paths:
            if p.is_absolute():
                file_paths.append(p)
                continue
            file_paths.append(self.settings.root_dir / p)
        return file_paths

    def run(self, *settings_info: SettingsInfoModel) -> list[Path]:
        """Run the generator.

        :param settings_info: The settings info to generate documentation for.
        :return: The list of file paths is written to.
        """
        updated_files: list[Path] = []
        result = self.generate(*settings_info)
        for path in self.file_paths():
            if path.is_file() and path.read_text() == result:
                # No need to update the file
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result)
            updated_files.append(path)
        return updated_files

    @staticmethod
    @final
    def generators() -> dict[str, type["AbstractGenerator"]]:
        """Get all generators.

        :return: The generators (key: generator name, value: generator class).
        """
        return {g.name: g for g in AbstractGenerator.ALL_GENERATORS}

    @staticmethod
    @final
    def create_generator_config_model(multiple_for_single: bool = False) -> type[BaseModel]:
        """Create the generator config model.

        This model contains all the generators' configuration information.
        The attribute is the generator name, the value is generator config.

        :param multiple_for_single: Whether to create a list of the generator config for the single generator.
        :return: The generator model.
        """

        def _make_arg(generator: type[AbstractGenerator]) -> tuple[Any, Any]:
            config: type[BaseGeneratorSettings] | None = getattr(generator, "config", None)
            if config is None:
                raise ValueError(f"Generator {generator.name} has no config")

            if multiple_for_single:
                return (
                    list[config],  # type: ignore[valid-type]
                    Field(default_factory=lambda: [config()]),
                )
            return (
                config,
                Field(default_factory=config),
            )

        fields: dict[str, tuple[Any, Any]] = {
            name: _make_arg(generator) for name, generator in AbstractGenerator.generators().items()
        }
        return create_model(  # type: ignore[call-overload]
            "Generators",
            **fields,
            __base__=BaseModel,
            __doc__="The configuration of generators.",
        )


class AbstractEnvGenerator(AbstractGenerator[CE]):
    """Base class for env-variable-centric generators (dotenv, markdown).

    Structural generators (TOML, simple, JSON, YAML) do *not* inherit from this class.

    Provides :meth:`apply_env_case` for consistent case normalization across all
    env generators.
    """

    @staticmethod
    def apply_env_case(name: str, *, to_upper_case: bool, case_sensitive: bool) -> str:
        """Apply case normalization to an env variable name.

        When the settings model declares ``case_sensitive=True``, *name* is returned
        unchanged regardless of *to_upper_case* — uppercasing a case-sensitive var name
        would produce incorrect documentation.

        :param name: Raw env variable name (as stored in ``FieldInfoModel.env_names``).
        :param to_upper_case: Generator preference (from generator config).
        :param case_sensitive: From ``SettingsInfoModel.case_sensitive``.
        :return: Case-normalized env variable name.
        """
        if case_sensitive:
            return name
        return name.upper() if to_upper_case else name

    @classmethod
    def _extra_subclass_checks(cls, **kwargs: Any) -> None:
        super()._extra_subclass_checks(**kwargs)
        if not issubclass(cls.config, BaseEnvGeneratorSettings):
            raise ValueError(
                f"EnvGenerator {cls.name!r} have config, "
                f"which is not inherited from {BaseEnvGeneratorSettings.__name__}"
            )
