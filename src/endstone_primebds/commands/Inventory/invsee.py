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
    "invsee",
    "Allows you to view another player's inventory!",
    ["/invsee <player: player> (chat|chest)[invsee_display: invsee_display]"],
    ["primebds.command.invsee"]
)

# INVSEE COMMAND FUNCTIONALITY
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
        xuid = self.db.get_xuid_by_name(args[0])

        if not xuid:
            sender.send_message("§cNo matching player found")
            return False
        
        combined_inventory = self.db.get_inventory(xuid)
        if not combined_inventory:
            sender.send_message("§cNo inventory found for that player")
            return False

        item_list = "\n".join(
            f"§7- §e{entry['type']} §7x{entry['amount']}"
            + (" §7(equipped)" if entry['slot_type'] in ("helmet","chestplate","leggings","boots","offhand","mainhand") else "")
            for entry in combined_inventory
        )

        if display_type == "chest":
            chest = ChestForm(self, f"{target.name}'s Inventory", True)

            for slot, item in enumerate(inv):
                if not item:
                    continue

                meta = getattr(item, "item_meta", None)

                if 9 <= slot <= 35:
                    chest_slot = slot - 9
                elif 0 <= slot <= 8: 
                    chest_slot = 36 + slot
                else:
                    continue 

                chest.set_slot(
                    chest_slot,
                    getattr(getattr(item, "type", None), "id", None),
                    None,
                    item_amount=getattr(item, "amount", None),
                    item_data=getattr(item, "data", None),
                    display_name=getattr(meta, "display_name", None) if meta else None,
                    lore=getattr(meta, "lore", None) if meta else None,
                    enchants=getattr(meta, "enchants", None) if meta else None,
            )

            start_slot = 54 - len(armor)
            for offset, item in enumerate(armor):
                if item:
                    meta = getattr(item, "item_meta", None)
                    chest.set_slot(
                        start_slot + offset,
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
            sender.send_message(f"§6Inventory of §e{target.name}§6:\n{item_list}")
        else:
            sender.send_message("§cInvalid display type")
        return True

    for target in targets:
        inv = target.inventory.contents
        armor = [target.inventory.helmet, target.inventory.chestplate, target.inventory.leggings, target.inventory.boots, target.inventory.item_in_off_hand]

        item_list = "\n".join(
            f"§7- §e{item.type} §7x{item.amount}"
            for item in inv if item
        )

        item_list += '\n'

        item_list += "\n".join(
             f"§7- §e{item.type} §7(equipped)"
            for item in armor if item
        )

        if display_type == "chest":
            chest = ChestForm(self, f"{target.name}'s Inventory", True)

            for slot, item in enumerate(inv):
                if not item:
                    continue

                meta = getattr(item, "item_meta", None)

                if 9 <= slot <= 35:
                    chest_slot = slot - 9
                elif 0 <= slot <= 8: 
                    chest_slot = 36 + slot
                else:
                    continue 

                chest.set_slot(
                    chest_slot,
                    getattr(getattr(item, "type", None), "id", None),
                    None,
                    item_amount=getattr(item, "amount", None),
                    item_data=getattr(item, "data", None),
                    display_name=getattr(meta, "display_name", None) if meta else None,
                    lore=getattr(meta, "lore", None) if meta else None,
                    enchants=getattr(meta, "enchants", None) if meta else None,
            )

            start_slot = 54 - len(armor)
            for offset, item in enumerate(armor):
                if item:
                    meta = getattr(item, "item_meta", None)
                    chest.set_slot(
                        start_slot + offset,
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
            sender.send_message(f"§6Inventory of §e{target.name}§6:\n{item_list}")
        else:
            sender.send_message("§cInvalid display type")

    return True


