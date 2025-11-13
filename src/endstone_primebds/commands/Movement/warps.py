from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

command, permission = create_command(
    "warps",
    "Manage server warps!",
    [
        "/warps (list)[warps_list: warps_list]",
        "/warps (create)[warp_create: warp_create] <name: message>",
        "/warps (delete)[warp_delete: warp_delete] <name: message>",
        "/warps (setcost)[warp_setcost: warp_setcost] <name: str> <cost: float>",
        "/warps (setdescription)[warp_setdescription: warp_setdescription] <name: str> <description: message>",
        "/warps (setcategory)[warp_setcategory: warp_setcategory] <name: str> <category: message>",
        "/warps (setdisplayname)[warp_setdisplayname: warp_setdisplayname] <name: str> <displayname: message>",
        "/warps (setname)[warp_setname: warp_setname] <old_name: str> <new_name: message>",
        "/warps (setdelay)[warp_setdelay: warp_setdelay] <name: str> <delay: float>",
        "/warps (setcooldown)[warp_setcooldown: warp_setcooldown] <name: str> <cooldown: float>"
    ],
    ["primebds.command.warps"]
)

warp_cooldowns: dict[str, float] = {}
warp_delays: dict[str, bool] = {}

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player")
        return False

    if not args:
        sender.send_message("§cUsage: /warps [list/create/delete/setcost/setdescription/setcategory/setdisplayname/setname/setdelay/setcooldown]")
        return False

    sub = args[0].lower()

    if sub == "list":
        warps = self.serverdb.get_all_warps(self.server)
        if not warps:
            sender.send_message("§cThere are no warps set")
            return True

        categories: dict[str, list[str]] = {}
        uncategorized: list[str] = []

        for name, warp in warps.items():
            cat = warp.get("category")
            display = warp.get("displayname") or name
            desc = warp.get("description")

            if desc:
                full_display = f"§b{display} §7- {desc}"
            else:
                full_display = f"§b{display}"

            if cat:
                categories.setdefault(cat, []).append(full_display)
            else:
                uncategorized.append(full_display)

        msg_lines: list[str] = []
        for cat, entries in categories.items():
            msg_lines.append(f"§6{cat}:")
            for line in entries:
                msg_lines.append(f"§7- {line}")

        if uncategorized:
            msg_lines.append("§6Uncategorized:")
            for line in uncategorized:
                msg_lines.append(f"§7- {line}")

        sender.send_message("§aWarps:\n" + "\n".join(msg_lines))
        return True

    if sub == "create" and len(args) >= 2:
        name = args[1]
        loc = sender.location
        if self.serverdb.create_warp(name, loc):
            sender.send_message(f"§aWarp §e{name} §aset at your current location")
        else:
            sender.send_message(f"§cWarp §e{name} §calready exists")
        return True

    if sub == "delete" and len(args) >= 2:
        name = args[1]
        if self.serverdb.delete_warp(name):
            sender.send_message(f"§aWarp §e{name} §adeleted")
        else:
            sender.send_message(f"§cWarp §e{name} §cdoes not exist")
        return True

    if sub.startswith("set") and len(args) >= 3:
        name = args[1]
        warp = self.serverdb.get_warp(name, self.server)
        if not warp:
            sender.send_message(f"§cWarp §e{name} §cdoes not exist")
            return True

        if sub == "setcost":
            try:
                cost = float(args[2])
                self.serverdb.update_warp_property(name, "cost", cost)
                sender.send_message(f"§aWarp §e{name} §acost updated to §e{cost}")
            except ValueError:
                sender.send_message("§cInvalid cost value")
            return True

        if sub == "setdescription":
            description = " ".join(args[2:])
            self.serverdb.update_warp_property(name, "description", description)
            sender.send_message(f"§aWarp §e{name} §adescription updated")
            return True

        if sub == "setcategory":
            category = args[2]
            self.serverdb.update_warp_property(name, "category", category)
            sender.send_message(f"§aWarp §e{name} §acategory updated to §e{category}")
            return True

        if sub == "setdisplayname":
            displayname = " ".join(args[2:])
            self.serverdb.update_warp_property(name, "displayname", displayname)
            sender.send_message(f"§aWarp §e{name} §adisplay name updated")
            return True

        if sub == "setname" and len(args) >= 3:
            new_name = args[2]
            self.serverdb.update_warp_property(name, "name", new_name)
            sender.send_message(f"§aWarp §e{name} §arenamed to §e{new_name}")
            return True

        if sub == "setdelay":
            try:
                delay = float(args[2])
                self.serverdb.update_warp_property(name, "delay", delay)
                sender.send_message(f"§aWarp §e{name} §adelay updated to §e{delay}s")
            except ValueError:
                sender.send_message("§cInvalid delay value")
            return True

        if sub == "setcooldown":
            try:
                cooldown = float(args[2])
                self.serverdb.update_warp_property(name, "cooldown", cooldown)
                sender.send_message(f"§aWarp §e{name} §acooldown updated to §e{cooldown}s")
            except ValueError:
                sender.send_message("§cInvalid cooldown value")
            return True

    sender.send_message("§cInvalid usage or missing arguments for /warps")
    return False
