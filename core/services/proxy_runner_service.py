from __future__ import annotations

import asyncio
import logging
from typing import Dict

from core.config.proxy_config_parser import ProxyConfig
from core.services.proxies import create_proxy, ProxyBase


logger = logging.getLogger(__name__)


class ProxyRunnerService:
    """Manages the lifecycle of running proxy instances."""

    def __init__(self):
        self._running_proxies: Dict[str, ProxyBase] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop to use for proxy tasks."""
        self._loop = loop

    def start_proxy(self, name: str, config: ProxyConfig) -> None:
        """Start a proxy instance."""
        if name in self._running_proxies:
            logger.warning(f"Proxy '{name}' is already running")
            return

        if not self._loop:
            raise RuntimeError("Event loop not set. Call set_event_loop() first.")

        try:
            proxy = create_proxy(config)
            self._running_proxies[name] = proxy

            # Schedule the start coroutine
            asyncio.run_coroutine_threadsafe(proxy.start(), self._loop)
            logger.info(f"Started proxy '{name}'")
        except Exception as e:
            logger.error(f"Failed to start proxy '{name}': {e}")
            if name in self._running_proxies:
                del self._running_proxies[name]
            raise

    def stop_proxy(self, name: str) -> None:
        """Stop a proxy instance."""
        proxy = self._running_proxies.get(name)
        if not proxy:
            logger.warning(f"Proxy '{name}' is not running")
            return

        if not self._loop:
            raise RuntimeError("Event loop not set")

        try:
            asyncio.run_coroutine_threadsafe(proxy.stop(), self._loop)
            del self._running_proxies[name]
            logger.info(f"Stopped proxy '{name}'")
        except Exception as e:
            logger.error(f"Failed to stop proxy '{name}': {e}")
            raise

    def is_proxy_running(self, name: str) -> bool:
        """Check if a proxy is running."""
        return name in self._running_proxies

    def get_running_proxies(self) -> list[str]:
        """Get list of running proxy names."""
        return list(self._running_proxies.keys())
