import os
import json
from math import ceil

from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.dbUtil import UserDB

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

command, permission = create_command(
    "plist",
    "Lists all players with a filter!",
    ["/plist (ops|defaults|online|offline|muted|banned|ipbanned)<plist_filter: plist_filter> [page: int]"],
    ["primebds.command.plist"]
)

MAX_PER_PAGE = 25

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    filter_type = args[0].lower()
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1

    db = UserDB("users.db")

    def get_ops():
        permissions_path = get_permissions_path()
        if not os.path.exists(permissions_path):
            return ["§cpermissions.json not found"]

        try:
            with open(permissions_path, 'r') as f:
                data = json.load(f)

            ops = [entry["xuid"] for entry in data if entry.get("permission") == "operator"]
            names = []
            for xuid in ops:
                name = db.get_name_by_xuid(xuid) or "§8Unknown"
                names.append(f"§e{name} §8({xuid})")
            return sorted(names, key=lambda n: (n.startswith("§8Unknown"), n.lower()))
        except Exception as e:
            return [f"§cFailed to read permissions.json: {e}"]

    def get_defaults():
        return [p['name'] for p in db.get_all_users() if p['internal_rank'].lower() == "default"]

    def get_online():
        return [pl.name for pl in self.server.online_players]

    def get_offline():
        online = {pl.name for pl in self.server.online_players}
        return [p['name'] for p in db.get_all_users() if p['name'] not in online]

    def get_muted():
        return [p['name'] for p in db.get_all_users() if db.get_offline_mod_log(p['name']).is_muted]

    def get_banned():
        return [p['name'] for p in db.get_all_users() if db.get_offline_mod_log(p['name']).is_banned]

    def get_ipbanned():
        return [p['name'] for p in db.get_all_users() if db.get_offline_mod_log(p['name']).is_ip_banned]

    filters = {
        "ops": get_ops,
        "defaults": get_defaults,
        "online": get_online,
        "offline": get_offline,
        "muted": get_muted,
        "banned": get_banned,
        "ipbanned": get_ipbanned
    }

    if filter_type not in filters:
        sender.send_message("§cInvalid filter type")
        db.close_connection()
        return False

    all_results = filters[filter_type]()
    total = len(all_results)

    if total == 0:
        sender.send_message(f"§7No {filter_type} players found")
        db.close_connection()
        return True

    total_pages = ceil(total / MAX_PER_PAGE)
    if page < 1 or page > total_pages:
        sender.send_message(f"§cInvalid page number. Available pages: 1-{total_pages}")
        db.close_connection()
        return False

    start_idx = (page - 1) * MAX_PER_PAGE
    end_idx = start_idx + MAX_PER_PAGE
    results = all_results[start_idx:end_idx]

    header = f"§r{filter_type.capitalize()} Players (Page {page}/{total_pages}):"
    body = "\n".join(f"§7- §e{name}" for name in results)
    sender.send_message(header + "\n" + body)

    db.close_connection()
    return True

def get_permissions_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while not (
        os.path.exists(os.path.join(current_dir, 'plugins')) and
        os.path.exists(os.path.join(current_dir, 'worlds'))
    ):
        current_dir = os.path.dirname(current_dir)
    return os.path.join(current_dir, 'permissions.json')
