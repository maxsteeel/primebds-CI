from typing import TYPE_CHECKING

from endstone.event import PlayerChatEvent
import endstone_primebds.utils.internal_permissions_util as perms_util
from endstone_primebds.utils.config_util import load_config
from endstone_primebds.utils.mod_util import format_time_remaining
from endstone_primebds.utils.logging_util import discordRelay

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_chat_event(self: "PrimeBDS", ev: PlayerChatEvent):
    
    user_muted = self.db.check_and_update_mute(ev.player.xuid, ev.player.name)
    ip_muted, ip_mute_time, ip_mute_reason = self.db.check_ip_mute(str(ev.player.address))
    if self.globalmute == 1 and not ev.player.has_permission("primebds.globalmute.exempt"):
        ev.player.send_message(f"§cGlobal chat is currently muted by an admin")
        ev.is_cancelled = True
        return False
    elif ev.player.xuid in self.silentmutes:
        ev.is_cancelled = True
        ev.player.send_message(f"§cYour chats are currently disabled")
        return False

    if user_muted or ip_muted:
        if user_muted:
            user_mod = self.db.get_mod_log(ev.player.xuid)
            ev.player.send_message(f"""§6You are currently muted.
§6Expires: §e{format_time_remaining(user_mod.mute_time)}
§6Reason: §e{user_mod.mute_reason}""")
        else:
            ev.player.send_message(f"""§6You are currently muted.
§6Expires: §e{format_time_remaining(ip_mute_time)}
§6Reason: §e{ip_mute_reason}""")
        ev.is_cancelled = True
        return False
    
    config = load_config()
    user = self.db.get_online_user(ev.player.xuid)
    if user.enabled_sc:
        message = f"{config["modules"]["server_messages"]["staff_chat_prefix"]}§e{ev.player.name}§7: §6{ev.message}"
        self.server.broadcast(message, "primebds.command.staffchat")
        ev.is_cancelled = True
        return False
    
    if config["modules"]["server_messages"]["enhanced_chat"]:
        prefix = perms_util.get_prefix(user.internal_rank, perms_util.PERMISSIONS)
        suffix = perms_util.get_suffix(user.internal_rank, perms_util.PERMISSIONS)
        message = f"{prefix}{ev.player.name_tag}{suffix}{config["modules"]["server_messages"]["chat_prefix"]}§r{ev.message}"
        ev.format = message

    discordRelay(f"**{ev.player.name}**: {ev.message}", "chat")

    return True

