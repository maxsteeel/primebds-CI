from endstone import Player
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

"""
class AddPlayerPacket(Packet): # CURRENTLY BUGGED
    def __init__(self):
        self.uuid = None
        self.username = ""
        self.runtime_id = None
        self.platform_chat_id = ""
        self.position = (0, 0, 0)
        self.velocity = (0, 0, 0)
        self.pitch = 0
        self.yaw = 0
        self.head_yaw = 0
        self.held_item = None
        self.gamemode = None
        self.metadata = None
        self.entity_properties = None
        self.long_runtime_id = None
        self.permission_level = None
        self.command_permission = None
        self.links = None
        self.device_id = ""
        self.device_os = None

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.AddPlayer

    def serialize(self) -> bytes:
        parts = []

        parts.append(PacketEncoder.encode_uuid(self.uuid))
        parts.append(PacketEncoder.encode_string(self.username))
        parts.append(PacketEncoder.encode_uvarint(self.runtime_id))
        parts.append(PacketEncoder.encode_string(self.platform_chat_id))
        parts.append(struct.pack("<fff", *self.position))
        parts.append(struct.pack("<fff", *self.velocity))
        parts.append(struct.pack("<fff", self.pitch, self.yaw, self.head_yaw))
        parts.append(PacketEncoder.encode_item(self.held_item))
        parts.append(PacketEncoder.encode_varint(PacketEncoder.encode_zigzag32(self.gamemode)))
        parts.append(PacketEncoder.encode_metadata_dictionary(self.metadata))
        parts.append(PacketEncoder.encode_entity_properties(self.entity_properties))
        parts.append(struct.pack("<q", self.long_runtime_id))
        parts.append(PacketEncoder.encode_permission_level(self.permission_level))
        parts.append(PacketEncoder.encode_command_permission_level(self.command_permission))
        parts.append(PacketEncoder.encode_links(self.links))
        parts.append(PacketEncoder.encode_string(self.device_id))
        parts.append(PacketEncoder.encode_device_os(self.device_os))

        return b"".join(parts)

    def deserialize(self, data: bytes):
        offset = 0

        # UUID (16 bytes)
        self.uuid, size = PacketEncoder.decode_uuid(data, offset)
        offset += size

        # Username (string)
        self.username, size = PacketEncoder.decode_string(data, offset)
        offset += size

        # Runtime ID (VarInt64)
        self.runtime_id, size = PacketEncoder.decode_uvarlong(data, offset)
        offset += size

        # Platform chat ID (string)
        self.platform_chat_id, size = PacketEncoder.decode_string(data, offset)
        offset += size

        # Position (vec3f)
        self.position = struct.unpack_from("<fff", data, offset)
        offset += 12

        # Velocity (vec3f)
        self.velocity = struct.unpack_from("<fff", data, offset)
        offset += 12

        # Pitch, Yaw, HeadYaw (lf32 each)
        self.pitch, self.yaw, self.head_yaw = struct.unpack_from("<fff", data, offset)
        offset += 12

        # Held Item
        self.held_item, size = PacketEncoder.decode_item(data, offset)
        offset += size

        # Gamemode (zigzag varint)
        raw_gamemode, size = PacketEncoder.decode_varint(data, offset)
        self.gamemode = PacketEncoder.decode_zigzag32(raw_gamemode)
        offset += size
        
        # Metadata
        self.metadata, size = PacketEncoder.decode_metadata_dictionary(data, offset)
        offset += size

        # Entity Properties
        self.entity_properties, size = PacketEncoder.decode_entity_properties(data, offset)
        offset += size

        # Unique ID (li64)
        self.long_runtime_id, size = PacketEncoder.decode_li64(data, offset)
        offset += size

        # Permission Level
        self.permission_level, size = PacketEncoder.decode_permission_level(data, offset)
        offset += size

        # Command Permission Level
        self.command_permission, size = PacketEncoder.decode_command_permission_level(data, offset)
        offset += size

        # Abilities Length (uint8) → we skip abilities data for now
        abilities_len = data[offset]
        offset += 1 + (abilities_len * PacketEncoder.ABILITY_LAYER_SIZE) 

        # Entity Links
        self.links, size = PacketEncoder.decode_links(data, offset)
        offset += size

        # Device ID (string)
        self.device_id, size = PacketEncoder.decode_string(data, offset)
        offset += size

        # Device OS
        self.device_os, size = PacketEncoder.decode_device_os(data, offset)
        offset += size"""

# TEMPORARY /VANISH IMPLEMENTATION
player_packet_cache = {}

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

def cache_add_player_packet(self: "PrimeBDS", player: Player, packet: bytes):
    """Cache player packet in memory and update DB."""
    player_packet_cache[player.xuid] = packet
    self.db.update_user_data(player.name, "last_vanish_blob", packet)

def return_cached_add_player_packet(self: "PrimeBDS", player: Player) -> bytes:
    """Return packet from memory cache, fallback to DB if missing."""
    if player.xuid in player_packet_cache:
        return player_packet_cache[player.xuid]

    user = self.db.get_online_user(player.xuid)
    if user and user.last_vanish_blob:
        player_packet_cache[player.xuid] = user.last_vanish_blob
        return user.last_vanish_blob

    return None
