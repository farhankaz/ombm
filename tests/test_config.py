"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ombm.config import ConfigLoader, create_default_config, load_config
from ombm.models import OMBMConfig


class TestConfigLoader:
    """Test configuration loader functionality."""

    def test_default_config_structure(self):
        """Test that default config has expected structure."""
        config = ConfigLoader.DEFAULT_CONFIG

        # Check top-level sections
        assert "openai" in config
        assert "scraping" in config
        assert "concurrency" in config
        assert "cache" in config
        assert "logging" in config
        assert "paths" in config

        # Check OpenAI section
        openai = config["openai"]
        assert openai["model"] == "gpt-4o"
        assert openai["max_tokens"] == 4000
        assert openai["temperature"] == 0.1
        assert openai["timeout"] == 30.0

        # Check scraping section
        scraping = config["scraping"]
        assert scraping["timeout"] == 10.0
        assert scraping["max_content_length"] == 10000
        assert "OMBM" in scraping["user_agent"]
        assert scraping["max_retries"] == 2
        assert scraping["retry_delay"] == 1.0

    def test_load_defaults_when_no_file(self, tmp_path):
        """Test loading defaults when config file doesn't exist."""
        config_path = tmp_path / "nonexistent.toml"
        loader = ConfigLoader(config_path)

        config = loader.load()

        assert isinstance(config, OMBMConfig)
        assert config.openai.model == "gpt-4o"
        assert config.scraping.timeout == 10.0
        assert config.concurrency.default_workers == 4

    def test_load_from_toml_file(self, tmp_path):
        """Test loading configuration from TOML file."""
        config_path = tmp_path / "config.toml"
        config_content = """
[openai]
model = "gpt-3.5-turbo"
max_tokens = 2000

[scraping]
timeout = 5.0
max_retries = 3

[concurrency]
default_workers = 8
"""

        config_path.write_text(config_content)
        loader = ConfigLoader(config_path)

        config = loader.load()

        # Check overridden values
        assert config.openai.model == "gpt-3.5-turbo"
        assert config.openai.max_tokens == 2000
        assert config.scraping.timeout == 5.0
        assert config.scraping.max_retries == 3
        assert config.concurrency.default_workers == 8

        # Check defaults are preserved
        assert config.openai.temperature == 0.1  # Not overridden
        assert config.cache.enabled is True  # Not overridden

    def test_env_overrides(self, tmp_path):
        """Test environment variable overrides."""
        config_path = tmp_path / "config.toml"
        loader = ConfigLoader(config_path)

        env_vars = {
            "OMBM_OPENAI_MODEL": "gpt-4-turbo",
            "OMBM_OPENAI_MAX_TOKENS": "8000",
            "OMBM_SCRAPING_TIMEOUT": "15.5",
            "OMBM_CACHE_ENABLED": "false",
            "OMBM_CONCURRENCY_DEFAULT_WORKERS": "12",
        }

        with patch.dict(os.environ, env_vars):
            config = loader.load()

        assert config.openai.model == "gpt-4-turbo"
        assert config.openai.max_tokens == 8000
        assert config.scraping.timeout == 15.5
        assert config.cache.enabled is False
        assert config.concurrency.default_workers == 12

    def test_env_value_conversion(self, tmp_path):
        """Test environment variable type conversion."""
        config_path = tmp_path / "config.toml"
        loader = ConfigLoader(config_path)

        env_vars = {
            "OMBM_CACHE_ENABLED": "true",
            "OMBM_CACHE_TTL_DAYS": "7",
            "OMBM_SCRAPING_TIMEOUT": "12.5",
            "OMBM_LOGGING_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars):
            config = loader.load()

        assert config.cache.enabled is True
        assert config.cache.ttl_days == 7
        assert config.scraping.timeout == 12.5
        assert config.logging.level == "DEBUG"

    def test_boolean_env_conversion(self):
        """Test boolean environment variable conversion."""
        loader = ConfigLoader()

        # Test true values
        for value in ["true", "1", "yes", "on", "TRUE", "True"]:
            assert loader._convert_env_value(value) is True

        # Test false values
        for value in ["false", "0", "no", "off", "FALSE", "False"]:
            assert loader._convert_env_value(value) is False

        # Test non-boolean values
        assert loader._convert_env_value("maybe") == "maybe"

    def test_create_default_config(self, tmp_path):
        """Test creating default configuration file."""
        config_path = tmp_path / "config.toml"
        loader = ConfigLoader(config_path)

        loader.create_default_config()

        assert config_path.exists()
        content = config_path.read_text()

        # Check that TOML sections are present
        assert "[openai]" in content
        assert "[scraping]" in content
        assert "[concurrency]" in content
        assert 'model = "gpt-4o"' in content

    def test_create_default_config_directory_creation(self, tmp_path):
        """Test that config directory is created if it doesn't exist."""
        config_dir = tmp_path / "nested" / "config"
        config_path = config_dir / "config.toml"
        loader = ConfigLoader(config_path)

        loader.create_default_config()

        assert config_dir.exists()
        assert config_path.exists()

    def test_config_file_permissions(self, tmp_path):
        """Test that config directory is created with proper permissions."""
        config_path = tmp_path / "config.toml"
        loader = ConfigLoader(config_path)

        loader.create_default_config()

        # Check directory permissions (should be 700)
        stat = config_path.parent.stat()
        perms = oct(stat.st_mode)[-3:]
        assert perms == "700"

    def test_merge_dicts(self):
        """Test dictionary merging functionality."""
        loader = ConfigLoader()

        base = {"a": 1, "b": {"x": 2, "y": 3}, "c": 4}

        override = {"b": {"x": 20, "z": 30}, "d": 5}

        result = loader._merge_dicts(base, override)

        assert result["a"] == 1  # unchanged
        assert result["b"]["x"] == 20  # overridden
        assert result["b"]["y"] == 3  # preserved
        assert result["b"]["z"] == 30  # added
        assert result["c"] == 4  # unchanged
        assert result["d"] == 5  # added

    def test_path_expansion(self, tmp_path):
        """Test path expansion functionality."""
        config_path = tmp_path / "config.toml"
        config_content = """
[paths]
config_dir = "~/custom_config"
"""

        config_path.write_text(config_content)
        loader = ConfigLoader(config_path)

        config = loader.load()

        # Path should be expanded
        assert "~" not in config.paths.config_dir
        assert config.paths.config_dir.startswith("/")

    def test_invalid_toml_file(self, tmp_path):
        """Test handling of invalid TOML file."""
        config_path = tmp_path / "config.toml"
        config_path.write_text("invalid toml content [[[")

        loader = ConfigLoader(config_path)

        # Should fall back to defaults and not raise exception
        config = loader.load()
        assert config.openai.model == "gpt-4o"  # Default value


class TestOMBMConfig:
    """Test OMBMConfig model functionality."""

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = ConfigLoader.DEFAULT_CONFIG
        config = OMBMConfig.from_dict(data)

        assert isinstance(config, OMBMConfig)
        assert config.openai.model == "gpt-4o"
        assert config.scraping.timeout == 10.0
        assert config.concurrency.default_workers == 4

    def test_path_methods(self):
        """Test path helper methods."""
        data = ConfigLoader.DEFAULT_CONFIG.copy()
        data["paths"]["config_dir"] = "/tmp/test_config"
        data["paths"]["cache_file"] = "test_cache.db"
        data["paths"]["log_dir"] = "test_logs"

        config = OMBMConfig.from_dict(data)

        assert config.get_config_dir() == Path("/tmp/test_config")
        assert config.get_cache_path() == Path("/tmp/test_config/test_cache.db")
        assert config.get_log_dir() == Path("/tmp/test_config/test_logs")


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_load_config(self, tmp_path):
        """Test load_config convenience function."""
        config_path = tmp_path / "config.toml"
        config_content = """
[openai]
model = "custom-model"
"""

        config_path.write_text(config_content)

        config = load_config(config_path)

        assert isinstance(config, OMBMConfig)
        assert config.openai.model == "custom-model"

    def test_create_default_config_function(self, tmp_path):
        """Test create_default_config convenience function."""
        config_path = tmp_path / "config.toml"

        create_default_config(config_path)

        assert config_path.exists()
        content = config_path.read_text()
        assert "[openai]" in content


@pytest.fixture
def clean_env():
    """Fixture to clean environment variables."""
    original_env = os.environ.copy()

    # Remove any OMBM_ variables
    for key in list(os.environ.keys()):
        if key.startswith("OMBM_"):
            del os.environ[key]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestIntegration:
    """Integration tests for configuration system."""

    def test_full_config_cycle(self, tmp_path, clean_env):
        """Test complete configuration loading cycle."""
        config_path = tmp_path / "config.toml"

        # 1. Create default config
        create_default_config(config_path)
        assert config_path.exists()

        # 2. Load default config
        config1 = load_config(config_path)
        assert config1.openai.model == "gpt-4o"

        # 3. Modify file and reload
        config_content = config_path.read_text()
        modified_content = config_content.replace(
            'model = "gpt-4o"', 'model = "gpt-3.5-turbo"'
        )
        config_path.write_text(modified_content)

        config2 = load_config(config_path)
        assert config2.openai.model == "gpt-3.5-turbo"

        # 4. Override with environment variable
        with patch.dict(os.environ, {"OMBM_OPENAI_MODEL": "gpt-4-turbo"}):
            config3 = load_config(config_path)
            assert config3.openai.model == "gpt-4-turbo"
