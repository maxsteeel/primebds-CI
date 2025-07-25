import socket
from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "connect",
    "Connect players to a specified server address!",
    ["/connect <player: player> <ip: string> <port: string>", "/connect (all)<selector: All> <ip: string> <port: string>"],
    ["primebds.command.connect"]
)

# CONNECT COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) < 3:
        sender.send_message("Usage: /transfer <player|all> <ip> <port>")
        return False

    target_name = args[0].lower()
    ip = args[1]
    port_str = args[2]

    if not is_valid_ip(ip):
        sender.send_message(f"Invalid IP address: {ip}")
        return False

    if not is_valid_port(port_str):
        sender.send_message(f"Invalid port number: {port_str}")
        return False

    port = int(port_str)

    if target_name == "all":
        for actor in self.server.level.actors:
            if isinstance(actor, Player):
                actor.transfer(ip, port)
    else:
        target = self.server.get_player(target_name)
        if target:
            target.transfer(ip, port)
        else:
            sender.send_message(f"Player {target_name} not found.")

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