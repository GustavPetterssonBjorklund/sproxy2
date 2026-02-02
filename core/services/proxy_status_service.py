from __future__ import annotations
from dataclasses import dataclass

from core.config.proxy_config_parser import ProxyConfig
from core.services.proxy_config_service import ConfigService

@dataclass
class Proxy(ProxyConfig):
    is_running: bool = False
    process_id: int | None = None
    
    
class ProxyStatusService:
    def __init__(self, config_service: ConfigService):
        self._proxies: dict[str, Proxy] = {}
        self._update_proxy_reference(config_service)
    
    def _update_proxy_reference(self, config_service: ConfigService) -> None:
        """Sync internal proxy list with config service."""
        current_proxies = config_service.config.proxies
        
        # Add new proxies
        for name, proxy_cfg in current_proxies.items():
            if name not in self._proxies:
                self._proxies[name] = Proxy(
                    listen_address=proxy_cfg.listen_address,
                    listen_port=proxy_cfg.listen_port,
                    bind_port=proxy_cfg.bind_port,
                )
        
        # Remove deleted proxies
        for name in list(self._proxies.keys()):
            if name not in current_proxies:
                del self._proxies[name]
                
    def get_proxy_status(self, name: str) -> Proxy | None:
        return self._proxies.get(name)
    
    def start_proxy(self, name: str, process_id: int) -> None:
        proxy = self._proxies.get(name)
        if proxy:
            proxy.is_running = True
            proxy.process_id = process_id