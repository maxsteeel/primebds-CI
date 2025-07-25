from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.selectorUtil import get_players_by_selector

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
    if len(args) < 2:
        sender.send_error_message("Usage: /popup <player> <message>")
        return False

    target_selector = args[0].strip('"')
    message = args[1]

    targets = get_players_by_selector(sender, target_selector, self.server)

    if not targets:
        sender.send_error_message(f"No valid players found for selector: {target_selector}")
        return True

    for target in targets:
        target.send_popup(message)

    if len(targets) == 1:
        sender.send_message(f"A popup packet was sent to {ColorFormat.YELLOW}{targets[0].name}")
    else:
        sender.send_message(f"A popup packet was sent to {len(targets)} players")

    return True
