import struct
from endstone import Player
from endstone_primebds.utils.packets.packet_util import encode_varint, encode_varint64, encode_string, encode_uvarlong

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

player_packet_cache = {}

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

def build_add_player_packet(
    username: str,
    player_uuid: bytes,
    entity_runtime_id: int,
    position: tuple[float, float, float],
    velocity: tuple[float, float, float],
    pitch: float,
    yaw: float,
    held_item: int,
    gamemode: int,
    metadata: int,
    entityprops: int,
    permlevel: int,
    cmdpermlevel: int,
    abilities: list,
    links: list,
    deviceID: str
) -> tuple[int, bytes]:
    packet_id = 12
    packet = bytearray()
    
    # UUID (16 bytes)
    packet.extend(player_uuid)

    # Username (MC String)
    packet.extend(encode_string(username))

    # Runtime ID (unsigned varint64)
    packet.extend(encode_varint64(entity_runtime_id))

    # Platform Chat ID (empty)
    packet.extend(encode_string(""))

    # Position floats (x, y, z)
    packet.extend(struct.pack("<fff", *position))

    # Velocity floats
    packet.extend(struct.pack("<fff", *velocity))

    # Pitch, yaw, head yaw
    packet.extend(struct.pack("<fff", pitch, yaw, yaw))

    # Held item (varint ZigZag32)
    packet.extend(encode_uvarlong(held_item))

    # Gamemode (varint ZigZag32)
    packet.extend(encode_uvarlong(gamemode))

    """
    # Metadata + Entity properties (both pre-encoded varints)
    packet.extend(encode_varint(metadata))
    packet.extend(encode_varint(entityprops))

    # li64 Runtime ID
    packet.extend(struct.pack("<q", entity_runtime_id))

    # Permission levels (2x u8)
    packet.extend(struct.pack("BB", permlevel & 0xFF, cmdpermlevel & 0xFF))

    # Abilities length, layer length, links length (3x u8)
    packet.extend(struct.pack("BBB", len(abilities) & 0xFF, len(abilities) & 0xFF, len(links) & 0xFF))

    # Device ID
    packet.extend(encode_string(deviceID))

    # Device OS (li32)
    packet.extend(struct.pack("<i", 0))"""

    return packet_id, bytes(packet)