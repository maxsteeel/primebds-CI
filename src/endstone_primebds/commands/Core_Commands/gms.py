from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "gms",
    "Sets your game mode to adventure!",
    ["/gms [player: player]"],
    ["primebds.command.gms"]
)

# GMA COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) == 0:
        if not isinstance(sender, Player):
            sender.send_message("This command can only be executed by a player")
            return False
        sender.perform_command("gamemode s @s")
        return True

    targets = get_matching_actors(self, args[0], sender)
    for target in targets:
        sender.perform_command(f"gamemode s {target.name}")

    return True
