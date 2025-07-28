from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "popup",
    "Sends a custom popup message!",
    ["/popup <player: player> <text: message>"],
    ["primebds.command.popup"]
)

# POPUP COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    targets = get_matching_actors(self, args[0], sender)
    for target in targets:
        target.send_popup(args[1])

    return True
