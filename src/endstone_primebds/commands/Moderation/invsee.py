from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.target_selector_util import get_matching_actors

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "invsee",
    "Allows you to view another player's inventory!",
    ["/invsee <player: player> (chest|chat)[invsee_display: invsee_display]"],
    ["primebds.command.invsee"]
)

# INVSEE COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_message("This command can only be executed by a player")
        return False

    if any("@a" in arg for arg in args):
        sender.send_message("§cYou cannot select all players for this command")
        return False
    
    display_type = "inv"  # Default
    if len(args) > 1 and args[1]:
        display_type = args[1].lower()

    targets = get_matching_actors(self, args[0], sender)
    if not targets:
        sender.send_message("§cNo matching player found")
        return False

    for target in targets:
        inv = target.inventory.contents
        
        item_list = "\n".join(
            f"§7- §e{item.type.key} §7x{item.amount}"
            for item in inv if item
        )

        if display_type == "chest":


            return
        elif display_type == "chat":
            sender.send_message(f"§6Inventory of §e{target.name}§6:\n{item_list}")
        else:
            sender.send_message("§cInvalid display type. Use chat or form.")

    return True