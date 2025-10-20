import time
from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from typing import TYPE_CHECKING

try:
    from bedrock_protocol.packets import MinecraftPacketIds
    PACKET_SUPPORT = True
except Exception as e:
    print(e)
    PACKET_SUPPORT = False

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Command registration
command, permission = create_command(
    "monitor",
    "Monitor server performance in real time!",
    ["/monitor (server|packets|disable)[debug: debug]"],
    ["primebds.command.monitor"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player")
        return True

    player_name = sender.name
    mode = args[0].lower() if args else "server"
    interval = 1.0

    if not hasattr(self, "monitor_intervals"):
        self.monitor_intervals = {}

    if player_name in self.monitor_intervals:
        self.server.scheduler.cancel_task(self.monitor_intervals[player_name])
        del self.monitor_intervals[player_name]

        if not args or args[0].lower() == "disable":
            if len(self.monitor_intervals) == 0:
                self.packets_sent_count.clear()
                self.packet_last_sample = {
                    "time": time.time(),
                    "counts": {}
                }
            sender.send_message("§cMonitoring turned off")
            return True

        sender.send_message("§ePrevious monitoring canceled, applying new settings...")

    if mode == "packets" and not PACKET_SUPPORT:
        return False
    else:
       PACKET_ID_TO_NAME = {
            v: k
            for k, v in MinecraftPacketIds.__dict__.items()
            if not k.startswith("__") and isinstance(v, int)
        }

    def monitor_interval(player_name, mode=mode):
        player = self.server.get_player(player_name)
        if not player:
            if player_name in self.monitor_intervals:
                self.server.scheduler.cancel_task(self.monitor_intervals[player_name])
                del self.monitor_intervals[player_name]
            return

        if mode == "server":
            overworld = self.server.level.get_dimension("Overworld")
            nether = self.server.level.get_dimension("Nether")
            the_end = self.server.level.get_dimension("TheEnd")

            tps = self.server.average_tps
            mspt = self.server.average_mspt
            mspt_cur = self.server.current_mspt
            tick_usage = self.server.average_tick_usage
            entity_count = len(self.server.level.actors)
            server_version = self.server.minecraft_version
            overworld_chunks = len(overworld.loaded_chunks) if overworld else 0
            nether_chunks = len(nether.loaded_chunks) if nether else 0
            the_end_chunks = len(the_end.loaded_chunks) if the_end else 0

            tps_display = int(tps)
            tps_fraction = int((tps - tps_display) * 10)
            tps_color = ColorFormat.GREEN if tps > 18 else ColorFormat.YELLOW if 14 <= tps <= 18 else ColorFormat.RED
            ping_color = get_ping_color(player.ping)
            mspt_color = ColorFormat.GREEN if mspt < 50 else ColorFormat.RED
            mspt_cur_color = ColorFormat.GREEN if mspt_cur < 50 else ColorFormat.RED
            entity_color = ColorFormat.GREEN if entity_count < 600 else ColorFormat.YELLOW if entity_count <= 800 else ColorFormat.RED
            dim_color = {"Overworld": ColorFormat.GREEN, "Nether": ColorFormat.RED, "TheEnd": ColorFormat.MATERIAL_IRON}.get(player.dimension.name, ColorFormat.GRAY)

            tps_str = f"{tps_color}{tps_display}.{tps_fraction:1d} §o§7({tick_usage:.1f})"
            ping_str = f"{ping_color}{player.ping}ms"
            mspt_str = f"{mspt_color}{mspt:.1f}ms §o§7(avg) §r§7| {mspt_cur_color}{mspt_cur:.1f}ms §o§7(cur)"
            entity_str = f"{entity_color}{entity_count}"
            version_str = f"§a{server_version}"
            chunk_str = f"§a{overworld_chunks} §7| §c{nether_chunks} §7| {ColorFormat.MATERIAL_IRON}{the_end_chunks}"
            your_dim = f"{dim_color}{player.dimension.name}"

            player.send_tip(
                f"§bServer Monitor§r\n"
                f"§r---------------------------\n"
                f"§rLevel: {self.server.level.name} §o§7(ver. {version_str}§7)\n"
                f"§rTPS: {tps_str} §r\n"
                f"§rMSPT: {mspt_str}\n"
                f"§rLoaded Chunks: {chunk_str}\n"
                f"§rLoaded Entities: {entity_str}\n"
                f"§r---------------------------\n"
                f"§rYour Ping: {ping_str}\n"
                f"§rCurrent DIM: {your_dim}"
            )

        elif mode == "packets":
            now = time.time()
            elapsed = now - self.packet_last_sample["time"]
            if elapsed <= 0:
                elapsed = 1

            lines = []
            for pid, count in self.packets_sent_count.items():
                prev = self.packet_last_sample["counts"].get(pid, 0)
                diff = count - prev
                pps = diff / elapsed

                if pps > 0: 
                    name = PACKET_ID_TO_NAME.get(pid, "Unknown")
                    lines.append(f"§r{name} §7({pid}): §a{pps:.1f} §7P/S")

            lines.sort(key=lambda l: float(l.split("§a")[1].split()[0]), reverse=True)
            if not lines:
                lines = ["No packets yet"]

            player.send_tip(
                f"§bPacket Monitor§r\n"
                f"§r-------------------\n"
                f"{chr(10).join(lines[:10])}\n"
                f"§r-------------------"
            )

            self.packet_last_sample = {
                "time": time.time(),
                "counts": {}
            }
            self.packets_sent_count.clear()

    task = self.server.scheduler.run_task(
        self,
        lambda: monitor_interval(player_name, mode),
        delay=0,
        period=int(interval * 20)
    )

    if task:
        self.monitor_intervals[player_name] = task.task_id
        sender.send_message(f"§aMonitoring turned on with {interval:.1f}s interval ({mode} mode)")
    else:
        sender.send_error_message("Failed to start monitoring task.")

    return True

def get_ping_color(ping: int) -> str:
    return ColorFormat.GREEN if ping <= 80 else ColorFormat.YELLOW if ping <= 160 else ColorFormat.RED

def clear_all_intervals(self: "PrimeBDS"):
    """Clear all active intervals."""
    for player_name, task_id in self.monitor_intervals.items():
        self.server.scheduler.cancel_task(task_id) 
    self.monitor_intervals.clear()
