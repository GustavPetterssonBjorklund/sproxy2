import asyncio
import logging

from .proxy import ProxyBase

logger = logging.getLogger(__name__)

class Socks5Proxy(ProxyBase):
    async def run(self) -> None:
        logger.info(f"SOCKS5 proxy listening on {self.config.listen_address}:{self.config.listen_port}")
        # TODO: Implement real SOCKS5 proxy logic
        while not self._stop_event.is_set():
            await asyncio.sleep(0.25)
        logger.info(f"SOCKS5 proxy {self.config.listen_address}:{self.config.listen_port} stopped")
