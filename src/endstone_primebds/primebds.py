import os
import threading
import time
import traceback
from endstone import ColorFormat, Player
from endstone.plugin import Plugin
from endstone.command import Command, CommandSender

from endstone_primebds.commands import (
    preloaded_commands,
    preloaded_permissions,
    preloaded_handlers
)

from endstone_primebds.commands.Server_Management.monitor import clear_all_intervals
from endstone_primebds.utils.config_util import load_config
from endstone_primebds.utils.db_util import UserDB, grieflog
from endstone_primebds.utils.internal_permissions_util import load_perms, get_permissions, MANAGED_PERMISSIONS_LIST

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

# EVENT & HANDLER IMPORTS
from endstone.event import (EventPriority, event_handler, PlayerLoginEvent, PlayerJoinEvent, PlayerQuitEvent,
                            ServerCommandEvent, PlayerCommandEvent, PlayerChatEvent, BlockBreakEvent, BlockPlaceEvent,
                            PlayerInteractEvent, ActorDamageEvent, ActorKnockbackEvent, PacketSendEvent)
from endstone_primebds.handlers.chat import handle_chat_event
from endstone_primebds.handlers.preprocesses import handle_command_preprocess, handle_server_command_preprocess
from endstone_primebds.handlers.connections import handle_login_event, handle_join_event, handle_leave_event
from endstone_primebds.handlers.grieflog import handle_block_break, handle_player_interact, handle_block_place
from endstone_primebds.handlers.combat import handle_kb_event, handle_damage_event
from endstone_primebds.handlers.multiworld import start_additional_servers, stop_additional_servers, is_nested_multiworld_instance
from endstone_primebds.handlers.intervals import interval_function, stop_interval
from endstone_primebds.handlers.packets import handle_packetsend_event

class PrimeBDS(Plugin):
    api_version = "0.6"
    authors = ["PrimeStrat"]
    name = "primebds"

    commands = preloaded_commands
    permissions = preloaded_permissions
    handlers = preloaded_handlers

    def __init__(self):
        super().__init__()
        # Command Controls
        self.monitor_intervals = {}
        self.globalmute = 0

        # Multiworld Handler
        self.multiworld_processes = {}
        self.multiworld_ports = {}
        self.multiworld_lock = threading.Lock()

        # Combat Handler
        self.entity_damage_cooldowns = {}
        self.entity_last_hit = {}

        # DB
        self.db = UserDB("users.db")
        self.dbgl = grieflog("grieflog.db")

    # EVENT HANDLER
    @event_handler()
    def on_packet_send(self, ev: PacketSendEvent):
        handle_packetsend_event(self, ev)

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
        load_perms(self)

        self.db.migrate_user_table()
        
        for player in self.server.online_players:
            self.reload_custom_perms(player)

        config = load_config()
        is_gl_enabled = config["modules"]["grieflog"]["enabled"]

        if is_gl_enabled:
            if config["modules"]["grieflog_storage_auto_delete"]["enabled"]:
                self.dbgl.delete_logs_older_than_seconds(config["modules"]["grieflog_storage_auto_delete"]["removal_time_in_seconds"], True)

        if config["modules"]["check_prolonged_death_screen"]["enabled"] or config["modules"]["check_afk"]["enabled"]:
            interval_function(self)

        self.check_for_inactive_sessions()

        if config["modules"]["multiworld"]["enabled"] and not is_nested_multiworld_instance():
            start_additional_servers(self)
            return

    def on_disable(self):
        clear_all_intervals(self)
        stop_interval(self)
        self.db.close_connection()
        self.dbgl.close_connection()

        if not is_nested_multiworld_instance():
            stop_additional_servers(self)
            return

    def check_for_inactive_sessions(self):
        """Checks for players who have active sessions (NULL end_time) and are not online. Ends their session."""

        # Fetch players with active sessions (where end_time is NULL)
        query = "SELECT xuid, name, start_time FROM sessions_log WHERE end_time IS NULL"
        active_sessions = self.dbgl.execute(query).fetchall()

        MAX_SESSION_TIME = 10800  # 3 hours in seconds

        for xuid, player_name, start_time in active_sessions:
            # Check if the player is online
            player = self.server.get_player(player_name)
            if not player:  # If player is not online
                current_time = int(time.time())
                session_duration = current_time - start_time

                # If session exceeds 3 hours, cap it at 3 hours
                end_time = start_time + MAX_SESSION_TIME if session_duration > MAX_SESSION_TIME else current_time

                # End the session with the calculated end_time
                self.dbgl.end_session(xuid, end_time)
                print(
                    f"[PrimeBDS] Ended session for offline player {player_name} (XUID: {xuid}) with end_time: {end_time}"
                )

    def reload_custom_perms(self, player: Player):
        # Update Internal DB
        
        self.db.save_user(player)
        user = self.db.get_online_user(player.xuid)

        # Remove Overwritten Permissions
        player.add_attachment(self, "endstone.command.ban", False)
        player.add_attachment(self, "endstone.command.unban", False)
        player.add_attachment(self, "endstone.command.banip", False)
        player.add_attachment(self, "endstone.command.unbanip", False)
        player.add_attachment(self, "endstone.command.banlist", False)

        permissions = get_permissions(user.internal_rank)

        # Reset Permissions
        for p in MANAGED_PERMISSIONS_LIST:
            player.add_attachment(self, p, False)

        # Apply Perms
        #print(f"{player.name}'s perms: {permissions}") # DEBUG
        for perm in permissions:
            player.add_attachment(self, perm, True)

        player.update_commands()
        player.recalculate_permissions()

    def get_runtime_id(self, block_id: str) -> int:
        block_data = self.server.create_block_data(block_id)
        return block_data.runtime_id

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        """Handle incoming commands dynamically."""
        try:
            if command.name in self.handlers:
                if any("@e" in arg for arg in args):
                    sender.send_message(f"§cSelector must be player-type")
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
                    f"§c========\n"
                    f"§6This command generated an error -> please report this on our GitHub and provide a copy of the error below!\n"
                    f"§c========\n\n"
                    f"§e{e}\n\n"
                    f"§eCommand Usage: {ColorFormat.AQUA}{command.name} + {args}\n\n"
                    + f"§e{clean_traceback(traceback.format_exc())}\n"
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