# pydantic-settings-export

[![PyPI version](https://img.shields.io/pypi/v/pydantic-settings-export?logo=pypi&label=pydantic-settings-export)](https://pypi.org/project/pydantic-settings-export/)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/pydantic-settings-export)

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

```python
from pydantic import BaseSettings

from pydantic_settings_export import Exporter, Generators, PSESettings
from pydantic_settings_export.generators import MarkdownGenerator


class Settings(BaseSettings):
  my_setting: str = "default value"
  another_setting: int = 42


# Export the settings to a Markdown file `docs/Configuration.md` and `.env.example` file
Exporter(
  PSESettings(
    generators=Generators(
      markdown=MarkdownGenerator.config(
        save_dirs=["docs"],
      ),
    )
  ),
).run_all(Settings)

# OR

Exporter(
  PSESettings.model_validate(
    {
      "generators": {
        "markdown": {
          "save_dirs": ["docs"],
        },
      },
    },
  ),
).run_all(Settings)
```

### As CLI

```bash
pydantic-settings-export --help
```

## Configuration

You can add a `pydantic_settings_export` section to your `pyproject.toml` file to configure the exporter.

```toml

[tool.pydantic_settings_export]
project_dir = "."
default_settings = [
  "pydantic_settings_export.settings:Settings",
]

[tool.pydantic_settings_export.generators.dotenv]
path = ".env.example"

[tool.pydantic_settings_export.generators.markdown]
path = "Configuration.md"
save_dirs = [
  "docs",
  "wiki",
]
```

## Todo

- [ ] Add tests
- [ ] Add more configuration options
- [ ] Add more output formats
  - [ ] TOML (and `pyproject.toml`)
  - [ ] JSON
  - [ ] YAML


## License

[MIT](https://github.com/jag-k/pydantic-settings-export/blob/main/LICENCE)
