from endstone_primebds.utils.packets.packetUtil import encode_varint

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def get_runtime_id(self: "PrimeBDS", blockID: str):
    return self.server.create_block_data(blockID).runtime_id

def build_update_block_packet(self, x: int, y: int, z: int, block_type):
    packet_id = 21

    packet = bytearray()
    packet.extend(encode_varint(x))
    packet.extend(encode_varint(y))
    packet.extend(encode_varint(z))
    packet.extend(encode_varint(get_runtime_id(self, block_type))) 
    packet.extend(encode_varint(3))
    packet.extend(encode_varint(0))

    return packet_id, bytes(packet)