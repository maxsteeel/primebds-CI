import time
from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command

from endstone_primebds.utils.db_util import grieflog, UserDB
from endstone_primebds.utils.time_util import TimezoneUtils
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "activity",
    "Lists out session information!",
    ["/activity <player: player> [page: int]"],
    ["primebds.command.activity"]
)

SESSIONS_PER_PAGE = 5

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_message(f"This command can only be executed by a player")
        return False
        
    if len(args) < 1:
        sender.sendMessage(f" Usage: /activity <player> [page: int]")
        return True
    
    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    player_name = args[0]
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    if page < 1:
        page = 1

    xuid = self.db.get_xuid_by_name(player_name)

    if not xuid:
        sender.send_message(f"No session history found for {player_name}")
        return True

    # Fetch all user sessions
    sessions = self.dbgl.get_user_sessions(xuid)
    if not sessions:
        sender.send_message(f"No session history found for {player_name}")
        return True

    total_playtime_seconds = self.dbgl.get_total_playtime(xuid)
    sender.send_message(f" §rSession History for {player_name} (Page {page}):")

    playtime_str = format_time(total_playtime_seconds)
    sender.send_message(f" §eTotal Playtime: §f{playtime_str}")

    sessions.sort(key=lambda s: s['start_time'], reverse=True)

    active_session = None
    for session in sessions:
        if session['end_time'] is None:
            active_session = session
            sessions.remove(session)
            break

    # Display active session first (if applicable)
    if active_session:
        start_time = TimezoneUtils.convert_to_timezone(active_session['start_time'], 'EST')
        active_seconds = int(time.time() - active_session['start_time'])
        sender.send_message(f"§7- §a{start_time}§7 - §aActive Now §f(+{format_time(active_seconds)})")

    # Paginate session history
    total_pages = (len(sessions) + SESSIONS_PER_PAGE - 1) // SESSIONS_PER_PAGE
    start_idx = (page - 1) * SESSIONS_PER_PAGE
    end_idx = start_idx + SESSIONS_PER_PAGE
    paginated_sessions = sessions[start_idx:end_idx]

    for session in paginated_sessions:
        start_time = TimezoneUtils.convert_to_timezone(session['start_time'], 'EST')
        end_time = TimezoneUtils.convert_to_timezone(session['end_time'], 'EST')
        duration_text = f"§f({format_time(session['duration'])})"
        sender.send_message(f"§7- §a{start_time}§7 - §c{end_time} {duration_text}")

    if page < total_pages:
        sender.send_message(f"§7- §eUse '/activity {player_name} {page + 1}' for more.")

    
    return True

def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"