---
name: pydantic-settings-export
description: >-
  Generate and maintain documentation and example config files (Markdown tables, .env.example, TOML examples, plain
  text) from pydantic-settings `BaseSettings` models with the `pydantic-settings-export` CLI (`pse`). Use when a Python
  project uses pydantic-settings and needs its configuration documented, an `.env.example` or config example created
  or kept in sync, `[tool.pydantic_settings_export]` set up or changed in `pyproject.toml`, a pre-commit hook or CI
  check for outdated generated config docs, or when `pydantic-settings-export`/`pse` fails.
---

# pydantic-settings-export

`pydantic-settings-export` reads `BaseSettings` classes and writes the same configuration contract into docs and
example files. Configuration lives in `[tool.pydantic_settings_export]` in `pyproject.toml`. The CLI is
`pydantic-settings-export`, with the short alias `pse`.

Run it the way the project runs its tools: `uv run pse`, `poetry run pse`, or `pse` in an activated venv.
Without a project install, use `uvx pydantic-settings-export` or `pipx run pydantic-settings-export`.
With `venv = "auto"` (the default) it adds the project's `./.venv`, `./venv`, uv or Poetry environment to the import
path, so the project's settings can still be imported.

Ask the tool about the installed version instead of guessing:

- `pse --help`: CLI flags. If `--check` is missing, the installed version predates it; suggest upgrading.
- `pse --help-generators`: every option of every generator, with defaults and examples.
- [references/pyproject.example.toml](references/pyproject.example.toml): every global option, as commented TOML.

## Set up in a project

1. **Find the settings.** Search for `BaseSettings` subclasses. Prefer pointing at classes (`app.settings:Settings`)
   or a module (`app.settings`, which picks up every `BaseSettings` subclass defined in it). Avoid a module-level
   instance such as `settings = Settings()`: importing it requires the real environment variables.
2. **Pick generators and extras** from what the project already uses:

   | Output                                   | Generator  | Extra needed                                  |
   |------------------------------------------|------------|-----------------------------------------------|
   | `docs/configuration.md`, README section  | `markdown` | `regions` only for `region = "..."`           |
   | `.env.example`                           | `dotenv`   | none                                          |
   | `config.example.toml`                    | `toml`     | `toml`                                        |
   | compact text                             | `simple`   | none                                          |

   Models that use `EmailStr` also need the `email` extra. Add the package as a dev dependency with the extras, for
   example `uv add --dev "pydantic-settings-export[toml]"`.
3. **Configure** `pyproject.toml`:

   ```toml
   [tool.pydantic_settings_export]
   project_dir = "."
   default_settings = ["app.settings:Settings"]

   [[tool.pydantic_settings_export.generators.markdown]]
   paths = ["docs/configuration.md"]

   [[tool.pydantic_settings_export.generators.dotenv]]
   paths = [".env.example"]
   ```

   - Each `[[...generators.<name>]]` block is one output configuration; repeat a block for several variants.
   - `paths` are relative to `root_dir`, which defaults to `project_dir`.
   - `settings = [...]` replaces `default_settings` for one block; `extend_settings = [...]` adds to it.
   - To inject a table into an existing Markdown file, add `<!-- region:config -->` and `<!-- endregion:config -->`
     to the file, then set `region = "config"` (and usually `table_only = true`). The file must already exist.
   - Generator names are `markdown`, `dotenv`, `toml`, `simple`. Recent versions reject unknown names.
4. **Run** `pse` and read the generated files. If a field is missing, has no description, or exposes a value, fix the
   settings model (see below), not the generated file: generated files are overwritten on every run.
5. **Keep it in sync** (next section).

## Make the settings document well

The output is only as good as the models:

- Give every field `Field(description=...)`. A class docstring becomes the section description.
- Add `Field(examples=[...])` for non-obvious values such as URLs, DSNs, lists, or enums.
- Use `SecretStr` for secrets: the output shows `**********`, not the default.
- Hide internal fields with `Field(exclude=True)`. It is respected by default (`respect_exclude = true`).
- Mark old fields with `Field(deprecated=...)`; they are flagged in the output.
- `env_prefix`, `env_nested_delimiter`, aliases, `case_sensitive`, and nested models are reflected in the generated
  variable names. Check names in the output after changing them.

## Keep generated files up to date

- **pre-commit / prek hook** (regenerates files):

  ```yaml
  - repo: https://github.com/jag-k/pydantic-settings-export
    rev: <latest tag>
    hooks:
      - id: pydantic-settings-export
  ```

  In recent versions the hooks install all extras by default. Setting `additional_dependencies` replaces that
  default, so keep `.[all]` (or the extras you need) in the list. In older versions, add
  `pydantic-settings-export[email,regions,toml]` instead.
- **Check only, for CI**: `pse --check` writes nothing. It prints a unified diff and exits with code 1 when a file is
  missing or outdated, or when a file could not be checked (failed generator, settings that cannot be imported,
  missing region file). There is also a `pydantic-settings-export-check` hook that runs on every commit.

  ```yaml
  # GitHub Actions, uv project with pydantic-settings-export as a dev dependency
  - uses: astral-sh/setup-uv@v7
  - run: uv sync --all-extras --dev
  - run: uv run pse --check
  ```

## Troubleshooting

| Symptom                                                     | Cause and fix                                                                                                                                                         |
|-------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `You have N missing settings ... set this required ENV Vars` | A module-level `Settings()` instance is created on import. Point at the class instead, or load values with `env_file = ".env"` / `--env-file` (dummy values in CI).    |
| `ModuleNotFoundError` while importing settings              | Wrong `project_dir`, or the project's dependencies are not importable. Run through the project env (`uv run pse`) or set `venv` (`"auto"`, `"uv"`, `"poetry"`, path). |
| `The region option is only available if the regions extra is installed` | Install `pydantic-settings-export[regions]` (in a hook: keep `.[all]` in `additional_dependencies`).                                                  |
| TOML generator missing or failing                           | Install the `toml` extra.                                                                                                                                             |
| `Unknown generator 'markdwon'. Did you mean 'markdown'?`    | Typo in `[[tool.pydantic_settings_export.generators.<name>]]`.                                                                                                        |
| `The file ... does not exist` with `region`                 | Region mode only edits existing files: create the file with the region markers first.                                                                                 |
| Absolute paths in output                                    | Defaults under `root_dir` are rendered as `<project_dir>/...`; adjust `[tool.pydantic_settings_export.relative_to]` if needed.                                        |
| `--check` fails in CI but passes locally                    | Different extras, env vars, or package versions in CI. Read the printed diff; regenerate locally with `pse` and commit.                                                |
