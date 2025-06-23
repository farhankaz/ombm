"""Keychain integration for secure API key storage in OMBM."""

import logging

import keyring
from keyring.errors import KeyringError

logger = logging.getLogger(__name__)

# Constants for keychain service names
OPENAI_SERVICE_NAME = "ombm-openai"
OPENAI_USERNAME = "api-key"


class KeychainError(Exception):
    """Exception raised for keychain-related errors."""

    pass


class KeychainManager:
    """Manager for secure storage and retrieval of API keys using macOS keychain."""

    def __init__(self) -> None:
        """Initialize the keychain manager."""
        self.service_name = OPENAI_SERVICE_NAME
        self.username = OPENAI_USERNAME

    def store_openai_key(self, api_key: str) -> None:
        """
        Store OpenAI API key in the keychain.

        Args:
            api_key: The OpenAI API key to store

        Raises:
            KeychainError: If storing the key fails
        """
        try:
            keyring.set_password(self.service_name, self.username, api_key)
            logger.info("OpenAI API key stored successfully in keychain")
        except KeyringError as e:
            logger.error(f"Failed to store OpenAI API key in keychain: {e}")
            raise KeychainError(f"Failed to store API key: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error storing API key: {e}")
            raise KeychainError(f"Unexpected error: {e}") from e

    def get_openai_key(self) -> str | None:
        """
        Retrieve OpenAI API key from the keychain.

        Returns:
            The stored API key, or None if not found

        Raises:
            KeychainError: If retrieval fails due to keychain errors
        """
        try:
            api_key = keyring.get_password(self.service_name, self.username)
            if api_key:
                logger.debug("OpenAI API key retrieved from keychain")
            else:
                logger.debug("No OpenAI API key found in keychain")
            return api_key
        except KeyringError as e:
            logger.error(f"Failed to retrieve OpenAI API key from keychain: {e}")
            raise KeychainError(f"Failed to retrieve API key: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error retrieving API key: {e}")
            raise KeychainError(f"Unexpected error: {e}") from e

    def delete_openai_key(self) -> bool:
        """
        Delete OpenAI API key from the keychain.

        Returns:
            True if key was deleted, False if key was not found

        Raises:
            KeychainError: If deletion fails due to keychain errors
        """
        try:
            # First check if the key exists
            if self.get_openai_key() is None:
                logger.info("No OpenAI API key found to delete")
                return False

            keyring.delete_password(self.service_name, self.username)
            logger.info("OpenAI API key deleted from keychain")
            return True
        except KeyringError as e:
            logger.error(f"Failed to delete OpenAI API key from keychain: {e}")
            raise KeychainError(f"Failed to delete API key: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error deleting API key: {e}")
            raise KeychainError(f"Unexpected error: {e}") from e

    def has_openai_key(self) -> bool:
        """
        Check if OpenAI API key exists in the keychain.

        Returns:
            True if key exists, False otherwise

        Raises:
            KeychainError: If keychain access fails
        """
        try:
            return self.get_openai_key() is not None
        except KeychainError:
            # Re-raise keychain errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error checking for API key: {e}")
            raise KeychainError(f"Unexpected error: {e}") from e


def get_api_key_with_fallback() -> str | None:
    """
    Get OpenAI API key with fallback chain: keychain -> environment variable.

    This function provides a unified way to retrieve the API key, checking
    the keychain first, then falling back to environment variables.

    Returns:
        The API key if found, None otherwise

    Raises:
        KeychainError: If keychain access fails
    """
    import os

    try:
        # First try keychain
        manager = KeychainManager()
        api_key = manager.get_openai_key()
        if api_key:
            logger.debug("Using OpenAI API key from keychain")
            return api_key
    except KeychainError:
        # Log but don't fail - try environment variable fallback
        logger.warning("Failed to access keychain, trying environment variable")

    # Fallback to environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.debug("Using OpenAI API key from environment variable")
        return api_key

    logger.debug("No OpenAI API key found in keychain or environment")
    return None


# Convenience functions for common operations
def store_openai_key(api_key: str) -> None:
    """Convenience function to store OpenAI API key."""
    manager = KeychainManager()
    manager.store_openai_key(api_key)


def get_openai_key() -> str | None:
    """Convenience function to get OpenAI API key from keychain only."""
    manager = KeychainManager()
    return manager.get_openai_key()


def delete_openai_key() -> bool:
    """Convenience function to delete OpenAI API key."""
    manager = KeychainManager()
    return manager.delete_openai_key()


def has_openai_key() -> bool:
    """Convenience function to check if OpenAI API key exists."""
    manager = KeychainManager()
    return manager.has_openai_key()
