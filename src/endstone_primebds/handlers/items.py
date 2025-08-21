from endstone.event import PlayerDropItemEvent, PlayerPickupItemEvent, PlayerItemConsumeEvent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_item_pickup_event(self: "PrimeBDS", ev: PlayerPickupItemEvent):
    user = self.db.get_online_user(ev.player.xuid)
    if user is not None and (getattr(user, "is_vanish", None) or getattr(user, "is_jailed", None)):
        ev.is_cancelled = True
    return

def handle_item_use(self: "PrimeBDS", ev: PlayerItemConsumeEvent):
    user = self.db.get_online_user(ev.player.xuid)
    if user is not None and (getattr(user, "is_jailed", None)):
        ev.is_cancelled = True
    return

def handle_item_drop_event(self: "PrimeBDS", ev: PlayerDropItemEvent):
    user = self.db.get_online_user(ev.player.xuid)
    if user is not None and (getattr(user, "is_jailed", None)):
        ev.is_cancelled = True
    return