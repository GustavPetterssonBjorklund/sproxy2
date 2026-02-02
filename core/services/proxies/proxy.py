from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from core.config.proxy_config_parser import ProxyConfig


class ProxyBase(ABC):
    def __init__(self, config: ProxyConfig):
        self.config = config
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self.is_running = False

    async def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self.run())
        self.is_running = True

    async def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.is_running = False

    async def wait_stopped(self) -> None:
        await self._stop_event.wait()

    @abstractmethod
    async def run(self) -> None:
        """Run the proxy loop until stopped."""
        raise NotImplementedError
