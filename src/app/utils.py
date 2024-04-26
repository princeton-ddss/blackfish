import socket
from app.logger import logger


def find_port(host="127.0.0.1", lower=8080, upper=8900) -> int:
    for port in range(lower, upper):
        try:
            client = socket.socket()
            client.bind((host, port))
            client.close()
            return int(port)
        except OSError:
            logger.debug(f"OSError: failed to bind port {port} on host {host}")
    raise OSError(f"OSError: no ports available in range {lower}-{upper}")
