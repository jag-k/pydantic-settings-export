# Configuration

Here you can find all available configuration options using ENV variables.

## Global Settings

The settings for the CLI.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__`

| Name                                         | Type               | Default           | Description                                                                                                                                                                                                                                                                                                  | Example                                                                                                                   |
|----------------------------------------------|--------------------|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `PYDANTIC_SETTINGS_EXPORT__DEFAULT_SETTINGS` | `array`            | `[]`              | The default settings to use. The settings are applied in the order they are listed. Each entry can be either 'module:attribute' to import a specific class or instance, or a plain module path (e.g. 'app.settings') to auto-discover all BaseSettings subclasses defined in that module.                    | `["settings:settings"]`, `["app.config.settings:Settings","app.config.settings.dev:Settings"]`, `["app.config.settings"]` |
| `PYDANTIC_SETTINGS_EXPORT__ROOT_DIR`         | `Path`             | `"<project_dir>"` | The project directory. Used for relative paths in the configuration file and .env file. If not set, will be the same as project_dir.                                                                                                                                                                         | `"<project_dir>"`                                                                                                         |
| `PYDANTIC_SETTINGS_EXPORT__PROJECT_DIR`      | `Path`             | `"<project_dir>"` | The project directory. Used for importing settings.                                                                                                                                                                                                                                                          | `"<project_dir>"`                                                                                                         |
| `PYDANTIC_SETTINGS_EXPORT__VENV`             | `string` \| `null` | `"auto"`          | Virtual environment to use when importing settings. Possible values: 'auto' (auto-detect from ./venv, ./.venv, uv, or poetry), 'uv' (use uv-managed venv), 'poetry' (use Poetry-managed venv), a path to the venv directory (relative paths are resolved from project_dir), or null/empty string to disable. | `"auto"`, `"poetry"`, `"uv"`, `"./.venv"`, `"/path/to/.venv"`                                                             |
| `PYDANTIC_SETTINGS_EXPORT__RESPECT_EXCLUDE`  | `boolean`          | `true`            | Respect the exclude attribute in the fields.                                                                                                                                                                                                                                                                 | `true`                                                                                                                    |
| `PYDANTIC_SETTINGS_EXPORT__ENV_FILE`         | `Path` \| `null`   | `null`            | The path to the .env file to load environment variables. Useful when you have a Settings class/instance, which requires values while running.                                                                                                                                                                | `null`                                                                                                                    |

### Relative Directory Settings

Settings for the relative directory.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__`

| Name                                                       | Type      | Default           | Description                                                | Example           |
|------------------------------------------------------------|-----------|-------------------|------------------------------------------------------------|-------------------|
| `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__REPLACE_ABS_PATHS` | `boolean` | `true`            | Replace absolute paths with relative path to project root. | `true`            |
| `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__ALIAS`             | `string`  | `"<project_dir>"` | The alias for the relative directory.                      | `"<project_dir>"` |
