from collections import OrderedDict
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from endstone import ColorFormat, Player
from endstone.plugin import Plugin
from endstone.command import Command, CommandSender
import psutil

from endstone_primebds.commands import (
    preloaded_commands,
    preloaded_permissions,
    preloaded_handlers
)

from endstone_primebds.events.intervalChecks import interval_function, stop_interval
from endstone_primebds.commands.Server_Management.monitor import clear_all_intervals
from endstone_primebds.utils.configUtil import load_config

from endstone_primebds.utils.dbUtil import UserDB, grieflog
from endstone_primebds.utils.internalPermissionsUtil import get_permissions
from endstone_primebds.utils.prefixUtil import errorLog


def plugin_text():
    print(
        """

██████╗░██████╗░██╗███╗░░░███╗███████╗██████╗░██████╗░░██████╗
██╔══██╗██╔══██╗██║████╗░████║██╔════╝██╔══██╗██╔══██╗██╔════╝
██████╔╝██████╔╝██║██╔████╔██║█████╗░░██████╦╝██║░░██║╚█████╗░
██╔═══╝░██╔══██╗██║██║╚██╔╝██║██╔══╝░░██╔══██╗██║░░██║░╚═══██╗
██║░░░░░██║░░██║██║██║░╚═╝░██║███████╗██████╦╝██████╔╝██████╔╝
╚═╝░░░░░╚═╝░░╚═╝╚═╝╚═╝░░░░░╚═╝╚══════╝╚═════╝░╚═════╝░╚═════╝░                  

Prime BDS Loaded!
        """
    )

# EVENT IMPORTS
from endstone.event import (EventPriority, event_handler, PlayerLoginEvent, PlayerJoinEvent, PlayerQuitEvent,
                            ServerCommandEvent, PlayerCommandEvent, PlayerChatEvent, BlockBreakEvent, BlockPlaceEvent,
                            PlayerInteractEvent, ActorDamageEvent, ActorKnockbackEvent)
from endstone_primebds.events.chat_events import handle_chat_event
from endstone_primebds.events.command_processes import handle_command_preprocess, handle_server_command_preprocess
from endstone_primebds.events.player_connect import handle_login_event, handle_join_event, handle_leave_event
from endstone_primebds.events.grieflog_events import handle_block_break, handle_player_interact, handle_block_place
from endstone_primebds.events.player_combat import handle_kb_event, handle_damage_event


class PrimeBDS(Plugin):
    api_version = "0.6"
    authors = ["PrimeStrat", "trainer jeo"]
    name = "primebds"

    commands = preloaded_commands
    permissions = preloaded_permissions
    handlers = preloaded_handlers

    def __init__(self):
        super().__init__()
        self.multiworld_processes = {}
        self.entity_damage_cooldowns = {}

    # EVENT HANDLER
    @event_handler()
    def on_entity_hurt(self, ev: ActorDamageEvent):
        handle_damage_event(self, ev)

    @event_handler()
    def on_entity_kb(self, ev: ActorKnockbackEvent):
        handle_kb_event(self, ev)

    @event_handler()
    def on_player_login(self, ev: PlayerLoginEvent):
        handle_login_event(self, ev)

    @event_handler()
    def on_player_join(self, ev: PlayerJoinEvent):
        handle_join_event(self, ev)

    @event_handler()
    def on_player_quit(self, ev: PlayerQuitEvent):
        handle_leave_event(self, ev)

    @event_handler()
    def on_player_command_preprocess(self, ev: PlayerCommandEvent) -> None:
        handle_command_preprocess(self, ev)

    @event_handler()
    def on_player_server_command_preprocess(self, ev: ServerCommandEvent) -> None:
        handle_server_command_preprocess(self, ev)

    @event_handler(priority=EventPriority.HIGHEST)
    def on_player_chat(self, ev: PlayerChatEvent):
        handle_chat_event(self, ev)

    @event_handler()
    def on_block_break(self, ev: BlockBreakEvent):
        handle_block_break(self, ev)

    @event_handler()
    def on_block_place(self, ev: BlockPlaceEvent):
        handle_block_place(self, ev)

    @event_handler()
    def on_player_int(self, ev: PlayerInteractEvent):
        handle_player_interact(self, ev)

    def on_load(self):
        plugin_text()

    def on_enable(self):
        self.register_events(self)
        
        for player in self.server.online_players:
            self.reload_custom_perms(player)

        config = load_config()
        is_gl_enabled = config["modules"]["grieflog"]["enabled"]

        if is_gl_enabled:
            if config["modules"]["grieflog_storage_auto_delete"]["enabled"]:
                dbgl = grieflog("grieflog.db")
                dbgl.delete_logs_older_than_seconds(config["modules"]["grieflog_storage_auto_delete"]["removal_time_in_seconds"], True)
                dbgl.close_connection()

        if config["modules"]["check_prolonged_death_screen"]["enabled"] or config["modules"]["check_afk"]["enabled"]:
            if config["modules"]["check_prolonged_death_screen"]["enabled"]:
                print(f"[PrimeBDS] doimmediaterespawn gamerule is now set to true since prolonged deathscreen check is enabled")
            interval_function(self)

        self.check_for_inactive_sessions()

        if config["modules"]["multiworld"]["enabled"] and not self._is_nested_multiworld_instance():
            self.start_additional_servers()

    def on_disable(self):
        clear_all_intervals(self)
        stop_interval(self)

        config = load_config()
        if config["modules"]["multiworld"]["enabled"] and not self._is_nested_multiworld_instance():
            self.stop_additional_servers()

    def start_additional_servers(self):
        config = load_config()
        multiworld = config["modules"].get("multiworld", {})
        if not multiworld.get("enabled", False):
            return

        worlds = multiworld.get("worlds", OrderedDict())
        current_profile = config["modules"]["allowlist"].get("profile", "default")

        # Load default server.properties
        default_path = os.path.join("endstone_primebds", "utils", "default_server.properties")
        default_props = {}
        if os.path.isfile(default_path):
            with open(default_path, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, val = line.strip().split("=", 1)
                        default_props[key.strip()] = val.strip()

        # Find project root (where plugins/ and worlds/ exist)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                print("[PrimeBDS] Could not locate project root containing 'plugins' and 'worlds'.")
                return
            current_dir = parent_dir

        root_plugins_dir = os.path.join(current_dir, "plugins")
        root_bds_dir = current_dir  # This is where plugins/ and worlds/ exist, so also where those config files are

        # Setup multiworld directories
        DB_FOLDER = os.path.join(current_dir, 'plugins', 'primebds_data')
        os.makedirs(DB_FOLDER, exist_ok=True)

        multiworld_base_dir = os.path.join(DB_FOLDER, "multiworld")
        os.makedirs(multiworld_base_dir, exist_ok=True)

        for world_key, settings in worlds.items():
            if world_key == current_profile:
                continue

            world_dir = os.path.join(multiworld_base_dir, world_key)
            first_time_setup = not os.path.exists(os.path.join(world_dir, "server.properties"))

            if first_time_setup:
                os.makedirs(world_dir, exist_ok=True)

                # Initialize Endstone directly in the world folder
                process = subprocess.run(
                    [sys.executable, "-m", "endstone", "--yes", f"--server-folder={world_key}"],
                    cwd=multiworld_base_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                )

                if process.returncode != 0:
                    print(f"[PrimeBDS] Failed to initialize world '{world_key}' via endstone.")
                    print(process.stdout)
                    print(process.stderr)
                    continue

                time.sleep(1.5)

            # Merge default + config properties
            merged_props = default_props.copy()
            for key, value in settings.items():
                merged_props[key] = str(value).lower() if isinstance(value, bool) else str(value)

            server_properties_path = os.path.join(world_dir, "server.properties")
            with open(server_properties_path, "w", encoding="utf-8") as f:
                for key, value in merged_props.items():
                    f.write(f"{key}={value}\n")

            # Launch Endstone server from multiworld_base_dir but target folder explicitly
            process = subprocess.Popen(
                [sys.executable, "-m", "endstone", "--yes", f"--server-folder={world_key}"],
                cwd=multiworld_base_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            level_name = merged_props.get("level-name", world_key)
            self.multiworld_processes[level_name] = process

            def forward_output(stream, prefix):
                while True:
                    try:
                        line = stream.readline()
                        if not line:
                            break
                        print(f"{prefix}{line}", end='')
                    except Exception as e:
                        print(f"{prefix}[ReadError]: {e}")
                        break

            threading.Thread(target=forward_output, args=(process.stdout, f"[{level_name}] "), daemon=True).start()
            threading.Thread(target=forward_output, args=(process.stderr, f"[{level_name}][ERR] "), daemon=True).start()

            time.sleep(2)

    def stop_additional_servers(self):
        for name, process in self.multiworld_processes.items():
            if process.poll() is None:  # still running
                print(f"[PrimeBDS] Sending stop command to world '{name}' (PID {process.pid})")
                try:
                    process.stdin.write("stop")
                    process.stdin.flush()
                except Exception as e:
                    print(f"[PrimeBDS] Failed to send stop command to world '{name}': {e}")

                try:
                    process.wait(timeout=10)
                    print(f"[PrimeBDS] World '{name}' stopped gracefully.")
                except subprocess.TimeoutExpired:
                    print(f"[PrimeBDS] Timeout waiting for world '{name}' to stop, killing process tree.")
                    try:
                        parent = psutil.Process(process.pid)
                        children = parent.children(recursive=True)
                        for child in children:
                            child.kill()
                        parent.kill()
                    except psutil.NoSuchProcess:
                        pass
            else:
                print(f"[PrimeBDS] World '{name}' already exited.")

        self.multiworld_processes.clear()
    
    def _is_nested_multiworld_instance(self):
        return "plugins{}primebds_data{}multiworld".format(os.sep, os.sep) in os.path.abspath(__file__)

    def check_for_inactive_sessions(self):
        """Checks for players who have active sessions (NULL end_time) and are not online. Ends their session."""
        dbgl = grieflog("grieflog.db")

        # Fetch players with active sessions (where end_time is NULL)
        query = "SELECT xuid, name, start_time FROM sessions_log WHERE end_time IS NULL"
        dbgl.cursor.execute(query)
        active_sessions = dbgl.cursor.fetchall()

        MAX_SESSION_TIME = 10800  # 3 hours in seconds

        for session in active_sessions:
            xuid = session[0]
            player_name = session[1]
            start_time = session[2]

            # Check if the player is online
            player = self.server.get_player(player_name)
            if not player:  # If player is not online
                current_time = int(time.time())
                session_duration = current_time - start_time

                # If session exceeds 3 hours, cap it at 3 hours
                end_time = start_time + MAX_SESSION_TIME if session_duration > MAX_SESSION_TIME else current_time

                # End the session with the calculated end_time
                dbgl.end_session(xuid, end_time)
                print(
                    f"[PrimeBDS] Ended session for offline player {player_name} (XUID: {xuid}) with end_time: {end_time}")

        dbgl.close_connection()

    # PERMISSIONS HANDLER
    def reload_custom_perms(self, player: Player):
        # Update Internal DB
        db = UserDB("users.db")
        db.save_user(player)
        user = db.get_online_user(player.xuid)

        if player.has_permission("minecraft.kick"):
            db.update_user_data(player.name, 'internal_rank', "Operator")
        elif user.internal_rank == "Operator" and not player.has_permission("minecraft.kick"):
            db.update_user_data(player.name, 'internal_rank', "Default")

        permissions = get_permissions(user.internal_rank)

        # Reset Permissions
        perms = self.permissions
        for p in perms:
            player.add_attachment(self, p, False)

        # Apply Perms
        if "*" in permissions:
            for perm in perms:
                player.add_attachment(self, perm, True)
        else:
            for perm in permissions:
                player.add_attachment(self, perm, True)

        # Remove Overwritten Permissions
        player.add_attachment(self, "endstone.command.ban", False)
        player.add_attachment(self, "endstone.command.banip", False)
        player.add_attachment(self, "endstone.command.unban", False)
        player.add_attachment(self, "endstone.command.unbanip", False)
        player.add_attachment(self, "endstone.command.banlist", False)

        player.update_commands()
        player.recalculate_permissions()

        db.close_connection()

    # COMMAND HANDLER
    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        """Handle incoming commands dynamically."""
        try:
            if command.name in self.handlers:
                if any("@" in arg for arg in args):
                    sender.send_message(f"{errorLog()}Invalid argument: @ symbols are not allowed for managed commands.")
                    return False
                else:
                    handler_func = self.handlers[command.name]  # Get the handler function
                    return handler_func(self, sender, args)  # Execute the handler
            else:
                sender.send_message(f"{errorLog()}Command '{command.name}' not found.")
                return False
        except Exception as e:
            # Hide file paths by removing drive letters and usernames
            def clean_traceback(tb):
                cleaned_lines = []
                for line in tb.splitlines():
                    if 'File "' in line:
                        # Replace file paths with "<hidden>"
                        path_start = line.find('"') + 1
                        path_end = line.find('"', path_start)
                        file_path = line[path_start:path_end]
                        hidden_path = os.path.basename(file_path)
                        line = line.replace(file_path, f"<hidden>/{hidden_path}")
                    cleaned_lines.append(line)
                return "\n".join(cleaned_lines)

            # Generate the error message
            error_message = (
                    f"{ColorFormat.RED}========\n"
                    f"{ColorFormat.GOLD}This command generated an error -> please report this on our GitHub and provide a copy of the error below!\n"
                    f"{ColorFormat.RED}========\n\n"
                    f"{ColorFormat.YELLOW}{e}\n\n"
                    f"{ColorFormat.YELLOW}Command Usage: {ColorFormat.AQUA}{command.name} + {args}\n\n"
                    + f"{ColorFormat.YELLOW}{clean_traceback(traceback.format_exc())}\n"
                      f"{ColorFormat.RESET}"
            )
            error_message_console = (
                    f"========\n"
                    f"This command generated an error -> please report this on our GitHub and provide a copy of the error below!\n"
                    f"========\n\n"
                    f"{e}\n\n"
                    f"Command Usage: {command.name} + {args}\n\n"
                    + clean_traceback(traceback.format_exc())
            )

            sender.send_message(error_message)

            # Only log to console if the sender isn't the server itself
            if sender.name != "Server":
                print(error_message_console)

            return False