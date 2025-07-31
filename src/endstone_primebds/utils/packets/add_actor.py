from endstone_primebds.utils.packets.packetUtil import encode_varint, encode_varint64, encode_string
import struct

# THIS IS CURRENTLY BUGGED
def build_add_actor_packet(
    player_uuid,
    entity_runtime_id,
    entity_type: str,
    position: tuple[float, float, float],
    velocity: tuple[float, float, float],
    pitch: float,
    yaw: float,
    attributes,
    metadata,
    entityprops,
    links
) -> tuple[int, bytes]:
    packet_id = 13                                                  # Packet ID for Add Player
    packet = bytearray()

    packet.extend(player_uuid)
    packet.extend(encode_varint64(entity_runtime_id))               # Runtime ID (varint64)
    packet.extend(encode_string(entity_type))                       # Username string      
    packet.extend(struct.pack("<fff", *position))                   # Position: X, Y, Z (floats)
    packet.extend(struct.pack("<fff", *velocity))                   # Velocity: X, Y, Z (floats)
    packet.extend(struct.pack("<f", pitch))                         # Pitch (float)
    packet.extend(struct.pack("<f", yaw))                           # Yaw (float)
    packet.extend(struct.pack("<f", yaw))                           # Head Yaw (float)
    packet.extend(struct.pack("<f", yaw))                           # Body Yaw (float)
    packet.extend(encode_varint(attributes))                        # Entity Attributes
    packet.extend(encode_varint(metadata))                          # Metadata
    packet.extend(encode_varint(entityprops))                       # Entity properties
    packet.extend(len(links) & 0xFF)

    return packet_id, bytes(packet)