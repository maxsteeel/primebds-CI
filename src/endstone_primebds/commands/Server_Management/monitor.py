from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "monitor",
    "Monitor server performance in real time!",
    ["/monitor (on|off)[toggle: toggle] [time_in_seconds: int]"],
    ["primebds.command.monitor"]
)

# Dictionary to store active intervals for each player
active_intervals = {}

# MONITOR COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player")
        return True

    specification = args[0] if len(args) > 0 else "on"
    player_name = sender.name

    if specification.lower() == 'off':
        if player_name in self.monitor_intervals:
            self.server.scheduler.cancel_task(self.monitor_intervals[player_name])
            del self.monitor_intervals[player_name]
            sender.send_message("Monitoring has been turned off")
        else:
            sender.send_message("No active monitoring found")
        return True

    # Cancel existing monitor task if present
    if player_name in self.monitor_intervals:
        self.server.scheduler.cancel_task(self.monitor_intervals[player_name])
        del self.monitor_intervals[player_name]

    time = int(args[1]) if len(args) > 1 else 1

    def monitor_interval(player_name):
        try:
            # Get player reference once per tick
            player = self.server.get_player(player_name)
            if player is None:
                raise RuntimeError("Player has disconnected.")

            # Validate location & dimension
            if not getattr(player, "location", None) or not getattr(player, "dimension", None):
                raise RuntimeError("Player has no valid location or dimension.")

            # Cache dimension objects once per tick
            overworld = self.server.level.get_dimension("Overworld")
            nether = self.server.level.get_dimension("Nether")
            the_end = self.server.level.get_dimension("TheEnd")

            # Server stats
            tps = self.server.average_tps
            mspt = self.server.average_mspt
            mspt_cur = self.server.current_mspt
            tick_usage = self.server.average_tick_usage
            entity_count = len(self.server.level.actors)
            server_version = self.server.minecraft_version
            overworld_chunks = len(overworld.loaded_chunks) if overworld else 0
            nether_chunks = len(nether.loaded_chunks) if nether else 0
            the_end_chunks = len(the_end.loaded_chunks) if the_end else 0

            ping_color = get_ping_color(player.ping)

            tps_display = int(tps)
            tps_fraction = int((tps - tps_display) * 10)

            tps_color = (
                ColorFormat.GREEN if tps > 18 else
                ColorFormat.YELLOW if 14 <= tps <= 18 else
                ColorFormat.RED
            )

            mspt_color = ColorFormat.GREEN if mspt < 50 else ColorFormat.RED
            mspt_cur_color = ColorFormat.GREEN if mspt_cur < 50 else ColorFormat.RED

            entity_color = (
                ColorFormat.GREEN if entity_count < 600 else
                ColorFormat.YELLOW if entity_count <= 800 else
                ColorFormat.RED
            )

            dim_color = {
                "Overworld": ColorFormat.GREEN,
                "Nether": ColorFormat.RED,
                "TheEnd": ColorFormat.MATERIAL_IRON,
            }.get(player.dimension.name, ColorFormat.GRAY)

            tps_str = f"{tps_color}{tps_display}.{tps_fraction:1d} §o§7({tick_usage:.1f})"
            ping_str = f"{ping_color}{player.ping}ms"
            mspt_str = f"{mspt_color}{mspt:.1f}ms §o§7(avg) {ColorFormat.RESET}§7| {mspt_cur_color}{mspt_cur:.1f}ms §o§7(cur)"
            entity_str = f"{entity_color}{entity_count}"
            version_str = f"{ColorFormat.GREEN}{server_version}"
            chunk_str = f"{ColorFormat.GREEN}{overworld_chunks} §7| §c{nether_chunks} §7| {ColorFormat.MATERIAL_IRON}{the_end_chunks}"
            your_dim = f"{dim_color}{player.dimension.name}"

            player.send_tip(
                f"{ColorFormat.AQUA}Server Monitor{ColorFormat.RESET}\n"
                f"{ColorFormat.RESET}---------------------------\n"
                f"{ColorFormat.RESET}Level: {self.server.level.name} §o§7(ver. {version_str}§7)\n"
                f"{ColorFormat.RESET}TPS: {tps_str} {ColorFormat.RESET}\n"
                f"{ColorFormat.RESET}MSPT: {mspt_str}\n"
                f"{ColorFormat.RESET}Loaded Chunks: {chunk_str}\n"
                f"{ColorFormat.RESET}Loaded Entities: {entity_str}\n"
                f"{ColorFormat.RESET}---------------------------\n"
                f"{ColorFormat.RESET}Your Ping: {ping_str}\n"
                f"{ColorFormat.RESET}Current DIM: {your_dim}"
            )

        except Exception:
            # On error (disconnect etc), cancel monitoring
            if player_name in self.monitor_intervals:
                self.server.scheduler.cancel_task(self.monitor_intervals[player_name])
                del self.monitor_intervals[player_name]

    task = self.server.scheduler.run_task(
        self,
        lambda: monitor_interval(player_name),
        delay=0,
        period=time * 20
    )

    if task:
        self.monitor_intervals[player_name] = task.task_id
        sender.send_message(f"Started monitoring on an interval of {time} second(s)")
    else:
        sender.send_error_message("Failed to start monitoring task.")

    return True

def get_ping_color(ping: int) -> str:
    """Returns the color formatting based on ping value."""
    return (
        ColorFormat.GREEN if ping <= 80 else
        ColorFormat.YELLOW if ping <= 160 else
        ColorFormat.RED
    )

def clear_all_intervals(self: "PrimeBDS"):
    """Clear all active intervals."""
    global active_intervals
    for player_name, task_id in active_intervals.items():
        self.server.scheduler.cancel_task(task_id) 
    active_intervals.clear()

def clear_invalid_intervals(self: "PrimeBDS"):
    """Clear all active intervals for players who are no longer online or cannot be retrieved."""
    global active_intervals
    for player_name, task_id in list(active_intervals.items()):
        try:
            player_exists = any(player.name == player_name for player in self.server.online_players)
        except Exception:
            player_exists = False

        if not player_exists:
            self.server.scheduler.cancel_task(task_id)
            del active_intervals[player_name]
