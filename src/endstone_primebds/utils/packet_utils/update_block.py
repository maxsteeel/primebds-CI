from endstone_primebds.utils.packet_utils.packet_util import MinecraftPacketIds, Packet
"""
class UpdateBlockPacket(Packet):
    def __init__(self, 
                 x: int,
                 y: int,
                 z: int, 
                 block_runtime_id: int = 0, 
                 update_flag: int = 3, 
                 block_layer: int = 0):
        self.x = x
        self.y = y
        self.z = z
        self.block_runtime_id = block_runtime_id
        self.update_flag = update_flag
        self.block_layer = block_layer

    def get_packet_id(self) -> 'MinecraftPacketIds':
        return MinecraftPacketIds.UpdateBlock

    def serialize(self) -> bytes:
        return (
            PacketEncoder.encode_varint(PacketEncoder.encode_zigzag32(self.x)) +
            PacketEncoder.encode_varint(self.y) +
            PacketEncoder.encode_varint(PacketEncoder.encode_zigzag32(self.z)) +
            PacketEncoder.encode_varint(self.block_runtime_id) +
            PacketEncoder.encode_varint(self.update_flag) +
            PacketEncoder.encode_varint(self.block_layer)
        )

    def deserialize(self, data: bytes) -> None:
        offset = 0
        self.x, size_x = PacketEncoder.decode_varint(data, offset)
        offset += size_x

        self.y, size_y = PacketEncoder.decode_uvarint(data, offset)
        offset += size_y

        self.z, size_z = PacketEncoder.decode_varint(data, offset)
        offset += size_z

        # Decode varint first
        zigzag_encoded, size_runtime = PacketEncoder.decode_varint(data, offset)
        offset += size_runtime

        # Then decode zigzag to get the signed value
        self.block_runtime_id = PacketEncoder.decode_zigzag64(zigzag_encoded)

        self.update_flag, size_flag = PacketEncoder.decode_uvarint(data, offset)
        offset += size_flag

        self.block_layer, _ = PacketEncoder.decode_uvarint(data, offset)"""
