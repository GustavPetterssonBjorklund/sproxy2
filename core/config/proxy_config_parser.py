from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal
from dataclasses import dataclass

ProxyType = Literal["socks5", "http"]

# Config structure
@dataclass(frozen=True)
class ProxyConfig:
    listen_address: str
    listen_port: int
    bind_port: int
    proxy_type: ProxyType
    run_on_startup: bool = False
    ssh_username: str | None = None


@dataclass(frozen=True)
class SProxy2Config:
    proxies: dict[str, ProxyConfig]


def _require(mapping: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Missing required key '{key}' in {ctx}")
    return mapping[key]


def _as_int(v: Any, ctx: str) -> int:
    if isinstance(v, bool):
        raise ValueError(f"Expected integer in {ctx}, got boolean")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    raise ValueError(f"Expected integer in {ctx}, got {type(v).__name__}")

def _as_proxy_type(v: Any, ctx: str) -> ProxyType:
    if isinstance(v, str) and v in (ProxyType.__args__):
        return v
    raise ValueError(f"Expected proxy type ('socks5' or 'http') in {ctx}, got {v!r}")

def _as_str(v: Any, ctx: str) -> str:
    if isinstance(v, str):
        return v
    raise ValueError(f"Expected string in {ctx}, got {type(v).__name__}")


def _check_port(p: int, ctx: str) -> int:
    if not (0 < p < 65536):
        raise ValueError(f"Port number out of range in {ctx}: {p}")
    return p


def validate_proxies(proxies: dict[str, ProxyConfig]) -> None:
    """Validate proxy configuration for duplicate listen endpoints."""
    listen_endpoints: set[tuple[str, int]] = set()
    
    for name, proxy in proxies.items():
        endpoint = (proxy.listen_address, proxy.listen_port)
        if endpoint in listen_endpoints:
            raise ValueError(
                f"Duplicate listen endpoint {proxy.listen_address}:{proxy.listen_port} for proxy '{name}'"
            )
        listen_endpoints.add(endpoint)


def load_config(path: Path) -> SProxy2Config:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Top-level config must be a table")

    proxies_raw = raw.get("proxies", {})
    if not isinstance(proxies_raw, dict):
        raise ValueError("'proxies' must be a table like [proxies.name]")

    proxies: dict[str, ProxyConfig] = {}

    for name, tbl in proxies_raw.items():
        ctx = f"proxies.{name}"
        if not isinstance(tbl, dict):
            raise ValueError(f"Proxy '{name}' config must be a table")

        listen_address = _as_str(_require(tbl, "listen_address", ctx), f"{ctx}.listen_address")
        listen_port = _as_int(_require(tbl, "listen_port", ctx), f"{ctx}.listen_port")
        bind_port = _as_int(_require(tbl, "bind_port", ctx), f"{ctx}.bind_port")
        proxy_type = _as_proxy_type(tbl.get("proxy_type", "socks5"), f"{ctx}.proxy_type")
        run_on_startup = bool(tbl.get("run_on_startup", False))
        ssh_username_raw = tbl.get("ssh_username", None)
        ssh_username = _as_str(ssh_username_raw, f"{ctx}.ssh_username") if ssh_username_raw is not None else None

        _check_port(listen_port, f"{ctx}.listen_port")
        _check_port(bind_port, f"{ctx}.bind_port")

        proxies[name] = ProxyConfig(
            listen_address=listen_address,
            listen_port=listen_port,
            bind_port=bind_port,
            proxy_type=proxy_type,
            run_on_startup=run_on_startup,
            ssh_username=ssh_username,
        )

    # Validate for duplicate endpoints
    validate_proxies(proxies)
    
    return SProxy2Config(proxies=proxies)


def write_default_config(path: Path) -> None:
    """
    Writes a valid starter config that your load_config() can parse.
    """
    default_cfg = SProxy2Config(
        proxies={
            "example": ProxyConfig(
                listen_address="127.0.0.1",
                listen_port=1080,
                bind_port=10800,
                proxy_type="socks5",
                run_on_startup=False,
                ssh_username=None,
            )
        }
    )
    path.write_text(dump_config(default_cfg), encoding="utf-8")


def _toml_escape(s: str) -> str:
    # Minimal TOML string escaping (enough for normal names/addresses).
    # If you expect arbitrary strings, expand this.
    return s.replace("\\", "\\\\").replace('"', '\\"')


def dump_config(config: SProxy2Config) -> str:
    """
    Serialize SProxy2Config -> TOML string in the format:
      [proxies.name]
      listen_address = "127.0.0.1"
      listen_port = 1080
      bind_port = 10800
    """
    lines: list[str] = []
    lines.append("# SProxy2 Configuration")
    lines.append("# Generated automatically")
    lines.append("")

    # Stable ordering is nice for diffs
    for name in sorted(config.proxies.keys()):
        proxy = config.proxies[name]
        lines.append(f"[proxies.{name}]")
        lines.append(f'listen_address = "{_toml_escape(proxy.listen_address)}"')
        lines.append(f"listen_port = {int(proxy.listen_port)}")
        lines.append(f"bind_port = {int(proxy.bind_port)}")
        lines.append(f'proxy_type = "{proxy.proxy_type}"')
        if proxy.ssh_username:
            lines.append(f'ssh_username = "{_toml_escape(proxy.ssh_username)}"')
        if proxy.run_on_startup:
            lines.append("run_on_startup = true")
        lines.append("")

    return "\n".join(lines)


def save_config(path: Path, config: SProxy2Config) -> None:
    """
    Convenience helper: write config to disk.
    """
    path.write_text(dump_config(config), encoding="utf-8")