import time
from endstone.command import CommandSender, BlockCommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.handlers.intervals import stop_jail_check_if_not_needed
from endstone.level import Location
from endstone import GameMode

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "unjail",
    "Free a jailed player!",
    [
        "/unjail <player: player>"
    ],
    ["primebds.command.unjail"]
)

# UNJAIL COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, BlockCommandSender):
        sender.send_message(f"§cThis command cannot be automated")
        return False
    
    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False
    
    player = self.db.get_mod_log(self.db.get_xuid_by_name(args[0]))
    
    if player:
        mod_user = self.db.get_mod_log(player.xuid)
        if mod_user.is_jailed:
            sender.send_message(f"§6Player §e{args[0]} §6was unjailed")
            self.db.force_unjail(mod_user.xuid)
        else:
            sender.send_message(f"§6Player §e{args[0]} §6is not jailed")
    else:
        sender.send_message(f"§cPlayer {args[0]} §6does not exist")