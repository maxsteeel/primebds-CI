from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.dbUtil import grieflog
from endstone._internal.endstone_python import Location

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

command, permission = create_command(
    "offlinetp",
    "Teleport to where a player last logged out.",
    ["/offlinetp [player: player]"],
    ["primebds.command.offlinetp"],
    "op",
    ["otp"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_message("§cThis command can only be executed by a player")
        return False

    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    if len(args) < 1:
        sender.send_message("§cYou must specify a player to teleport to")
        return False

    target_name = args[0]
    logout_log = self.db.get_offline_user(target_name).last_logout_pos
    if not logout_log:
        sender.send_message(f"§cNo logout record found for {target_name}")
        return True

    try:
        parts = logout_log.split(",")
        x = float(parts[0])
        y = float(parts[1])
        z = float(parts[2])
        dim = parts[3] if len(parts) > 3 else "Overworld"
    except (ValueError, AttributeError, IndexError):
        sender.send_message(f"§cInvalid logout record format for {target_name}")
        return True

        if None in (x, y, z):
            sender.send_message(f"§cLogout location data missing or incomplete for {target_name}")
            return True

    try:
        sender.teleport(Location(self.server.level.get_dimension(dim), x, y, z))
        sender.send_message(f"Teleported to §e{target_name}§r's last logout location at §e({x:.1f}, {y:.1f}, {z:.1f} / {dim})")
    except Exception as e:
        sender.send_message(f"§cFailed to teleport to {target_name}'s logout location")
        print(e)

    return True
