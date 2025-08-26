import os
import threading
import time
import traceback
from endstone import Player
from endstone.plugin import Plugin
from endstone.command import Command, CommandSender

from endstone_primebds.commands import (
    preloaded_commands,
    preloaded_permissions,
    preloaded_handlers
)

from endstone_primebds.commands.Server.monitor import clear_all_intervals
from endstone_primebds.utils.config_util import load_config
from endstone_primebds.utils.db_util import UserDB, sessionDB, ServerDB, User, ModLog, ServerData
from endstone_primebds.utils.internal_permissions_util import check_rank_exists, load_perms, get_rank_permissions, invalidate_perm_cache, MANAGED_PERMISSIONS_LIST

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
                            ServerCommandEvent, PlayerCommandEvent, PlayerChatEvent, ActorDamageEvent, ActorKnockbackEvent, PacketSendEvent, PlayerPickupItemEvent, 
                            PlayerGameModeChangeEvent, PlayerInteractActorEvent, PlayerDropItemEvent, PlayerItemConsumeEvent, 
                            PacketReceiveEvent, ServerLoadEvent)
from endstone_primebds.handlers.chat import handle_chat_event
from endstone_primebds.handlers.preprocesses import handle_command_preprocess, handle_server_command_preprocess
from endstone_primebds.handlers.connections import handle_login_event, handle_join_event, handle_leave_event
from endstone_primebds.handlers.combat import handle_kb_event, handle_damage_event
from endstone_primebds.handlers.multiworld import start_additional_servers, stop_additional_servers, is_nested_multiworld_instance
from endstone_primebds.handlers.intervals import stop_intervals, init_jail_intervals
from endstone_primebds.handlers.packets import handle_packetsend_event, handle_packetreceive_event
from endstone_primebds.handlers.actions import handle_gamemode_event, handle_interact_event
from endstone_primebds.handlers.items import handle_item_pickup_event, handle_item_use, handle_item_drop_event

class PrimeBDS(Plugin):
    api_version = "0.6"
    authors = ["PrimeStrat"]
    name = "primebds"
    description = "An essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition."
    website = "https://github.com/PrimeStrat/primebds"

    commands = preloaded_commands
    permissions = preloaded_permissions
    handlers = preloaded_handlers

    def __init__(self):
        super().__init__()
        # Command Controls
        self.monitor_intervals = {}
        self.globalmute = 0
        self.crasher_patch_applied = set()

        # Multiworld Handler
        self.multiworld_processes = {}
        self.multiworld_ports = {}
        self.multiworld_lock = threading.Lock()

        # Combat Handler
        self.entity_damage_cooldowns = {}
        self.entity_last_hit = {}

        # DB
        self.db = UserDB("users.db")
        self.sldb = sessionDB("sessionlog.db")
        self.serverdb = ServerDB("server.db")

    # EVENT HANDLER
    @event_handler
    def on_player_gamemode(self, ev: PlayerGameModeChangeEvent):
        handle_gamemode_event(self, ev)

    @event_handler
    def on_player_interact(self, ev: PlayerInteractActorEvent):
        handle_interact_event(self, ev)

    @event_handler()
    def on_packet_send(self, ev: PacketSendEvent):
        handle_packetsend_event(self, ev)

    @event_handler()
    def on_packet_receive(self, ev: PacketReceiveEvent):
        handle_packetreceive_event(self, ev)

    @event_handler()
    def on_item_use(self, ev: PlayerItemConsumeEvent):
        handle_item_use(self, ev)

    @event_handler()
    def on_item_pickup(self, ev: PlayerPickupItemEvent):
        handle_item_pickup_event(self, ev)

    @event_handler()
    def on_item_drop(self, ev: PlayerDropItemEvent):
        handle_item_drop_event(self, ev)

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
    def on_server_load(self, ev: ServerLoadEvent):
        load_perms(self)
        for player in self.server.online_players:
            self.reload_custom_perms(player)

    def on_load(self):
        plugin_text()

    def on_enable(self):
        self.register_events(self)
        self.db.migrate_table("users", User)
        self.db.migrate_table("mod_logs", ModLog)
        self.serverdb.migrate_table("server_info", ServerData)

        load_config()

        init_jail_intervals(self)
        last_shutdown_time = self.serverdb.get_server_info().last_shutdown_time
        self.last_shutdown_time = last_shutdown_time 

        if not self.serverdb.get_server_info().allowlist_profile:
            self.serverdb.update_server_info("allowlist_profile", "default")

        self.check_for_inactive_sessions()
        self.server.scheduler.run_task(self, start_additional_servers(self), 1)

    def on_disable(self):
        stop_intervals(self)
        clear_all_intervals(self)
        self.db.close_connection()
        self.sldb.close_connection()

        self.serverdb.update_server_info("last_shutdown_time", int(time.time()))
        self.serverdb.close_connection()

        if not is_nested_multiworld_instance():
            stop_additional_servers(self)
            return

    def check_for_inactive_sessions(self):
        current_time = int(time.time())
        RELOAD_THRESHOLD = 60  # seconds
        MAX_SESSION_LENGTH = 4 * 3600  # 4 hours max session length

        was_quick_reload = (
            self.last_shutdown_time
            and current_time - self.last_shutdown_time <= RELOAD_THRESHOLD
        )

        query = "SELECT xuid, name, start_time FROM sessions_log WHERE end_time IS NULL"
        active_sessions = self.sldb.execute(query).fetchall()

        for xuid, player_name, start_time in active_sessions:
            player = self.server.get_player(player_name)
            if not player and not was_quick_reload:
                candidate_end = None
                if self.last_shutdown_time and self.last_shutdown_time > start_time:
                    candidate_end = self.last_shutdown_time
                else:
                    candidate_end = current_time

                max_allowed_end = start_time + MAX_SESSION_LENGTH
                if candidate_end > max_allowed_end:
                    candidate_end = max_allowed_end

                self.sldb.end_session(xuid, candidate_end)

    def reload_custom_perms(self, player: Player):
        user = self.db.get_online_user(player.xuid)
        if not user:
            return

        internal_rank = check_rank_exists(self, player, user.internal_rank)

        permissions = get_rank_permissions(internal_rank)
        user_permissions = self.db.get_permissions(player.xuid)
        managed_perms = MANAGED_PERMISSIONS_LIST[:]

        final_permissions = {rperm: False for rperm in managed_perms}
        for perm, allowed in permissions.items():
            final_permissions[perm] = allowed
        for perm, allowed in user_permissions.items():
            final_permissions[perm] = allowed

        to_remove = [attinfo.attachment for attinfo in player.effective_permissions
             if attinfo.permission == "primebdsoverride"]
        
        for attachment in to_remove:
            attachment.remove()

        perms_to_apply = list(final_permissions.items())
        attachment = player.add_attachment(self, "primebdsoverride", True)

        plugin_stars = {}
        internal = {"minecraft", "minecraft.command", "endstone", "endstone.command"}
        for plugin in self.server.plugin_manager.plugins:
            if plugin.is_enabled:
                for perm, value in perms_to_apply:
                    if perm in internal:
                        continue
                    prefix = perm.split(".")[0]
                    cmd = f"{prefix}.command"
                    if prefix == perm or cmd == perm:
                        plugin_stars[prefix] = value
                        
        for perm, value in perms_to_apply:
            if perm in internal:
                continue

            prefix = perm.split(".")[0]
            if prefix in plugin_stars:
                attachment.set_permission(perm, plugin_stars[prefix])
            else:
                attachment.set_permission(perm, value)

        config = load_config()
        modules = config.get("modules", {})
        perms_manager = modules.get("permissions_manager", {})
        endstone_enabled = perms_manager.get("endstone", True)
        if endstone_enabled:
            player.add_attachment(self, "endstone.command.banip", False)
            player.add_attachment(self, "endstone.command.unbanip", False)
            player.add_attachment(self, "endstone.command.banlist", False)
        player.update_commands()
        player.recalculate_permissions()
        invalidate_perm_cache(self, player.xuid)

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        """Handle incoming commands dynamically"""
        try:
            if command.name in self.handlers:
                if any(arg.find("@e") != -1 or arg.find("@n") != -1 for arg in args):
                    sender.send_message("§cSelector must be player-type")
                    return False
                else:
                    handler_func = self.handlers[command.name]
                    return handler_func(self, sender, args)
            else:
                sender.send_message(f"Command '{command.name}' not found")
                return False

        except Exception as e:
            def clean_traceback(tb):
                cleaned_lines = []
                for line in tb.splitlines():
                    if 'File "' in line:
                        path_start = line.find('"') + 1
                        path_end = line.find('"', path_start)
                        file_path = line[path_start:path_end]
                        hidden_path = os.path.basename(file_path)
                        line = line.replace(file_path, f"<hidden>/{hidden_path}")
                    cleaned_lines.append(line)
                return "\n".join(cleaned_lines)

            error_message = (
                f"§c========\n"
                f"§6This command generated an error -> please report this on our GitHub and provide a copy of the error below!\n"
                f"§c========\n\n"
                f"§e{e}\n\n"
                f"§eCommand Usage: §b{command.name} + {args}\n\n"
                + f"§e{clean_traceback(traceback.format_exc())}\n"
                  f"§r"
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

            if sender.name != "Server":
                print(error_message_console)

            return False