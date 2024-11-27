import warnings
from inspect import getdoc, isclass
from pathlib import Path
from types import UnionType
from typing import TYPE_CHECKING, Any, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.fields import FieldInfo
from pydantic_core import PydanticSerializationError, PydanticUndefined
from pydantic_settings import BaseSettings

from pydantic_settings_export.constants import FIELD_TYPE_MAP

if TYPE_CHECKING:
    from pydantic_settings_export.settings import PSESettings
else:
    PSESettings = BaseSettings

__all__ = (
    "FieldInfoModel",
    "SettingsInfoModel",
)


BASE_SETTINGS_DOCS = getdoc(BaseSettings).strip()
BASE_MODEL_DOCS = getdoc(BaseModel).strip()


def value_to_jsonable(value: Any, value_type: type | None = None) -> Any:
    if value_type is None:
        value_type = type(value)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return TypeAdapter(value_type).dump_json(value).decode()
    except PydanticSerializationError:
        return str(value)


def _prepare_example(example: Any, value_type: type | None = None) -> str:
    """Prepare the example for the field."""
    if isinstance(example, set):
        example = sorted(example)
    return value_to_jsonable(example, value_type)


P = TypeVar("P", bound=Path)


def default_path(default: P, global_settings: PSESettings | None = None) -> P:
    # Check if default is a Path and is absolute
    if default.is_absolute():
        # if we need to replace absolute paths
        if global_settings and global_settings.relative_to.replace_abs_paths:
            project_dir = global_settings.project_dir.resolve().absolute()

            # Make the default path relative to the global_settings
            if default.is_relative_to(project_dir):
                default = Path(global_settings.relative_to.alias) / default.relative_to(
                    global_settings.project_dir.resolve().absolute()
                )

        # Make the default path relative to the user's home directory
        home_dir = Path.home().resolve().absolute()
        if default.is_relative_to(home_dir):
            default = "~" / default.relative_to(home_dir)

    return default


class FieldInfoModel(BaseModel):
    """Info about the field of the settings model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the field.")
    type: str = Field(..., description="The type of the field.")
    default: str | None = Field(None, description="The default value of the field as a string.")
    description: str | None = Field(None, description="The description of the field.")
    examples: list[str] = Field(default_factory=list, description="The example of the field.")
    alias: str | None = Field(None, description="The alias of the field.")
    deprecated: bool = Field(False, description="Mark this field as an deprecated field.")

    @property
    def is_required(self) -> bool:
        """Check if the field is required."""
        return self.default is None

    @staticmethod
    def create_default(field: FieldInfo, global_settings: PSESettings | None = None) -> str | None:
        """Make the default value for the field.

        :param field: The field info to generate the default value for.
        :param global_settings: The global settings.
        :return: The default value for the field as a string, or None if there is no default value.
        """
        default: object | PydanticUndefined = field.default

        if default is PydanticUndefined and field.default_factory:
            default = field.default_factory()

        if default is PydanticUndefined:
            return None

        if isinstance(default, set):
            default = sorted(default)

        # Validate Path values
        if isinstance(default, Path):
            default = default_path(default, global_settings)

        return value_to_jsonable(default)

    @classmethod
    def from_settings_field(
        cls,
        name: str,
        field: FieldInfo,
        global_settings: PSESettings | None = None,
    ) -> Self:
        """Generate FieldInfoModel using name and field.

        :param name: The name of the field.
        :param field: The field info to generate FieldInfoModel from.
        :param global_settings: The global settings.
        :return: Instance of FieldInfoModel.
        """
        # Parse the annotation of the field
        annotation = field.annotation

        if isinstance(annotation, UnionType):
            args = list(filter(bool, getattr(annotation, "__args__", [])))
            annotation = args[0] if args else None

        # Get the name from the alias if it exists
        name: str = field.alias or name
        # Get the type from the FIELD_TYPE_MAP if it exists
        type_: str = FIELD_TYPE_MAP.get(annotation, annotation.__name__ if annotation else "any")
        # Get the default value from the field if it exists
        default = cls.create_default(field, global_settings)
        # Get the description from the field if it exists
        description: str | None = field.description or None
        # Get the example from the field if it exists
        examples: list[str] = [_prepare_example(example, field.annotation) for example in (field.examples or [])]
        if not examples and default:
            examples = [default]
        # Get the deprecated status from the field if it exists
        deprecated: bool = field.deprecated or False

        return cls(
            name=name,
            type=type_,
            default=default,
            description=description,
            examples=examples,
            alias=field.alias,
            deprecated=deprecated,
        )


class SettingsInfoModel(BaseModel):
    """Info about the settings model."""

    name: str = Field(..., description="The name of the settings model.")
    docs: str = Field("", description="The documentation of the settings model.")
    env_prefix: str = Field("", description="The prefix of the environment variables.")
    fields: list[FieldInfoModel] = Field(default_factory=list, description="The fields of the settings model.")
    child_settings: list["SettingsInfoModel"] = Field(
        default_factory=list, description="The child settings of the settings model."
    )

    @classmethod
    def from_settings_model(
        cls,
        settings: BaseSettings | type[BaseSettings],
        global_settings: PSESettings | None = None,
        prefix: str = "",
        nested_delimiter: str = "_",
    ) -> Self:
        """Generate SettingsInfoModel using a settings model.

        :param settings: The settings model to generate SettingsInfoModel from.
        :param global_settings: The global settings.
        :param prefix: The prefix of the environment variables.
        :param nested_delimiter: The delimiter to use for nested settings.
        :return: Instance of SettingsInfoModel.
        """
        conf = settings.model_config
        fields_info = settings.model_fields

        # If the settings are a BaseSettings, then we can get the prefix and nested delimiter from the model config
        if isinstance(settings, BaseSettings) or (isclass(settings) and issubclass(settings, BaseSettings)):
            prefix = prefix + settings.model_config.get("env_prefix", "")
            nested_delimiter = settings.model_config.get("env_nested_delimiter", "_")

        child_settings = []
        fields = []
        for name, field_info in fields_info.items():
            if global_settings and global_settings.respect_exclude and field_info.exclude:
                continue
            annotation = field_info.annotation

            # If the annotation is a BaseModel (also match to BaseSettings),
            # then we need to generate a SettingsInfoModel for it
            if isclass(annotation) and issubclass(annotation, BaseModel):
                child_settings.append(
                    cls.from_settings_model(
                        annotation,
                        global_settings=global_settings,
                        # Add the prefix and nested delimiter to the child settings
                        # We need to change the prefix to uppercase to match the env prefix
                        prefix=f"{prefix}{name}{nested_delimiter}".upper(),
                        nested_delimiter=nested_delimiter,
                    )
                )
                continue
            fields.append(FieldInfoModel.from_settings_field(name, field_info, global_settings))

        docs = getdoc(settings) or ""

        # If the docs are the same as the base model/settings docs, then remove them
        if docs.strip() in (BASE_SETTINGS_DOCS, BASE_MODEL_DOCS):
            docs = ""

        # Remove all text after the first form feed character
        docs = docs.split("\f", 1)[0].strip()

        return cls(
            name=(
                # Get the title from the settings model if it exists
                conf.get("title", None)
                # Otherwise, get the name from the settings model if it exists
                or getattr(settings, "__name__", None)
                # Otherwise, get the class name from the settings model
                or str(settings.__class__.__name__)
            ),
            docs=docs.strip(),
            env_prefix=prefix,
            fields=fields,
            child_settings=child_settings,
        )
