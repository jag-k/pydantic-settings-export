# pydantic-settings-export

[![PyPI - Project version](https://img.shields.io/pypi/v/pydantic-settings-export?logo=pypi)](https://pypi.org/p/pydantic-settings-export/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pydantic-settings-export)](https://pypi.org/p/pydantic-settings-export/)
[![Pepy - Total Downloads](https://img.shields.io/pepy/dt/pydantic-settings-export)](https://pypi.org/p/pydantic-settings-export/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pydantic-settings-export)](https://pypi.org/project/pydantic-settings-export/)
[![PyPI - License](https://img.shields.io/pypi/l/pydantic-settings-export)](https://github.com/jag-k/pydantic-settings-export/blob/main/LICENSE)

*Export your Pydantic settings to Markdown and .env.example files!*

This package provides a way to use [pydantic](https://docs.pydantic.dev/) (and [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)) models to generate a Markdown file with the settings and their descriptions, and a `.env.example` file with the settings and their default values.

## Installation

```bash
pip install pydantic-settings-export
# or
pipx install pydantic-settings-export  # for a global installation and using as a CLI
# or
uv tool install pydantic-settings-export
```

## Usage

You can see the usage examples of this package in the [./docs/Configuration.md](https://github.com/jag-k/pydantic-settings-export/blob/main/docs/Configuration.md) and [.env.example](https://github.com/jag-k/pydantic-settings-export/blob/main/.env.example).

### As code

This project is not well-designed for using as a library. But you still can use it as a code.

```python
from pydantic import BaseSettings

from pydantic_settings_export import Exporter, PSESettings
from pydantic_settings_export.generators import MarkdownGenerator


class Settings(BaseSettings):
  my_setting: str = "default value"
  another_setting: int = 42


# Export the settings to a Markdown file `docs/Configuration.md`
pse_settings = PSESettings()
Exporter(
    pse_settings,
    generators=[
        MarkdownGenerator(
            pse_settings,
            MarkdownGenerator.config(
                save_dirs=["docs"],
            ),
        )
    ]
).run_all(Settings)
```

### As CLI

<!-- region:cli -->
```bash
pydantic-settings-export --help
```
<!-- endregion:cli -->

## Configuration

You can add a `pydantic_settings_export` section to your `pyproject.toml` file to configure the exporter.

```toml

[tool.pydantic_settings_export]
project_dir = "."
default_settings = [
  "pydantic_settings_export.settings:PSESettings",
]

[[tool.pydantic_settings_export.generators.dotenv]]
paths = [
  ".env.example",
]

[tool.pydantic_settings_export.generators.markdown]
paths = [
  "docs/Configuration.md",
  "wiki/Configuration.md",
]
```

## Todo

- [x] Add more configuration options
- [ ] Add tests


## License

[MIT](https://github.com/jag-k/pydantic-settings-export/blob/main/LICENCE)
