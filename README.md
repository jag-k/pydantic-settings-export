<!-- markdownlint-configure-file
{
  "MD007": {
    "indent": 4
  }
}
-->

# pydantic-settings-export

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![PyPI - Project version](https://img.shields.io/pypi/v/pydantic-settings-export?logo=pypi)][pypi]
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pydantic-settings-export)][pypi]
[![Pepy - Total Downloads](https://img.shields.io/pepy/dt/pydantic-settings-export)][pypi]
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pydantic-settings-export)][pypi]
[![PyPI - License](https://img.shields.io/pypi/l/pydantic-settings-export)][license]

Generate documentation and example config files from [pydantic-settings] models.

`pydantic-settings-export` reads `BaseSettings` classes or instances and writes the same configuration contract to the
files your project already uses: Markdown documentation, `.env.example`, TOML examples, or plain text output.

## What It Exports

| Output     | Generator  | Typical file            | Notes                                                                        |
|------------|------------|-------------------------|------------------------------------------------------------------------------|
| Markdown   | `markdown` | `docs/configuration.md` | Tables with env names, types, defaults, descriptions, and examples.          |
| dotenv     | `dotenv`   | `.env.example`          | Required variables stay uncommented; values with defaults are commented.     |
| TOML       | `toml`     | `config.example.toml`   | Structured config with comments, sections, defaults, and optional prefixing. |
| Plain text | `simple`   | `settings.txt`          | Compact human-readable output; also used by `--help-generators`.             |

The exporter understands:

- `Field(description=...)`, `Field(examples=...)`, aliases, deprecation markers, defaults, and required fields.
- `env_prefix`, `env_nested_delimiter`, `case_sensitive`, nested settings models, and `populate_by_name`.
- settings classes, settings instances, or a whole module containing `BaseSettings` subclasses.
- generator-specific `settings` and `extend_settings` overrides when different outputs need different settings models.

## Requirements

- Python 3.10+
- `pydantic >= 2.7`
- `pydantic-settings >= 2.3`

Optional extras:

| Extra     | Installs                        | Required for                                      |
|-----------|---------------------------------|---------------------------------------------------|
| `email`   | `email-validator`               | Models that use `pydantic.EmailStr`.              |
| `regions` | `text-region-parser`            | Markdown region replacement via `region = "..."`. |
| `toml`    | `tomlkit`                       | TOML generation.                                  |
| `all`     | all optional dependencies above | Projects that use every optional feature.         |

## Installation

```bash
pip install pydantic-settings-export
pip install "pydantic-settings-export[toml]"
pip install "pydantic-settings-export[email,regions,toml]"
```

For CLI-only usage:

```bash
pipx install pydantic-settings-export
uv tool install pydantic-settings-export
```

## Quick Start

Create a settings model:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    debug: bool = Field(False, description="Enable debug mode.")
    api_key: str = Field(..., description="API key used by the application.")
```

Add exporter configuration to `pyproject.toml`:

```toml
[tool.pydantic_settings_export]
project_dir = "."
default_settings = ["app.settings:AppSettings"]

[[tool.pydantic_settings_export.generators.markdown]]
paths = ["docs/configuration.md"]

[[tool.pydantic_settings_export.generators.dotenv]]
paths = [".env.example"]
```

Run the exporter:

```bash
pydantic-settings-export
```

or pass settings directly:

```bash
pydantic-settings-export app.settings:AppSettings
pse app.settings
```

`module:attribute` imports one settings class or instance. A plain module path imports all `BaseSettings` subclasses
defined in that module.

## CLI

```bash
# Use settings from pyproject.toml
pydantic-settings-export

# Export one class
pydantic-settings-export app.settings:AppSettings

# Auto-discover BaseSettings subclasses in a module
pydantic-settings-export app.settings

# Load values needed while importing settings
pydantic-settings-export --env-file .env -- app.settings:AppSettings

# Override virtual environment detection
pydantic-settings-export --venv uv app.settings:AppSettings
pydantic-settings-export --venv .venv app.settings:AppSettings
pydantic-settings-export --venv "" app.settings:AppSettings

# Inspect selected generator configuration fields
pydantic-settings-export --generator markdown dotenv -- --help-generators

# Inspect all generator configuration fields
pydantic-settings-export --help-generators
```

CLI options override environment variables and `pyproject.toml`.

## Configuration

Global configuration lives under `[tool.pydantic_settings_export]`:

```toml
[tool.pydantic_settings_export]
project_dir = "."
root_dir = "."
default_settings = ["app.settings:AppSettings"]
env_file = ".env"
venv = "auto"
respect_exclude = true

[tool.pydantic_settings_export.relative_to]
replace_abs_paths = true
alias = "<project_dir>"
```

| Field              | Default           | Purpose                                                                                                  |
|--------------------|-------------------|----------------------------------------------------------------------------------------------------------|
| `project_dir`      | current directory | Added to `sys.path` before importing settings.                                                           |
| `root_dir`         | `project_dir`     | Base directory for relative output paths and relative path rendering.                                    |
| `default_settings` | `[]`              | Import strings used when no settings are passed on the CLI.                                              |
| `env_file`         | `null`            | Loads environment variables before settings are imported.                                                |
| `venv`             | `"auto"`          | Import packages from `./venv`, `./.venv`, `uv`, `poetry`, an explicit venv path, or disable with `null`. |
| `respect_exclude`  | `true`            | Skip fields marked with Pydantic `exclude`.                                                              |
| `relative_to`      | object            | Rewrites absolute paths under `root_dir` as `<project_dir>/...` in generated output.                     |

## Generator Blocks

Every generator block supports these common fields:

| Field             | Purpose                                                                                      |
|-------------------|----------------------------------------------------------------------------------------------|
| `enabled`         | Disable a configured block without deleting it.                                              |
| `paths`           | Output files. Relative paths are resolved from `root_dir`.                                   |
| `settings`        | Replace `default_settings` for this generator block.                                         |
| `extend_settings` | Add settings to `default_settings` for this generator block. Ignored when `settings` is set. |

### Markdown

```toml
[[tool.pydantic_settings_export.generators.markdown]]
paths = ["docs/configuration.md"]
file_prefix = "# Configuration"
table_only = false
to_upper_case = true

[[tool.pydantic_settings_export.generators.markdown]]
paths = ["README.md"]
region = "settings"
table_only = true
```

Useful options:

| Field           | Default               | Purpose                                                                        |
|-----------------|-----------------------|--------------------------------------------------------------------------------|
| `file_prefix`   | configuration heading | Text placed before generated Markdown.                                         |
| `table_headers` | all columns           | Reorder or remove `Name`, `Type`, `Default`, `Description`, `Example`.         |
| `table_only`    | `false`               | Generate one combined table instead of per-settings sections.                  |
| `region`        | `false`               | Replace a named region in an existing Markdown file. Requires `regions` extra. |
| `to_upper_case` | `true`                | Uppercase env names unless the settings model is `case_sensitive=True`.        |

### dotenv

```toml
[[tool.pydantic_settings_export.generators.dotenv]]
paths = [".env.example"]
mode = "all"
split_by_group = true
add_examples = true
to_upper_case = true
```

Useful options:

| Field            | Default | Purpose                                                                 |
|------------------|---------|-------------------------------------------------------------------------|
| `mode`           | `"all"` | Use `"all"`, `"only-optional"`, or `"only-required"`.                   |
| `split_by_group` | `true`  | Add section headers for settings classes.                               |
| `add_examples`   | `true`  | Append examples from `Field(examples=...)` as comments.                 |
| `to_upper_case`  | `true`  | Uppercase env names unless the settings model is `case_sensitive=True`. |

### TOML

Install the TOML extra first:

```bash
pip install "pydantic-settings-export[toml]"
```

```toml
[[tool.pydantic_settings_export.generators.toml]]
paths = ["config.example.toml"]
mode = "all"
comment_defaults = true
section_depth = 2
prefix = "tool.my_app"
```

Useful options:

| Field              | Default | Purpose                                                                      |
|--------------------|---------|------------------------------------------------------------------------------|
| `mode`             | `"all"` | Use `"all"`, `"only-optional"`, or `"only-required"`.                        |
| `comment_defaults` | `true`  | Comment out fields that have defaults. Required fields are always commented. |
| `show_header`      | `true`  | Include settings class name and docstring comments.                          |
| `show_types`       | `true`  | Include type comments.                                                       |
| `show_description` | `true`  | Include field descriptions.                                                  |
| `show_default`     | `true`  | Include default comments.                                                    |
| `show_examples`    | `true`  | Include example comments.                                                    |
| `section_depth`    | `null`  | Control when nested settings become TOML sections vs dotted keys.            |
| `prefix`           | `null`  | Put all generated keys under a dotted prefix such as `tool.my_app`.          |

## pre-commit Hook

The published hook can keep generated files current in another project:

```yaml
repos:
  - repo: https://github.com/jag-k/pydantic-settings-export
    rev: v1.0.0
    hooks:
      - id: pydantic-settings-export
        files: ^app/settings\.py$
        additional_dependencies:
          - pydantic-settings-export[email,regions,toml]
```

When the hook needs to import packages from your project, configure venv discovery:

```toml
[tool.pydantic_settings_export]
venv = "auto"
```

Detection order for `"auto"` is `./venv`, `./.venv`, uv, then Poetry.

## Python API

The API is useful when you need to run exporters from tests, scripts, or a custom workflow.

```python
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from pydantic_settings_export import Exporter, PSESettings
from pydantic_settings_export.generators.dotenv import DotEnvGenerator, DotEnvSettings
from pydantic_settings_export.generators.markdown import MarkdownGenerator, MarkdownSettings


class AppSettings(BaseSettings):
    """Application configuration."""

    debug: bool = Field(False, description="Enable debug mode.")
    api_key: str


settings = PSESettings(project_dir=Path("."), root_dir=Path("."))
generators = [
    MarkdownGenerator(settings, MarkdownSettings(paths=[Path("docs/configuration.md")])),
    DotEnvGenerator(settings, DotEnvSettings(paths=[Path(".env.example")])),
]

updated_files = Exporter(settings, generators).run_all(AppSettings)
```

You can pass a settings instance instead of a class when the generated output should include runtime values:

```python
app_settings = AppSettings(api_key="secret", debug=True)
Exporter(settings, generators).run_all(app_settings)
```

## Examples

Generated examples in this repository:

- [examples/.env.example](examples/.env.example)
- [examples/.env.only_optional_mode.example](examples/.env.only_optional_mode.example)
- [examples/Configuration.md](examples/Configuration.md)
- [examples/SimpleConfiguration.md](examples/SimpleConfiguration.md)
- [examples/InjectedConfiguration.md](examples/InjectedConfiguration.md)
- [examples/config.example.toml](examples/config.example.toml)
- [examples/pyproject.example.toml](examples/pyproject.example.toml)

The repository's own export configuration is in [pyproject.toml](pyproject.toml).

## Development

This project uses `uv`, `prek`, Ruff, and `ty`.

```bash
uv sync --all-extras --dev
uv run pytest
uv run ruff check . --fix
uv run ruff format .
uv run ty check
uv run prek run --all-files
```

Generated documentation and examples are refreshed with:

```bash
uv run pydantic-settings-export
```

## Contributing

Before opening a pull request:

1. Create a GitHub issue first.
2. Fork the repository.
3. Create a branch named `<domain>/<issue-number>-<short-description>`, where `<domain>` is `fix` or `feature`.
4. Make the change and update generated examples/docs when behavior changes.
5. Open a PR with a short changelog in the description.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Support

- [Issue Tracker][gh-issues]
- [Discussions][gh-discussions]
- [Wiki][gh-wiki]

## License

[MIT][license]

[pypi]: https://pypi.org/project/pydantic-settings-export/
[license]: https://github.com/jag-k/pydantic-settings-export/blob/main/LICENCE
[gh-wiki]: https://github.com/jag-k/pydantic-settings-export/wiki
[gh-issues]: https://github.com/jag-k/pydantic-settings-export/issues
[gh-discussions]: https://github.com/jag-k/pydantic-settings-export/discussions
[pydantic-settings]: https://github.com/pydantic/pydantic-settings
