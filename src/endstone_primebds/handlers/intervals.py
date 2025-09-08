from endstone import GameMode
from endstone.level import Location

from endstone_primebds.utils.intervals_util import IntervalManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

import threading

def init_jail_intervals(self: "PrimeBDS"):
    """Initialize the jail interval system in a separate thread."""
    def worker():
        init_intervals(self)

    t = threading.Thread(target=worker, name="JailIntervalInit")
    t.start()

def init_intervals(self: "PrimeBDS"):
    """Actual interval setup, safe to run in its own thread."""
    setup_intervals(self)
    start_jail_check_if_needed(self)

def refresh_jail_cache(self: "PrimeBDS", player):
    """Update jail cache from DB only when needed."""
    is_jailed, is_expired = self.db.check_jailed(player.xuid)
    if is_jailed:
        mod_user = self.db.get_mod_log(player.xuid)
        self.jail_cache[player.xuid] = {
            "is_jailed": True,
            "is_expired": is_expired,
            "data": mod_user,
        }
    else:
        self.jail_cache[player.xuid] = {"is_jailed": False, "is_expired": False, "data": None}

def setup_intervals(self: "PrimeBDS"):
    """Prepare jail-check system, but don't start it until needed."""
    self.interval_manager = IntervalManager(self, tick_interval=20)
    self.interval_manager.add_check(check_jailed)

def start_jail_check_if_needed(self: "PrimeBDS"):
    """Run this on the main tick scheduler to avoid threading issues."""
    def main_thread_check():
        if any(self.db.check_jailed(p.xuid)[0] for p in self.server.online_players):
            if not getattr(self.interval_manager, "_task_id", None):
                self.interval_manager.start()
    self.server.scheduler.run_task(self, main_thread_check, 0)

def stop_jail_check_if_not_needed(self: "PrimeBDS"):
    """Stop interval if no online player is jailed."""
    if not any(self.db.check_jailed(p.xuid)[0] for p in self.server.online_players):
        if getattr(self.interval_manager, "_task_id", None):
            self.interval_manager.stop()

def check_jailed(self: "PrimeBDS"):
    """Handle players whose jail time has expired."""
    for player in self.server.online_players:
        try:
            cached = self.jail_cache.get(player.xuid)

            if not cached or (cached["is_jailed"] and cached["is_expired"]):
                refresh_jail_cache(player)
                cached = self.jail_cache[player.xuid]

            if cached["is_jailed"] and cached["is_expired"]:
                mod_user = cached["data"]

                x, y, z = map(float, mod_user.return_jail_pos.split(","))
                loc = Location(
                    self.server.level.get_dimension(mod_user.return_jail_dim),
                    x, y, z,
                    player.location.pitch,
                    player.location.yaw,
                )
                player.teleport(loc)
                player.game_mode = GameMode(int(mod_user.jail_gamemode))
                self.db.remove_jail(player.name)
                self.server.dispatch_command(
                    self.server.command_sender,
                    f'effect "{player.name}" clear saturation'
                )
                player.send_message("§6You were freed from jail, time expired!")

                self.db.load_inventory(player)
                self.jail_cache[player.xuid] = {"is_jailed": False, "is_expired": False, "data": None}

        except Exception as e:
            print(f"[PrimeBDS] Error handling player {getattr(player, 'name', 'Unknown')}: {e}")

        stop_jail_check_if_not_needed(self)

def stop_intervals(self: "PrimeBDS"):
    """Stop all periodic checks safely (on shutdown)."""
    if hasattr(self, "interval_manager"):
        self.interval_manager.stop()