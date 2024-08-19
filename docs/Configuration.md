# Configuration

Here you can find all available configuration options using ENV variables.

## Global Settings

Global settings for pydantic_settings_export.

**Environment Prefix**: `PYDANTIC_SETTINGS_EXPORT_`

| Name                                        | Type       | Default           | Description                                                                                                                                     | Example           |
|---------------------------------------------|------------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|
| `PYDANTIC_SETTINGS_EXPORT_DEFAULT_SETTINGS` | `list`     | `[]`              | The default settings to use. The settings are applied in the order they are listed.                                                             | `[]`              |
| `PYDANTIC_SETTINGS_EXPORT_ROOT_DIR`         | `Path`     | `"<project_dir>"` | The project directory. Used for relative paths in the configuration file and .env file.                                                         | `"<project_dir>"` |
| `PYDANTIC_SETTINGS_EXPORT_PROJECT_DIR`      | `Path`     | `"<project_dir>"` | The project directory. Used for relative paths in the configuration file and .env file.                                                         | `"<project_dir>"` |
| `PYDANTIC_SETTINGS_EXPORT_RESPECT_EXCLUDE`  | `boolean`  | `true`            | Respect the exclude attribute in the fields.                                                                                                    | `true`            |
| `PYDANTIC_SETTINGS_EXPORT_ENV_FILE`         | `Optional` | `null`            | The path to the `.env` file to load environment variables. Useful, then you have a Settings class/instance, which require values while running. | `null`            |

### Relative Directory Settings

Settings for the relative directory.

**Environment Prefix**: `RELATIVE_TO_`

| Name                            | Type      | Default           | Description                                                | Example           |
|---------------------------------|-----------|-------------------|------------------------------------------------------------|-------------------|
| `RELATIVE_TO_REPLACE_ABS_PATHS` | `boolean` | `true`            | Replace absolute paths with relative path to project root. | `true`            |
| `RELATIVE_TO_ALIAS`             | `string`  | `"<project_dir>"` | The alias for the relative directory.                      | `"<project_dir>"` |

### Configuration File Settings

Settings for the Markdown file.

**Environment Prefix**: `CONFIG_FILE_`

| Name                    | Type      | Default              | Description                                     | Example              |
|-------------------------|-----------|----------------------|-------------------------------------------------|----------------------|
| `CONFIG_FILE_ENABLED`   | `boolean` | `true`               | Enable the configuration file generation.       | `true`               |
| `CONFIG_FILE_NAME`      | `string`  | `"Configuration.md"` | The name of the configuration file.             | `"Configuration.md"` |
| `CONFIG_FILE_SAVE_DIRS` | `list`    | `[]`                 | The directories to save configuration files to. | `[]`                 |

### .env File Settings

Settings for the .env file.

**Environment Prefix**: `DOTENV_`

| Name          | Type     | Default          | Description                | Example          |
|---------------|----------|------------------|----------------------------|------------------|
| `DOTENV_NAME` | `string` | `".env.example"` | The name of the .env file. | `".env.example"` |
