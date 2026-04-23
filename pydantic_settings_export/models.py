import json
import logging
import sys
import warnings
from inspect import getdoc, getfile, isclass
from pathlib import Path
from types import GenericAlias
from typing import TYPE_CHECKING, Any, ForwardRef, Literal, TypeVar, Union, cast, get_args, get_origin

from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field, PydanticDeprecationWarning, TypeAdapter
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
    "format_types",
    "to_python_jsonable",
    "type_repr",
    "value_repr",
)

logger = logging.getLogger(__name__)

BASE_SETTINGS_DOCS = (getdoc(BaseSettings) or "").strip()
BASE_MODEL_DOCS = (getdoc(BaseModel) or "").strip()


def to_python_jsonable(value: Any, value_type: type | None = None) -> Any:
    """Convert *value* to a JSON-serialisable Python object (not a string).

    Pydantic serialisation (``dump_python(mode="json")``) is used so that
    custom types such as ``SecretStr``, ``AnyUrl``, ``Path``, etc. are
    reduced to their JSON-native equivalents before any further processing.

    :param value: The value to convert.
    :param value_type: Optional explicit type hint; falls back to ``type(value)``.
    :return: A JSON-serialisable Python value (``str``, ``int``, ``float``,
        ``bool``, ``None``, ``list``, or ``dict``).
    """
    if value_type is None:
        value_type = type(value)
    try:
        return TypeAdapter(value_type).dump_python(value, mode="json", warnings="error")
    except PydanticSerializationError:
        return str(value)


def value_to_jsonable(value: Any, value_type: type | None = None) -> str:
    """Convert *value* to a JSON string.

    Thin wrapper around :func:`to_python_jsonable` followed by
    :func:`json.dumps`.  Kept for backward compatibility.

    :param value: The value to convert.
    :param value_type: Optional explicit type hint.
    :return: JSON-encoded string (e.g. ``'"hello"'``, ``'42'``, ``'true'``).
    """
    return json.dumps(to_python_jsonable(value, value_type), separators=(",", ":"))


def value_repr(v: Any) -> str:
    """Render a raw JSON-serialisable value as a JSON string for display.

    Used by generators to turn a value stored in
    :attr:`FieldInfoModel.default`, :attr:`FieldInfoModel.value`, or an
    element of :attr:`FieldInfoModel.examples` into a human-readable string.

    :param v: A value as returned by :func:`to_python_jsonable`.
    :return: Compact JSON string, e.g. ``'"hello"'``, ``'42'``, ``'true'``,
        ``'null'``, ``'["a","b"]'``.
    """
    return json.dumps(v, separators=(",", ":"))


def _prepare_example(example: Any, value_type: type | None = None) -> Any:
    """Prepare the example for the field."""
    if isinstance(example, set):
        example = sorted(example)
    return to_python_jsonable(example, value_type)


def _alias_path_to_str(value: AliasPath | str) -> str:
    """Convert an AliasPath or string to its string representation.

    :param value: The AliasPath or string to convert
    :return: String representation of the path
    """
    if isinstance(value, AliasPath):
        return str(value.path[0])
    return value


def _compute_env_names(
    aliases: list[str],
    name: str,
    env_prefix: str,
    is_nested: bool,
    populate_by_name: bool,
    env_accessible: bool = True,
) -> list[str]:
    """Compute env variable names for a field without case normalization.

    Case normalization is the responsibility of generators via ``SettingsInfoModel.case_sensitive``.

    :param aliases: Raw aliases from the field definition.
    :param name: Python field name.
    :param env_prefix: Accumulated env prefix (e.g. ``APP_nested__``).
    :param is_nested: True when the field belongs to a nested model.
    :param populate_by_name: When True, also add ``env_prefix + name``.
    :param env_accessible: When False, returns an empty list.
    :return: List of env variable names, primary first; empty when not env-accessible.
    """
    if not env_accessible:
        return []
    if aliases:
        env_names = [f"{env_prefix}{a}" for a in aliases] if is_nested else list(aliases)
        if populate_by_name:
            field_env = f"{env_prefix}{name}"
            if field_env not in env_names:
                env_names.append(field_env)
    else:
        env_names = [f"{env_prefix}{name}"]
    return env_names


def _unwrap_union_type(annotation: Any) -> Any:
    """Extract the non-None type from a Union type annotation.

    Handles both Union[Type, None] and Type | None syntax.
    If the annotation is not a Union or doesn't contain a non-None type,
    returns the original annotation.
    """
    origin = get_origin(annotation)
    if origin in UnionTypes:
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if non_none_args:
            return non_none_args[0]
    return annotation


def _resolve_field_annotation(annotation: Any) -> Any:
    """Unwrap Union/Optional and GenericAlias to the concrete inner type.

    :param annotation: Raw field annotation.
    :return: Resolved annotation (may still be a type or None).
    """
    annotation = _unwrap_union_type(annotation)
    if isinstance(annotation, GenericAlias):
        annotation = annotation.__origin__
    origin = get_origin(annotation)
    if origin in UnionTypes:
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            annotation = non_none[0]
    return annotation


P = TypeVar("P", bound=Path)


def get_type_by_annotation(annotation: Any, remove_none: bool = True) -> list[Any]:
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

    # If it is a Literal, return raw Python values (generators decide how to format).
    if origin is Literal:
        return list(args)

    # If it is a ForwardRef, try to resolve it first (Pydantic sets __forward_value__
    # after model_rebuild). Fall back to keeping the ForwardRef object as-is.
    if isinstance(annotation, ForwardRef):
        try:
            resolved = annotation.__forward_value__
            if resolved is not None:
                return get_type_by_annotation(resolved)
        except Exception:  # noqa: BLE001
            logger.debug("Could not resolve ForwardRef %r", annotation)
        return [annotation]

    # Normalize None / NoneType to type(None) for consistent handling.
    if annotation is None or annotation is type(None):
        return [type(None)]

    # Return the type object itself; generators apply their own formatting.
    return [annotation]


def type_repr(t: Any) -> str:
    """Convert a single type annotation item to a human-readable string.

    Items in the ``FieldInfoModel.types`` list can be:

    * A :class:`type` object (e.g. ``str``, ``int``, :class:`~pathlib.Path`)
    * A raw Python value from a ``Literal`` annotation (e.g. ``"a"``, ``1``)
    * A :class:`~typing.ForwardRef` for unresolved forward references

    :param t: A single element as returned by :func:`get_type_by_annotation`.
    :return: Human-readable string representation suitable for display.
    """
    if isinstance(t, type):
        return FIELD_TYPE_MAP.get(t, t.__name__)
    if isinstance(t, ForwardRef):
        resolved = None
        try:
            resolved = t.__forward_value__
        except Exception:  # noqa: BLE001
            logger.debug("Could not get __forward_value__ from ForwardRef %r", t)
        return type_repr(resolved) if resolved is not None else (t.__forward_arg__ or repr(t))
    # bool must come before int because bool is a subclass of int
    if isinstance(t, bool):
        return json.dumps(t)
    if isinstance(t, (int, float)):
        return str(t)
    if isinstance(t, (str, Path)):
        return json.dumps(str(t))
    return repr(t)


def format_types(types: list[Any]) -> list[str]:
    """Convert a list of type annotation items to display strings.

    :param types: The ``types`` list from a :class:`FieldInfoModel` instance.
    :return: List of human-readable strings, one per type item.
    """
    return [type_repr(t) for t in types]


def default_path(default: P, global_settings: PSESettings | None = None) -> P:
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


def settings_source(settings: BaseModel | type[BaseModel], global_settings: PSESettings | None = None) -> str:
    """Build a stable human-readable source reference for a settings class."""
    settings_class = cast(type[BaseModel], settings if isclass(settings) else settings.__class__)

    try:
        source_path = Path(getfile(settings_class)).resolve().absolute()
    except (OSError, TypeError):
        return f"{settings_class.__module__}:{settings_class.__qualname__}"

    if global_settings:
        relative_to = global_settings.project_dir.resolve().absolute()
    else:
        relative_to = Path.cwd().resolve().absolute()
    try:
        display_path = source_path.relative_to(relative_to)
        path_string = f"./{display_path!s}"
    except ValueError:
        path_string = str(source_path)

    return f"{path_string}:{settings_class.__qualname__}"


class FieldInfoModel(BaseModel):
    """Info about the field of the settings model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the field.")
    types: list[Any] = Field(..., description="The type of the field.")
    is_required: bool = Field(False, description="True when the field has no default value (required field).")
    default: Any = Field(
        None,
        description="The default value of the field as a raw Python object. Only meaningful when is_required=False.",
    )
    value: Any = Field(
        PydanticUndefined,
        description="The actual value from an instance as a raw Python object. Only meaningful when has_value=True.",
    )
    description: str | None = Field(None, description="The description of the field.")
    examples: list[Any] = Field(default_factory=list, description="The examples of the field as raw Python objects.")
    aliases: list[str] = Field(default_factory=list, description="The aliases of the field.")
    env_names: list[str] = Field(default_factory=list, description="Computed env variable names (primary first).")
    deprecated: bool = Field(False, description="Mark this field as an deprecated field.")
    env_accessible: bool = Field(True, description="False when the field is inside a non-env-expandable nested model.")
    is_env_only: bool = Field(
        False,
        description="True for synthetic JSON fields representing a non-env-expandable nested model. "
        "Structural generators (TOML, simple) skip these.",
    )

    @property
    def has_value(self) -> bool:
        """True when an instance value that differs from the default is available."""
        return self.value is not PydanticUndefined and self.value != self.default

    @property
    def full_name(self) -> str:
        """Get the display name (first alias if present, otherwise field name)."""
        return self.aliases[0] if self.aliases else self.name

    def has_examples(self) -> bool:
        """Check if the field has examples."""
        return bool(self.examples and self.examples != [self.default])

    @staticmethod
    def create_default(field: FieldInfo, global_settings: PSESettings | None = None) -> Any:
        """Make the default value for the field.

        :param field: The field info to generate the default value for.
        :param global_settings: The global settings.
        :return: Raw JSON-serialisable Python value, or :data:`~pydantic_core.PydanticUndefined`
            when the field has no default (i.e. it is required).
        """
        default: object | PydanticUndefined = field.default  # type: ignore[valid-type]

        if default is PydanticUndefined and field.default_factory:
            try:
                default = field.default_factory()
            except Exception:
                logger.warning("Failed to compute default value for field %s", field)
                return PydanticUndefined

        if default is PydanticUndefined:
            return PydanticUndefined

        if isinstance(default, set):
            default = sorted(default)

        # Validate Path values
        if isinstance(default, Path):
            default = default_path(default, global_settings)

        return to_python_jsonable(default)

    @staticmethod
    def create_value(
        instance: BaseSettings,
        field_name: str,
        global_settings: PSESettings | None = None,
    ) -> Any:
        """Extract the actual value from an instance.

        :param instance: The settings instance to extract the value from.
        :param field_name: The name of the field.
        :param global_settings: The global settings.
        :return: Raw JSON-serialisable Python value, or :data:`~pydantic_core.PydanticUndefined`
            when the value is unavailable.
        """
        value = getattr(instance, field_name, PydanticUndefined)

        if value is PydanticUndefined:
            return PydanticUndefined

        if isinstance(value, set):
            value = sorted(value)

        if isinstance(value, Path):
            value = default_path(value, global_settings)

        return to_python_jsonable(value)

    @classmethod
    def from_settings_field(
        cls,
        name: str,
        field: FieldInfo,
        global_settings: PSESettings | None = None,
        instance: BaseSettings | None = None,
        *,
        env_prefix: str = "",
        is_nested: bool = False,
        case_sensitive: bool = False,
        populate_by_name: bool = False,
        env_accessible: bool = True,
    ) -> Self:
        """Generate FieldInfoModel using name and field.

        :param name: The name of the field.
        :param field: The field info to generate FieldInfoModel from.
        :param global_settings: The global settings.
        :param instance: Optional settings instance to extract actual values from.
        :param env_prefix: Accumulated env prefix (e.g. ``APP_NESTED__``).
        :param is_nested: True when field belongs to a nested model (alias gets prefix).
        :param case_sensitive: When True, env names are not uppercased.
        :param populate_by_name: When True, also add ``env_prefix + name`` to env_names.
        :param env_accessible: When False, field is inside a non-env-expandable model; env_names will be empty.
        :return: Instance of FieldInfoModel.
        """
        # Parse the annotation of the field
        annotation = field.annotation

        # Get the name from the alias if it exists
        name: str = name
        # Get the type from the FIELD_TYPE_MAP if it exists
        types: list[Any] = get_type_by_annotation(annotation)
        raw_default = cls.create_default(field, global_settings)
        is_required = raw_default is PydanticUndefined
        default: Any = None if is_required else raw_default
        value = cls.create_value(instance, name, global_settings) if instance else PydanticUndefined
        # Get the description from the field if it exists
        description: str | None = field.description or None
        # Get the example from the field if it exists
        examples: list[Any] = [_prepare_example(example, field.annotation) for example in (field.examples or [])]
        if not examples and not is_required:
            examples = [default]
        # Get the deprecated status from the field if it exists
        deprecated: bool = bool(field.deprecated or False)

        # Get the aliases from the field if it exists
        aliases: list[str] = []
        validation_alias: str | AliasChoices | AliasPath | None = field.validation_alias
        if field.alias:
            aliases = [field.alias]

        if validation_alias:
            if isinstance(validation_alias, str):
                aliases.append(validation_alias)
            elif isinstance(validation_alias, AliasChoices):
                aliases.extend(map(_alias_path_to_str, validation_alias.choices))
            elif isinstance(validation_alias, AliasPath):
                aliases = [_alias_path_to_str(validation_alias)]

        aliases = list(dict.fromkeys(aliases))
        env_names = _compute_env_names(aliases, name, env_prefix, is_nested, populate_by_name, env_accessible)

        return cls(
            name=name,
            types=types,
            is_required=is_required,
            default=default,
            value=value,
            description=description,
            examples=examples,
            aliases=aliases,
            env_names=env_names,
            deprecated=deprecated,
            env_accessible=env_accessible,
        )


class SettingsInfoModel(BaseModel):
    """Info about the settings model."""

    name: str = Field(..., description="The name of the settings model.")
    source: str = Field("", description="The source location of the settings model.")
    docs: str = Field("", description="The documentation of the settings model.")
    env_prefix: str = Field("", description="The prefix of the environment variables.")
    field_name: str = Field("", description="The original field name (for child settings).")
    fields: list[FieldInfoModel] = Field(default_factory=list, description="The fields of the settings model.")
    child_settings: list["SettingsInfoModel"] = Field(
        default_factory=list, description="The child settings of the settings model."
    )
    env_accessible: bool = Field(
        True,
        description="False when this child model is not expandable via env vars (no nested_delimiter). "
        "Structural generators (TOML, simple) ignore this; env generators (dotenv) skip expansion.",
    )
    case_sensitive: bool = Field(
        False,
        description="Propagated from root model_config. When False, generators should uppercase env names.",
    )

    @classmethod
    def from_settings_model(  # noqa: C901
        cls,
        settings: BaseModel | type[BaseModel],
        global_settings: PSESettings | None = None,
        prefix: str = "",
        nested_delimiter: str | None = None,
        field_name: str = "",
        case_sensitive: bool = False,
        env_accessible: bool = True,
    ) -> Self:
        """Generate the SettingsInfoModel using a settings model.

        :param settings: The settings model to generate SettingsInfoModel from.
        :param global_settings: The global settings.
        :param prefix: The prefix of the environment variables.
        :param nested_delimiter: The delimiter to use for nested settings.
        :param field_name: The original field name (for child settings).
        :param case_sensitive: When True, env names are not uppercased (propagated from root).
        :param env_accessible: Propagated to child fields; False → env_names=[]. Used by env generators.
        :return: Instance of SettingsInfoModel.
        """
        if isinstance(settings, BaseModel):
            instance = settings
            settings_class = settings.__class__
        else:
            instance = None
            settings_class = settings

        conf = settings.model_config
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=PydanticDeprecationWarning)
            fields_info = settings_class.model_fields

        # Read root-level config values only when not called recursively (field_name is empty).
        # BUG-2 fix: child BaseSettings must not override the parent's nested_delimiter.
        # BUG-1 fix: None delimiter means no expansion of nested models.
        # BUG-5 fix: case_sensitive propagated from root so generators preserve case.
        if isinstance(settings, BaseSettings) or (isclass(settings) and issubclass(settings, BaseSettings)):
            prefix = prefix or settings.model_config.get("env_prefix", "")
            if not field_name:
                nested_delimiter = settings.model_config.get("env_nested_delimiter")
                case_sensitive = bool(settings.model_config.get("case_sensitive", False))

        populate_by_name = bool(conf.get("populate_by_name", False))
        is_nested = bool(field_name)

        child_settings: list[SettingsInfoModel] = []
        fields = []
        for name, field_info in fields_info.items():
            if global_settings and global_settings.respect_exclude and field_info.exclude:
                continue

            annotation = _resolve_field_annotation(field_info.annotation)

            # Nested BaseModel/BaseSettings: always add to child_settings (structural generators
            # like TOML/simple always expand). For env generators (dotenv/markdown), only
            # env_accessible=True children are expanded; False ones appear as JSON fields.
            if isclass(annotation) and issubclass(annotation, (BaseModel, BaseSettings)):
                child_instance = getattr(instance, name, None) if instance else None

                # A BaseSettings subclass with its own env_prefix is always independently
                # accessible via that prefix (BaseSettings.__init__ always runs its own env
                # sources, regardless of parent's nested_delimiter or default_factory path).
                has_own_prefix = issubclass(annotation, BaseSettings) and bool(
                    annotation.model_config.get("env_prefix", "")
                )
                env_expandable = nested_delimiter is not None or has_own_prefix

                if nested_delimiter is not None:
                    # Parent-delimiter path: {prefix}{field}{delimiter}{subfield}=value
                    child_prefix = f"{prefix}{name}{nested_delimiter}"
                    child_nested_delimiter: str | None = nested_delimiter
                elif has_own_prefix:
                    # Own-prefix path: child is a standalone BaseSettings with its own prefix.
                    # Use child's own env_prefix and its own nested_delimiter (if any).
                    child_prefix = str(annotation.model_config.get("env_prefix", ""))
                    child_nested_delimiter = annotation.model_config.get("env_nested_delimiter") or None  # type: ignore[assignment]
                else:
                    child_prefix = ""  # no env prefix — fields will have empty env_names
                    child_nested_delimiter = None

                child_settings.append(
                    cls.from_settings_model(
                        child_instance if child_instance else cast(type[BaseSettings], annotation),
                        global_settings=global_settings,
                        prefix=child_prefix,
                        nested_delimiter=child_nested_delimiter if env_expandable else None,
                        field_name=name,
                        case_sensitive=case_sensitive,
                        env_accessible=env_expandable,
                    )
                )
                if env_expandable:
                    continue  # env-accessible: only in child_settings
                # Not env-accessible: also add a synthetic JSON field for env generators.
                # Structural generators (TOML, simple) will skip is_env_only=True fields.
                json_field = FieldInfoModel.from_settings_field(
                    name,
                    field_info,
                    global_settings,
                    instance,
                    env_prefix=prefix,
                    is_nested=is_nested,
                    case_sensitive=case_sensitive,
                    populate_by_name=populate_by_name,
                    env_accessible=env_accessible,
                )
                fields.append(json_field.model_copy(update={"is_env_only": True}))
                continue  # always explicit, never fall through

            fields.append(
                FieldInfoModel.from_settings_field(
                    name,
                    field_info,
                    global_settings,
                    instance,
                    env_prefix=prefix,
                    is_nested=is_nested,
                    case_sensitive=case_sensitive,
                    populate_by_name=populate_by_name,
                    env_accessible=env_accessible,
                )
            )

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
        return cls(
            name=settings_name,
            source=settings_source(settings, global_settings),
            docs=docs,
            env_prefix=prefix,
            field_name=field_name,
            fields=fields,
            child_settings=child_settings,
            env_accessible=env_accessible,
            case_sensitive=case_sensitive,
        )
