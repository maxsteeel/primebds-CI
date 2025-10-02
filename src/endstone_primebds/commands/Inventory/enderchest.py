from endstone import Player
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
    ["/enderchest <player: player> (chat)[echest_display: echest_display]"],
    ["primebds.command.enderchest"],
    "op",
    ["echest"]
)

# ECHEST COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:

    if any("@a" in arg for arg in args):
        sender.send_message("§cYou cannot select all players for this command")
        return False
    
    display_type = "chest"  # Default
    if len(args) > 1 and args[1]:
        display_type = args[1].lower()

    if not isinstance(sender, Player):
        display_type = "chat"

    targets = get_matching_actors(self, args[0], sender)
    if not targets:
        xuid = self.db.get_xuid_by_name(args[0])
        
        if not xuid:
            sender.send_message("§cNo matching player found")
            return False

        inv = self.db.get_enderchest(xuid)
        if not inv:
            sender.send_message(f"§cNo ender chest data found for {args[0]}")
            return False

        item_list = "\n".join(
            f"§7- §e{item['type']} §7x{item['amount']}"
            for item in inv
        )
        if display_type == "chest":
            chest = ChestForm(self, f"{target.name}'s Ender Chest", False)

            for slot, item in enumerate(inv):
                if not item:
                    continue

                meta = getattr(item, "item_meta", None)
                chest.set_slot(
                    slot,
                    getattr(getattr(item, "type", None), "id", None),
                    None,
                    item_amount=getattr(item, "amount", None),
                    item_data=getattr(item, "data", None),
                    display_name=getattr(meta, "display_name", None) if meta else None,
                    lore=getattr(meta, "lore", None) if meta else None,
                    enchants=getattr(meta, "enchants", None) if meta else None,
            )

            chest.send_to(sender)

        elif display_type == "chat":
            sender.send_message(f"§6Ender Chest of §e{target.name}§6:\n{item_list}")
        else:
            sender.send_message("§cInvalid display type. Use chat or form.")
        return True

    for target in targets:
        inv = target.ender_chest.contents
        
        item_list = "\n".join(
            f"§7- §e{item.type} §7x{item.amount}"
            for item in inv if item
        )

        if display_type == "chest":
            chest = ChestForm(self, f"{target.name}'s Ender Chest", False)

            for slot, item in enumerate(inv):
                if not item:
                    continue

                meta = getattr(item, "item_meta", None)
                chest.set_slot(
                    slot,
                    getattr(getattr(item, "type", None), "id", None),
                    None,
                    item_amount=getattr(item, "amount", None),
                    item_data=getattr(item, "data", None),
                    display_name=getattr(meta, "display_name", None) if meta else None,
                    lore=getattr(meta, "lore", None) if meta else None,
                    enchants=getattr(meta, "enchants", None) if meta else None,
            )

            chest.send_to(sender)

        elif display_type == "chat":
            sender.send_message(f"§6Ender Chest of §e{target.name}§6:\n{item_list}")
        else:
            sender.send_message("§cInvalid display type. Use chat or form.")

    return True