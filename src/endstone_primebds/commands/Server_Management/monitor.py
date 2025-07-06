from endstone import Player, ColorFormat, Server
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.prefixUtil import infoLog, errorLog

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

    if specification.lower() == 'off':
        if sender.name in active_intervals:
            task_id = active_intervals[sender.name]
            self.server.scheduler.cancel_task(task_id)
            del active_intervals[sender.name]
            sender.send_message(f"{infoLog()}Monitoring has been turned off")
        else:
            sender.send_message(f"{infoLog()}No active monitoring found")
        return True

    if sender.name in active_intervals:
        task_id = active_intervals[sender.name]
        self.server.scheduler.cancel_task(task_id)
        del active_intervals[sender.name]

    time = int(args[1]) if len(args) > 1 else 1

    def monitor_interval():
        try:

            # If player has left, cleanup and exit
            if sender.name not in [p.name for p in self.server.online_players]:
                raise RuntimeError("Player has disconnected.")

            player = self.server.get_player(sender.name)
            if player is None:
                raise RuntimeError("Player has disconnected.")

            player_location = getattr(player, "location", None)
            player_dimension = getattr(player, "dimension", None)

            if not player_location or not player_dimension:
                raise RuntimeError("Player has no valid location or dimension.")

            dim_color = ColorFormat.GREEN
            tps = self.server.average_tps
            mspt = self.server.average_mspt
            mspt_cur = self.server.current_mspt
            tick_usage = self.server.average_tick_usage
            tps_display = int(tps)
            tps_fraction = int((tps - tps_display) * 10)
            entity_count = len(self.server.level.actors)
            server_version = self.server.minecraft_version
            overworld_chunks = len(self.server.level.get_dimension("Overworld").loaded_chunks)
            nether_chunks = len(self.server.level.get_dimension("Nether").loaded_chunks)
            the_end_chunks = len(self.server.level.get_dimension("TheEnd").loaded_chunks)

            nearest_chunk, player_chunk_x, player_chunk_z = get_nearest_chunk(player, self.server.level)
            is_laggy = check_entities_in_chunk(self, nearest_chunk.x, nearest_chunk.z)

            ping_color = get_ping_color(player.ping)

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

            chunk_lag_str = f"§aO" if not is_laggy else f"§cX"

            tps_str = f"{tps_color}{tps_display}.{tps_fraction:1d} {ColorFormat.ITALIC}{ColorFormat.GRAY}({tick_usage:.1f})"
            ping_str = f"{ping_color}{player.ping // 1}ms"
            mspt_str = f"{mspt_color}{mspt:.1f}ms {ColorFormat.ITALIC}{ColorFormat.GRAY}(avg) {ColorFormat.RESET}{ColorFormat.GRAY}| {mspt_cur_color}{mspt_cur:.1f}ms {ColorFormat.ITALIC}{ColorFormat.GRAY}(cur)"
            entity_str = f"{entity_color}{entity_count}"
            version_str = f"{ColorFormat.GREEN}{server_version}"
            chunk_str = f"{ColorFormat.GREEN}{overworld_chunks} {ColorFormat.GRAY}| {ColorFormat.RED}{nether_chunks} {ColorFormat.GRAY}| {ColorFormat.MATERIAL_IRON}{the_end_chunks}"
            your_chunk_str = f"{ColorFormat.GREEN}x={player_chunk_x}, z={player_chunk_z}"
            your_dim = f"{dim_color}{player.dimension.name}"

            player.send_tip(f"{ColorFormat.AQUA}Server Monitor{ColorFormat.RESET}\n"
                            f"{ColorFormat.RESET}---------------------------\n"
                            f"{ColorFormat.RESET}Level: {self.server.level.name} {ColorFormat.ITALIC}{ColorFormat.GRAY}(ver. {version_str}{ColorFormat.GRAY})\n"
                            f"{ColorFormat.RESET}TPS: {tps_str} {ColorFormat.RESET}\n"
                            f"{ColorFormat.RESET}MSPT: {mspt_str}\n"
                            f"{ColorFormat.RESET}Loaded Chunks: {chunk_str}\n"
                            f"{ColorFormat.RESET}Loaded Entities: {entity_str}\n"
                            f"{ColorFormat.RESET}---------------------------\n"
                            f"{ColorFormat.RESET}Your Ping: {ping_str}\n"
                            f"{ColorFormat.RESET}Current Chunk: {your_chunk_str}, {chunk_lag_str}\n"
                            f"{ColorFormat.RESET}Current DIM: {your_dim}")

            task_id = self.server.scheduler.run_task(
                self, monitor_interval, delay=time * 20
            )
            active_intervals[sender.name] = task_id.task_id

        except Exception as e:
            if sender.name in active_intervals:
                self.server.scheduler.cancel_task(active_intervals[sender.name])
                del active_intervals[sender.name]

    monitor_interval()
    sender.send_message(f"{infoLog()}Started monitoring on an interval of {time} seconds")
    return True

def get_ping_color(ping: int) -> str:
    """Returns the color formatting based on ping value."""
    return (
        ColorFormat.GREEN if ping <= 80 else
        ColorFormat.YELLOW if ping <= 160 else
        ColorFormat.RED
    )

def check_entities_in_chunk(self: "PrimeBDS", target_chunk_x: int, target_chunk_z: int) -> bool:
    """Checks the number of entities in a specific chunk and returns True if the count exceeds 400."""
    entity_count = 0

    for entity in self.server.level.actors:
        entity_chunk_x = entity.location.x // 16
        entity_chunk_z = entity.location.z // 16

        if entity_chunk_x == target_chunk_x and entity_chunk_z == target_chunk_z:
            entity_count += 1

    return entity_count > 400

def get_nearest_chunk(player: Player, level):
    player_chunk_x = int(player.location.x) // 16 if player.location and player.location.x is not None else 0
    player_chunk_z = int(player.location.z) // 16 if player.location and player.location.z is not None else 0

    loaded_chunks = level.get_dimension(player.dimension.name).loaded_chunks if level else []

    if not loaded_chunks:
        return 0, player_chunk_x, player_chunk_z  

    # Initialize closest chunk tracking
    closest_chunk = None
    min_distance_sq = float('inf')

    # Iterate through each loaded chunk
    for chunk in loaded_chunks:
        chunk_x, chunk_z = getattr(chunk, "x", 0), getattr(chunk, "z", 0) 

        # Compute squared Euclidean distance
        dx = chunk_x - player_chunk_x
        dz = chunk_z - player_chunk_z
        distance_sq = dx * dx + dz * dz

        # Check if this is the closest chunk so far
        if distance_sq < min_distance_sq:
            min_distance_sq = distance_sq
            closest_chunk = chunk

    # Default to chunk (0,0) if no valid chunk is found
    closest_chunk = closest_chunk or type("Chunk", (), {"x": 0, "z": 0})()

    return closest_chunk, player_chunk_x, player_chunk_z

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
