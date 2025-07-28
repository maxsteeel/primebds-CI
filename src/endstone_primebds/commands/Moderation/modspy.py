from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.dbUtil import UserDB

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "modspy",
    "Allows you to view moderation logs!",
    ["/modspy [toggle: bool]"],
    ["primebds.command.modspy"]
)

# MODSPY COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player")
        return False

    db = UserDB("users.db")
    user = db.get_offline_user(sender.name)
    current_status = bool(user.enabled_logs)

    if not args:
        status_message = f"Mod logs are currently {f'§aEnabled' if current_status else f'§cDisabled'}"
        sender.send_message(status_message)
    else:
        new_status = args[0].lower() in ["true", "1", "yes", "enable"]
        db.update_user_data(sender.name, "enabled_logs", int(new_status))
        sender.send_message(f"§6Mod logs have been {f'§aEnabled' if new_status else f'§cDisabled'}")

    db.close_connection()
    return True
