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
[![PyPI - Project version](https://img.shields.io/pypi/v/pydantic-settings-export?logo=pypi)][pypi]
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pydantic-settings-export)][pypi]
[![Pepy - Total Downloads](https://img.shields.io/pepy/dt/pydantic-settings-export)][pypi]
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pydantic-settings-export)][pypi]
[![PyPI - License](https://img.shields.io/pypi/l/pydantic-settings-export)][license]

*Export your Pydantic settings to documentation with ease!*

This package seamlessly integrates with [pydantic] and [pydantic-settings] to automatically generate documentation from your settings models.
Create Markdown docs, `.env.example` files, and more with minimal configuration.

## ✨ Key Features

- 📝 Documentation Generation
    - Markdown with tables and descriptions
    - Environment files (`.env.example`)
    - Support for region injection in existing files
    - Customizable output formats

- 🔄 Smart Configuration Handling
    - Automatic type detection
    - Environment variables validation
    - Default values preservation
    - Optional/required fields distinction

- 🛠 Flexible Integration
    - Command-line interface
    - [pre-commit] hook support
    - GitHub Actions compatibility
    - Python API for custom solutions

- 🔌 Additional Features
    - Email validation support (optional)
    - Markdown region injection (optional)
    - Multiple output paths for each generator
    - Configurable through `pyproject.toml`

## 📋 Requirements

- Python 3.11 or higher
- pydantic >= 2.7
- pydantic-settings >= 2.3

Optional dependencies (aka `extras`):

- `email` -- for email validation support (`email-validator >= 2.2.0`).
    - Required for `pydantic.EmailStr` type.
- `regions` -- for Markdown region insertion support (`text-region-parser >= 0.1.1`).
    - Required for Markdown generator with `region` option.

Install with optional dependencies:

```bash
# Install with all optional dependencies
pip install "pydantic-settings-export[email,regions]"  # Install with all extras

# Install with specific optional dependency
pip install "pydantic-settings-export[email]"  # Install with email extra
pip install "pydantic-settings-export[regions]"  # Install with regions extra
```

## 🚀 Quick Start

1. Install the package:
    ```bash
    pip install pydantic-settings-export
    ```
2. Create your settings model:
    ```python
    from pydantic_settings import BaseSettings


    class AppSettings(BaseSettings):
        """Application settings."""
        debug: bool = False
        api_key: str
    ```
3. Generate documentation:
    ```bash
    pydantic-settings-export app.settings:AppSettings
    ```

For more detailed usage, see our [Getting Started Guide][gh-wiki/getting-started].

> Note: The package follows [SemVer](https://semver.org).
> GitHub releases/tags use `v` prefix (e.g. `v1.0.0`), while PyPI versions don't (e.g. `1.0.0`).

## Installation

Choose your preferred installation method:

```bash
# Using pip
pip install pydantic-settings-export

# Using pipx (recommended for CLI usage)
pipx install pydantic-settings-export

# Using uv
uv tool install pydantic-settings-export
```

## Usage

The recommended way to use this package is through its CLI or as a [pre-commit] hook.

### CLI Usage

The CLI provides a powerful interface for generating documentation:

```bash
# Basic usage
pydantic-settings-export your_app.settings:Settings

# Multiple generators
pydantic-settings-export --generator markdown --generator dotenv your_app.settings:Settings

# Help with all options and sub-commands
pydantic-settings-export --help
```

For complete documentation including:

- All command options
- Environment variables
- Pre-commit integration
- Troubleshooting guide

See the [CLI Documentation][gh-wiki/cli]

### pre-commit hook

The tool can be used as a pre-commit hook to automatically update documentation:

<!-- @formatter:off -->
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/jag-k/pydantic-settings-export
    # Use a tag version with the `v` prefix (e.g. v1.0.0)
    rev: v1.0.0
    hooks:
     - id: pydantic-settings-export
       # Optionally, specify the settings file to trigger the hook only on changes to this file
       files: ^app/config/settings\.py$
       # Optionally, add extra dependencies
       additional_dependencies:
         - pydantic-settings-export[email,regions]
```

NOTE: You can use `pre-commit autoupdate` to update the hook to the latest version.

### CI/CD Integration

<!-- @formatter:off -->
```yaml
# .github/workflows/docs.yml
name: Update Settings Documentation
on:
  push:
    # Optionally, specify the settings file to trigger the hook only on changes to this file
    paths: [ '**/settings.py' ]
jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"  # Minimum required version
      - run: pip install pydantic-settings-export
      - run: pydantic-settings-export your_app.settings:Settings
```

### Programmatic Usage

While CLI is the recommended way, you can also use the package programmatically:

```python
from pydantic_settings import BaseSettings
from pydantic_settings_export import Exporter


class MySettings(BaseSettings):
    """Application settings."""
    debug: bool = False
    api_key: str

    class Config:
        env_prefix = "APP_"


# Create and run exporter
exporter = Exporter()
exporter.run_all(MySettings)
```

This will generate documentation using all available generators. For custom configuration, see our [Wiki][gh-wiki].

## Configuration

Basic configuration in `pyproject.toml`:

```toml
[tool.pydantic_settings_export]
project_dir = "."
default_settings = ["my_app.settings:AppSettings"]
env_file = ".env"

# Generate Markdown docs
[[tool.pydantic_settings_export.generators.markdown]]
paths = ["docs/settings.md"]

# Generate .env example
[[tool.pydantic_settings_export.generators.dotenv]]
paths = [".env.example"]
```

For advanced configuration options, see our [Configuration Guide][gh-wiki/config].

## Examples

See real-world examples of different output formats:

### Environment Files

- [.env.example](examples/.env.example) - Full example with comments and sections
- [.env.only-optional.example](examples/.env.only-optional.example) - Example with only optional fields

### Documentation

- [Configuration.md](examples/Configuration.md) - Full configuration documentation with tables and descriptions
- [SimpleConfiguration.md](examples/SimpleConfiguration.md) - Basic table-only configuration
- [InjectedConfiguration.md](examples/InjectedConfiguration.md) - Configuration injected into existing file

## 📚 Learn More

Check out our comprehensive documentation:

- 🏁 [Getting Started Guide][gh-wiki/getting-started]
- ⚙️ [Configuration Options][gh-wiki/config]
- 🔍 [Understanding Parsers][gh-wiki/parsers]
- 🎨 [Available Generators][gh-wiki/generators]
- 💻 [CLI Documentation][gh-wiki/cli]

## 🎯 Why This Project?

Managing configuration in Python applications can be challenging:

- Documentation gets outdated
- Environment variables are poorly documented
- Configuration options are scattered

This project solves these problems by:

- Automatically generating documentation from your Pydantic models
- Keeping documentation in sync with code
- Providing multiple output formats for different use cases

## Development Context

This is a personal pet project maintained in my spare time. The development priorities are:

1. Bug fixes
2. Features from Roadmap:
    - Issues with closest milestone.
    - General milestone issues.
    - Issues labeled `bug` or `feature request`.
    - Features listed in this README.
3. New feature proposals

> Note: While we strive for quality and responsiveness, resolution timelines can't be guaranteed.

### Development Tools

This project uses modern Python development tools:

- 🚀 [uv] - Fast Python package installer and resolver
- 🔍 [ruff] - Fast Python linter and formatter
- 📦 [hatch] - Modern Python project management
- ✅ [pre-commit] - Git hooks management

## Contributing

We welcome contributions! Before contributing:

1. Create a GitHub Issue first — this is **required**
2. Fork the repository
3. Create a branch following our naming convention:
    - Format: `<domain>/<issue-number>-<short-description>`.
    - Domains: `fix` or `feature`.
    - Example: `feature/6-inject-config-to-markdown`.
4. Make your changes
5. Submit a PR with changelog in description

For complete guidelines, see our:

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Contributing Guide](CONTRIBUTING.md)

## Support

### Primary Contact

- 🐛 [Issue Tracker][gh-issues] (required first point of contact)

### Secondary Contact (after creating an issue)

- 📧 GitHub email: `30597878+jag-k@users.noreply.github.com`
- 💬 [Discussions][gh-discussions]
- 📚 [Documentation][gh-wiki]

## License

[MIT][license]


[pypi]: https://pypi.org/project/pydantic-settings-export/

[license]: https://github.com/jag-k/pydantic-settings-export/blob/main/LICENSE

[gh-wiki]: https://github.com/jag-k/pydantic-settings-export/wiki

[gh-wiki/cli]: https://github.com/jag-k/pydantic-settings-export/wiki/CLI

[gh-wiki/config]: https://github.com/jag-k/pydantic-settings-export/wiki/Configuration

[gh-wiki/getting-started]: https://github.com/jag-k/pydantic-settings-export/wiki/Getting-Started

[gh-wiki/parsers]: https://github.com/jag-k/pydantic-settings-export/wiki/Parsers

[gh-wiki/generators]: https://github.com/jag-k/pydantic-settings-export/wiki/Generators

[gh-issues]: https://github.com/jag-k/pydantic-settings-export/issues

[gh-discussions]: https://github.com/jag-k/pydantic-settings-export/discussions

[pydantic]: https://github.com/pydantic/pydantic

[pydantic-settings]: https://github.com/pydantic/pydantic-settings

[pre-commit]: https://github.com/pre-commit/pre-commit

[uv]: https://github.com/astral-sh/uv

[ruff]: https://github.com/astral-sh/ruff

[hatch]: https://github.com/pypa/hatch
