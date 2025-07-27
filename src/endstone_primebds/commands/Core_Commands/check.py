from datetime import datetime

from endstone_primebds.utils.timeUtil import TimezoneUtils

from endstone import ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.dbUtil import UserDB

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

    db = UserDB("users.db")

    if target is None:
        # Check Offline DB
        user = db.get_offline_user(player_name)
        if user is None:
            sender.send_message(
                f"Player {ColorFormat.YELLOW}{player_name}{ColorFormat.RED} not found in database.")
            db.close_connection()
            return False

        xuid = user.xuid
        uuid = user.uuid
        name = user.name
        ping = f"{user.ping}ms {ColorFormat.GRAY}[Last Recorded{ColorFormat.GRAY}]"
        device = user.device_os
        version = user.client_ver
        rank = user.internal_rank
        last_join = user.last_join
        last_leave = user.last_leave
        status = f"{ColorFormat.RED}Offline"

    else:
        # Fetch Online Data
        user = db.get_online_user(target.xuid)
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

    db.close_connection()

    join_time = TimezoneUtils.convert_to_timezone(last_join, "EST")

    dt = datetime.fromtimestamp(last_leave)
    year = dt.year

    if year < 2000:
        leave_time_str = "N/A"
    else:
        leave_time_str = TimezoneUtils.convert_to_timezone(last_leave, "EST")

    # Format and send the message
    sender.send_message(f"""{ColorFormat.AQUA}Player Information:
§7- {ColorFormat.YELLOW}Name: {ColorFormat.WHITE}{name} {ColorFormat.GRAY}[{status}{ColorFormat.GRAY}]
§7- {ColorFormat.YELLOW}XUID: {ColorFormat.WHITE}{xuid}
§7- {ColorFormat.YELLOW}UUID: {ColorFormat.WHITE}{uuid}
§7- {ColorFormat.YELLOW}Internal Rank: {ColorFormat.WHITE}{rank}
§7- {ColorFormat.YELLOW}Device OS: {ColorFormat.WHITE}{device}
§7- {ColorFormat.YELLOW}Client Version: {ColorFormat.WHITE}{version}
§7- {ColorFormat.YELLOW}Ping: {ColorFormat.WHITE}{ping}
§7- {ColorFormat.YELLOW}Last Join: {ColorFormat.WHITE}{join_time}
§7- {ColorFormat.YELLOW}Last Leave: {ColorFormat.WHITE}{leave_time_str}
""")

    return True


