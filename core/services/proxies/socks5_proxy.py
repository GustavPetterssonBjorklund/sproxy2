import asyncio
import logging
import struct
import subprocess
import sys

from .proxy import ProxyBase

logger = logging.getLogger(__name__)

class Socks5Proxy(ProxyBase):
    def __init__(self, config):
        super().__init__(config)
        self._server = None
        self._ssh_process = None

    async def run(self) -> None:
        # If SSH username is provided, use SSH tunnel
        if self.config.ssh_username:
            await self._run_ssh_tunnel()
        else:
            await self._run_direct_proxy()

    async def _run_ssh_tunnel(self) -> None:
        """Run SOCKS5 proxy via SSH dynamic port forwarding."""
        try:
            # SSH command with dynamic port forwarding
            # -D binds local port for SOCKS5 proxy
            # -N means don't execute remote command
            # -T disables pseudo-terminal allocation
            # -o BatchMode=yes prevents password prompts
            # -o ConnectTimeout=10 sets connection timeout
            # -o ServerAliveInterval=60 keeps connection alive
            ssh_cmd = [
                'ssh',
                '-D', f'127.0.0.1:{self.config.bind_port}',
                '-N',
                '-T',
                '-o', 'BatchMode=yes',
                '-o', 'ConnectTimeout=10',
                '-o', 'ServerAliveInterval=60',
                '-o', 'ServerAliveCountMax=3',
                f'{self.config.ssh_username}@{self.config.listen_address}',
                '-p', str(self.config.listen_port)
            ]
            
            logger.info(f"Starting SSH tunnel to {self.config.ssh_username}@{self.config.listen_address}:{self.config.listen_port}")
            
            # Start SSH process in background (no window on Windows)
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            self._ssh_process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Wait for SSH to establish connection (or fail)
            logger.info("Waiting for SSH connection to establish...")
            connection_established = False
            
            for i in range(20):  # Wait up to 10 seconds
                if self._ssh_process.returncode is not None:
                    # Process already terminated - connection failed
                    stderr = await self._ssh_process.stderr.read()
                    error_msg = stderr.decode('utf-8', errors='ignore').strip()
                    
                    if 'Permission denied' in error_msg or 'publickey' in error_msg:
                        logger.error(f"SSH authentication failed - no valid SSH key found for {self.config.ssh_username}@{self.config.listen_address}")
                        logger.error("Please set up SSH key authentication or check your SSH keys")
                    elif 'Connection refused' in error_msg:
                        logger.error(f"SSH connection refused by {self.config.listen_address}:{self.config.listen_port}")
                    elif 'No route to host' in error_msg or 'Connection timed out' in error_msg:
                        logger.error(f"Cannot reach SSH server at {self.config.listen_address}:{self.config.listen_port}")
                    else:
                        logger.error(f"SSH tunnel failed to start: {error_msg}")
                    raise RuntimeError(f"SSH connection failed: {error_msg}")
                
                # Check if port is listening (simple check)
                try:
                    test_reader, test_writer = await asyncio.wait_for(
                        asyncio.open_connection('127.0.0.1', self.config.bind_port),
                        timeout=0.1
                    )
                    test_writer.close()
                    await test_writer.wait_closed()
                    connection_established = True
                    break
                except:
                    pass
                
                await asyncio.sleep(0.5)
            
            if not connection_established:
                logger.warning("SSH tunnel started but port not yet accessible (may still be connecting)")
            else:
                logger.info(f"SOCKS5 proxy via SSH tunnel listening on 127.0.0.1:{self.config.bind_port}")
            
            # Monitor SSH process with regular health checks
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    # Check if SSH process is still alive
                    if self._ssh_process.returncode is not None:
                        logger.error(f"SSH process terminated unexpectedly with code {self._ssh_process.returncode}")
                        stderr = await self._ssh_process.stderr.read()
                        if stderr:
                            logger.error(f"SSH error: {stderr.decode('utf-8', errors='ignore')}")
                        raise RuntimeError("SSH tunnel disconnected")
                    continue
            
            # Clean up
            if self._ssh_process and self._ssh_process.returncode is None:
                self._ssh_process.terminate()
                try:
                    await asyncio.wait_for(self._ssh_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self._ssh_process.kill()
                    await self._ssh_process.wait()
            
            logger.info(f"SOCKS5 SSH tunnel stopped")
        except Exception as e:
            logger.error(f"SOCKS5 SSH tunnel error: {e}")
            raise

    async def _run_direct_proxy(self) -> None:
        """Run direct SOCKS5 proxy server (no SSH)."""
        self._server = None
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                '127.0.0.1',
                self.config.bind_port
            )
            logger.info(f"SOCKS5 proxy listening on 127.0.0.1:{self.config.bind_port}")
            
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
            
            logger.info(f"SOCKS5 proxy {self.config.listen_address}:{self.config.listen_port} stopped")
        except asyncio.CancelledError:
            logger.info(f"SOCKS5 proxy cancelled")
            raise
        except Exception as e:
            logger.error(f"SOCKS5 proxy error: {e}")
            raise
        finally:
            if self._server:
                self._server.close()
                try:
                    await self._server.wait_closed()
                except:
                    pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming SOCKS5 connections."""
        try:
            # Authentication handshake
            if not await self._handshake(reader, writer):
                writer.close()
                await writer.wait_closed()
                return
            
            # Connection request
            target = await self._parse_request(reader, writer)
            if not target:
                writer.close()
                await writer.wait_closed()
                return
            
            host, port = target
            
            # Connect to target
            try:
                remote_reader, remote_writer = await asyncio.open_connection(host, port)
            except Exception as e:
                logger.error(f"Failed to connect to {host}:{port}: {e}")
                # Send connection refused
                writer.write(b'\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00')
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
            
            # Send success response
            writer.write(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
            await writer.drain()
            
            # Relay data
            await self._relay_data(reader, writer, remote_reader, remote_writer)
            
        except Exception as e:
            logger.error(f"Error handling SOCKS5 client: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

    async def _handshake(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """Perform SOCKS5 handshake."""
        try:
            # Read version and number of methods
            data = await reader.readexactly(2)
            version, nmethods = struct.unpack('!BB', data)
            
            if version != 5:
                return False
            
            # Read methods
            methods = await reader.readexactly(nmethods)
            
            # We support no authentication (0x00)
            if 0 in methods:
                writer.write(b'\x05\x00')  # Version 5, no auth
                await writer.drain()
                return True
            else:
                writer.write(b'\x05\xFF')  # No acceptable methods
                await writer.drain()
                return False
                
        except Exception as e:
            logger.error(f"Handshake error: {e}")
            return False

    async def _parse_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Parse SOCKS5 connection request."""
        try:
            # Read request header
            data = await reader.readexactly(4)
            version, cmd, _, atyp = struct.unpack('!BBBB', data)
            
            if version != 5:
                return None
            
            if cmd != 1:  # Only CONNECT is supported
                writer.write(b'\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00')  # Command not supported
                await writer.drain()
                return None
            
            # Parse destination address
            if atyp == 1:  # IPv4
                addr_data = await reader.readexactly(4)
                host = '.'.join(str(b) for b in addr_data)
            elif atyp == 3:  # Domain name
                addr_len = (await reader.readexactly(1))[0]
                addr_data = await reader.readexactly(addr_len)
                host = addr_data.decode('utf-8')
            elif atyp == 4:  # IPv6
                addr_data = await reader.readexactly(16)
                host = ':'.join(f'{addr_data[i]:02x}{addr_data[i+1]:02x}' for i in range(0, 16, 2))
            else:
                writer.write(b'\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00')  # Address type not supported
                await writer.drain()
                return None
            
            # Parse port
            port_data = await reader.readexactly(2)
            port = struct.unpack('!H', port_data)[0]
            
            return (host, port)
            
        except Exception as e:
            logger.error(f"Request parsing error: {e}")
            return None

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
