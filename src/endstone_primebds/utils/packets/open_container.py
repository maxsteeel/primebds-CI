from endstone_primebds.utils.packets.packet_util import encode_varint, encode_uvarlong

def build_open_container_packet(window_type = 0, x: int = 0, y: int = 0, z: int = 0, container_unique_id = 1):
    packet_id = 46

    packet = bytearray()
    packet.append(2)
    packet.append(window_type)
    packet.extend(encode_varint(x))
    packet.extend(encode_varint(y))
    packet.extend(encode_varint(z))
    packet.extend(encode_uvarlong(container_unique_id))

    return packet_id, bytes(packet)