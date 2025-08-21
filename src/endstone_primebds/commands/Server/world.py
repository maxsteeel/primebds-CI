import json
import os
import shutil
import time
import socket
from endstone import Player
from endstone.command import CommandSender, BlockCommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.config_util import find_and_load_config, save_config, load_config
from endstone_primebds.utils.target_selector_util import get_matching_actors
from endstone_primebds.utils.address_util import is_valid_port

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "world",
    "Manages PrimeBDS multiworld!",
    [
        "/world (delete)<world_delete: world_delete> <world_name: string> [erase_files: bool]",
        "/world (create)<world_create: world_create> <world_name: string> <port: int>",
        "/world (config)<world_config: world_config> <world_name: string>",
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

    if isinstance(sender, BlockCommandSender):
        sender.send_message(f"§cThis command cannot be automated")
        return False

    subaction = args[0].lower() if len(args) > 0 else None
    world_name = args[1] if len(args) > 1 else None

    start_path = os.path.dirname(os.path.abspath(__file__))
    config = find_and_load_config("primebds_data/config.json", start_path)
    server_properties = find_and_load_config("server.properties", start_path)

    if subaction == "cmd":
        command_to_run = " ".join(args[2:])

        if server_properties is None:
            send_feedback("[PrimeBDS] Unable to locate properties list")
            return False

        main_level = server_properties.get("level-name", "Unknown")

        if world_name.lower() == main_level.lower():
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

        lines = []

        if server_properties.get("enabled", True):
            lines.append(f"§7- §a[+] §r{current_world} §o§8({main_port}) §r§a[current]§r")

        for world_key, world_data in worlds.items():
            port = world_data.get("server-port", 19132)
            level_name = world_data.get("level-name", world_key)
            is_current = level_name == current_world
            is_enabled = world_data.get("enabled", False)
            current_suffix = " §r§a[current]" if is_current else ""
            enabled_str = f"§a[+]" if is_enabled else f"§c[-]"
            lines.append(f"§7- {enabled_str} §r{level_name} §o§8({port}) {current_suffix}")

        send_feedback("[PrimeBDS] Worlds List:\n" + "\n".join(lines))
        return True

    elif subaction == "send":
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
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        # Determine target IP/port
        if world_name.lower() == main_world.lower():
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
            
            port = target_world.get("server-port", 19132)

        for target in targets:
            try:
                target.transfer(ip, port)
                return True
            except Exception as e:
                send_feedback(f"[PrimeBDS] Failed to send player '{target.name}': {e}")
                return False

    elif subaction == "create":
        main_level = server_properties.get("level-name", "Unknown")
        if self.server.level.name != main_level:
            send_feedback("[PrimeBDS] Worlds can only be created from the main world")
            return False

        port = args[2]
        if not is_valid_port(port):
            sender.send_message(f"Invalid port number: {port}")
            return False

        port = int(port)
        config = load_config()
        multiworld = config.setdefault("modules", {}).setdefault("multiworld", {})
        worlds = multiworld.setdefault("worlds", {})

        used_ports = {w.get("server-port") for w in worlds.values()}
        used_ports.update({w.get("server-portv6") for w in worlds.values()})
        main_ipv4 = int(server_properties.get("server-port", 19132))
        main_ipv6 = int(server_properties.get("server-portv6", 19133))
        used_ports.update({main_ipv4, main_ipv6})

        if port in used_ports:
            send_feedback(f"[PrimeBDS] Port {port} is already in use by another world.")
            return False

        port_v6 = port + 1
        while port_v6 in used_ports:
            port_v6 += 1
        used_ports.add(port_v6)

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

        world_props = {
            "enabled": True,
            "linked": False,
            "server-port": port,
            "server-portv6": port_v6,
            "level-name": world_name,
            "server-name": "Dedicated Server",
            "gamemode": "survival",
            "difficulty": "easy",
            "default-player-permission-level": "member",
            "max-players": 10,
            "view-distance": 12,
            "tick-distance": 4,
            "max-threads": 0,
            "level-seed": "",
            "compression-threshold": 30000,
            "texturepack-required": False,
            "allow-list": False,
            "allow-cheats": True
        }

        worlds[world_name] = world_props

        try:
            save_config(config, True)
        except Exception as e:
            send_feedback(f"[PrimeBDS] Failed to save configuration: {e}")
            return False

        send_feedback(f"[PrimeBDS] World '{world_name}' registered with PORT {port} (IPv6: {port_v6}), please run §e/reload §rto restart worlds")
        return True

    elif subaction == "delete":        
        main_level = server_properties.get("level-name", "Unknown")
        if self.server.level.name != main_level:
            send_feedback(f"[PrimeBDS] Worlds can only be deleted from the main world")
            return False

        erase_files = args[2].lower() == "true" if len(args) > 2 else False

        config = load_config()
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
            
        try:
            save_config(config, True)
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
            send_feedback(f"[PrimeBDS] World '{world_name}' removed from config only with files kept")

        return True

    else:
        send_feedback(f"[PrimeBDS] Unknown subaction '{subaction}'.")
        return False

