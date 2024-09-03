# pydantic-settings-export

[![PyPI version](https://img.shields.io/pypi/v/pydantic-settings-export?logo=pypi&label=pydantic-settings-export)](https://pypi.org/project/pydantic-settings-export/)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/pydantic-settings-export)

*Export your Pydantic settings to a Markdown and .env.example files!*

This package provides a way to use [pydantic](https://docs.pydantic.dev/) (and [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)) models to generate a Markdown file with the settings and their descriptions, and a `.env.example` file with the settings and their default values.

## Installation

```bash
pip install pydantic-settings-export
# or
pipx install pydantic-settings-export  # for a global installation and using as a CLI
```

## Usage

You can see the examples of usage this package in the [./docs/Configuration.md](./docs/Configuration.md) and [.env.example](./.env.example).

### As code

```python
from pydantic import BaseSettings
from pydantic_settings_export import Exporter, MarkdownSettings, Settings as PSESettings


class Settings(BaseSettings):
  my_setting: str = "default value"
  another_setting: int = 42


# Export the settings to a Markdown file `docs/Configuration.md` and `.env.example` file
Exporter(
  PSESettings(
    markdown=MarkdownSettings(
      save_dirs=["docs"],
    ),
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
dotenv = { "name" = ".env.example" }

[tool.pydantic_settings_export.markdown]
name = "Configuration.md"
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

[MIT](./LICENCE)
