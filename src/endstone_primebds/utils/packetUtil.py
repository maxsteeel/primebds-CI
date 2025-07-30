import struct
from binarystream import *

DEVICE_OS = {
    "Undefined": 0,
    "Android": 1,
    "IOS": 2,
    "OSX": 3,
    "FireOS": 4,
    "GearVR": 5,
    "Hololens": 6,
    "Win10": 7,
    "Win32": 8,
    "Dedicated": 9,
    "TVOS": 10,
    "Orbis": 11,
    "NintendoSwitch": 12,
    "Xbox": 13,
    "WindowsPhone": 14,
    "Linux": 15
}

def encode_varint(value: int) -> bytes:
    buffer = b""
    while True:
        temp = value & 0b01111111
        value >>= 7
        if value != 0:
            buffer += struct.pack("B", temp | 0b10000000)
        else:
            buffer += struct.pack("B", temp)
            break
    return buffer

def encode_string(s: str) -> bytes:
    encoded = s.encode("utf-8")
    return encode_varint(len(encoded)) + encoded

def encode_position(x: int, y: int, z: int) -> bytes:
    return struct.pack('<iii', x, y, z)

def encode_zigzag32(n: int) -> int:
    return (n << 1) ^ (n >> 31)

def encode_zigzag64(value: int) -> int:
    return (value << 1) ^ (value >> 63)

def encode_varint32(value: int) -> bytes:
    buffer = b""
    while True:
        temp = value & 0x7F
        value >>= 7
        if value:
            buffer += struct.pack("B", temp | 0x80)
        else:
            buffer += struct.pack("B", temp)
            break
    return buffer

def encode_varint64(value: int) -> bytes:
    buf = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value != 0:
            buf.append(to_write | 0x80)
        else:
            buf.append(to_write)
            break
    return bytes(buf)

def encode_li64(value: int) -> bytes:
    return struct.pack("<q", value)

def encode_li32(value: int) -> bytes:
    return struct.pack("<i", value)

def debug_packet(packet_bytes: bytes):

    if not isinstance(packet_bytes, (bytes, bytearray)):
        raise TypeError("debug_packet expects bytes or bytearray")

    def to_hex_line(data, start):
        hex_str = ' '.join(f'{b:02X}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
        return f"{start:04X}: {hex_str:<48}  {ascii_str}"

    length = len(packet_bytes)
    print(f"Packet length: {length} bytes")
    print("-" * 60)
    for i in range(0, length, 16):
        line = packet_bytes[i:i+16]
        print(to_hex_line(line, i))
    print("-" * 60)

    if length == 0:
        print("Empty packet")
        return

    if length < 2:
        print("Packet is suspiciously short")

    if length >= 3 and packet_bytes[-3:] == b'\x00\x00\x00':
        print("Packet ends with multiple null bytes, might be malformed")

    print("Debug complete\n")

def build_remove_actor_packet(entity_id: int) -> tuple[int, bytes]:
    packet_id = 14
    packet = bytearray()
    
    varint_bytes = encode_varint(encode_zigzag64(entity_id))
    packet.extend(varint_bytes)
    
    return packet_id, bytes(packet)

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

    debug_packet(packet)
    return packet_id, bytes(packet)

DEVICE_OS_MAP = {
    "Undefined": 0,
    "Android": 1,
    "IOS": 2,
    "OSX": 3,
    "FireOS": 4,
    "GearVR": 5,
    "Hololens": 6,      # Deprecated
    "Win10": 7,
    "Win32": 8,
    "Dedicated": 9,
    "TVOS": 10,
    "Orbis": 11,
    "NintendoSwitch": 12,
    "Xbox": 13,
    "WindowsPhone": 14,
    "Linux": 15
}
def build_add_player_packet(
    username: str,
    player_uuid: bytes,
    entity_runtime_id: int,
    position: tuple[float, float, float],
    velocity: tuple[float, float, float],
    pitch: float,
    yaw: float,
    held_item,
    gamemode: int,
    metadata,
    entityprops,
    permlevel: int,
    cmdpermlevel: int,
    abilities,
    links,
    deviceID: str
) -> tuple[int, bytes]:
    packet_id = 12
    stream = BinaryStream()

    stream.write_bytes(player_uuid)                              # UUID 
    stream.write_string(username)                                # Username string
    stream.write_unsigned_varint64(entity_runtime_id)            # Runtime ID (varint64)
    stream.write_string("")                                      # Platform Chat ID

    # Position floats
    stream._write("<f", position[0])
    stream._write("<f", position[1])
    stream._write("<f", position[2])

    # Velocity floats
    stream._write("<f", velocity[0])
    stream._write("<f", velocity[1])
    stream._write("<f", velocity[2])

    # Pitch, yaw, head yaw floats
    stream._write("<f", pitch)
    stream._write("<f", yaw)
    stream._write("<f", yaw)

    # Held Item (varint + zigzag32 in your original — assuming held_item is int)
    stream.write_varint(encode_zigzag32(held_item))

    # Gamemode (varint + zigzag32)
    stream.write_varint(encode_zigzag32(gamemode))

    stream.write_varint(metadata)                               # Metadata (pre-encoded varint)
    stream.write_varint(entityprops)                            # Entity properties (pre-encoded varint)

    stream.write_signed_int64(entity_runtime_id)                # li64 Runtime ID

    stream.write_unsigned_char(permlevel & 0xFF)                # Permission level (u8)
    stream.write_unsigned_char(cmdpermlevel & 0xFF)             # Command permission level (u8)

    stream.write_unsigned_char(len(abilities) & 0xFF)           # Abilities length (u8)
    stream.write_unsigned_char(len(abilities) & 0xFF)           # Ability layers data length (u8)
    stream.write_unsigned_char(len(links) & 0xFF)               # Entity links length (u8)

    stream.write_string(deviceID)                               # Device ID string
    stream.write_signed_int(0)                                  # Device OS (li32)

    debug_packet(stream.getvalue())
    return packet_id, stream.getvalue()
