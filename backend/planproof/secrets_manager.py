"""
Secrets management module for production environments.

Supports multiple secret backends:
- Azure Key Vault (production)
- Environment variables (development/fallback)
- Local file (development only, not recommended)

Usage:
    from planproof.secrets_manager import get_secret, init_secrets
    
    # Initialize at app startup
    init_secrets()
    
    # Get secrets
    api_key = get_secret("AZURE_OPENAI_API_KEY")
"""

import os
import logging
from typing import Optional, Dict, Any
from enum import Enum

LOGGER = logging.getLogger(__name__)


class SecretBackend(str, Enum):
    """Supported secret backends."""
    AZURE_KEY_VAULT = "azure_keyvault"
    ENVIRONMENT = "environment"
    FILE = "file"


class SecretsManager:
    """Centralized secrets management with multiple backend support."""
    
    def __init__(self, backend: Optional[SecretBackend] = None):
        """
        Initialize secrets manager.
        
        Args:
            backend: Secret backend to use. If None, auto-detect based on environment.
        """
        self.backend = backend or self._auto_detect_backend()
        self._cache: Dict[str, str] = {}
        self._initialized = False
        
        LOGGER.info(f"Secrets manager initialized with backend: {self.backend}")
    
    def _auto_detect_backend(self) -> SecretBackend:
        """Auto-detect which secret backend to use."""
        # Check if Azure Key Vault is configured
        if os.getenv("AZURE_KEY_VAULT_NAME") or os.getenv("AZURE_KEY_VAULT_URL"):
            return SecretBackend.AZURE_KEY_VAULT
        
        # Check if running in Azure (App Service, AKS, etc.)
        if os.getenv("WEBSITE_INSTANCE_ID") or os.getenv("IDENTITY_ENDPOINT"):
            LOGGER.warning(
                "Running in Azure but no Key Vault configured. "
                "Consider setting AZURE_KEY_VAULT_NAME for production."
            )
        
        # Default to environment variables
        return SecretBackend.ENVIRONMENT
    
    def initialize(self) -> None:
        """Initialize the secrets backend."""
        if self._initialized:
            return
        
        if self.backend == SecretBackend.AZURE_KEY_VAULT:
            self._init_azure_key_vault()
        elif self.backend == SecretBackend.ENVIRONMENT:
            self._init_environment()
        else:
            raise ValueError(f"Unsupported secret backend: {self.backend}")
        
        self._initialized = True
        LOGGER.info("Secrets manager initialized successfully")
    
    def _init_azure_key_vault(self) -> None:
        """Initialize Azure Key Vault client."""
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential
        except ImportError:
            raise ImportError(
                "Azure Key Vault support requires: pip install azure-keyvault-secrets azure-identity"
            )
        
        vault_name = os.getenv("AZURE_KEY_VAULT_NAME")
        vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        
        if not vault_url:
            if vault_name:
                vault_url = f"https://{vault_name}.vault.azure.net/"
            else:
                raise ValueError(
                    "Either AZURE_KEY_VAULT_NAME or AZURE_KEY_VAULT_URL must be set"
                )
        
        # Use DefaultAzureCredential which supports:
        # - Managed Identity (production)
        # - Azure CLI (development)
        # - Environment variables (CI/CD)
        credential = DefaultAzureCredential()
        self._kv_client = SecretClient(vault_url=vault_url, credential=credential)
        
        LOGGER.info(f"Connected to Azure Key Vault: {vault_url}")
    
    def _init_environment(self) -> None:
        """Initialize environment variable backend (no-op)."""
        LOGGER.info("Using environment variables for secrets")
    
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret by name.
        
        Args:
            secret_name: Name of the secret (e.g., "AZURE_OPENAI_API_KEY")
            default: Default value if secret not found
        
        Returns:
            Secret value or default if not found
        
        Raises:
            ValueError: If secret not found and no default provided
        """
        # Check cache first
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        # Retrieve from backend
        value = None
        
        if self.backend == SecretBackend.AZURE_KEY_VAULT:
            value = self._get_from_key_vault(secret_name)
        elif self.backend == SecretBackend.ENVIRONMENT:
            value = self._get_from_environment(secret_name)
        
        # Fallback to environment variable if not found in primary backend
        if value is None and self.backend != SecretBackend.ENVIRONMENT:
            LOGGER.warning(
                f"Secret '{secret_name}' not found in {self.backend}, trying environment variables"
            )
            value = self._get_from_environment(secret_name)
        
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"Secret '{secret_name}' not found and no default provided")
        
        # Cache the value
        self._cache[secret_name] = value
        return value
    
    def _get_from_key_vault(self, secret_name: str) -> Optional[str]:
        """Retrieve secret from Azure Key Vault."""
        try:
            # Convert environment variable name to Key Vault format
            # Example: AZURE_OPENAI_API_KEY -> azure-openai-api-key
            kv_secret_name = secret_name.lower().replace("_", "-")
            
            secret = self._kv_client.get_secret(kv_secret_name)
            LOGGER.debug(f"Retrieved secret '{secret_name}' from Key Vault")
            return secret.value
        except Exception as e:
            LOGGER.warning(f"Failed to retrieve secret '{secret_name}' from Key Vault: {e}")
            return None
    
    def _get_from_environment(self, secret_name: str) -> Optional[str]:
        """Retrieve secret from environment variables."""
        value = os.getenv(secret_name)
        if value:
            LOGGER.debug(f"Retrieved secret '{secret_name}' from environment")
        return value
    
    def set_secret(self, secret_name: str, value: str) -> None:
        """
        Set a secret value (mainly for testing).
        
        Args:
            secret_name: Name of the secret
            value: Secret value
        
        Note:
            This only updates the local cache, not the backend storage.
        """
        self._cache[secret_name] = value
    
    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()
        LOGGER.debug("Secrets cache cleared")
    
    def list_secrets(self) -> list[str]:
        """
        List all available secret names (for debugging).
        
        Returns:
            List of secret names (values are not included)
        """
        if self.backend == SecretBackend.AZURE_KEY_VAULT:
            try:
                return [s.name for s in self._kv_client.list_properties_of_secrets()]
            except Exception as e:
                LOGGER.error(f"Failed to list secrets from Key Vault: {e}")
                return []
        elif self.backend == SecretBackend.ENVIRONMENT:
            # Return cached secrets only for security
            return list(self._cache.keys())
        return []


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def init_secrets(backend: Optional[SecretBackend] = None) -> SecretsManager:
    """
    Initialize the global secrets manager.
    
    Args:
        backend: Secret backend to use. If None, auto-detect.
    
    Returns:
        Initialized SecretsManager instance
    """
    global _secrets_manager
    _secrets_manager = SecretsManager(backend=backend)
    _secrets_manager.initialize()
    return _secrets_manager


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    if _secrets_manager is None:
        return init_secrets()
    return _secrets_manager


def get_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get a secret.
    
    Args:
        secret_name: Name of the secret
        default: Default value if secret not found
    
    Returns:
        Secret value or default
    """
    manager = get_secrets_manager()
    return manager.get_secret(secret_name, default=default)


# Example usage for loading configuration from secrets
def load_config_from_secrets() -> Dict[str, Any]:
    """
    Load application configuration from secrets.
    
    Returns:
        Dictionary of configuration values
    """
    manager = get_secrets_manager()
    
    config = {
        "database_url": manager.get_secret("DATABASE_URL"),
        "azure_storage_connection_string": manager.get_secret("AZURE_STORAGE_CONNECTION_STRING"),
        "azure_docintel_endpoint": manager.get_secret("AZURE_DOCINTEL_ENDPOINT"),
        "azure_docintel_key": manager.get_secret("AZURE_DOCINTEL_KEY"),
        "azure_openai_endpoint": manager.get_secret("AZURE_OPENAI_ENDPOINT"),
        "azure_openai_api_key": manager.get_secret("AZURE_OPENAI_API_KEY"),
        "azure_openai_chat_deployment": manager.get_secret("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        "jwt_secret_key": manager.get_secret("JWT_SECRET_KEY", default=""),
    }
    
    return config
