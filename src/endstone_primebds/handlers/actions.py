from typing import TYPE_CHECKING

from endstone.event import PlayerGameModeChangeEvent, PlayerInteractActorEvent

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_gamemode_event(self: "PrimeBDS", ev: PlayerGameModeChangeEvent):
    self.db.update_user_data(ev.player.name, "gamemode", ev.new_game_mode.value)

def handle_interact_event(self: "PrimeBDS", ev: PlayerInteractActorEvent):
    if self.db.get_mod_log(ev.player.xuid).is_jailed:
        ev.is_cancelled = True
