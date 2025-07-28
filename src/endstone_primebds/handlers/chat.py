from datetime import datetime
from typing import TYPE_CHECKING

from endstone import Player
from endstone.event import PlayerChatEvent
from endstone_primebds.utils.loggingUtil import discordRelay
from endstone_primebds.utils.dbUtil import UserDB
from endstone_primebds.utils.modUtil import format_time_remaining

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_chat_event(self: "PrimeBDS", ev: PlayerChatEvent):
    if not handle_mute_status(ev.player):
        ev.cancel() # Utilize until fix then switch to ev.is_cancelled = true
        return False


    
    discordRelay(f"**{ev.player.name}**: {ev.message}", "chat")
    return True

def handle_mute_status(player: Player) -> bool:
    mute_data = load_mute_from_db(player.xuid)
    if not mute_data or not mute_data["is_muted"]:
        return True  # Not muted

    if not mute_data["is_permanent"] and mute_data["mute_time"] < datetime.now().timestamp():
        remove_expired_mute(player.name)
        return True

    reason = mute_data["reason"]
    if mute_data["is_permanent"]:
        player.send_message(f"§6You are permanently muted for §e{reason}")
    else:
        remaining = format_time_remaining(mute_data["mute_time"])
        if remaining == "":
            remaining = "0 seconds"
        player.send_message(f"§6You are muted for §e\"{reason}\" §6which expires in §e{remaining}")
    return False

def load_mute_from_db(xuid):
    """Fetch mute data directly from the database."""
    db = UserDB("users.db")
    mod_log = db.get_mod_log(xuid)
    db.close_connection()

    if not mod_log or not mod_log.is_muted:
        return None

    return {
        "is_muted": mod_log.is_muted,
        "reason": mod_log.mute_reason,
        "mute_time": mod_log.mute_time,
        "is_permanent": mod_log.mute_time > (datetime.now().timestamp() + (10 * 365 * 24 * 60 * 60))  # 10 years
    }

def remove_expired_mute(player_name):
    """Remove expired mute from the database."""
    db = UserDB("users.db")
    db.remove_mute(player_name)
    db.close_connection()
