from typing import TYPE_CHECKING

from endstone.event import PlayerGameModeChangeEvent, PlayerInteractActorEvent, PlayerTeleportEvent

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_gamemode_event(self: "PrimeBDS", ev: PlayerGameModeChangeEvent):
    self.db.update_user_data(ev.player.name, "gamemode", ev.new_game_mode.value)

def handle_teleport_event(self: "PrimeBDS", ev: PlayerTeleportEvent):
    return

def handle_interact_event(self: "PrimeBDS", ev: PlayerInteractActorEvent):
    if self.db.get_mod_log(ev.player.xuid).is_jailed:
        ev.is_cancelled = True
    elif not self.gamerules.get("can_interact", 1):
        ev.is_cancelled = True
