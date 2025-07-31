import shlex
from endstone.event import PlayerCommandEvent, ServerCommandEvent
from typing import TYPE_CHECKING

from endstone_primebds.utils.config_util import load_config
from endstone_primebds.utils.internal_permissions_util import check_perms
from endstone_primebds.utils.logging_util import log, discordRelay

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_command_preprocess(self: "PrimeBDS", event: PlayerCommandEvent):
    command = event.command
    player = event.player

    try:
        args = shlex.split(command)
    except ValueError as e:
        player.send_message(f"§cInvalid command syntax: {e}")
        return True 
    except IndexError:
        player.send_message("§cInvalid command format")
        return True
        
    cmd = args[0].lstrip("/").lower() if args else ""
    config = load_config()

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
            return True
        
        target = self.db.get_offline_user(args[1])

        if any("@" in arg for arg in args) and cmd != "kick":
            event.player.send_message("§cTarget selectors are invalid for this command")
            event.is_cancelled = True
            return True

        if target is not None:
            if cmd == "kick" and check_perms(self, target, "primebds.kick.exempt"):
                event.player.send_message(f"§6Player §e{target.name} §6is exempt from being kicked")
                is_exempt = True

            elif cmd in {"mute", "tempmute"} and check_perms(self, target, "primebds.mute.exempt"):
                event.player.send_message(f"§6Player §e{target.name} §6is exempt from being muted")
                is_exempt = True

            elif cmd in {"permban", "tempban", "ipban", "ban"} and check_perms(self, target, "primebds.ban.exempt"):
                event.player.send_message(f"§6Player §e{target.name} §6is exempt from being banned")
                is_exempt = True

    if is_exempt:
        event.is_cancelled = True
        return True

    # Overrides
    if cmd == "ban":
        args[0] = "permban"
        player.perform_command(" ".join(args))
        event.is_cancelled = True
        return False
    elif cmd in {"unban", "pardon"}:
        args[0] = "removeban"
        player.perform_command(" ".join(args))
        event.is_cancelled = True
        return False
        
    if args and cmd == "op": # Override
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" operator")
        event.is_cancelled = True
        
        return False
    elif args and cmd == "deop": # Override
        self.server.dispatch_command(self.server.command_sender, f"setrank \"{args[1]}\" default")
        event.is_cancelled = True
        
        return False

    # /me Crasher Fix
    abused_cmds = {"me", "tellraw", "tell", "w", "whisper", "msg"}
    if cmd in abused_cmds and command.count("@e") >= 5:
        for perm in ["minecraft.command.me", "minecraft.command.tellraw", "minecraft.command.tell", "minecraft.command.w", "minecraft.command.msg"]:
            event.player.add_attachment(self, perm, False)
        event.is_cancelled = True

        # Log the staff message
        if config["modules"]["me_crasher_patch"]["enabled"]:
            if config["modules"]["me_crasher_patch"]["ban"]:
                self.server.dispatch_command(self.server.command_sender, f"tempban {player.name} 7 day Crasher Exploit")
                
                return False
            else:
                log(self, f"Player §e{player.name} §6was kicked due to §eCrasher Exploit", "mod")
                player.kick("Disconnected")
                
                return False

    # Social Spy
    if cmd in abused_cmds and len(args) > 1:
        if self.db.get_mod_log(player.xuid).is_muted:
            self.db.check_and_update_mute(player.xuid, player.name)
            event.is_cancelled = True
            
            return True

        message = " ".join(args[2:]) if len(args) > 2 else ""
        target = args[1]

        for pl in self.server.online_players:
            if self.db.get_online_user(pl.xuid).enabled_ss == 1:
                pl.send_message(f"§8[§r{player.name} §7-> §r{target}§8] §7{message}")

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