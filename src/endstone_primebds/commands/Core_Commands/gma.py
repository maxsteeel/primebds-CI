from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "gma",
    "Sets your game mode to adventure!",
    ["/gma [player: player]"],
    ["primebds.command.gma"]
)

# GMA COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) == 0:
        if not isinstance(sender, Player):
            sender.send_message("This command can only be executed by a player")
            return False
        sender.perform_command("gamemode a @s")
        return True

    targets = get_matching_actors(self, args[0], sender)
    for target in targets:
        sender.perform_command(f"gamemode a {target.name}")

    return True
