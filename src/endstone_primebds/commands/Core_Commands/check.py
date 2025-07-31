from datetime import datetime

from endstone_primebds.utils.time_util import TimezoneUtils

from endstone import ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "check",
    "Checks a player's client info!",
    ["/check <player: player>"],
    ["primebds.command.check"],
    "op",
    ["seen"]
)

# CHECK COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:

    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    player_name = args[0].strip('"')
    target = sender.server.get_player(player_name)

    if target is None:
        # Check Offline DB
        user = self.db.get_offline_user(player_name)
        if user is None:
            sender.send_message(
                f"Player §e{player_name}§c not found in database.")
            
            return False

        xuid = user.xuid
        uuid = user.uuid
        name = user.name
        ping = f"{user.ping}ms §7[Last Recorded§7]"
        device = user.device_os
        version = user.client_ver
        rank = user.internal_rank
        last_join = user.last_join
        last_leave = user.last_leave
        status = f"§cOffline"

    else:
        # Fetch Online Data
        user = self.db.get_online_user(target.xuid)
        xuid = target.xuid
        uuid = target.unique_id
        name = target.name
        ping = f"{target.ping}ms"
        device = target.device_os
        version = target.game_version
        rank = user.internal_rank
        last_join = user.last_join
        last_leave = user.last_leave
        status = f"{ColorFormat.GREEN}Online"

    join_time = TimezoneUtils.convert_to_timezone(last_join, "EST")

    dt = datetime.fromtimestamp(last_leave)
    year = dt.year

    if year < 2000:
        leave_time_str = "N/A"
    else:
        leave_time_str = TimezoneUtils.convert_to_timezone(last_leave, "EST")

    # Format and send the message
    sender.send_message(f"""{ColorFormat.AQUA}Player Information:
§7- §eName: {ColorFormat.WHITE}{name} §7[{status}§7]
§7- §eXUID: {ColorFormat.WHITE}{xuid}
§7- §eUUID: {ColorFormat.WHITE}{uuid}
§7- §eInternal Rank: {ColorFormat.WHITE}{rank}
§7- §eDevice OS: {ColorFormat.WHITE}{device}
§7- §eClient Version: {ColorFormat.WHITE}{version}
§7- §ePing: {ColorFormat.WHITE}{ping}
§7- §eLast Join: {ColorFormat.WHITE}{join_time}
§7- §eLast Leave: {ColorFormat.WHITE}{leave_time_str}
""")

    return True


