from typing import TYPE_CHECKING
from endstone.event import ActorSpawnEvent, ActorRemoveEvent

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_spawn_event(self: "PrimeBDS", ev: ActorSpawnEvent):
    return

def handle_remove_event(self: "PrimeBDS", ev: ActorRemoveEvent):
    return