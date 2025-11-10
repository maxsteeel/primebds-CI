from typing import TYPE_CHECKING

from endstone.event import (PlayerInteractActorEvent, PlayerEmoteEvent, LeavesDecayEvent, 
                            PlayerSkinChangeEvent, PlayerPickupItemEvent)

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_emote_event(self: "PrimeBDS", ev: PlayerEmoteEvent):
    #ev.is_cancelled = True
    return

def handle_interact_event(self: "PrimeBDS", ev: PlayerInteractActorEvent):
    #ev.is_cancelled = True
    return
