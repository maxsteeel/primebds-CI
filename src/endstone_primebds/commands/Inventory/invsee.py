from endstone import Player
from endstone.level import Location
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.target_selector_util import get_matching_actors
from endstone_primebds.utils.lookup_util import get_runtime_id

try:
    from bedrock_protocol.packets import minecraft_packets, MinecraftPacketIds, types
    from bedrock_protocol.nbt import IntTag, StringTag, compound_tag
    PACKET_SUPPORT = True
except Exception as e:
    print(e)
    PACKET_SUPPORT = False

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
        sender.send_message(f"§bInventory for {args[0]}:\n{item_list}")
        return True

    for target in targets:
        inv = target.inventory.contents
        armor = [target.inventory.helmet, target.inventory.chestplate, target.inventory.leggings, target.inventory.boots, target.inventory.item_in_off_hand]
        combined = inv + armor

        item_list = "\n".join(
            f"§7- §e{item.type} §7x{item.amount}"
            for item in inv if item
        )

        item_list += '\n'

        item_list += "\n".join(
             f"§7- §e{item.type} §7(equipped)"
            for item in armor if item
        )

        if display_type == "chest" and PACKET_SUPPORT:
            x = int(sender.location.block_x)
            y = int(sender.location.block_y + 3)
            z = int(sender.location.block_z)
            chest = get_runtime_id(self, "minecraft:chest")
            chestView(self, sender, x, y, z, chest, combined)

        elif display_type == "chat":
            sender.send_message(f"§6Inventory of §e{target.name}§6:\n{item_list}")
        else:
            sender.send_message("§cInvalid display type")

    return True

open_chests = {}
def chestView(self: "PrimeBDS", sender: Player, x, y, z, chest, items):
    ub_id = MinecraftPacketIds.UpdateBlock

    fakechest1 = minecraft_packets.UpdateBlockPacket(types.NetworkBlockPosition(x, y, z), chest, 3, 0)
    payload1 = fakechest1.serialize()
    sender.send_packet(ub_id, payload1)
    
    fakechest2 = minecraft_packets.UpdateBlockPacket(types.NetworkBlockPosition(x+1, y, z), chest, 3, 0)
    payload2 = fakechest2.serialize()
    sender.send_packet(ub_id, payload2)

    pos1 = fakechest1.block_position
    pos2 = fakechest2.block_position

    chest1_nbt = compound_tag.CompoundTag()
    chest1_nbt.put("id", StringTag("Chest"))
    chest1_nbt.put("x", IntTag(pos1.x))
    chest1_nbt.put("y", IntTag(pos1.y))
    chest1_nbt.put("z", IntTag(pos1.z))
    chest1_nbt.put("pairx", IntTag(pos2.x))
    chest1_nbt.put("pairz", IntTag(pos2.z))
    chest1_nbt.put("pairLead", IntTag(1))

    chest2_nbt = compound_tag.CompoundTag()
    chest2_nbt.put("id", StringTag("Chest"))
    chest2_nbt.put("x", IntTag(pos2.x))
    chest2_nbt.put("y", IntTag(pos2.y))
    chest2_nbt.put("z", IntTag(pos2.z))
    chest2_nbt.put("pairx", IntTag(pos1.x))
    chest2_nbt.put("pairz", IntTag(pos1.z))
    chest2_nbt.put("pairLead", IntTag(0))

    bap1 = minecraft_packets.BlockActorDataPacket(types.NetworkBlockPosition(x, y, z), nbt=chest1_nbt)
    bap2 = minecraft_packets.BlockActorDataPacket(types.NetworkBlockPosition(x+1, y, z), nbt=chest2_nbt)
    bap1_payload = bap1.serialize()
    bap2_payload = bap2.serialize()
    sender.send_packet(bap1.get_packet_id(), bap1_payload)
    sender.send_packet(bap2.get_packet_id(), bap2_payload)
    
    open_packet = minecraft_packets.ContainerOpenPacket(2, 0, x, y, z, 1)
    oc_id = open_packet.get_packet_id()
    payload3 = open_packet.serialize()
    sender.send_packet(oc_id, payload3)

    if not hasattr(self, "open_chests"):
        self.open_chests = {}

    open_chests[sender.name] = [
        (x, y, z),
        (x + 1, y, z)
    ]

def closeChestView(self: "PrimeBDS", sender: Player):
    if not hasattr(self, "open_chests"):
        return
    
    chest_coords = open_chests.get(sender.name)
    if not chest_coords:
        return
    
    ub_id = MinecraftPacketIds.UpdateBlock

    for (cx, cy, cz) in chest_coords:
        block_id = self.server.level.get_dimension(sender.location.dimension.name).get_block_at(Location(sender.location.dimension, cx, cy, cz)).type
        replace_id = get_runtime_id(self, block_id)
        pkt = minecraft_packets.UpdateBlockPacket(cx, cy, cz, replace_id, 3, 0)
        sender.send_packet(ub_id, pkt.serialize())
    
    del open_chests[sender.name]

