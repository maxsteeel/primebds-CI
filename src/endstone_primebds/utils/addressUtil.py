import socket

def is_valid_ip(ip: str) -> bool:
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def is_valid_port(port_str: str) -> bool:
    if not port_str.isdigit():
        return False
    port = int(port_str)
    return 1 <= port <= 65535