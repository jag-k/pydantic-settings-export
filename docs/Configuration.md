# Configuration

Here you can find all available configuration options using ENV variables.

## Global Settings

The settings for the CLI.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__`

| Name                                         | Type                 | Default           | Description                                                                                                                                  | Example                                                                                        |
|----------------------------------------------|----------------------|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `PYDANTIC_SETTINGS_EXPORT__DEFAULT_SETTINGS` | `array`              | `[]`              | The default settings to use. The settings are applied in the order they are listed.                                                          | `["settings:settings"]`, `["app.config.settings:Settings","app.config.settings.dev:Settings"]` |
| `PYDANTIC_SETTINGS_EXPORT__ROOT_DIR`         | `Path`               | `"<project_dir>"` | The project directory. Used for relative paths in the configuration file and .env file.                                                      | `"<project_dir>"`                                                                              |
| `PYDANTIC_SETTINGS_EXPORT__PROJECT_DIR`      | `Path`               | `"<project_dir>"` | The project directory. Used for relative paths in the configuration file and .env file.                                                      | `"<project_dir>"`                                                                              |
| `PYDANTIC_SETTINGS_EXPORT__RESPECT_EXCLUDE`  | `boolean`            | `true`            | Respect the exclude attribute in the fields.                                                                                                 | `true`                                                                                         |
| `PYDANTIC_SETTINGS_EXPORT__ENV_FILE`         | `Path` \| `NoneType` | `null`            | he path to the .env file to load environment variables. Useful when you have a Settings class/instance, which requires values while running. | `null`                                                                                         |

### Relative Directory Settings

Settings for the relative directory.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__`

| Name                                                       | Type      | Default           | Description                                                | Example           |
|------------------------------------------------------------|-----------|-------------------|------------------------------------------------------------|-------------------|
| `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__REPLACE_ABS_PATHS` | `boolean` | `true`            | Replace absolute paths with relative path to project root. | `true`            |
| `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__ALIAS`             | `string`  | `"<project_dir>"` | The alias for the relative directory.                      | `"<project_dir>"` |
