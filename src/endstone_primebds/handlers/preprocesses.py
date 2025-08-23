import shlex
from endstone.event import PlayerCommandEvent, ServerCommandEvent
from typing import TYPE_CHECKING

from endstone_primebds.utils.config_util import load_config
from endstone_primebds.utils.internal_permissions_util import check_perms
from endstone_primebds.utils.logging_util import log, discordRelay

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Move outside the function to avoid rebuilding every time
MODERATION_COMMANDS = {
    "kick", "ban", "pardon", "unban",
    "permban", "tempban", "tempmute",
    "mute", "ipban", "unmute", "warn",
    "ban-ip", "unban-ip", "banlist"
}
MSG_CMDS = {"me", "tell", "w", "whisper", "msg"}
PARSE_COMMANDS = (
    MODERATION_COMMANDS
    | MSG_CMDS
    | {"ban", "unban", "pardon", "op", "deop", "allowlist", "whitelist", "transfer"}
)

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
    if cmd not in PARSE_COMMANDS:
        return 
    
    config = load_config()

    if cmd in MSG_CMDS and command.count("@e") >= 5:
        if player.xuid not in self.crasher_patch_applied:
            for perm in [
                "minecraft.command.me", "minecraft.command.tellraw", "minecraft.command.tell",
                "minecraft.command.w", "minecraft.command.msg"
            ]:
                event.player.add_attachment(self, perm, False)

            self.crasher_patch_applied.add(player.xuid)

        event.is_cancelled = True

        if config["modules"]["me_crasher_patch"]["enabled"]:
            if config["modules"]["me_crasher_patch"]["ban"]:
                self.server.dispatch_command(
                    self.server.command_sender,
                    f"tempban {player.name} 7 day Crasher Exploit"
                )
            else:
                log(self, f"§6Player §e{player.name} §6was kicked due to §eCrasher Exploit", "mod")
                player.kick("Disconnected")
        return False
    
    if config["modules"]["discord_logging"]["commands"]["enabled"]:
        discordRelay(f"**{player.name}** ran: {command}", "cmd")

    player_db = self.db.get_online_user(player.xuid)
    player_perm = player.permission_level.name.lower()
    if player_perm == "default" and player_db.internal_rank.lower() == "operator":
        self.server.dispatch_command(self.server.command_sender, f"rank set \"{player.name}\" default")
        player.send_message("Permissions were manually changed and have been updated! Try again!")
        event.is_cancelled = True
        return True
    elif player_perm == "op" and player_db.internal_rank.lower() == "default":
        self.server.dispatch_command(self.server.command_sender, f"rank set \"{player.name}\" op")

    is_exempt = False
    if cmd in MODERATION_COMMANDS and len(args) >= 2 and "@" not in args[1]:
        target = self.db.get_offline_user(args[1])
        if target:
            if (
                (cmd == "jail" and check_perms(self, target, "primebds.exempt.jail")) or
                (cmd == "warn" and check_perms(self, target, "primebds.exempt.warn")) or
                (cmd == "kick" and check_perms(self, target, "primebds.exempt.kick")) or
                (cmd in {"mute", "tempmute"} and check_perms(self, target, "primebds.exempt.mute")) or
                (cmd in {"permban", "tempban", "ipban", "ban", "ban-ip"} and check_perms(self, target, "primebds.exempt.ban"))
            ):
                player.send_message(f"§6Player §e{target.name} §6is exempt from {cmd}")
                is_exempt = True
    if is_exempt:
        event.is_cancelled = True
        return True

    if cmd == "ban-ip" or cmd == "unban-ip" or cmd == "banlist":
        event.is_cancelled = True
        return False
    elif cmd == "ban" and len(args) > 1:
        player.perform_command(f'permban \"{args[1]}\"')
        event.is_cancelled = True
        return False
    elif cmd in {"unban", "pardon"} and len(args) > 1:
        player.perform_command(f'removeban \"{args[1]}\"')
        event.is_cancelled = True
        return False
    elif cmd == "op" and len(args) > 1:
        self.server.dispatch_command(self.server.command_sender, f"rank set \"{args[1]}\" operator")
        event.is_cancelled = True
        return False
    elif cmd == "deop" and len(args) > 1:
        self.server.dispatch_command(self.server.command_sender, f"rank set \"{args[1]}\" default")
        event.is_cancelled = True
        return False
    elif cmd in {"allowlist", "whitelist"} and len(args) > 1:
        sub = args[1]
        if sub in {"add", "remove"} and len(args) > 2:
            player.perform_command(f'alist {sub} \"{args[2]}\"')
        elif sub == "list":
            player.perform_command("alist list")
        elif sub in {"on", "off"}:
            player.send_message("Mojang has this feature disabled")
        event.is_cancelled = True
        return False
    elif cmd == "transfer" and len(args) > 2:
        port = args[3] if len(args) >= 4 else 19132
        player.perform_command(f"send \"{args[1]}\" {args[2]} {port}")
        event.is_cancelled = True
        return False

    if cmd in MSG_CMDS and len(args) > 1:
        if self.db.get_mod_log(player.xuid).is_muted == 1:
            self.db.check_and_update_mute(player.xuid, player.name)
            event.is_cancelled = True
            return True
        
        target = args[1]
        if "@" in target:
            player.send_message("§cTarget selectors are invalid for this command")
            event.is_cancelled = True
            return True
        
        if self.db.get_offline_user(target).enabled_mt == 0 and not player.has_permission("primebds.exempt.msgtoggle"):
            player.send_message("§cThis player has private messages disabled")
            event.is_cancelled = True
            return True

        message = " ".join(args[2:]) if len(args) > 2 else ""
        self.db.update_user_data(player.name, 'last_messaged', target)
        discordRelay(f"**{player.name} -> {target}**: {message}", "chat")

        for pl in self.server.online_players:
            if self.db.get_online_user(pl.xuid).enabled_ss == 1:
                pl.send_message(f"§8[§bSocial Spy§8] §8[§r{player.name} §7-> §r{target}§8] §7{message}")

def handle_server_command_preprocess(self: "PrimeBDS", event: ServerCommandEvent):
    args = event.command.split()
    if not args:
        return

    cmd = args[0].lstrip("/").lower()
    if cmd not in PARSE_COMMANDS:
        return 

    # Simple remap commands
    remap_commands = {
        "ban": lambda: ["permban"] + args[1:],
        "unban": lambda: ["removeban"] + args[1:],
        "pardon": lambda: ["removeban"] + args[1:],
        "op": lambda: ["rank", "set", f"\"{args[1]}\"", "operator"],
        "deop": lambda: ["rank", "set", f"\"{args[1]}\"", "default"],
    }

    # Allowlist/Whitelist handling
    allowlist_aliases = {"allowlist", "whitelist"}

    if cmd in remap_commands:
        new_args = remap_commands[cmd]()
        self.server.dispatch_command(self.server.command_sender, " ".join(new_args))
        event.is_cancelled = True
        return False

    if cmd in allowlist_aliases and len(args) > 1:
        if args[1] in {"add", "remove"} and len(args) > 2:
            self.server.dispatch_command(self.server.command_sender, f'alist {args[1]} \"{args[2]}\"')
        elif args[1] in {"on", "off", "list"}:
            self.server.dispatch_command(self.server.command_sender, f'alist {args[1]}')
        event.is_cancelled = True
        return False

    # Transfer command
    if cmd == "transfer" and len(args) >= 3:
        port = args[3] if len(args) >= 4 else 19132
        if "@s" not in args[0]:
            self.server.dispatch_command(self.server.command_sender, f"send \"{args[1]}\" {args[2]} {port}")
        event.is_cancelled = True
        return False
