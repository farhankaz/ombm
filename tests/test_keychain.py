"""Tests for the keychain integration module."""

import os
from unittest.mock import Mock, patch

import pytest
from keyring.errors import KeyringError

from ombm.keychain import (
    KeychainError,
    KeychainManager,
    delete_openai_key,
    get_api_key_with_fallback,
    get_openai_key,
    has_openai_key,
    store_openai_key,
)


class TestKeychainManager:
    """Test suite for KeychainManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.manager = KeychainManager()

    @patch("ombm.keychain.keyring.set_password")
    def test_store_openai_key_success(self, mock_set_password: Mock) -> None:
        """Test successful storage of OpenAI API key."""
        api_key = "sk-test123456789"

        self.manager.store_openai_key(api_key)

        mock_set_password.assert_called_once_with("ombm-openai", "api-key", api_key)

    @patch("ombm.keychain.keyring.set_password")
    def test_store_openai_key_keyring_error(self, mock_set_password: Mock) -> None:
        """Test KeyringError during storage."""
        mock_set_password.side_effect = KeyringError("Keyring access denied")

        with pytest.raises(KeychainError, match="Failed to store API key"):
            self.manager.store_openai_key("sk-test123")

    @patch("ombm.keychain.keyring.set_password")
    def test_store_openai_key_unexpected_error(self, mock_set_password: Mock) -> None:
        """Test unexpected error during storage."""
        mock_set_password.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(KeychainError, match="Unexpected error"):
            self.manager.store_openai_key("sk-test123")

    @patch("ombm.keychain.keyring.get_password")
    def test_get_openai_key_found(self, mock_get_password: Mock) -> None:
        """Test successful retrieval of OpenAI API key."""
        expected_key = "sk-test123456789"
        mock_get_password.return_value = expected_key

        result = self.manager.get_openai_key()

        assert result == expected_key
        mock_get_password.assert_called_once_with("ombm-openai", "api-key")

    @patch("ombm.keychain.keyring.get_password")
    def test_get_openai_key_not_found(self, mock_get_password: Mock) -> None:
        """Test retrieval when no key is stored."""
        mock_get_password.return_value = None

        result = self.manager.get_openai_key()

        assert result is None

    @patch("ombm.keychain.keyring.get_password")
    def test_get_openai_key_keyring_error(self, mock_get_password: Mock) -> None:
        """Test KeyringError during retrieval."""
        mock_get_password.side_effect = KeyringError("Keyring access denied")

        with pytest.raises(KeychainError, match="Failed to retrieve API key"):
            self.manager.get_openai_key()

    @patch("ombm.keychain.keyring.get_password")
    def test_get_openai_key_unexpected_error(self, mock_get_password: Mock) -> None:
        """Test unexpected error during retrieval."""
        mock_get_password.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(KeychainError, match="Unexpected error"):
            self.manager.get_openai_key()

    @patch("ombm.keychain.keyring.delete_password")
    @patch("ombm.keychain.keyring.get_password")
    def test_delete_openai_key_success(
        self, mock_get_password: Mock, mock_delete_password: Mock
    ) -> None:
        """Test successful deletion of OpenAI API key."""
        mock_get_password.return_value = "sk-test123"

        result = self.manager.delete_openai_key()

        assert result is True
        mock_delete_password.assert_called_once_with("ombm-openai", "api-key")

    @patch("ombm.keychain.keyring.get_password")
    def test_delete_openai_key_not_found(self, mock_get_password: Mock) -> None:
        """Test deletion when no key is stored."""
        mock_get_password.return_value = None

        result = self.manager.delete_openai_key()

        assert result is False

    @patch("ombm.keychain.keyring.delete_password")
    @patch("ombm.keychain.keyring.get_password")
    def test_delete_openai_key_keyring_error(
        self, mock_get_password: Mock, mock_delete_password: Mock
    ) -> None:
        """Test KeyringError during deletion."""
        mock_get_password.return_value = "sk-test123"
        mock_delete_password.side_effect = KeyringError("Keyring access denied")

        with pytest.raises(KeychainError, match="Failed to delete API key"):
            self.manager.delete_openai_key()

    @patch("ombm.keychain.keyring.get_password")
    def test_has_openai_key_exists(self, mock_get_password: Mock) -> None:
        """Test checking for key when it exists."""
        mock_get_password.return_value = "sk-test123"

        result = self.manager.has_openai_key()

        assert result is True

    @patch("ombm.keychain.keyring.get_password")
    def test_has_openai_key_not_exists(self, mock_get_password: Mock) -> None:
        """Test checking for key when it doesn't exist."""
        mock_get_password.return_value = None

        result = self.manager.has_openai_key()

        assert result is False

    @patch("ombm.keychain.keyring.get_password")
    def test_has_openai_key_keyring_error(self, mock_get_password: Mock) -> None:
        """Test KeyringError during existence check."""
        mock_get_password.side_effect = KeyringError("Keyring access denied")

        with pytest.raises(KeychainError, match="Failed to retrieve API key"):
            self.manager.has_openai_key()


class TestFallbackFunction:
    """Test suite for get_api_key_with_fallback function."""

    @patch("ombm.keychain.KeychainManager")
    def test_keychain_success(self, mock_manager_class: Mock) -> None:
        """Test successful retrieval from keychain."""
        mock_manager = Mock()
        mock_manager.get_openai_key.return_value = "sk-keychain123"
        mock_manager_class.return_value = mock_manager

        result = get_api_key_with_fallback()

        assert result == "sk-keychain123"

    @patch("ombm.keychain.KeychainManager")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env123"})
    def test_environment_fallback(self, mock_manager_class: Mock) -> None:
        """Test fallback to environment variable."""
        mock_manager = Mock()
        mock_manager.get_openai_key.return_value = None
        mock_manager_class.return_value = mock_manager

        result = get_api_key_with_fallback()

        assert result == "sk-env123"

    @patch("ombm.keychain.KeychainManager")
    @patch.dict(os.environ, {}, clear=True)
    def test_no_key_found(self, mock_manager_class: Mock) -> None:
        """Test when no key is found anywhere."""
        mock_manager = Mock()
        mock_manager.get_openai_key.return_value = None
        mock_manager_class.return_value = mock_manager

        result = get_api_key_with_fallback()

        assert result is None

    @patch("ombm.keychain.KeychainManager")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env123"})
    def test_keychain_error_fallback(self, mock_manager_class: Mock) -> None:
        """Test fallback to environment when keychain fails."""
        mock_manager = Mock()
        mock_manager.get_openai_key.side_effect = KeychainError("Access denied")
        mock_manager_class.return_value = mock_manager

        result = get_api_key_with_fallback()

        assert result == "sk-env123"


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    @patch("ombm.keychain.KeychainManager")
    def test_store_openai_key(self, mock_manager_class: Mock) -> None:
        """Test store_openai_key convenience function."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        store_openai_key("sk-test123")

        mock_manager.store_openai_key.assert_called_once_with("sk-test123")

    @patch("ombm.keychain.KeychainManager")
    def test_get_openai_key(self, mock_manager_class: Mock) -> None:
        """Test get_openai_key convenience function."""
        mock_manager = Mock()
        mock_manager.get_openai_key.return_value = "sk-test123"
        mock_manager_class.return_value = mock_manager

        result = get_openai_key()

        assert result == "sk-test123"

    @patch("ombm.keychain.KeychainManager")
    def test_delete_openai_key(self, mock_manager_class: Mock) -> None:
        """Test delete_openai_key convenience function."""
        mock_manager = Mock()
        mock_manager.delete_openai_key.return_value = True
        mock_manager_class.return_value = mock_manager

        result = delete_openai_key()

        assert result is True

    @patch("ombm.keychain.KeychainManager")
    def test_has_openai_key(self, mock_manager_class: Mock) -> None:
        """Test has_openai_key convenience function."""
        mock_manager = Mock()
        mock_manager.has_openai_key.return_value = True
        mock_manager_class.return_value = mock_manager

        result = has_openai_key()

        assert result is True


class TestIntegration:
    """Integration tests for keychain functionality."""

    @patch("ombm.keychain.keyring.set_password")
    @patch("ombm.keychain.keyring.get_password")
    def test_store_and_retrieve_round_trip(
        self, mock_get_password: Mock, mock_set_password: Mock
    ) -> None:
        """Test complete store and retrieve cycle."""
        api_key = "sk-test123456789"

        # Mock store operation
        manager = KeychainManager()
        manager.store_openai_key(api_key)

        # Mock retrieve operation
        mock_get_password.return_value = api_key
        retrieved_key = manager.get_openai_key()

        assert retrieved_key == api_key
        mock_set_password.assert_called_once_with("ombm-openai", "api-key", api_key)
        mock_get_password.assert_called_once_with("ombm-openai", "api-key")

    @patch("ombm.keychain.keyring")
    def test_service_name_consistency(self, mock_keyring: Mock) -> None:
        """Test that all operations use consistent service name."""
        manager = KeychainManager()

        # Perform various operations
        manager.store_openai_key("sk-test123")
        manager.get_openai_key()
        manager.delete_openai_key()

        # Verify all calls use the same service name
        for call in mock_keyring.method_calls:
            if call[0] in ["set_password", "get_password", "delete_password"]:
                assert call[1][0] == "ombm-openai"  # service name
                assert call[1][1] == "api-key"  # username
