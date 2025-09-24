"""
FUSE - (python dev tool) - Utils
Network Utils - Enhanced utilities for network operations.
"""

import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple


class NetworkUtils:
    """Enhanced network utilities with performance optimizations."""

    _port_cache = {}
    _cache_lock = threading.Lock()

    @staticmethod
    def find_free_port(
        host: str = "127.0.0.1", start_port: int = 8000, max_attempts: int = 100
    ) -> int:
        """
        Find a free port starting from start_port.

        Args:
            host: Host to check ports on
            start_port: Starting port number
            max_attempts: Maximum number of ports to check

        Returns:
            Free port number

        Raises:
            RuntimeError: If no free port found within max_attempts
        """
        cache_key = f"{host}:{start_port}"

        with NetworkUtils._cache_lock:
            if cache_key in NetworkUtils._port_cache:
                cached_port = NetworkUtils._port_cache[cache_key]
                if NetworkUtils.check_port_available(host, cached_port):
                    return cached_port
                else:
                    # Remove stale cache entry
                    del NetworkUtils._port_cache[cache_key]

        # Try to find a free port
        for port in range(start_port, start_port + max_attempts):
            if NetworkUtils.check_port_available(host, port):
                # Cache the result
                with NetworkUtils._cache_lock:
                    NetworkUtils._port_cache[cache_key] = port
                return port

        raise RuntimeError(
            f"No free port found in range {start_port}-{start_port + max_attempts}"
        )

    @staticmethod
    def check_port_available(host: str, port: int, timeout: float = 1.0) -> bool:
        """
        Check if a port is available for binding on the given host.

        Args:
            host: Host to check
            port: Port number to check
            timeout: Not used for binding check, kept for API compatibility

        Returns:
            True if port is available for binding, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return True  # Successfully bound = port is available
        except (socket.error, OSError):
            return False  # Failed to bind = port is not available

    @staticmethod
    def check_multiple_ports(
        host: str, ports: List[int], timeout: float = 1.0
    ) -> List[Tuple[int, bool]]:
        """
        Check multiple ports concurrently for availability.

        Args:
            host: Host to check ports on
            ports: List of port numbers to check
            timeout: Connection timeout in seconds

        Returns:
            List of tuples (port, is_available)
        """
        results = []

        def check_single_port(port: int) -> Tuple[int, bool]:
            return port, NetworkUtils.check_port_available(host, port, timeout)

        with ThreadPoolExecutor(max_workers=min(len(ports), 10)) as executor:
            future_to_port = {
                executor.submit(check_single_port, port): port for port in ports
            }

            for future in as_completed(future_to_port):
                try:
                    port, is_available = future.result()
                    results.append((port, is_available))
                except Exception as e:
                    port = future_to_port[future]
                    results.append((port, False))

        return sorted(results, key=lambda x: x[0])

    @staticmethod
    def find_free_port_range(
        host: str = "127.0.0.1", start_port: int = 8000, count: int = 2
    ) -> List[int]:
        """
        Find a range of consecutive free ports.

        Args:
            host: Host to check ports on
            start_port: Starting port number
            count: Number of consecutive ports needed

        Returns:
            List of consecutive free port numbers

        Raises:
            RuntimeError: If required consecutive ports not found
        """
        max_attempts = 1000
        for start in range(start_port, start_port + max_attempts - count + 1):
            ports_to_check = list(range(start, start + count))
            port_results = NetworkUtils.check_multiple_ports(host, ports_to_check)

            if all(available for _, available in port_results):
                return ports_to_check

        raise RuntimeError(
            f"Could not find {count} consecutive free ports starting from {start_port}"
        )

    @staticmethod
    def is_valid_port(port: int) -> bool:
        """Check if port number is in valid range."""
        return 1 <= port <= 65535

    @staticmethod
    def is_privileged_port(port: int) -> bool:
        """Check if port is in privileged range (< 1024)."""
        return 1 <= port < 1024

    @staticmethod
    def get_local_ip() -> str:
        """Get the local IP address."""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def clear_port_cache() -> None:
        """Clear the port cache."""
        with NetworkUtils._cache_lock:
            NetworkUtils._port_cache.clear()


"""
FUSE - (python dev tool) - Utils
Domain Utils - Utilities for domain and URL management.
"""

from typing import Optional, Dict, List
from urllib.parse import urljoin
import socket


class DomainUtils:
    """Utilities for managing domains and URLs in development."""

    def __init__(self):
        self.host: Optional[str] = None
        self.app_port: Optional[int] = None
        self.ui_port: Optional[int] = None
        self._local_ip: Optional[str] = None

    def configure(self, host: str, app_port: int, ui_port: int) -> None:
        """
        Configure the domain utilities with host and ports.

        Args:
            host: Host address
            app_port: Main application port
            ui_port: Development UI port
        """
        self.host = host
        self.app_port = app_port
        self.ui_port = ui_port
        self._local_ip = self._get_local_ip()

    def get_app_url(self, protocol: str = "http") -> str:
        """
        Get the main application URL.

        Args:
            protocol: Protocol to use (http/https)

        Returns:
            Complete application URL
        """
        if not self.host or not self.app_port:
            raise ValueError("DomainUtils not configured. Call configure() first.")

        return f"{protocol}://{self.host}:{self.app_port}"

    def get_ui_url(self, protocol: str = "http") -> str:
        """
        Get the development UI URL.

        Args:
            protocol: Protocol to use (http/https)

        Returns:
            Complete UI URL
        """
        if not self.host or not self.ui_port:
            raise ValueError("DomainUtils not configured. Call configure() first.")

        return f"{protocol}://{self.host}:{self.ui_port}"

    def get_api_url(self, endpoint: str = "", protocol: str = "http") -> str:
        """
        Get API URL with optional endpoint.

        Args:
            endpoint: API endpoint path
            protocol: Protocol to use (http/https)

        Returns:
            Complete API URL
        """
        base_url = self.get_app_url(protocol)
        if endpoint:
            return urljoin(base_url + "/", endpoint.lstrip("/"))
        return base_url

    def get_local_network_urls(self) -> Dict[str, Dict[str, str]]:
        """
        Get URLs accessible from local network.

        Returns:
            Dictionary with app and ui URLs for different interfaces
        """
        urls = {"app": {}, "ui": {}}

        # Localhost URLs
        urls["app"]["localhost"] = f"http://localhost:{self.app_port}"
        urls["ui"]["localhost"] = f"http://localhost:{self.ui_port}"

        # 127.0.0.1 URLs
        urls["app"]["loopback"] = f"http://127.0.0.1:{self.app_port}"
        urls["ui"]["loopback"] = f"http://127.0.0.1:{self.ui_port}"

        # Local IP URLs (for network access)
        if self._local_ip and self._local_ip != "127.0.0.1":
            urls["app"]["network"] = f"http://{self._local_ip}:{self.app_port}"
            urls["ui"]["network"] = f"http://{self._local_ip}:{self.ui_port}"

        return urls

    def get_dev_domain(self, subdomain: str = "app") -> str:
        """
        Generate a development domain (for future local DNS features).

        Args:
            subdomain: Subdomain prefix

        Returns:
            Development domain
        """
        return f"{subdomain}.local-dev.test"

    def get_qr_code_url(self, service: str = "app") -> Optional[str]:
        """
        Get URL suitable for QR code generation (network accessible).

        Args:
            service: Service type ("app" or "ui")

        Returns:
            Network accessible URL or None if not available
        """
        if not self._local_ip or self._local_ip == "127.0.0.1":
            return None

        port = self.app_port if service == "app" else self.ui_port
        return f"http://{self._local_ip}:{port}"

    def get_all_access_urls(self) -> Dict[str, List[str]]:
        """
        Get all possible access URLs for services.

        Returns:
            Dictionary with all access URLs for app and ui
        """
        app_urls = [
            f"http://localhost:{self.app_port}",
            f"http://127.0.0.1:{self.app_port}",
        ]

        ui_urls = [
            f"http://localhost:{self.ui_port}",
            f"http://127.0.0.1:{self.ui_port}",
        ]

        # Add network URLs if available
        if self._local_ip and self._local_ip not in ["127.0.0.1", "localhost"]:
            app_urls.append(f"http://{self._local_ip}:{self.app_port}")
            ui_urls.append(f"http://{self._local_ip}:{self.ui_port}")

        # Add configured host if different
        if self.host not in ["localhost", "127.0.0.1", self._local_ip]:
            app_urls.append(f"http://{self.host}:{self.app_port}")
            ui_urls.append(f"http://{self.host}:{self.ui_port}")

        return {
            "app": list(set(app_urls)),  # Remove duplicates
            "ui": list(set(ui_urls)),
        }

    def validate_host(self, host: str) -> bool:
        """
        Validate if host is accessible.

        Args:
            host: Host to validate

        Returns:
            True if host is valid and accessible
        """
        try:
            socket.gethostbyname(host)
            return True
        except socket.gaierror:
            return False

    def is_localhost(self, host: str) -> bool:
        """
        Check if host refers to localhost.

        Args:
            host: Host to check

        Returns:
            True if host is localhost
        """
        localhost_variants = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        return host.lower() in localhost_variants

    def get_external_url(
        self, service: str = "app", use_ngrok: bool = False
    ) -> Optional[str]:
        """
        Get external URL for service (placeholder for future tunnel integration).

        Args:
            service: Service type ("app" or "ui")
            use_ngrok: Whether to use ngrok tunneling (future feature)

        Returns:
            External URL or None if not configured
        """
        # Placeholder for future external tunneling features
        # Could integrate with ngrok, localtunnel, etc.
        if use_ngrok:
            # Future: return ngrok tunnel URL
            pass

        return None

    def _get_local_ip(self) -> str:
        """Get the local IP address of the machine."""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def generate_urls_table_data(self) -> List[Dict[str, str]]:
        """
        Generate data for displaying URLs in a table format.

        Returns:
            List of dictionaries with service, type, and URL information
        """
        table_data = []
        all_urls = self.get_all_access_urls()

        # Add app URLs
        for i, url in enumerate(all_urls["app"]):
            url_type = (
                "Primary"
                if i == 0
                else "Network"
                if "127.0.0.1" not in url and "localhost" not in url
                else "Local"
            )
            table_data.append(
                {
                    "service": "Application" if i == 0 else "",
                    "type": url_type,
                    "url": url,
                    "description": "Main application server",
                }
            )

        # Add UI URLs
        for i, url in enumerate(all_urls["ui"]):
            url_type = (
                "Primary"
                if i == 0
                else "Network"
                if "127.0.0.1" not in url and "localhost" not in url
                else "Local"
            )
            table_data.append(
                {
                    "service": "Dev UI" if i == 0 else "",
                    "type": url_type,
                    "url": url,
                    "description": "Development dashboard",
                }
            )

        return table_data

    def __str__(self) -> str:
        """String representation of domain configuration."""
        return f"DomainUtils(host={self.host}, app_port={self.app_port}, ui_port={self.ui_port})"

    def __repr__(self) -> str:
        """Detailed representation of domain configuration."""
        return (
            f"DomainUtils("
            f"host='{self.host}', "
            f"app_port={self.app_port}, "
            f"ui_port={self.ui_port}, "
            f"local_ip='{self._local_ip}'"
            f")"
        )
