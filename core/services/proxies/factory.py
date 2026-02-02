from core.config.proxy_config_parser import ProxyConfig

from .http_proxy import HttpProxy
from .socks5_proxy import Socks5Proxy
from .proxy import ProxyBase


def create_proxy(config: ProxyConfig) -> ProxyBase:
    if config.proxy_type == "http":
        return HttpProxy(config)
    return Socks5Proxy(config)
