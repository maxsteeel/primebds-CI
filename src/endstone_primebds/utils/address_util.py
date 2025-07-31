import re
import socket

def is_valid_ip(ip: str) -> bool:

    # Validate IPv4
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        pass

    # Validate hostname (RFC 1123)
    hostname_regex = re.compile(
        r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
        r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
    )
    return bool(hostname_regex.match(ip))

def is_valid_port(port_str: str) -> bool:
    if not port_str.isdigit():
        return False
    port = int(port_str)
    return 1 <= port <= 65535