from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "tip",
    "Sends a custom tip message!",
    ["/tip <player: player> <text: message>"],
    ["primebds.command.tip"]
)

# TIP COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    matches = get_matching_actors(self.server, args[0], sender)
    if not matches:
        sender.send_message(f"No valid players matched selector: {args[0]}")
        return False

    for player in matches:
        player.send_tip(args[1])

    if len(matches) == 1:
        sender.send_message(f"A tip packet was sent to {ColorFormat.YELLOW}{matches[0].name}")
    else:
        sender.send_message(f"A tip packet was sent to {len(matches)} players")

    return True
