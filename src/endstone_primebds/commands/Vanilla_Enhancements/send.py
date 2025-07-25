import socket
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "send",
    "Sends players to a specified server address!",
    ["/send <player: player> <ip: string> <port: int>"],
    ["primebds.command.send"]
)

# CONNECT COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) < 3:
        sender.send_message("Usage: /send <player> <ip> <port>")
        return False

    ip = args[1]
    port_str = args[2]

    if not is_valid_ip(ip):
        sender.send_message(f"Invalid IP address: {ip}")
        return False

    if not is_valid_port(port_str):
        sender.send_message(f"Invalid port number: {port_str}")
        return False

    port = int(port_str)

    targets = get_matching_actors(self, args[0], sender)
    for target in targets:
        target.transfer(ip, port)

    return True

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