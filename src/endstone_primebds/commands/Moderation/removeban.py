from endstone.command import CommandSender, BlockCommandSender
from endstone_primebds.utils.command_util import create_command

from endstone_primebds.utils.logging_util import log

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "removeban",
    "Removes an active ban from a player!",
    ["/removeban <player: player>"],
    ["primebds.command.pardon"]
)

# REMOVEBAN COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, BlockCommandSender):
        sender.send_message(f"§cThis command cannot be automated")
        return False

    if len(args) < 1:
        sender.send_message(f"Usage: /removeban <player>")
        return False
    
    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    player_name = args[0].strip('"')
    

    # Get the mod log to check if the player is banned
    mod_log = self.db.get_offline_mod_log(player_name)

    if not mod_log or not mod_log.is_banned:
        # Player is not banned, return an error message
        sender.send_message(f"§6Player §e{player_name} §6is not banned")
        
        return False

    # Remove the ban
    self.db.remove_ban(player_name)
    #self.server.ban_list.remove_ban(player_name)

    # Notify the sender that the ban has been removed
    sender.send_message(f"§6Player §e{player_name} §6has been unbanned")

    log(self, f"§6Player §e{player_name} §6was unbanned by §e{sender.name}", "mod")

    return True

