from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.target_selector_util import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "ping",
    "Checks the server ping!",
    ["/ping [player: player]"],
    ["primebds.command.ping"]
)

# PING COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) == 0:
        if not isinstance(sender, Player):
            sender.send_error_message("This command can only be executed by a player")
            return False
        target = sender
        ping = target.ping
        sender.send_message(
            f"Your ping is {get_ping_color(ping)}{ping}§rms"
        )
        return True

    selector = args[0].strip('"')
    matched = get_matching_actors(self, selector, sender)

    if not matched:
        sender.send_error_message(f"No matching players found for '{selector}'.")
        return True

    if len(matched) == 1:
        player = matched[0]
        ping = player.ping
        sender.send_message(
            f"The ping of {player.name} is {get_ping_color(ping)}{ping}§rms"
        )
    else:
        ping_list = [
            f"§7- §r{player.name}: {get_ping_color(player.ping)}{player.ping}§rms"
            for player in matched if isinstance(player, Player)
        ]
        sender.send_message(f"§bMatched Players' Pings:\n" + "\n".join(ping_list))
    return True

def get_ping_color(ping: int) -> str:
    """Returns the color formatting based on ping value."""
    return (
        ColorFormat.GREEN if ping <= 80 else
        ColorFormat.YELLOW if ping <= 160 else
        ColorFormat.RED
    )
