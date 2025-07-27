import json
import os
from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.configUtil import find_and_load_config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "world",
    "Manages PrimeBDS multiworld!",
    [
        "/world (create|delete|load|unload)<world_subaction: world_subaction> <world_name: string>",
        "/world (cmd)<world_command: world_command> <world_name: string> <command: string>",
        "/world (send)<world_send: world_send> <world_name: string> <player: player>",
        "/world (list)<world_list: world_list>"
     ],
    ["primebds.command.world"]
)

# WORLD COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    def send_feedback(message: str):
        if isinstance(sender, Player):
            sender.send_message(message.replace("[PrimeBDS]", "").strip())
        else:
            print(message)

    subaction = args[0].lower() if len(args) > 0 else None
    world_name = args[1] if len(args) > 1 else None

    if subaction == "cmd":
        if len(args) < 3:
            send_feedback("[PrimeBDS] Usage: /world <world_name> cmd <command>")
            return False

        command_to_run = " ".join(args[2:])

        if world_name == self.server.level.name:
            try:
                self.server.dispatch_command(self.server.command_sender, command_to_run)
                send_feedback(f"[PrimeBDS] Command executed on primary world '{world_name}': {command_to_run}")
                return True
            except Exception as e:
                send_feedback(f"[PrimeBDS] Failed to execute command on primary world '{world_name}': {e}")
                return False

        if world_name not in self.multiworld_processes:
            send_feedback(f"[PrimeBDS] World '{world_name}' is not loaded or registered.")
            return False

        process = self.multiworld_processes[world_name]
        try:
            if process.stdin:
                process.stdin.write(f"{command_to_run}\n")
                process.stdin.flush()
                send_feedback(f"[PrimeBDS] Command sent to world '{world_name}': {command_to_run}")
                return True
            else:
                send_feedback(f"[PrimeBDS] Cannot send command: stdin not available for world '{world_name}'")
                return False
        except Exception as e:
            send_feedback(f"[PrimeBDS] Failed to send command to world '{world_name}': {e}")
            return False

    elif subaction == "list":

        start_path = os.path.dirname(os.path.abspath(__file__))
        config = find_and_load_config("primebds_data/config.json", start_path)
        server_properties = find_and_load_config("server.properties", start_path)

        if config is None or server_properties is None:
            send_feedback("[PrimeBDS] Unable to locate config list")
            return False

        main_port = int(server_properties.get("server-port", 19132))
        current_world = self.server.level.name

        multiworld = config["modules"].get("multiworld", {})
        worlds = multiworld.get("worlds", {})

        main_ip = multiworld.get("ip_main", "127.0.0.1")

        lines = []

        # Add the main server first
        if server_properties.get("level-name") == current_world:
            lines.append(f"§8- §r{current_world} §o§8({main_ip}:{main_port}) §r§a[current]§r")
        else:
            lines.append(f"§8- §r{server_properties.get('level-name', 'Unknown')} §o§8({main_ip}:{main_port})")

        # Add additional worlds
        for world_key, world_data in worlds.items():
            ip = world_data.get("ip", main_ip)
            port = world_data.get("server-port", 19132)
            level_name = world_data.get("level-name", world_key)

            if level_name == current_world:
                lines.append(f"§8- §r{level_name} §o§8({ip}:{port}) §r§a[current]§r")
            else:
                lines.append(f"§8- §r{level_name} §o§8({ip}:{port})")

        send_feedback("[PrimeBDS] Worlds List:\n" + "\n".join(lines))
        return True

    elif subaction == "send":
        if len(args) < 3:
            send_feedback("[PrimeBDS] Usage: /world <world_name> send <player>")
            return False

        world_name = args[1]
        player_name = args[2]

        # Load config and server.properties references
        start_path = os.path.dirname(os.path.abspath(__file__))
        config = find_and_load_config("primebds_data/config.json", start_path)
        server_properties = find_and_load_config("server.properties", start_path)

        if config is None or server_properties is None:
            send_feedback("[PrimeBDS] Unable to locate config list")
            return False

        # Main world IP and port defaults
        main_port = int(server_properties.get("server-port", 19132))
        main_world = server_properties.get("level-name", 19132)

        # Config overrides
        multiworld = config.get("modules", {}).get("multiworld", {})
        worlds = multiworld.get("worlds", {})
        main_ip = multiworld.get("main_ip", "127.0.0.1")

        player = self.server.get_player(player_name)
        if not player:
            send_feedback(f"Player '{player_name}' not found.")
            return False

        # Determine target IP/port
        if world_name.lower() == main_world.lower():
            ip = main_ip
            port = main_port
        else:
            target_world = worlds.get(world_name)

            if not target_world:
                # Try to match via level-name if key mismatch
                for key, data in worlds.items():
                    if data.get("level-name").lower() == world_name.lower():
                        target_world = data
                        break

            if not target_world:
                send_feedback(f"[PrimeBDS] World '{world_name.lower()}' not found in configuration.")
                return False

            ip = target_world.get("ip", main_ip)
            port = target_world.get("server-port", 19132)

        try:
            player.transfer(ip, port)
            send_feedback(f"[PrimeBDS] Sent player '{player.name}' to world '{world_name.lower()}' ({ip}:{port})")
            return True
        except Exception as e:
            send_feedback(f"[PrimeBDS] Failed to send player '{player.name}': {e}")
            return False

    else:
        send_feedback(f"[PrimeBDS] Unknown subaction '{subaction}'.")
        return False

