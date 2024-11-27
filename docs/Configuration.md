# Configuration

Here you can find all available configuration options using ENV variables.

## Global Settings

Global settings for pydantic_settings_export.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__`

| Name                                         | Type      | Default           | Description                                                                                                                                     | Example                                                                                        |
|----------------------------------------------|-----------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `PYDANTIC_SETTINGS_EXPORT__DEFAULT_SETTINGS` | `list`    | `[]`              | The default settings to use. The settings are applied in the order they are listed.                                                             | `["settings:settings"]`, `["app.config.settings:Settings","app.config.settings.dev:Settings"]` |
| `PYDANTIC_SETTINGS_EXPORT__ROOT_DIR`         | `Path`    | `"<project_dir>"` | The project directory. Used for relative paths in the configuration file and .env file.                                                         | `"<project_dir>"`                                                                              |
| `PYDANTIC_SETTINGS_EXPORT__PROJECT_DIR`      | `Path`    | `"<project_dir>"` | The project directory. Used for relative paths in the configuration file and .env file.                                                         | `"<project_dir>"`                                                                              |
| `PYDANTIC_SETTINGS_EXPORT__RESPECT_EXCLUDE`  | `boolean` | `true`            | Respect the exclude attribute in the fields.                                                                                                    | `true`                                                                                         |
| `PYDANTIC_SETTINGS_EXPORT__ENV_FILE`         | `Path`    | `null`            | The path to the `.env` file to load environment variables. Useful, then you have a Settings class/instance, which require values while running. | `null`                                                                                         |

### Relative Directory Settings

Settings for the relative directory.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__`

| Name                                                       | Type      | Default           | Description                                                | Example           |
|------------------------------------------------------------|-----------|-------------------|------------------------------------------------------------|-------------------|
| `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__REPLACE_ABS_PATHS` | `boolean` | `true`            | Replace absolute paths with relative path to project root. | `true`            |
| `PYDANTIC_SETTINGS_EXPORT__RELATIVE_TO__ALIAS`             | `string`  | `"<project_dir>"` | The alias for the relative directory.                      | `"<project_dir>"` |

### Generator: Markdown Configuration File Settings

Settings for the Markdown file.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__MARKDOWN__`

| Name                                            | Type      | Default              | Description                                     | Example              |
|-------------------------------------------------|-----------|----------------------|-------------------------------------------------|----------------------|
| `PYDANTIC_SETTINGS_EXPORT__MARKDOWN__ENABLED`   | `boolean` | `true`               | Enable the configuration file generation.       | `true`               |
| `PYDANTIC_SETTINGS_EXPORT__MARKDOWN__NAME`      | `string`  | `"Configuration.md"` | The name of the configuration file.             | `"Configuration.md"` |
| `PYDANTIC_SETTINGS_EXPORT__MARKDOWN__SAVE_DIRS` | `list`    | `[]`                 | The directories to save configuration files to. | `[]`                 |

### Generator: dotenv File Settings

Settings for the .env file.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT__DOTENV__`

| Name                                        | Type      | Default          | Description                        | Example                           |
|---------------------------------------------|-----------|------------------|------------------------------------|-----------------------------------|
| `PYDANTIC_SETTINGS_EXPORT__DOTENV__ENABLED` | `boolean` | `true`           | Enable the dotenv file generation. | `true`                            |
| `PYDANTIC_SETTINGS_EXPORT__DOTENV__PATH`    | `Path`    | `".env.example"` | The name of the .env file.         | `".env.example"`, `".env.sample"` |
