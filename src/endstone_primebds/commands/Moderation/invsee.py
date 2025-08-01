from endstone import Player
from endstone.inventory import ItemStack
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.target_selector_util import get_matching_actors
from endstone._internal.endstone_python import Location
from endstone_primebds.utils.packet_utils.packet_util import MinecraftPacketIds, UpdateBlockPacket, OpenContainerPacket, InventoryContentPacket

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "invsee",
    "Allows you to view another player's inventory!",
    ["/invsee <player: player> (chat)[invsee_display: invsee_display]"],
    ["primebds.command.invsee"]
)

# INVSEE COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_message("This command can only be executed by a player")
        return False

    if any("@a" in arg for arg in args):
        sender.send_message("§cYou cannot select all players for this command")
        return False
    
    display_type = "chat"  # Default
    if len(args) > 1 and args[1]:
        display_type = args[1].lower()

    targets = get_matching_actors(self, args[0], sender)
    if not targets:
        sender.send_message("§cNo matching player found")
        return False

    for target in targets:
        inv = target.inventory.contents
        armor = [target.inventory.helmet, target.inventory.chestplate, target.inventory.leggings, target.inventory.boots, target.inventory.item_in_off_hand]
        combined = inv + armor

        item_list = "\n".join(
            f"§7- §e{item.type.key} §7x{item.amount}"
            for item in inv if item
        )

        item_list += '\n'

        item_list += "\n".join(
             f"§7- §e{item.type.key} §7(equipped)"
            for item in armor if item
        )

        if display_type == "chest":
            x = int(sender.location.block_x)
            y = int(sender.location.block_y + 3)
            z = int(sender.location.block_z)
            chest = self.get_runtime_id("minecraft:chest")
            chestView(self, sender, x, y, z, chest, combined)

        elif display_type == "chat":
            sender.send_message(f"§6Inventory of §e{target.name}§6:\n{item_list}")
        else:
            sender.send_message("§cInvalid display type")

    return True

open_chests = {}
def chestView(self: "PrimeBDS", sender: Player, x, y, z, chest, items):
    ub_id = MinecraftPacketIds.UpdateBlock
    
    fakechest1 = UpdateBlockPacket(x, y, z, chest, 3, 0)
    payload1 = fakechest1.serialize()
    sender.send_packet(ub_id, payload1)
    
    fakechest2 = UpdateBlockPacket(x + 1, y, z, chest, 3, 0)
    payload2 = fakechest2.serialize()
    sender.send_packet(ub_id, payload2)
    
    open_packet = OpenContainerPacket(2, 0, x, y, z, 1)
    oc_id = open_packet.get_packet_id()
    payload3 = open_packet.serialize()
    sender.send_packet(oc_id, payload3)

    if not hasattr(self, "open_chests"):
        self.open_chests = {}

    open_chests[sender.name] = [
        (x, y, z),
        (x + 1, y, z)
    ]

    #content_packet = InventoryContentPacket(2, items, "Chest")
    #id = MinecraftPacketIds.InventoryContent
    #payload4 = content_packet.serialize()
    #sender.send_packet(id, payload4)

def closeChestView(self: "PrimeBDS", sender: Player):
    if not hasattr(self, "open_chests"):
        return
    
    chest_coords = open_chests.get(sender.name)
    if not chest_coords:
        return
    
    ub_id = MinecraftPacketIds.UpdateBlock

    for (cx, cy, cz) in chest_coords:
        block_id = self.server.level.get_dimension(sender.location.dimension.name).get_block_at(Location(sender.location.dimension, cx, cy, cz)).type
        replace_id = self.get_runtime_id(block_id)
        pkt = UpdateBlockPacket(cx, cy, cz, replace_id, 3, 0)
        sender.send_packet(ub_id, pkt.serialize())
    
    del open_chests[sender.name]

