from endstone.event import PlayerCommandEvent, ServerCommandEvent
from typing import TYPE_CHECKING

from endstone_primebds.handlers.chat import handle_mute_status
from endstone_primebds.utils.configUtil import load_config
from endstone_primebds.utils.dbUtil import UserDB
from endstone_primebds.utils.internalPermissionsUtil import check_internal_rank
from endstone_primebds.utils.loggingUtil import log, discordRelay
from endstone_primebds.commands import moderation_commands

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_command_preprocess(self: "PrimeBDS", event: PlayerCommandEvent):
    command = event.command
    player = event.player
    args = command.split()
    cmd = args[0].lstrip("/").lower() if args else ""
    config = load_config()
    db = UserDB("users.db")

    if config["modules"]["discord_logging"]["commands"]["enabled"]:
        discordRelay(f"**{player.name}** ran: {command}", "cmd")

    # Internal Permissions Handler
    if ((db.get_online_user(player.xuid).internal_rank == "Operator" and not player.has_permission("minecraft.kick")) or
            (db.get_online_user(player.xuid).internal_rank == "Default" and player.is_op) or not player.has_permission("primebds.command.refresh")):
        self.reload_custom_perms(player)

    if args and len(args) > 0 and cmd in moderation_commands \
            or (len(args) > 0 and cmd == "kick"): # Edge case for kick

        if cmd == "punishments" or "modspy":
            return True

        target = self.server.get_player(args[1])
        if target and self.server.get_player(target.name).is_op:
            if target.xuid != player.xuid: # Allow you to punish OR remove a punishment from yourself
                event.is_cancelled = True
                event.player.send_message(
                    f"Player §e{target.name} §6has higher permissions")
                return True

        elif target:
            target_user = db.get_online_user(target.xuid)
            sender = db.get_online_user(player.xuid)

            if target_user and sender:
                is_valid = check_internal_rank(target_user.internal_rank, sender.internal_rank)
                if is_valid and not player.is_op:
                    event.is_cancelled = True
                    event.player.send_message(f"Player §e{target.name} §6has higher permissions")

        elif not target:
            target_user = db.get_offline_user(args[1])
            sender = db.get_online_user(player.xuid)

            if target_user and sender:
                is_valid = check_internal_rank(target_user.internal_rank, sender.internal_rank)
                if is_valid and not player.is_op:
                    event.is_cancelled = True
                    event.player.send_message(
                        f"Player §e{target.name} §6has higher permissions")

    elif args and cmd == "ban" or cmd == "unban" or cmd == "pardon":
        player.send_message(f"Hardcoded Endstone Moderation Commands are disabled by primebds")
        event.is_cancelled = True
        return False
    elif args and cmd == "op":
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" operator")
        event.is_cancelled = True
        return False
    elif args and cmd == "deop":
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" default")
        event.is_cancelled = True
        return False

    # /me Crasher Fix
    abused_cmds = {"me", "tellraw", "tell", "w", "msg"}
    msg_cmds = {"tellraw", "tell", "w", "msg"}
    if cmd in abused_cmds and command.count("@e") >= 5:
        for perm in ["minecraft.command.me", "minecraft.command.tellraw", "minecraft.command.tell", "minecraft.command.w", "minecraft.command.msg"]:
            event.player.add_attachment(self, perm, False)
        event.is_cancelled = True

        # Log the staff message
        if config["modules"]["me_crasher_patch"]["enabled"]:
            if config["modules"]["me_crasher_patch"]["ban"]:
                self.server.dispatch_command(self.server.command_sender, f"tempban {player.name} 7 day Crasher Exploit")
            else:
                log(self, f"Player §e{player.name} §6was kicked due to §eCrasher Exploit", "mod")
                player.kick("Disconnected")

    # Social Spy
    if cmd in msg_cmds and args:

        if db.get_mod_log(player.xuid).is_muted:
            handle_mute_status(player)
            event.is_cancelled = True
            return True

        message = " ".join(args[2:])
        for pl in self.server.online_players:
            if int(db.get_online_user(pl.xuid).enabled_ss) == 1:
                pl.send_message(f"§8[§r{player.name} §7-> §r{args[1]}§8] §7{message}")

    db.close_connection()

def handle_server_command_preprocess(self: "PrimeBDS", event: ServerCommandEvent):
    command = event.command
    player = event.sender
    args = command.split()

    cmd = args[0].lstrip("/").lower() if args else ""

    if args and cmd == "ban" or cmd == "unban" or args[0].lstrip(
            "/").lower() == "pardon":
        player.send_message(f"Hardcoded Endstone Moderation Commands are disabled by primebds\nPlease use \"permban\" or \"removeban\"")
        event.is_cancelled = True
        return False
    elif args and cmd == "op":
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" operator")
        self.server.dispatch_command(self.server.command_sender, f"op \"{args[1]}\"")
        event.is_cancelled = True
        return False
    elif args and cmd == "deop":
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" default")
        self.server.dispatch_command(self.server.command_sender, f"drop \"{args[1]}\"")
        event.is_cancelled = True
        return False