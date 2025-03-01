# Contributing to pydantic-settings-export

Thank you for your interest in contributing to pydantic-settings-export!
This document provides guidelines and instructions for contributing.

## Development Setup

1. **Install `uv` for development**
   ```bash
   # On macOS and Linux.
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # On Windows.
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   More info about installing `uv` can be found [here](https://github.com/astral-sh/uv#installation).

2. **Clone the repository**
   ```bash
   git clone https://github.com/jag-k/pydantic-settings-export.git
   cd pydantic-settings-export
   ```

3. **Set up a development environment**
   ```bash
   # Using uv
   uv sync --all-extras

   # Install pre-commit hooks
   pre-commit install
   ```

## Development Process

### Code Style

We use several tools to maintain code quality:

- **Ruff** for linting and formatting
- **MyPy** for type checking
- **pre-commit** for automated checks

Configuration for these tools is in `pyproject.toml`.

### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and ensure all tests pass:
   ```bash
   pytest
   ```

3. Update documentation if needed:
   ```bash
   pydantic-settings-export --generator markdown
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: your descriptive commit message"
   ```

   We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Pull Request Process

1. Update the README.md if needed
2. Update documentation if you're adding/changing features
3. Add tests for new functionality
4. Ensure that all checks pass
5. Submit your PR with a clear description

## Testing

Run tests with pytest:
```bash
pytest
```

Add new tests in the `tests/` directory, following existing patterns.

## Documentation

- Update relevant documentation to [GitHub Wiki](https://github.com/jag-k/pydantic-settings-export/wiki)
- Keep docstrings up to date
- Add examples for new features

## Release Process

The release process is only made by maintainers:

  - Project owner: [@jag-k](https://github.com/jag-k)

1. Create a new git tag by running `git tag -a v1.0.0 -m "Release v1.0.0"`
2. CI will automatically publish to PyPI and create a GitHub release

## Getting Help

- Open an [issue](https://github.com/jag-k/pydantic-settings-export/issues)
- Start a [discussion](https://github.com/jag-k/pydantic-settings-export/discussions)
- Ask questions in existing issues/discussions

## Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md).
By participating in this project, you agree to abide by its terms.
