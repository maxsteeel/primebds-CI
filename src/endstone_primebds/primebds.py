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

from endstone_primebds.events.intervals import interval_function, stop_interval
from endstone_primebds.commands.Server_Management.monitor import clear_all_intervals
from endstone_primebds.utils.configUtil import load_config

from endstone_primebds.utils.dbUtil import UserDB, grieflog
from endstone_primebds.utils.internalPermissionsUtil import get_permissions


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
from endstone_primebds.events.chat import handle_chat_event
from endstone_primebds.events.commands import handle_command_preprocess, handle_server_command_preprocess
from endstone_primebds.events.connections import handle_login_event, handle_join_event, handle_leave_event
from endstone_primebds.events.grieflog import handle_block_break, handle_player_interact, handle_block_place
from endstone_primebds.events.combat import handle_kb_event, handle_damage_event

class PrimeBDS(Plugin):
    api_version = "0.6"
    authors = ["PrimeStrat", "trainer jeo"]
    name = "primebds"

    commands = preloaded_commands
    permissions = preloaded_permissions
    handlers = preloaded_handlers

    def __init__(self):
        super().__init__()
        self.monitor_intervals = {}
        self.multiworld_processes = {}
        self.multiworld_ports = {}
        self.entity_damage_cooldowns = {}
        self.entity_last_hit = {}

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
            return

    def on_disable(self):
        clear_all_intervals(self)
        stop_interval(self)

        config = load_config()
        if config["modules"]["multiworld"]["enabled"] and not self._is_nested_multiworld_instance():
            self.stop_additional_servers()
            return

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
            with open(default_path, "r", encoding="utf-8") as f:
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

        DB_FOLDER = os.path.join(current_dir, 'plugins', 'primebds_data')
        multiworld_base_dir = os.path.join(DB_FOLDER, "multiworld")

        # Setup multiworld directories
        os.makedirs(DB_FOLDER, exist_ok=True)
        os.makedirs(multiworld_base_dir, exist_ok=True)

        root_plugins_dir = os.path.join(current_dir, "plugins")
        seen_level_names = {}

        def launch_endstone_server(folder, level_name, max_retries=1):
            attempt = 0
            while attempt <= max_retries:

                process = subprocess.Popen(
                    [sys.executable, "-m", "endstone", "--yes", f"--server-folder={folder}"],
                    cwd=multiworld_base_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                time.sleep(5)
                if process.poll() is not None:
                    print(f"[PrimeBDS] World '{level_name}' crashed or exited early (attempt {attempt + 1}).")
                    attempt += 1
                else:
                    return process
            print(f"[PrimeBDS] World '{level_name}' failed to start after {max_retries + 1} attempts.")
            return None

        def stop_process_for_folder(folder_name):
            # Look for processes matching the folder (level_name)
            to_stop = []
            for level_name, proc in self.multiworld_processes.items():
                # You can match by exact level_name or some mapping from folder to level_name
                # Assuming level_name == folder_name or similar here:
                if level_name.startswith(folder_name):
                    to_stop.append(level_name)

            for level_name in to_stop:
                proc = self.multiworld_processes.get(level_name)
                if proc is None:
                    continue

                print(f"[PrimeBDS] Attempting to stop existing process for '{level_name}'")

                try:
                    # Attempt graceful stop by sending stop command
                    if proc.stdin:
                        proc.stdin.write("stop\n")
                        proc.stdin.flush()

                    # Wait up to 5 seconds for graceful exit
                    try:
                        proc.wait(timeout=5)
                        print(f"[PrimeBDS] Process for '{level_name}' stopped gracefully.")
                    except subprocess.TimeoutExpired:
                        print(f"[PrimeBDS] Process for '{level_name}' did not stop in time, killing...")
                        proc.kill()
                        proc.wait()
                        print(f"[PrimeBDS] Process for '{level_name}' killed.")
                except Exception as e:
                    print(f"[PrimeBDS] Error stopping process for '{level_name}': {e}")

                # Remove from tracking dict
                self.multiworld_processes.pop(level_name, None)
                self.multiworld_ports.pop(level_name, None)

        def copy_plugins_to_world(root_plugins_dir, world_plugins_dir):
            """
            Copy only .whl files from root_plugins_dir to world_plugins_dir,
            but only if no .whl file containing 'primebds' is already present in world_plugins_dir.
            """

            if not os.path.exists(world_plugins_dir):
                os.makedirs(world_plugins_dir, exist_ok=True)

            for item in os.listdir(root_plugins_dir):
                if not item.endswith(".whl"):
                    continue

                source_path = os.path.join(root_plugins_dir, item)
                target_path = os.path.join(world_plugins_dir, item)

                try:
                    shutil.copy2(source_path, target_path)
                except Exception as e:
                    print(f"[PrimeBDS] Failed to copy '{item}': {e}")

        for idx, (world_key, settings) in enumerate(worlds.items()):
            if world_key == current_profile:
                continue

            world_dir = os.path.join(multiworld_base_dir, world_key)
            os.makedirs(world_dir, exist_ok=True)
            stop_process_for_folder(world_dir)

            # Copy plugin wheels if needed
            world_plugins_dir = os.path.join(world_dir, "plugins")
            copy_plugins_to_world(root_plugins_dir, world_plugins_dir)

            # Write server.properties
            server_properties_path = os.path.join(world_dir, "server.properties")
            with open(server_properties_path, "w", encoding="utf-8") as f:
                for key, value in default_props.items():
                    f.write(f"{key}={value}\n")
                for key, value in settings.items():
                    value_str = str(value).lower() if isinstance(value, bool) else str(value)
                    f.write(f"{key}={value_str}\n")

            # Determine level name
            level_name = settings.get("level-name", world_key)
            original_level_name = level_name
            if level_name in seen_level_names:
                seen_level_names[level_name] += 1
                level_name = f"{original_level_name}_{seen_level_names[original_level_name]}"
            else:
                seen_level_names[level_name] = 0

            # Launch server
            process = launch_endstone_server(world_key, level_name, max_retries=3)
            if not process:
                continue

            self.multiworld_processes[level_name] = process

            # Assign proper port
            port_str = settings.get("server-port")
            try:
                port = int(port_str)
            except (TypeError, ValueError):
                port = self.base_port + idx + 1
                print(f"[PrimeBDS] Invalid or missing port for '{level_name}', using fallback: {port}")

            self.multiworld_ports[level_name] = port

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
        for level_name, process in list(self.multiworld_processes.items()):
            if process.poll() is None:  # still running
                print(f"[PrimeBDS] Closing '{level_name}' (PID {process.pid})")

                try:
                    # Attempt clean shutdown via stdin
                    if process.stdin:
                        try:
                            process.stdin.write("stop\n")
                            process.stdin.flush()
                        except Exception as e:
                            print(f"[PrimeBDS] Failed to send stop command to '{level_name}': {e}")

                    # Wait for graceful shutdown
                    process.wait(timeout=3)
                    print(f"[PrimeBDS] World '{level_name}' stopped correctly")
                except subprocess.TimeoutExpired:
                    # Force kill the process tree
                    try:
                        parent = psutil.Process(process.pid)
                        for child in parent.children(recursive=True):
                            try:
                                child.kill()
                            except psutil.NoSuchProcess:
                                pass
                        parent.kill()
                        print(f"[PrimeBDS] Killed process tree for world '{level_name}'.")
                    except psutil.NoSuchProcess:
                        print(f"[PrimeBDS] Process for world '{level_name}' already exited.")
                    except Exception as e:
                        print(f"[PrimeBDS] Error killing process tree for world '{level_name}': {e}")
            else:
                print(f"[PrimeBDS] World '{level_name}' already exited.")

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

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        """Handle incoming commands dynamically."""
        try:
            if command.name in self.handlers:
                if any("@" in arg for arg in args):
                    sender.send_message(f"Invalid argument: @ symbols are not allowed for managed commands.")
                    return False
                else:
                    handler_func = self.handlers[command.name]  # Get the handler function
                    return handler_func(self, sender, args)  # Execute the handler
            else:
                sender.send_message(f"Command '{command.name}' not found.")
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