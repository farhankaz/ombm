"""Configuration management for OMBM.

Handles loading configuration from TOML files and environment variables.
"""

import os
import tomllib
from pathlib import Path
from typing import Any

import structlog

from ombm.models import OMBMConfig

logger = structlog.get_logger(__name__)


class ConfigLoader:
    """Configuration loader with TOML file and environment variable support."""

    DEFAULT_CONFIG = {
        "openai": {
            "model": "gpt-4o",
            "max_tokens": 4000,
            "temperature": 0.1,
            "timeout": 30.0,
        },
        "scraping": {
            "timeout": 10.0,
            "max_content_length": 10000,
            "user_agent": "OMBM/1.0 (macOS Safari Bookmark Organizer)",
            "max_retries": 2,
            "retry_delay": 1.0,
        },
        "concurrency": {
            "default_workers": 4,
            "max_workers": 16,
        },
        "cache": {
            "enabled": True,
            "ttl_days": 30,
        },
        "logging": {
            "level": "INFO",
            "format": "human",  # "human" or "json"
        },
        "paths": {
            "config_dir": "~/.ombm",
            "cache_file": "cache.db",
            "log_dir": "logs",
        },
    }

    ENV_PREFIX = "OMBM_"

    def __init__(self, config_path: Path | None = None):
        """Initialize the config loader.

        Args:
            config_path: Optional path to config file. Defaults to ~/.ombm/config.toml
        """
        if config_path is None:
            config_dir = Path.home() / ".ombm"
            config_path = config_dir / "config.toml"

        self.config_path = config_path
        self.config_dir = config_path.parent

    def load(self) -> OMBMConfig:
        """Load configuration from file and environment variables.

        Returns:
            Loaded configuration object
        """
        # Start with defaults
        config_dict = self._deep_copy_dict(self.DEFAULT_CONFIG)

        # Load from TOML file if it exists
        if self.config_path.exists():
            try:
                with open(self.config_path, "rb") as f:
                    file_config = tomllib.load(f)
                config_dict = self._merge_dicts(config_dict, file_config)
                logger.debug(
                    "Loaded configuration from file", path=str(self.config_path)
                )
            except Exception as e:
                logger.warning(
                    "Failed to load config file, using defaults",
                    path=str(self.config_path),
                    error=str(e),
                )
        else:
            logger.debug(
                "Config file not found, using defaults", path=str(self.config_path)
            )

        # Apply environment variable overrides
        config_dict = self._apply_env_overrides(config_dict)

        # Expand paths
        config_dict = self._expand_paths(config_dict)

        return OMBMConfig.from_dict(config_dict)

    def create_default_config(self) -> None:
        """Create default configuration file if it doesn't exist."""
        if self.config_path.exists():
            logger.debug("Config file already exists", path=str(self.config_path))
            return

        # Ensure config directory exists
        self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Create default TOML config
        toml_content = self._dict_to_toml(self.DEFAULT_CONFIG)

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(toml_content)
            logger.info(
                "Created default configuration file", path=str(self.config_path)
            )
        except Exception as e:
            logger.error(
                "Failed to create config file", path=str(self.config_path), error=str(e)
            )
            raise

    def _deep_copy_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        """Deep copy a dictionary."""
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy_dict(value)
            else:
                result[key] = value
        return result

    def _merge_dicts(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge two dictionaries."""
        result = self._deep_copy_dict(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to config."""
        env_vars = {
            k: v for k, v in os.environ.items() if k.startswith(self.ENV_PREFIX)
        }

        if not env_vars:
            return config

        logger.debug("Applying environment overrides", count=len(env_vars))

        result = self._deep_copy_dict(config)

        for env_key, env_value in env_vars.items():
            # Remove prefix and convert to lowercase
            config_key = env_key[len(self.ENV_PREFIX) :].lower()

            # Handle nested keys (e.g., OMBM_OPENAI_MODEL -> openai.model)
            # Split only on the first underscore to get section and key
            if "_" in config_key:
                section, remaining_key = config_key.split("_", 1)

                # Navigate to the section
                if section not in result:
                    result[section] = {}
                elif not isinstance(result[section], dict):
                    # Can't override non-dict with nested value
                    continue

                # Set the final value with type conversion
                result[section][remaining_key] = self._convert_env_value(env_value)
            else:
                # Top-level key
                result[config_key] = self._convert_env_value(env_value)

        return result

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        elif value.lower() in ("false", "0", "no", "off"):
            return False

        # Number conversion
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _expand_paths(self, config: dict[str, Any]) -> dict[str, Any]:
        """Expand user paths in configuration."""
        result = self._deep_copy_dict(config)

        if "paths" in result:
            paths = result["paths"]
            if "config_dir" in paths:
                paths["config_dir"] = str(Path(paths["config_dir"]).expanduser())

        return result

    def _dict_to_toml(self, d: dict[str, Any], indent: int = 0) -> str:
        """Convert dictionary to TOML format string."""
        lines = []
        prefix = "  " * indent

        # First pass: non-dict values
        for key, value in d.items():
            if not isinstance(value, dict):
                if isinstance(value, str):
                    lines.append(f'{prefix}{key} = "{value}"')
                elif isinstance(value, bool):
                    lines.append(f"{prefix}{key} = {str(value).lower()}")
                else:
                    lines.append(f"{prefix}{key} = {value}")

        # Second pass: dict values (sections)
        for key, value in d.items():
            if isinstance(value, dict):
                if lines and lines[-1].strip() != "":
                    lines.append("")  # Add blank line before section
                lines.append(f"{prefix}[{key}]")
                section_content = self._dict_to_toml(value, indent + 1)
                lines.append(section_content)

        return "\n".join(lines)


def load_config(config_path: Path | None = None) -> OMBMConfig:
    """Load configuration using the default loader.

    Args:
        config_path: Optional path to config file

    Returns:
        Loaded configuration object
    """
    loader = ConfigLoader(config_path)
    return loader.load()


def create_default_config(config_path: Path | None = None) -> None:
    """Create default configuration file.

    Args:
        config_path: Optional path to config file
    """
    loader = ConfigLoader(config_path)
    loader.create_default_config()
