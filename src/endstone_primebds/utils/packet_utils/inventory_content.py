from endstone.inventory import ItemStack
from endstone_primebds.utils.packet_utils.packet_util import MinecraftPacketIds,  Packet
"""
class InventoryContentPacket(Packet): # CURRENTLY BUGGED
    def __init__(self,
                 window_id: int = 0,
                 content: list = None,
                 container_name: str = "",
                 storage_item=None):
        self.window_id = window_id
        self.content = content if content is not None else []
        self.container_name = container_name
        self.storage_item = storage_item

    def get_packet_id(self) -> 'MinecraftPacketIds':
        return MinecraftPacketIds.InventoryContent

    def serialize(self) -> bytes:
        payload = PacketEncoder.encode_uvarint(self.window_id)
        payload += PacketEncoder.encode_varint(len(self.content))
        for item in self.content:
            payload += item.serialize()
        payload += PacketEncoder.encode_string(self.container_name)
        payload += self.storage_item.serialize() if self.storage_item else b"\x00"
        return payload

    def deserialize(self, data: bytes) -> None:
        offset = 0

        self.window_id, size_id = PacketEncoder.decode_uvarint(data, offset)
        offset += size_id

        length, size_len = PacketEncoder.decode_varint(data, offset)
        offset += size_len

        self.content = []
        for _ in range(length):
            item = ItemStack()
            item.deserialize(data[offset:])
            offset += item.get_size()
            self.content.append(item)

        self.container_name, size_name = PacketEncoder.decode_string(data, offset)
        offset += size_name

        self.storage_item = ItemStack()
        self.storage_item.deserialize(data[offset:])"""