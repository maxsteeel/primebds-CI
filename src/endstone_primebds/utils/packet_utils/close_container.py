from endstone_primebds.utils.packet_utils.packet_util import MinecraftPacketIds, Packet, BufferWriter, BufferReader

class CloseContainerPacket(Packet):
    def __init__(self, 
                 window_id: int = 2,
                 window_type: int = 0,
                 server: bool = False):
        self.window_id = window_id
        self.window_type = window_type
        self.server = server

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.ContainerClose

    def serialize(self) -> bytes:
        w = BufferWriter()
        w.write_byte(self.window_id)
        w.write_byte(self.window_type)
        w.write_bool(self.server) 
        return w.getvalue()

    def deserialize(self, data: bytes) -> None:
        r = BufferReader(data)
        self.window_id = r.read_byte()
        self.window_type = r.read_byte()
        self.server = r.read_bool()
