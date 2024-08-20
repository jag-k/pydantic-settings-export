import warnings
from inspect import getdoc, isclass
from pathlib import Path
from types import UnionType
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.fields import FieldInfo
from pydantic_core import PydanticSerializationError, PydanticUndefined
from pydantic_settings import BaseSettings

from pydantic_settings_export.constants import FIELD_TYPE_MAP
from pydantic_settings_export.settings import Settings

__all__ = (
    "FieldInfoModel",
    "SettingsInfoModel",
)


def _prepare_example(example: Any) -> str:
    """Prepare the example for the field."""
    if isinstance(example, set):
        example = sorted(example)
    return str(example)


class FieldInfoModel(BaseModel):
    """Info about the field of the settings model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="The name of the field.")
    type: str = Field(..., description="The type of the field.")
    default: str | None = Field(
        None,
        description="The default value of the field.",
        validate_default=False,
    )
    description: str | None = Field(None, description="The description of the field.")
    example: str | None = Field(None, description="The example of the field.")
    alias: str | None = Field(None, description="The alias of the field.")

    @property
    def is_required(self) -> bool:
        """Check if the field is required."""
        return self.default is PydanticUndefined

    @staticmethod
    def create_default(field: FieldInfo, global_settings: Settings | None = None) -> str | None:
        """Make the default value for the field.

        :param field: The field info to generate the default value for.
        :param global_settings: The global settings.
        :return: The default value for the field as a string, or None if there is no default value.
        """
        default: object | PydanticUndefined = field.default

        if default is PydanticUndefined and field.default_factory:
            default = field.default_factory()

        if (
            # if we need to replace absolute paths
            global_settings
            and global_settings.relative_to.replace_abs_paths
            # Check if default is a Path and is absolute
            and isinstance(default, Path)
            and default.is_absolute()
        ):
            try:
                # Make the default path relative to the global_settings
                default = Path(global_settings.relative_to.alias) / default.relative_to(
                    global_settings.project_dir.resolve().absolute()
                )
            except ValueError:
                pass

        if default is PydanticUndefined:
            return None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return TypeAdapter(field.annotation).dump_json(default).decode()
        except PydanticSerializationError:
            return str(default)

    @classmethod
    def from_settings_field(
        cls,
        name: str,
        field: FieldInfo,
        global_settings: Settings | None = None,
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
        example: str | None = _prepare_example(field.examples[0]) if field.examples else default

        return cls(
            name=name,
            type=type_,
            default=default,
            description=description,
            example=example,
            alias=field.alias,
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
        global_settings: Settings | None = None,
    ) -> Self:
        """Generate SettingsInfoModel using a settings model.

        :param settings: The settings model to generate SettingsInfoModel from.
        :param global_settings: The global settings.
        :return: Instance of SettingsInfoModel.
        """
        conf = settings.model_config
        fields_info = settings.model_fields

        child_settings = []
        fields = []
        for name, field_info in fields_info.items():
            if global_settings and global_settings.respect_exclude and field_info.exclude:
                continue
            annotation = field_info.annotation
            if isclass(annotation) and issubclass(annotation, BaseSettings):
                child_settings.append(cls.from_settings_model(annotation, global_settings=global_settings))
                continue
            fields.append(FieldInfoModel.from_settings_field(name, field_info, global_settings))

        return cls(
            name=(
                # Get the title from the settings model if it exists
                conf.get("title", None)
                # Otherwise, get the name from the settings model if it exists
                or getattr(settings, "__name__", None)
                # Otherwise, get the class name from the settings model
                or str(settings.__class__.__name__)
            ),
            docs=(getdoc(settings) or "").strip(),
            env_prefix=conf.get("env_prefix", ""),
            fields=fields,
            child_settings=child_settings,
        )
