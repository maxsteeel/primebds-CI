from endstone.event import PlayerCommandEvent, ServerCommandEvent
from typing import TYPE_CHECKING

from endstone_primebds.handlers.chat import handle_mute_status
from endstone_primebds.utils.configUtil import load_config
from endstone_primebds.utils.dbUtil import UserDB
from endstone_primebds.utils.internalPermissionsUtil import check_perms
from endstone_primebds.utils.loggingUtil import log, discordRelay

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

    moderation_commands = {
        "kick", "ban", "pardon", "unban",
        "permban", "tempban", "tempmute",
        "mute", "ipban"
    }
    
    is_exempt = False
    if args and cmd in moderation_commands:
        if len(args) < 2:
            event.player.send_message("§cInvalid or missing target for this command.")
            event.is_cancelled = True
            db.close_connection()
            return True
        
        target = db.get_offline_user(args[1])

        if any("@" in arg for arg in args):
            event.player.send_message("§cTarget selectors are invalid for this command")
            event.is_cancelled = True
            db.close_connection()
            return True

        if target is not None:
            print(target.name)
            if cmd == "kick" and check_perms(target, "primebds.kick.exempt"):
                event.player.send_message(f"§6Player §e{target.name} §6is exempt from being kicked")
                is_exempt = True

            elif cmd in {"mute", "tempmute"} and check_perms(target, "primebds.mute.exempt"):
                event.player.send_message(f"§6Player §e{target.name} §6is exempt from being muted")
                is_exempt = True

            elif cmd in {"permban", "tempban", "ipban", "ban"} and check_perms(target, "primebds.ban.exempt"):
                event.player.send_message(f"§6Player §e{target.name} §6is exempt from being banned")
                is_exempt = True

    if is_exempt:
        event.is_cancelled = True
        db.close_connection()
        return True

    # Overrides
    if cmd == "ban":
        args[0] = "permban"
        player.perform_command(" ".join(args))
        event.is_cancelled = True
        db.close_connection()
        return False
    elif cmd in {"unban", "pardon"}:
        player.perform_command(" ".join(args))
        event.is_cancelled = True
        db.close_connection()
        return False
        
    if args and cmd == "op": # Override
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" operator")
        event.is_cancelled = True
        db.close_connection()
        return False
    elif args and cmd == "deop": # Override
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" default")
        event.is_cancelled = True
        db.close_connection()
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
                db.close_connection()
                return False
            else:
                log(self, f"Player §e{player.name} §6was kicked due to §eCrasher Exploit", "mod")
                player.kick("Disconnected")
                db.close_connection()
                return False

    # Social Spy
    if cmd in msg_cmds and args:
        if db.get_mod_log(player.xuid).is_muted:
            handle_mute_status(player)
            event.is_cancelled = True
            db.close_connection()
            return True

        message = " ".join(args[2:])
        for pl in self.server.online_players:
            if int(db.get_online_user(pl.xuid).enabled_ss) == 1:
                pl.send_message(f"§8[§r{player.name} §7-> §r{args[1]}§8] §7{message}")

    db.close_connection()

def handle_server_command_preprocess(self: "PrimeBDS", event: ServerCommandEvent):
    command = event.command
    args = command.split()

    cmd = args[0].lstrip("/").lower() if args else ""

    if args and cmd == "ban":
        args[0] = "permban"
        self.server.dispatch_command(self.server.command_sender, " ".join(args))
        event.is_cancelled = True
        return False
    elif args and (cmd == "unban" or cmd == "pardon"):
        args[0] = "removeban"
        self.server.dispatch_command(self.server.command_sender, " ".join(args))
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