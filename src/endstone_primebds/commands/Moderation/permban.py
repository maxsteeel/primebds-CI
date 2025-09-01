from endstone.command import CommandSender
try:
    from endstone.command import BlockCommandSender
except ImportError:
    BlockCommandSender = None 

from endstone_primebds.utils.command_util import create_command

from endstone_primebds.utils.logging_util import log
from endstone_primebds.utils.mod_util import format_time_remaining, ban_message
from datetime import timedelta, datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "permban",
    "Permanently bans a player from the server!",
    ["/permban <player: player> [reason: message]"],
    ["primebds.command.permban"]
)

# PERMBAN COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if BlockCommandSender is not None and isinstance(sender, BlockCommandSender):
       sender.send_message("§cThis command cannot be automated")
       return False

    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    player_name = args[0].strip('"')
    target = self.server.get_player(player_name)

    # Check if the player is already banned (online or offline)
    if target:
        # Check if the player is already banned while online
        if self.db.get_mod_log(target.xuid).is_banned:
            sender.send_message(
                f"§6Player §e{player_name} §cis already permanently banned")
            
            return False
    else:
        # If the player is offline, check the ban status in the database
        mod_log = self.db.get_offline_mod_log(player_name)
        if mod_log and mod_log.is_banned:
            sender.send_message(
                f"§6Player §e{player_name} §cis already permanently banned")
            
            return False

        if not mod_log:
            sender.send_message(f"§6Player '{player_name}' not found")
            
            return False

    # Proceed with the permanent ban if not already banned
    ban_duration = timedelta(days=365 * 200)  # This equals 100 years
    ban_expiration = datetime.now() + ban_duration
    reason = " ".join(args[1:]) if len(args) > 1 else "Negative Behavior"

    # Convert datetime to timestamp for format_time_remaining
    formatted_expiration = format_time_remaining(int(ban_expiration.timestamp()))
    message = ban_message(self.server.level.name, formatted_expiration, reason)

    if target:
        # If the player is online, add the ban directly
        self.db.add_ban(target.xuid, int(ban_expiration.timestamp()), reason)
        target.kick(message)
        sender.send_message(
            f"§6Player §e{player_name} §6was permanently banned for §e\"{reason}\" §6")
    else:
        # If the player is offline, use XUID to ban them
        xuid = self.db.get_xuid_by_name(player_name)
        self.db.add_ban(xuid, int(ban_expiration.timestamp()), reason)
        #self.server.ban_list.add_ban(player_name, None, xuid, reason, ban_expiration)
        sender.send_message(
            f"§6Player §e{player_name} §6was permanently banned for §e\"{reason}\" §7§o(Offline)")

    log(self, f"§6Player §e{player_name} §6was perm banned by §e{sender.name} §6for §e\"{reason}\" §6until §e{formatted_expiration}", "mod")

    return True
