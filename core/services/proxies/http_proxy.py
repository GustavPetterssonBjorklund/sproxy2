import asyncio
import logging
import subprocess

from .proxy import ProxyBase

logger = logging.getLogger(__name__)

class HttpProxy(ProxyBase):
    def __init__(self, config):
        super().__init__(config)
        self._server = None
        self._ssh_process = None

    async def run(self) -> None:
        # Note: SSH doesn't natively support HTTP proxy tunneling like it does SOCKS5
        # For HTTP proxies via SSH, we'd need to run a local HTTP proxy that connects through SSH
        # For now, we only support direct HTTP proxy
        if self.config.ssh_username:
            logger.error("HTTP proxy via SSH tunnel is not yet supported. Use SOCKS5 instead.")
            return
        
        await self._run_direct_proxy()

    async def _run_direct_proxy(self) -> None:
        """Run direct HTTP proxy server (no SSH)."""
        self._server = None
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                '127.0.0.1',
                self.config.bind_port
            )
            logger.info(f"HTTP proxy listening on 127.0.0.1:{self.config.bind_port}")
            
            async with self._server:
                # Wait for stop event with periodic health checks
                while not self._stop_event.is_set():
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # Health check passed, continue
                        if self._server is None or self._server.is_serving() == False:
                            logger.error("Server stopped unexpectedly")
                            raise RuntimeError("Server is no longer serving")
                        continue
            
            logger.info(f"HTTP proxy {self.config.listen_address}:{self.config.listen_port} stopped")
        except asyncio.CancelledError:
            logger.info(f"HTTP proxy cancelled")
            raise
        except Exception as e:
            logger.error(f"HTTP proxy error: {e}")
            raise
        finally:
            if self._server:
                self._server.close()
                try:
                    await self._server.wait_closed()
                except:
                    pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming HTTP CONNECT requests."""
        try:
            # Read the HTTP request line
            request_line = await reader.readline()
            request_str = request_line.decode('utf-8', errors='ignore').strip()
            
            if not request_str:
                writer.close()
                await writer.wait_closed()
                return
            
            # Parse request
            parts = request_str.split()
            if len(parts) < 2:
                writer.close()
                await writer.wait_closed()
                return
            
            method = parts[0]
            target = parts[1]
            
            # Read headers
            headers = {}
            while True:
                line = await reader.readline()
                if line == b'\r\n' or line == b'\n':
                    break
                if line:
                    header_str = line.decode('utf-8', errors='ignore').strip()
                    if ':' in header_str:
                        key, value = header_str.split(':', 1)
                        headers[key.strip()] = value.strip()
            
            # Handle CONNECT method for HTTPS
            if method == 'CONNECT':
                await self._handle_connect(target, reader, writer)
            else:
                # Handle regular HTTP request
                await self._handle_http(method, target, headers, reader, writer)
                
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

    async def _handle_connect(self, target: str, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Handle HTTP CONNECT for HTTPS tunneling."""
        try:
            # Parse target host:port
            if ':' in target:
                host, port_str = target.rsplit(':', 1)
                port = int(port_str)
            else:
                host = target
                port = 443
            
            # Connect to target server
            try:
                remote_reader, remote_writer = await asyncio.open_connection(host, port)
            except Exception as e:
                logger.error(f"Failed to connect to {host}:{port}: {e}")
                client_writer.write(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
                await client_writer.drain()
                return
            
            # Send success response
            client_writer.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            await client_writer.drain()
            
            # Relay data bidirectionally
            await self._relay_data(client_reader, client_writer, remote_reader, remote_writer)
            
        except Exception as e:
            logger.error(f"CONNECT error: {e}")

    async def _handle_http(self, method: str, target: str, headers: dict, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Handle regular HTTP requests."""
        try:
            # Parse target URL
            if target.startswith('http://'):
                target = target[7:]
            
            if '/' in target:
                host_port, path = target.split('/', 1)
                path = '/' + path
            else:
                host_port = target
                path = '/'
            
            if ':' in host_port:
                host, port_str = host_port.rsplit(':', 1)
                port = int(port_str)
            else:
                host = host_port
                port = 80
            
            # Connect to target server
            try:
                remote_reader, remote_writer = await asyncio.open_connection(host, port)
            except Exception as e:
                logger.error(f"Failed to connect to {host}:{port}: {e}")
                client_writer.write(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
                await client_writer.drain()
                return
            
            # Forward the request
            request = f"{method} {path} HTTP/1.1\r\n"
            request += f"Host: {host}\r\n"
            for key, value in headers.items():
                if key.lower() not in ['proxy-connection']:
                    request += f"{key}: {value}\r\n"
            request += "\r\n"
            
            remote_writer.write(request.encode())
            await remote_writer.drain()
            
            # Relay response back to client
            while True:
                data = await remote_reader.read(8192)
                if not data:
                    break
                client_writer.write(data)
                await client_writer.drain()
            
            remote_writer.close()
            await remote_writer.wait_closed()
            
        except Exception as e:
            logger.error(f"HTTP request error: {e}")

    async def _relay_data(self, client_reader, client_writer, remote_reader, remote_writer):
        """Relay data between client and remote server."""
        async def forward(reader, writer):
            try:
                while True:
                    data = await reader.read(8192)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
            except:
                pass
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
        
        await asyncio.gather(
            forward(client_reader, remote_writer),
            forward(remote_reader, client_writer),
            return_exceptions=True
        )
