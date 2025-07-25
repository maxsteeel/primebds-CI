import json
import os
from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.configUtil import load_config

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
        result = find_main_files(start_path)
        config = result["config"]
        server_properties = result["server_properties"]

        main_port = int(server_properties.get("server-port", 19132))
        current_world = self.server.level.name

        config = load_config()
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
        result = find_main_files(start_path)
        config = result["config"]
        server_properties = result["server_properties"]

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

# Stupidly complex file searching system to find the right config.json path
def find_main_files(start_path=None):
    """
    Walks up the directory tree from start_path (or CWD) to find the topmost:
    - 'plugins/primebds_data/config.json'
    - '<root>/server.properties' (assumed just above plugins dir)
    
    Returns a dict:
        {
            "config": dict or None,
            "server_properties": dict or None,
        }
    """
    if start_path is None:
        start_path = os.getcwd()

    current_path = os.path.abspath(start_path)
    config_path = None

    while True:
        plugins_path = os.path.join(current_path, "plugins")
        candidate_config = os.path.join(plugins_path, "primebds_data", "config.json")

        if os.path.isfile(candidate_config):
            config_path = candidate_config 

        parent = os.path.dirname(current_path)
        if parent == current_path: 
            break

        current_path = parent

    config = None
    server_properties = None

    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[PrimeBDS] Failed to load config: {e}")

        root_dir = os.path.abspath(os.path.join(os.path.dirname(config_path), "..", ".."))
        candidate_properties = os.path.join(root_dir, "server.properties")

        if os.path.isfile(candidate_properties):
            server_properties = candidate_properties
            try:
                with open(candidate_properties, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if "=" in line and not line.strip().startswith("#")]
                    server_properties = dict(line.split("=", 1) for line in lines)
            except Exception as e:
                print(f"[PrimeBDS] Failed to load server.properties: {e}")

    return {
        "config": config,
        "server_properties": server_properties,
    }

