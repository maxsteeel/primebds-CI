from endstone import ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.configUtil import load_config
from endstone_primebds.utils.dbUtil import UserDB
from endstone_primebds.utils.loggingUtil import log

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "unmute",
    "Removes an active mute from a player!",
    ["/unmute <player: player>"],
    ["primebds.command.unmute"]
)

# UNMUTE COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) < 1:
        sender.send_message(f"Usage: /unmute <player>")
        return False
    
    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    player_name = args[0].strip('"')
    

    # Get the mod log to check if the player is muted
    mod_log = self.db.get_offline_mod_log(player_name)

    if not mod_log or not mod_log.is_muted:
        # Player is not muted, return an error message
        sender.send_message(f"§6Player §e{player_name} §6is not muted")
        
        return False

    # Remove the mute
    self.db.remove_mute(player_name)
    

    # Notify the sender that the mute has been removed
    sender.send_message(f"§6Player §e{player_name} §6has been unmuted")
    log(self, f"§6Player §e{player_name} §6was unmuted by §e{sender.name}", "mod")

    return True
