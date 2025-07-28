import os
import json

from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.dbUtil import UserDB

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "plist",
    "Lists all players with a filter!",
    ["/plist (ops|defaults|online|offline|muted|banned|ipbanned)<playerlist: filter>"],
    ["primebds.command.plist"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:

    if args[0] == "ops":
        permissions_path = get_permissions_path()
        if not os.path.exists(permissions_path):
            sender.send_message("§cpermissions.json file not found.")
            return True

        try:
            with open(permissions_path, 'r') as f:
                data = json.load(f)

            ops = [entry["xuid"] for entry in data if entry.get("permission") == "operator"]

            if not ops:
                sender.send_message("§7No operators found in permissions.json.")
                return True

            lines = []
            for xuid in ops:
                db = UserDB("users.db")
                name = db.get_name_by_xuid(xuid)
                if not name:
                    name = "§8Unknown"
                db.close_connection()
                lines.append((name, xuid))

            lines.sort(key=lambda item: item[0] == "§8Unknown")

            sender.send_message("§rOperators:\n" + "\n".join(f"§7- §6{name} §8({xuid})" for name, xuid in lines))

        except Exception as e:
            sender.send_message(f"§cFailed to read permissions.json: {e}")
        return True

def get_permissions_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while not (
        os.path.exists(os.path.join(current_dir, 'plugins')) and
        os.path.exists(os.path.join(current_dir, 'worlds'))
    ):
        current_dir = os.path.dirname(current_dir)
    return os.path.join(current_dir, 'permissions.json')
