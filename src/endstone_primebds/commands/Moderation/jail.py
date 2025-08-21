from endstone.command import CommandSender, BlockCommandSender
from endstone_primebds.utils.command_util import create_command
from endstone import GameMode
from endstone.inventory import ItemStack

from endstone_primebds.handlers.intervals import start_jail_check_if_needed
from endstone_primebds.utils.logging_util import log
from endstone_primebds.utils.mod_util import format_time_remaining, safe_duration
from datetime import timedelta, datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "jail",
    "Jails a player to a specified area!",
    [
        "/jail <player: player> <jail: string> <duration_number: int> (second|minute|hour|day|week|month|year)<duration_length: jail_length> [reason: message]",
        "/jail <player: player> <jail: string> (forever)<perm_jail: perm_jail> [reason: message]"
    ],
    ["primebds.command.jail"]
)

# JAIL COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, BlockCommandSender):
        sender.send_message(f"§cThis command cannot be automated")
        return False

    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False
    
    target_jail = args[1]
    jail = self.serverdata.get_jail(target_jail, self.server)

    if jail == None:
        sender.send_message(f"§6Jail §e\"{target_jail}\" §6does not exist")
        return False

    player_name = args[0].strip('"')
    target = self.server.get_player(player_name)

    if target:
        if self.db.get_mod_log(target.xuid).is_jailed:
            sender.send_message(f"§6Player §e{player_name} §cis already jailed")
            return False
    else:
        mod_log = self.db.get_offline_mod_log(player_name)
        if mod_log and mod_log.is_jailed:
            sender.send_message(f"§6Player §e{player_name} §cis already jailed")
            return False

        if not mod_log:
            sender.send_message(f"§6Player '{player_name}' not found")
            return False

    reason = "Negative Behavior"
    permanent = args[2].lower() == "forever"

    if permanent:
        jail_expiration = datetime.now() + timedelta(days=365 * 200)
        reason = " ".join(args[4:]) if len(args) > 3 else reason
    else:
        if len(args) < 3:
            sender.send_message(f"Invalid duration format. Use an integer followed by a time unit")
            return False

        try:
            duration_number = int(args[2])

            if duration_number < 0:
                sender.send_message(f"§6Duration must be a positive number")
                return False

            duration_unit = args[3].lower()
        except ValueError:
            sender.send_message(f"Invalid duration format. Use an integer followed by a time unit")
            return False

        # Supported time units
        time_units = {
            "second": timedelta(seconds=duration_number),
            "minute": timedelta(minutes=duration_number),
            "hour": timedelta(hours=duration_number),
            "day": timedelta(days=duration_number),
            "week": timedelta(weeks=duration_number),
            "month": timedelta(days=30 * duration_number),  # Approximation
            "year": timedelta(days=361 * duration_number)  # Approximation
        }

        if duration_unit not in time_units:
            sender.send_message(f"Invalid time unit. Use: second, minute, hour, day, week, month, year")
            return False

        jail_duration = safe_duration(time_units[duration_unit].total_seconds())
        jail_expiration = datetime.now() + jail_duration
        reason = " ".join(args[4:]) if len(args) > 4 else reason

    # Convert datetime to timestamp for format_time_remaining
    formatted_expiration = "Never" if permanent else format_time_remaining(int(jail_expiration.timestamp()))
    target_user = target if target else self.db.get_offline_mod_log(player_name)
    target_data = self.db.get_offline_user(player_name)

    if not target_user or not target_data:
        sender.send_message(f"Could not retrieve user '{player_name}'")
        return False

    if target:
        xuid = target.xuid
        jail_pos = target.location
        jail_dim = target.dimension.name
        gamemode = target.game_mode.value
    else:  
        offline_log = self.db.get_offline_mod_log(player_name)
        offline_data = self.db.get_offline_user(player_name)
        if not offline_log or not offline_data:
            sender.send_message(f"Could not retrieve user '{player_name}'")
            return False
        xuid = offline_log.xuid
        gamemode = offline_data.gamemode
        jail_pos = offline_data.last_logout_pos
        jail_dim = offline_data.last_logout_dim

    self.db.add_jail(
        xuid,
        int(jail_expiration.timestamp()),
        reason,
        jail["name"],
        gamemode,
        jail_pos,
        jail_dim
    )

    if target:
        self.db.save_inventory(target)
        target.inventory.clear()
        air = ItemStack("minecraft:air", 1)
        target.inventory.helmet = air
        target.inventory.chestplate = air
        target.inventory.leggings = air
        target.inventory.boots = air
        target.inventory.item_in_off_hand = air
        target.game_mode = GameMode.ADVENTURE
        self.server.dispatch_command(self.server.command_sender, f"effect \"{target.name}\" saturation infinite 255 true")
        target.teleport(jail["pos"])

        if permanent:
            sender.send_message(
                f"§6Player §e{player_name} §6was permanently jailed for §e'{reason}' §7§o(Permanent Jailed)"
            )
        else:
            sender.send_message(
                f"§6Player §e{player_name} §6was jailed for §e'{reason}' §6for {formatted_expiration} §7§o(Jailed)"
            )
    else:
        if permanent:
            sender.send_message(
                f"§6Player §e{player_name} §6was permanently jailed for §e'{reason}' §7§o(Offline, Permanent Jailed)"
            )
        else:
            sender.send_message(
                f"§6Player §e{player_name} §6was jailed for §e'{reason}' §6for {formatted_expiration} §7§o(Offline, Jailed)"
            )

    log(self,
            f"§6Player §e{player_name} §6was jailed by §e{sender.name} for §e\"{reason}\" until §e{formatted_expiration}",
            "mod")
    
    start_jail_check_if_needed(self)
    return True
