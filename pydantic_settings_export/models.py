import json
import sys
from inspect import getdoc, isclass
from pathlib import Path
from types import GenericAlias
from typing import TYPE_CHECKING, Any, ForwardRef, Literal, Optional, TypeVar, Union, cast, get_args, get_origin

from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.fields import FieldInfo
from pydantic_core import PydanticSerializationError, PydanticUndefined
from pydantic_settings import BaseSettings

from pydantic_settings_export.constants import FIELD_TYPE_MAP

try:
    from types import UnionType  # type: ignore[attr-defined]

    UnionTypes: tuple[Any, ...] = (UnionType, Union)  # Just for type checking in code
except ImportError:
    UnionTypes = (Union,)

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

if TYPE_CHECKING:
    from pydantic_settings_export.settings import PSESettings
else:
    PSESettings = BaseSettings

__all__ = (
    "FieldInfoModel",
    "SettingsInfoModel",
)


BASE_SETTINGS_DOCS = (getdoc(BaseSettings) or "").strip()
BASE_MODEL_DOCS = (getdoc(BaseModel) or "").strip()


def value_to_jsonable(value: Any, value_type: Optional[type] = None) -> Any:
    if value_type is None:
        value_type = type(value)

    try:
        return TypeAdapter(value_type).dump_json(value).decode()
    except PydanticSerializationError:
        return str(value)


def _prepare_example(example: Any, value_type: Optional[type] = None) -> str:
    """Prepare the example for the field."""
    if isinstance(example, set):
        example = sorted(example)
    return value_to_jsonable(example, value_type)


P = TypeVar("P", bound=Path)


def get_type_by_annotation(annotation: Any, remove_none: bool = True) -> list[str]:
    args: list[Any] = list(get_args(annotation))
    if remove_none:
        args = [arg for arg in args if arg is not None]

    # If it is an Alias (like `list[int]`), get the origin (like `list`)
    origin = get_origin(annotation)
    if origin is not None:
        annotation = origin

    # If it is a Union, get all types to return something like `integer | string`
    # instead of `Union[int, str]`, `int | str`, or `Union`.
    if origin in UnionTypes:
        args = list(filter(bool, args))
        if args:
            return [t for arg in args for t in get_type_by_annotation(arg)]
        else:
            annotation = None

    # If it is a Literal, get all types to return in "original" format like `1 | 'some-str'`
    # instead of `Literal[1, 'some-str']` or `Literal`.
    if origin is Literal:
        return [json.dumps(a, default=repr) for a in args]

    # If it is a ForwardRef, get the value or the argument to return something like `CustomType`
    # instead of `"CustomType"`, `ForwardRef("CustomType")` or `ForwardRef`.
    if isinstance(annotation, ForwardRef):
        return [annotation.__forward_value__ or annotation.__forward_arg__]

    # Map the annotation to the type in the FIELD_TYPE_MAP
    return [FIELD_TYPE_MAP.get(annotation, annotation.__name__ if annotation else "any")]


def default_path(default: P, global_settings: Optional[PSESettings] = None) -> P:
    # Check if default is a Path and is absolute
    if default.is_absolute():
        # if we need to replace absolute paths
        if global_settings and global_settings.relative_to.replace_abs_paths:
            root_dir = global_settings.root_dir.resolve().absolute()

            # Make the default path relative to the global_settings
            if default.is_relative_to(root_dir):
                default = cast(
                    P,
                    Path(global_settings.relative_to.alias)
                    / default.relative_to(global_settings.root_dir.resolve().absolute()),
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
    types: list[str] = Field(..., description="The type of the field.")
    default: Optional[str] = Field(None, description="The default value of the field as a string.")
    description: Optional[str] = Field(None, description="The description of the field.")
    examples: list[str] = Field(default_factory=list, description="The examples of the field.")
    aliases: list[str] = Field(default_factory=list, description="The aliases of the field.")
    deprecated: bool = Field(False, description="Mark this field as an deprecated field.")

    @property
    def full_name(self) -> str:
        """Get the full name (aliased or not) of the field."""
        return self.aliases[0] if self.aliases else self.name

    @property
    def is_required(self) -> bool:
        """Check if the field is required."""
        return self.default is None

    def has_examples(self) -> bool:
        """Check if the field has examples."""
        return bool(self.examples and self.examples != [self.default])

    @staticmethod
    def create_default(field: FieldInfo, global_settings: Optional[PSESettings] = None) -> Optional[str]:
        """Make the default value for the field.

        :param field: The field info to generate the default value for.
        :param global_settings: The global settings.
        :return: The default value for the field as a string, or None if there is no default value.
        """
        default: Union[object, PydanticUndefined] = field.default  # type: ignore[valid-type]

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
        global_settings: Optional[PSESettings] = None,
    ) -> Self:
        """Generate FieldInfoModel using name and field.

        :param name: The name of the field.
        :param field: The field info to generate FieldInfoModel from.
        :param global_settings: The global settings.
        :return: Instance of FieldInfoModel.
        """
        # Parse the annotation of the field
        annotation = field.annotation

        # Get the name from the alias if it exists
        name: str = name
        # Get the type from the FIELD_TYPE_MAP if it exists
        types: list[str] = get_type_by_annotation(annotation)
        # Get the default value from the field if it exists
        default = cls.create_default(field, global_settings)
        # Get the description from the field if it exists
        description: Optional[str] = field.description or None
        # Get the example from the field if it exists
        examples: list[str] = [_prepare_example(example, field.annotation) for example in (field.examples or [])]
        if not examples and default:
            examples = [default]
        # Get the deprecated status from the field if it exists
        deprecated: bool = bool(field.deprecated or False)

        # Get the aliases from the field if it exists
        aliases: list[str] = []
        validation_alias: Optional[Union[str, AliasChoices, AliasPath]] = field.validation_alias
        if field.alias:
            aliases = [field.alias]

        def _alias_path_to_str(value: Union[AliasPath, str]) -> str:
            if isinstance(value, AliasPath):
                return ".".join(map(str, value.path))
            return value

        if validation_alias:
            if isinstance(validation_alias, str):
                aliases.append(validation_alias)
            elif isinstance(validation_alias, AliasChoices):
                aliases.extend(map(_alias_path_to_str, validation_alias.choices))
            elif isinstance(validation_alias, AliasPath):
                aliases = [_alias_path_to_str(validation_alias)]

        return cls(
            name=name,
            types=types,
            default=default,
            description=description,
            examples=examples,
            aliases=aliases,
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
        settings: Union[BaseSettings, type[BaseSettings]],
        global_settings: Optional[PSESettings] = None,
        prefix: str = "",
        nested_delimiter: str = "_",
    ) -> Self:
        """Generate the SettingsInfoModel using a settings model.

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
            prefix = prefix or settings.model_config.get("env_prefix", "")
            nested_delimiter = settings.model_config.get("env_nested_delimiter", "_") or "_"

        child_settings: list[SettingsInfoModel] = []
        fields = []
        for name, field_info in fields_info.items():
            if global_settings and global_settings.respect_exclude and field_info.exclude:
                continue
            annotation = field_info.annotation
            if isinstance(annotation, GenericAlias):
                annotation = annotation.__origin__

            # If the annotation is a BaseModel (also match to BaseSettings),
            # then we need to generate a SettingsInfoModel for it
            if isclass(annotation) and issubclass(annotation, (BaseModel, BaseSettings)):
                child_settings.append(
                    cls.from_settings_model(
                        cast(type[BaseSettings], annotation),
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
        settings_name = (
            # Get the title from the settings model if it exists
            conf.get("title", None)
            # Otherwise, get the name from the settings model if it exists
            or getattr(settings, "__name__", None)
            # Otherwise, get the class name from the settings model
            or str(settings.__class__.__name__)
        )
        return cls(name=settings_name, docs=docs, env_prefix=prefix, fields=fields, child_settings=child_settings)
