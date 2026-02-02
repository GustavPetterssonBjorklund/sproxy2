from __future__ import annotations
from pathlib import Path
from core.config.proxy_config_parser import SProxy2Config, ProxyConfig, load_config, save_config, validate_proxies


class ConfigService:
    """Single source of truth for runtime config. All changes flow through here."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config = load_config(config_path)
    
    @property
    def config(self) -> SProxy2Config:
        """Get current config (read-only view)."""
        return self._config
    
    def add_proxy(self, name: str, listen_address: str, listen_port: int, bind_port: int) -> None:
        """Add a new proxy and persist to disk."""
        # Check if name already exists
        if name in self._config.proxies:
            raise ValueError(f"Proxy name '{name}' already exists")
        
        new_proxy = ProxyConfig(
            listen_address=listen_address,
            listen_port=listen_port,
            bind_port=bind_port
        )
        
        # Update in-memory config (immutable, so create new dict)
        updated_proxies = dict(self._config.proxies)
        updated_proxies[name] = new_proxy
        
        # Validate for duplicate endpoints using shared validation
        validate_proxies(updated_proxies)
        
        self._config = SProxy2Config(proxies=updated_proxies)
        
        # Persist to disk
        save_config(self.config_path, self._config)
    
    def remove_proxy(self, name: str) -> None:
        """Remove a proxy and persist to disk."""
        if name not in self._config.proxies:
            raise KeyError(f"Proxy '{name}' not found")
        
        updated_proxies = dict(self._config.proxies)
        del updated_proxies[name]
        self._config = SProxy2Config(proxies=updated_proxies)
        
        save_config(self.config_path, self._config)
    
    def reload_from_disk(self) -> None:
        """Reload config from disk (useful if externally modified)."""
        self._config = load_config(self.config_path)
