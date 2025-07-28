import json
import os
import shutil
import time
from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.configUtil import find_and_load_config
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors
from endstone_primebds.utils.addressUtil import is_valid_ip, is_valid_port

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "world",
    "Manages PrimeBDS multiworld!",
    [
        "/world (delete)<world_subaction: world_subaction> <world_name: string> [erase_files: bool]",
        "/world (create)<world_action: world_action> <world_name: string> <ip: string> <port: int>",
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

    start_path = os.path.dirname(os.path.abspath(__file__))
    config = find_and_load_config("primebds_data/config.json", start_path)
    server_properties = find_and_load_config("server.properties", start_path)

    multiworld = config["modules"].get("multiworld", {})
    enabled = multiworld.get("enabled", False)
    if not enabled:
        send_feedback("[PrimeBDS] Multiworld is currently §cDisabled")
        return True

    if subaction == "cmd":
        if len(args) < 3:
            send_feedback("[PrimeBDS] Usage: /world <world_name> cmd <command>")
            return False

        command_to_run = " ".join(args[2:])

        if server_properties is None:
            send_feedback("[PrimeBDS] Unable to locate properties list")
            return False

        main_level = server_properties.get("level-name", "Unknown")

        if world_name == main_level.lower():
            try:
                self.server.dispatch_command(self.server.command_sender, command_to_run)
                return True
            except Exception as e:
                send_feedback(f"[PrimeBDS] Failed to execute command on primary world '{world_name}': {e}")
                return False

        if world_name not in self.multiworld_processes:
            if world_name.lower() == main_level.lower():
                send_feedback(f"[PrimeBDS] Commands can only be sent from the main world")
            else:
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
        targets = get_matching_actors(self, args[2], sender)

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

        for target in targets:
            try:
                target.transfer(ip, port)
                return True
            except Exception as e:
                send_feedback(f"[PrimeBDS] Failed to send player '{target.name}': {e}")
                return False

    elif subaction == "create":
        if len(args) < 4:
            send_feedback("[PrimeBDS] Usage: /world create <world_name> <ip> <port>")
            return False
        
        main_level = server_properties.get("level-name", "Unknown")
        if self.server.level.name != main_level:
            send_feedback(f"[PrimeBDS] Worlds can only be created from the main world")
            return False

        ip = args[2]
        port = args[3]

        if not is_valid_ip(ip):
            sender.send_message(f"Invalid IP address: {ip}")
            return False

        if not is_valid_port(port):
            sender.send_message(f"Invalid port number: {port}")
            return False

        if config is None:
            send_feedback("[PrimeBDS] Could not load config.json.")
            return False

        multiworld = config.setdefault("modules", {}).setdefault("multiworld", {})
        worlds = multiworld.setdefault("worlds", {})

        if world_name in worlds:
            send_feedback(f"[PrimeBDS] World '{world_name}' already exists in configuration.")
            return False

        current_dir = os.path.dirname(os.path.abspath(__file__))
        while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                send_feedback("[PrimeBDS] Could not locate project root containing 'plugins' and 'worlds'.")
                return False
            current_dir = parent_dir

        level_name = world_name
        world_props = {
            "ip": ip,
            "server-port": int(port),
            "server-portv6": int(port) + 1,
            "level-name": world_name,
            "server-name": "Dedicated Server",
            "gamemode": "survival",
            "difficulty": "easy",
            "default-player-permission-level": "member",
            "max-players": 10,
            "view-distance": 10,
            "tick-distance": 4,
            "max-threads": 8,
            "level-seed": "",
            "compression-threshold": 1,
            "texturepack-required": False,
            "allow-list": False,
            "allow-cheats": True
        }

        worlds[world_name] = world_props

        config_path = os.path.join(current_dir, "plugins", "primebds_data", "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            send_feedback(f"[PrimeBDS] Failed to write config.json: {e}")
            return False

        send_feedback(f"[PrimeBDS] World '{world_name}' registered with IP {ip}:{port}, please run §e/reload §rto restart worlds")
        return True

    elif subaction == "delete":
        if not world_name:
            send_feedback("[PrimeBDS] Usage: /world delete <world_name> [erase_files: bool]")
            return False
        
        main_level = server_properties.get("level-name", "Unknown")
        if self.server.level.name != main_level:
            send_feedback(f"[PrimeBDS] Worlds can only be deleted from the main world")
            return False

        erase_files = args[2].lower() == "true" if len(args) > 2 else False

        if config is None:
            send_feedback("[PrimeBDS] Could not load config.json.")
            return False

        multiworld = config.get("modules", {}).get("multiworld", {})
        worlds = multiworld.get("worlds", {})

        if world_name not in worlds:
            send_feedback(f"[PrimeBDS] World '{world_name}' not found in config")
            return False

        del worlds[world_name]

        current_dir = os.path.dirname(os.path.abspath(__file__))
        while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                send_feedback("[PrimeBDS] Could not locate project root containing 'plugins' and 'worlds'.")
                return False
            current_dir = parent_dir
            
        config_path = os.path.join(current_dir, "plugins", "primebds_data", "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            send_feedback(f"[PrimeBDS] Failed to update config.json: {e}")
            return False

        if erase_files:
            main_port = int(server_properties.get("server-port", 19132))
            main_ip = multiworld.get("ip_main", "127.0.0.1")
            process = self.multiworld_processes[world_name]
            if process.stdin:
                process.stdin.write(f"send @a {main_ip} {main_port}\n")
                process.stdin.write(f"stop\n")
                process.stdin.flush()
                time.sleep(5
                           )
            world_folder = os.path.join(current_dir, "plugins", "primebds_data", "multiworld", world_name)
            try:
                if os.path.isdir(world_folder):
                    shutil.rmtree(world_folder)
                    send_feedback(f"[PrimeBDS] World '{world_name}' files erased from disk")
                else:
                    send_feedback(f"[PrimeBDS] No folder found for world '{world_name}', config entry only deleted")
            except Exception as e:
                send_feedback(f"[PrimeBDS] Failed to delete world files: {e}")
                return False
        else:
            send_feedback(f"[PrimeBDS] World '{world_name}' removed from config only. Files kept.")

        return True

    else:
        send_feedback(f"[PrimeBDS] Unknown subaction '{subaction}'.")
        return False

