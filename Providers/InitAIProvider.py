#initAiProvider.py
import os
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

from Providers.OpenAIProvider import OpenAIProvider
from Providers.AnthropicProvider import AnthropicProvider
from Providers.GroqProvider import GroqProvider
from Providers.GeminiProvider import GeminiProvider
from pathlib import Path

from config import provider_path as config_path , provider_name as config_name
# from Providers.InitAIProvider import  ProviderType

_CONFIG_FILE = _CONFIG_FILE = Path(config_path) / config_name  # core/provider_singleton.json
# from Providers.provider_singleton import save_provider
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProviderType(Enum):
    """Enumeration of available AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"

@dataclass
class ProviderConfig:
    """Configuration for AI provider."""
    provider_type: ProviderType
    api_key: str
    model_name: Optional[str] = None
    max_retries: int = 3
    timeout: int = 30

class AIProviderManager:
    """Manages AI provider instances and configuration."""
    
    _PROVIDER_CLASSES = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.GROQ: GroqProvider,
    }
    
    def __init__(self):
        self._providers: Dict[ProviderType, Any] = {}
        self._default_provider: Optional[Any] = None
    
    def create_provider(self, config: ProviderConfig) -> Any:
        """
        Create an AI provider instance based on configuration.
        
        Args:
            config: Provider configuration
            
        Returns:
            AI provider instance
            
        Raises:
            ValueError: If provider type is not supported
            RuntimeError: If provider initialization fails
        """
        if not config.api_key:
            raise ValueError(f"API key is required for {config.provider_type.value}")
        
        if config.provider_type not in self._PROVIDER_CLASSES:
            raise ValueError(f"Unsupported provider type: {config.provider_type.value}")
        
        try:
            provider_class = self._PROVIDER_CLASSES[config.provider_type]
            provider = provider_class(config.api_key)
            
            # Store the provider
            self._providers[config.provider_type] = provider
            self.save_provider(config)
            logger.info(f"Successfully initialized {config.provider_type.value} provider")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to initialize {config.provider_type.value} provider: {e}")
            raise RuntimeError(f"Provider initialization failed: {e}")
    
    def get_provider(self, provider_type: ProviderType) -> Optional[Any]:
        """Get an existing provider instance."""
        return self._providers.get(provider_type)
    
    def set_default_provider(self, provider_type: ProviderType) -> None:
        """Set the default provider."""
        if provider_type not in self._providers:
            raise ValueError(f"Provider {provider_type.value} not initialized")
        self._default_provider = self._providers[provider_type]
        logger.info(f"Set default provider to {provider_type.value}")
    
    def get_default_provider(self) -> Optional[Any]:
        """Get the default provider."""
        return self._default_provider
    
    @classmethod
    def from_environment(cls, provider_type: ProviderType) -> 'AIProviderManager':
        """
        Create provider manager with configuration from environment variables.
        
        Args:
            provider_type: Type of provider to initialize
            
        Returns:
            Configured AIProviderManager instance
        """
        # Environment variable mapping
        env_var_map = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY", 
            ProviderType.GEMINI: "GEMINI_API_KEY",
            ProviderType.GROQ: "GROQ_API_KEY",
        }
        
        api_key = os.getenv(env_var_map[provider_type])
        if not api_key:
            raise ValueError(f"Environment variable {env_var_map[provider_type]} not found")
        
        manager = cls()
        config = ProviderConfig(provider_type=provider_type, api_key=api_key)
        manager.create_provider(config)
        manager.set_default_provider(provider_type)
        
        return manager
    
    def list_available_providers(self) -> list[str]:
        """List all available provider types."""
        return [provider.value for provider in ProviderType]
    
    def list_initialized_providers(self) -> list[str]:
        """List currently initialized providers."""
        return [provider.value for provider in self._providers.keys()]

# Factory function for backward compatibility and simple usage
    def create_ai_provider(self,provider_type: str, api_key: str) -> Any:
        """
        Factory function to create AI provider (backward compatible).
        
        Args:
            provider_type: Provider type as string
            api_key: API key for the provider
            
        Returns:
            AI provider instance
        """
        # Map string choices to enum values
        provider_map = {
            "1": ProviderType.OPENAI,
            "2": ProviderType.ANTHROPIC, 
            "3": ProviderType.GEMINI,
            "4": ProviderType.GROQ,
            "openai": ProviderType.OPENAI,
            "anthropic": ProviderType.ANTHROPIC,
            "gemini": ProviderType.GEMINI,
            "groq": ProviderType.GROQ,
        }
        print(f"Creating AI provider of type: {provider_type.lower()}")
        provider_enum = provider_map.get(provider_type.lower())
        if not provider_enum:
            raise ValueError(f"Invalid provider type: {provider_type}")
        
        # manager = AIProviderManager()
        config = ProviderConfig(provider_type=provider_enum, api_key=api_key)
        return self.create_provider(config)
    

    def get_provider(self):
        """
        Return a singleton AIProviderManager already initialized with
        the last-used API key & provider type.
        If no config exists yet, returns an empty manager (caller must init).
        """
        mgr = AIProviderManager()
        if _CONFIG_FILE.exists():
            try:
                cfg = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
                pt = ProviderType[cfg["provider"]]
                key = cfg["api_key"]
                model = cfg.get("model")
                retries = cfg.get("max_retries", 3)
                timeout = cfg.get("timeout", 30)
                from InitAIProvider import ProviderConfig
                mgr.create_provider(
                    ProviderConfig(provider_type=pt, api_key=key,
                                model_name=model, max_retries=retries, timeout=timeout)
                )
                mgr.set_default_provider(pt)
            except Exception:
                pass  # ignore corrupted file
        return mgr

    def save_provider(self, config: ProviderConfig):
        """Store selection so it survives restarts."""
        _CONFIG_FILE.write_text(
            json.dumps({
                "provider": config.provider_type.name,
                "api_key": config.api_key,
                "model": config.model_name,
                "max_retries": config.max_retries,
                "timeout": config.timeout
            }),
            encoding="utf-8"
        )
        
    def load_provider(self) -> list[str] | None:
        """
        Load the provider manager from the config file.
        If the file does not exist, return an empty manager.
        """
        if _CONFIG_FILE.exists() :
            
                cfg = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
                if cfg.get("provider") is None or cfg.get("api_key") is None:
                    return None
                # pt = ProviderType[cfg["provider"]]
                pt = cfg["provider"]
                key = cfg["api_key"]
                model = cfg.get("model")
                retries = cfg.get("max_retries", 3)
                timeout = cfg.get("timeout", 30)
                return [pt, key, model, retries, timeout]
        
        return None
# Example usage patterns
if __name__ == "__main__":
    # Method 1: Using environment variables (recommended for production)
    try:
        manager = AIProviderManager.from_environment(ProviderType.GEMINI)
        ai_provider = manager.get_default_provider()
        print(f"Initialized provider: {ai_provider}")
    except ValueError as e:
        print(f"Environment setup error: {e}")
    
    # Method 2: Manual configuration
    try:
        manager = AIProviderManager()
        config = ProviderConfig(
            provider_type=ProviderType.GEMINI,
            api_key=os.getenv("GEMINI_API_KEY", "your-api-key-here"),
            max_retries=5,
            timeout=45
        )
        ai_provider = manager.create_provider(config)
        manager.set_default_provider(ProviderType.GEMINI)
        print(f"Available providers: {manager.list_available_providers()}")
        print(f"Initialized providers: {manager.list_initialized_providers()}")
    except Exception as e:
        print(f"Initialization error: {e}")
    
    # Method 3: Backward compatible factory function
    try:
        api_key = os.getenv("GEMINI_API_KEY", "your-api-key-here")
        ai_provider = manager.create_ai_provider("gemini", api_key)
        print(f"Factory created provider: {ai_provider}")
    except Exception as e:
        print(f"Factory error: {e}")
        
    