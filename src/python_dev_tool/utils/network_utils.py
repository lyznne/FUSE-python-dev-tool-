"""
FUSE - (python dev tool) - Utils
Network Utils - Utilities for network operations.
"""


import socket

class NetworkUtils:
    """Network utilities."""

    @staticmethod
    def find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    @staticmethod
    def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) != 0
