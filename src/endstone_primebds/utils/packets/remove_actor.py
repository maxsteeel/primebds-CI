from endstone.actor import Actor
from endstone_primebds.utils.packets.packet_util import encode_varint, encode_zigzag64

def build_remove_actor_packet(actor: Actor) -> tuple[int, bytes]:
    packet_id = 14
    packet = bytearray()
    
    varint_bytes = encode_varint(encode_zigzag64(actor.id))
    packet.extend(varint_bytes)
    
    return packet_id, bytes(packet)
