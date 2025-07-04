from endstone import Player
from endstone.command import CommandSender
import psutil
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.configUtil import load_config
from endstone_primebds.utils.prefixUtil import infoLog, errorLog

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
        "/world (transfer)<world_transfer: world_transfer> <world_name: string> <player: player>",
        "/world (list)<world_list: world_list>"
     ],
    ["primebds.command.world"]
)

# WORLD COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    def send_feedback(message: str): # TO BE USED IN FUTURE CMD IMPLEMENTATIONS AND REFACTORS
        if isinstance(sender, Player):
            sender.send_message(infoLog() + message.replace("[PrimeBDS]", "").strip())
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

        process = self.multiworld_processes.get(world_name)

        if process is None:
            send_feedback(f"[PrimeBDS] World '{world_name}' is not loaded or not found.")
            return False

        try:
            process.stdin.write(f"{command_to_run}\n")
            process.stdin.flush()
            send_feedback(f"[PrimeBDS] Command sent to world '{world_name}': {command_to_run}")
            return True
        except Exception as e:
            send_feedback(f"[PrimeBDS] Failed to send command to world '{world_name}': {e}")
            return False

    elif subaction == "list":
        # List loaded worlds (keys in multiworld_processes)
        loaded_worlds = list(self.multiworld_processes.keys())
        if not loaded_worlds:
            send_feedback("[PrimeBDS] No additional worlds are currently loaded.")
        else:
            send_feedback(f"[PrimeBDS] Loaded worlds: {self.server.level.name}, {', '.join(loaded_worlds)}")
        return True
        
    elif subaction == "transfer":
        if len(args) < 3:
            send_feedback("[PrimeBDS] Usage: /world <world_name> transfer <player>")
            return False

        player_name = args[2]
        player = self.server.get_player(player_name)
        if player is None:
            send_feedback(f"[PrimeBDS] Player '{player_name}' not found.")
            return False

        config = load_config()
        multiworld = config["modules"].get("multiworld", {})
        worlds = multiworld.get("worlds", {})
        main_ip = multiworld.get("main_ip", "127.0.0.1")

        if world_name == self.server.level.name:
            ip = main_ip
            port = self.server.port
        else:
            target_world = None
            for key, data in worlds.items():
                if key == world_name or data.get("level-name") == world_name:
                    target_world = data
                    break

            if not target_world:
                send_feedback(f"[PrimeBDS] World '{world_name}' not found in configuration.")
                return False

            ip = target_world.get("ip", "127.0.0.1")
            port = target_world.get("server-port", 19132)

        try:
            player.transfer(ip, port)
            send_feedback(f"[PrimeBDS] Transferred player '{player_name}' to world '{world_name}' ({ip}:{port}).")
            return True
        except Exception as e:
            send_feedback(f"[PrimeBDS] Failed to transfer player '{player_name}': {e}")
            return False

    else:
        send_feedback(f"[PrimeBDS] Unknown subaction '{subaction}'.")
        return False
