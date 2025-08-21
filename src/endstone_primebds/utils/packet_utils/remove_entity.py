from endstone_primebds.utils.packet_utils.packet_util import MinecraftPacketIds, Packet, BufferWriter, BufferReader

class RemoveEntityPacket(Packet):
    def __init__(self, actor_id: int = 0):
        self.actor_id = actor_id

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.RemoveEntity

    def serialize(self) -> bytes:
        buf = BufferWriter()
        buf.write_zigzag64_varint(self.actor_id)
        return buf.getvalue()

    def deserialize(self, data: bytes) -> None:
        buf = BufferReader(data)
        raw_id = buf.read_varint()
        self.actor_id = buf.read_zigzag64_varint(raw_id)
