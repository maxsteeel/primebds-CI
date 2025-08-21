from endstone_primebds.utils.packet_utils.packet_util import MinecraftPacketIds, Packet,  BufferReader, BufferWriter

class OpenContainerPacket(Packet):
    def __init__(self,
                 window_id: int = 2,
                 window_type: int = 0,
                 x: int = 0,
                 y: int = 0,
                 z: int = 0,
                 container_unique_id: int = 1):
        self.window_id = window_id
        self.window_type = window_type
        self.x = x
        self.y = y
        self.z = z
        self.container_unique_id = container_unique_id

    def get_packet_id(self) -> 'MinecraftPacketIds':
        return MinecraftPacketIds.OpenContainer

    def serialize(self) -> bytes:
        w = BufferWriter()
        w.write_varint(self.window_id)
        w.write_varint(self.window_type)
        w.write_varlong(self.x)
        w.write_varint(self.y)
        w.write_varlong(self.z)
        w.write_varint(self.container_unique_id)
        return w.getvalue()

    def deserialize(self, data: bytes) -> None:
        r = BufferReader(data)
        self.window_id = r.read_varint()
        self.window_type = r.read_varint()
        self.x = r.read_varlong()
        self.y = r.read_varint()
        self.z = r.read_varlong()
        self.container_unique_id = r.read_varint()
