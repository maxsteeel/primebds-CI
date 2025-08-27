from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.target_selector_util import get_matching_actors

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "enchantforce",
    "Forces a given enchantment onto an item!",
    ["/enchantforce <player: player> <enchantmentName: str> [level: int]"],
    ["primebds.command.enchantforce"],
    "op",
    ["enchantf", "forceenchant"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) < 2:
        sender.send_message("§cUsage: /enchantforce <player> <enchantmentName> [level]")
        return False

    target_selector = args[0]
    enchant_name = args[1].lower()

    level = 1
    if len(args) >= 3:
        try:
            level = int(args[2])
            if level > 32767:
                sender.send_message("§cEnchantments cannot exceed level 32767")
                return False
            elif level < -32767:
                sender.send_message("§cEnchantments cannot be below level -32767")
                return False
        except ValueError:
            sender.send_message("§cInvalid enchantment level; must be a number")
            return False

    targets = get_matching_actors(self, target_selector, sender)
    if not targets:
        sender.send_message("§cNo matching players found")
        return False
    
    try:
        self.server.enchantment_registry.get_or_throw(enchant_name)
    except Exception:
        sender.send_message(f"§cEnchantment '{enchant_name}' is not registered")
        return False

    for target in targets:
        held_item = target.inventory.item_in_main_hand
        if held_item is None:
            if len(targets) == 1:
                return False
            else:
                continue
            
        meta_data = held_item.item_meta
        meta_data.add_enchant(enchant_name, level, True)
        held_item.set_item_meta(meta_data)
        target.inventory.set_item(target.inventory.held_item_slot, held_item)

    if len(targets) == 1:
        sender.send_message(f"§e{targets[0].name} §rwas enchanted with §e{enchant_name} §rlevel §e{level}")
    else:
        sender.send_message(f"§e{len(targets)} §rplayers were enchanted with §e{enchant_name} §rlevel §e{level}")

    return True
