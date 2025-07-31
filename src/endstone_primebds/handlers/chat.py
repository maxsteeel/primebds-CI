from typing import TYPE_CHECKING

from endstone.event import PlayerChatEvent
from endstone_primebds.utils.logging_util import discordRelay
from endstone_primebds.utils.internal_permissions_util import check_perms

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_chat_event(self: "PrimeBDS", ev: PlayerChatEvent):

    if self.globalmute == 1 and not check_perms(self, ev.player, "primebds.globalmute.exempt"):
        ev.player.send_message(f"§cGlobal chat is currently Disabled")
        ev.cancel() # Utilize until fix then switch to ev.is_cancelled = true
        return False

    if self.db.check_and_update_mute(ev.player.xuid, ev.player.name):
        ev.cancel() # Utilize until fix then switch to ev.is_cancelled = true
        return False
    
    discordRelay(f"**{ev.player.name}**: {ev.message}", "chat")
    return True

