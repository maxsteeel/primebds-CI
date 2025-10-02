from endstone import Player
from endstone.inventory import ItemStack
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.target_selector_util import get_matching_actors
from chest_form_api_endstone import ChestForm

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "enderchest",
    "Allows you to view another player's ender chest!",
    ["/enderchest <player: player> (chat|chest)[echest_display: echest_display]"],
    ["primebds.command.enderchest"],
    "op",
    ["echest"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if any("@a" in arg for arg in args):
        sender.send_message("§cYou cannot select all players for this command")
        return False
    
    display_type = "chest"
    if len(args) > 1 and args[1]:
        display_type = args[1].lower()

    if not isinstance(sender, Player):
        display_type = "chat"

    targets = get_matching_actors(self, args[0], sender)

    if not targets:
        user = self.db.get_offline_user(args[0])
        if not user or not user.xuid:
            sender.send_message("§cNo matching player found")
            return False

        ender_inv = self.db.get_enderchest(user.xuid)
        if not ender_inv:
            sender.send_message(f"§cNo ender chest data found for {args[0]}")
            return False

        items = [normalize_item(entry) for entry in ender_inv]
        if display_type == "chat":
            sender.send_message(f"§6Ender Chest of §e{user.name}§6:\n{build_item_list(items)}")
        elif display_type == "chest":
            show_chest(self, sender, f"{user.name}'s Ender Chest", items, False)
        else:
            sender.send_message("§cInvalid display type. Use chat or chest.")
        return True

    for target in targets:
        items = [normalize_item(item, slot) for slot, item in enumerate(target.ender_chest.contents)]
        items = [i for i in items if i]

        if display_type == "chat":
            sender.send_message(f"§6Ender Chest of §e{target.name}§6:\n{build_item_list(items)}")
        elif display_type == "chest":
            show_chest(self, sender, f"{target.name}'s Ender Chest", items, False)
        else:
            sender.send_message("§cInvalid display type. Use chat or chest.")

    return True

def normalize_item(item, slot: int | None = None):
    def invalid_item(slot: int | None = None):
        return {
            "slot": slot,
            "type": "minecraft:barrier",
            "amount": 1,
            "data": 0,
            "display_name": "§cItem No Longer Exists",
            "lore": None,
            "enchants": None,
        }

    if not item:
        return None

    if isinstance(item, dict):
        item_id = item.get("type")
        amount = item.get("amount", 1)
        data = item.get("data", 0)

        try:
            _ = ItemStack(item_id, amount, data)
        except Exception:
            return invalid_item(item.get("slot"))

        return {
            "slot": item.get("slot"),
            "type": item_id,
            "amount": amount,
            "data": data,
            "display_name": item.get("display_name"),
            "lore": item.get("lore"),
            "enchants": item.get("enchants"),
        }

    else:
        item_id = getattr(getattr(item, "type", None), "id", None)
        amount = getattr(item, "amount", 1)
        data = getattr(item, "data", 0)

        try:
            _ = ItemStack(item_id, amount, data)
        except Exception:
            return invalid_item(slot)

        meta = getattr(item, "item_meta", None)
        return {
            "slot": slot,
            "type": item_id,
            "amount": amount,
            "data": data,
            "display_name": getattr(meta, "display_name", None) if meta else None,
            "lore": getattr(meta, "lore", None) if meta else None,
            "enchants": getattr(meta, "enchants", None) if meta else None,
        }

def build_item_list(items: list[dict]) -> str:
    return "\n".join(
        f"§7- §e{entry['type']} §7x{entry['amount']}"
        for entry in items if entry
    )

def show_chest(self, sender, title: str, items: list[dict], allow_armor: bool = False):
    chest = ChestForm(self, title, allow_armor)
    for entry in items:
        if not entry:
            continue
        slot = entry.get("slot")
        if slot is None:
            continue

        item_type = entry.get("type") or "minecraft:barrier"
        item_amount = entry.get("amount") or 1
        item_data = entry.get("data") or 0
        display_name = entry.get("display_name") or ("§cInvalid Item" if item_type == "minecraft:barrier" else None)

        chest.set_slot(
            slot,
            item_type,
            None,
            item_amount=item_amount,
            item_data=item_data,
            display_name=display_name,
            lore=entry.get("lore"),
            enchants=entry.get("enchants"),
        )
    chest.send_to(sender)