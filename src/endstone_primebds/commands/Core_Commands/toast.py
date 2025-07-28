from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "toast",
    "Sends a custom toast message!",
    ["/toast <player: player> <title: string> <text: message>"],
    ["primebds.command.toast"]
)

# TOAST COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    targets = get_matching_actors(self, args[0], sender)
    for player in targets:
        player.send_toast(args[1], args[2])
    return True
