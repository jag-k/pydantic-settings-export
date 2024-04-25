from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, SecretStr


__all__ = (
    "StrAsPath",
    "FIELD_TYPE_MAP",
)

StrAsPath = Annotated[Path, BeforeValidator(lambda v: Path(v))]

FIELD_TYPE_MAP = {
    SecretStr: "string",
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    None: "null",
}
