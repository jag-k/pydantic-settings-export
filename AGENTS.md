# AGENTS.md

`pydantic-settings-export` (CLI: `pydantic-settings-export` / `pse`) turns Pydantic `BaseSettings` classes into
docs and example files: Markdown, `.env`, TOML, plain text. Python 3.10+, managed with `uv`.

## Before you finish

Run these; CI runs the same (tests on Python 3.10-3.14):

```bash
uv run --group tests pytest   # `pytest` is in the `tests` group: plain `uv run pytest` fails to spawn
uv run prek run --all-files   # ruff, ruff format, ssort, ty, taplo, uv-lock/export, and `pse` itself
uv run pse --check            # examples/ and README regions are up to date (exit 1 + diff if not)
```

- If hooks modified files (ruff format, ssort, `pse`), re-stage and run again.
- If you changed `PSESettings`, a generator config, or output format: run `uv run pse` and commit the regenerated
  `examples/` and README regions.
- Behavior change in CLI, config, or hooks: update `README.md`.
- First setup: `uv sync --all-extras --dev --group tests`. Other Python: add `--python 3.13 --all-extras`.

## Where things are

| Path                                         | What                                                                                       |
|----------------------------------------------|--------------------------------------------------------------------------------------------|
| `pydantic_settings_export/cli.py`            | argparse CLI, `PSECLISettings` (reads `[tool.pydantic_settings_export]`), `--check`        |
| `pydantic_settings_export/exporter.py`       | `Exporter.run_all()` writes, `changes_all()` only computes; both use `_for_each_generator` |
| `pydantic_settings_export/models.py`         | `SettingsInfoModel` / `FieldInfoModel`: settings class -> structured info                  |
| `pydantic_settings_export/generators/`       | `abstract.py` (base, `FileChange`) + one module per generator                              |
| `pydantic_settings_export/settings.py`       | `PSESettings`: the tool's own settings (also exported to `examples/`)                      |
| `pydantic_settings_export/exceptions.py`     | `ExportWarning`                                                                            |
| `pydantic_settings_export/venv.py`           | finds the user's venv (`venv = "auto"`) so their settings can be imported                  |
| `tests/`, `tests/generators/`                | pytest; shared fixtures in `tests/conftest.py`                                             |
| `prek.toml`                                  | local + CI hooks (do not add `.pre-commit-config.yaml`)                                    |
| `.pre-commit-hooks.yaml`                     | hooks published for *other* projects; installs `.[all]` by default                         |

Flow: CLI -> `PSECLISettings` -> import settings classes -> `SettingsInfoModel.from_settings_model()` ->
`Exporter` -> each generator's `changes()` -> `run()` applies them (or `--check` diffs them).

## Rules that are easy to get wrong

- **Generators**: subclass `AbstractGenerator` (`AbstractEnvGenerator` for env-var output) with `name`, `config`
  (a `BaseGeneratorSettings`) and `generate_single()`. Subclasses register globally on definition. To control
  which files get what content, override `changes()` returning `FileChange`s. Never override `run()`: it is
  `@final`, `--check` would not see it, and it emits a `DeprecationWarning`.
- **Config**: generator blocks are `[[tool.pydantic_settings_export.generators.<name>]]`; unknown names are an error.
- **Warnings**: export problems that are skipped so the rest can continue (generator failed, settings not
  importable, file unreadable/unwritable) must use `ExportWarning`: `--check` counts them as failures. Set `stacklevel`.
- **File IO**: always `encoding="utf-8"`.
- **Complexity** is capped at 10 (ruff C901). `cli.main` is at the limit: add helpers, not branches.
- **Docstrings**: reST fields (`:param x:`, `:return:`, `:raises X:`).
- **Types**: checked by `ty`, not mypy. Suppress with `# ty: ignore[<rule>]`.
- **Extras**: `email`, `regions` (Markdown `region = ...`), `toml`; keep `all` = union of them.

## Testing gotchas

- Use real files in `tmp_path` rather than mocking IO.
- Generator subclasses defined in tests register globally: give them unique `name`s.
  `tests/generators/test_abstract.py` restores the registry with an autouse fixture.
- `main(["--config-file", ...])` mutates class-level `PSECLISettings.model_config`; `tests/test_cli.py` restores it
  with an autouse fixture. Put such tests there or restore it yourself.
- `-g/--generator` is `nargs="*"` and swallows following positional args.
- `cp1252_default_encoding` fixture emulates a non-UTF-8 OS for encoding tests.

## Dependencies and lock files

- `uv.lock` and `pylock.toml` are kept in sync by hooks. `pylock.toml` excludes extras.
- The `uv-lock` hook pins uv (`rev` of `astral-sh/uv-pre-commit` in `prek.toml`). A newer local uv bumps `revision`
  in `uv.lock`; lock with the pinned one: `uvx uv@<rev> lock [--upgrade-package <name>]`.
- Python 3.10 support means some deps resolve to older versions for 3.10 only (split `resolution-markers` in
  `uv.lock`), e.g. `dnspython` 2.9+ needs 3.11.

## Git

- Branch off `main`, open a PR; PRs are squash-merged. Greptile reviews PRs.
- Commit message: sentence-style subject ending with a period, blank line, indented bullets (`    - ...`).
  See `git log`.
- Versions come from git tags (`dynamic = ["version"]`).
