import struct

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

def read_varint(data, offset=0):
    value = 0
    shift = 0
    pos = offset
    while True:
        byte = data[pos]
        value |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return value, pos

def read_string(data, offset):
    length, pos = read_varint(data, offset)
    string_bytes = data[pos:pos+length]
    string_value = string_bytes.decode('utf-8', errors='ignore')
    return string_value, pos + length

def extract_player_name_from_addplayer(packet: bytes):
    pos = 16  
    player_name, _ = read_string(packet, pos)
    return player_name

def encode_uvarlong(value: int) -> bytes:
    """Encodes an unsigned 64-bit integer into UVarLong format."""
    if value < 0:
        raise ValueError("UVarLong cannot encode negative values")
    
    buffer = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            buffer.append(byte | 0x80)
        else:
            buffer.append(byte)
            break
    return bytes(buffer)

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
