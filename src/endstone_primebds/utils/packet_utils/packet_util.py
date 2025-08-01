import struct

from typing import TYPE_CHECKING, List, Optional
import uuid

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

from enum import Enum, IntEnum
from abc import ABC, abstractmethod

from endstone import Player
from endstone.inventory import ItemStack

class MinecraftPacketIds(IntEnum):
    AddPlayer = 12
    TakeItemEntity = 17
    RemoveEntity = 14
    UpdateBlock = 21
    BlockEvent = 26
    OpenContainer = 46
    CloseContainer = 47
    InventoryContent = 49
    PlayerList = 63
    ItemRegistry = 162

class DeviceOS(IntEnum):
    Undefined = 0
    Android = 1
    IOS = 2
    OSX = 3
    FireOS = 4
    GearVR = 5
    Hololens = 6
    Win10 = 7
    Win32 = 8
    Dedicated = 9
    TVOS = 10
    Orbis = 11
    NintendoSwitch = 12
    Xbox = 13
    WindowsPhone = 14
    Linux = 15

class ActionType(Enum):
    ADD = 0
    REMOVE = 1

class Color:
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 0

    def clamp(self):
        """Ensure each channel stays between 0 and 255."""
        self.r = max(0, min(255, self.r))
        self.g = max(0, min(255, self.g))
        self.b = max(0, min(255, self.b))
        self.a = max(0, min(255, self.a))
        return self

    @staticmethod
    def serialize_fcolor_rgb(color: "Color") -> bytes:
        """Serialize to 3 floats (RGB normalized to 0–1)."""
        return struct.pack(
            "<fff",
            color.r / 255.0,
            color.g / 255.0,
            color.b / 255.0
        )

    @staticmethod
    def deserialize_fcolor_rgb(data: bytes, offset: int = 0) -> "Color":
        """Deserialize 3 floats into a Color."""
        r, g, b = struct.unpack_from("<fff", data, offset)
        return Color(int(r * 255), int(g * 255), int(b * 255), 0)

    @staticmethod
    def serialize_icolor_rgba(color: "Color") -> bytes:
        """Serialize to 32-bit integer (little-endian)."""
        packed = (
            (color.r & 0xFF)
            | ((color.g & 0xFF) << 8)
            | ((color.b & 0xFF) << 16)
            | ((color.a & 0xFF) << 24)
        )
        return struct.pack("<i", packed)

    @staticmethod
    def deserialize_icolor_rgba(data: bytes, offset: int = 0) -> "Color":
        """Deserialize from 32-bit integer (little-endian)."""
        (packed,) = struct.unpack_from("<i", data, offset)
        return Color(
            packed & 0xFF,
            (packed >> 8) & 0xFF,
            (packed >> 16) & 0xFF,
            (packed >> 24) & 0xFF
        )
    
    @staticmethod
    def serialize_ivarcolor_rgba(color: "Color", encode_varint) -> bytes:
        """Serialize to VarInt with RGBA bit packing."""
        packed = (
            (color.r & 0xFF)
            | ((color.g & 0xFF) << 8)
            | ((color.b & 0xFF) << 16)
            | ((color.a & 0xFF) << 24)
        )
        return encode_varint(packed)

    @staticmethod
    def deserialize_ivarcolor_rgba(data: bytes, decode_varint, offset: int = 0) -> "Color":
        """Deserialize VarInt RGBA."""
        packed, size = decode_varint(data, offset)
        return Color(
            packed & 0xFF,
            (packed >> 8) & 0xFF,
            (packed >> 16) & 0xFF,
            (packed >> 24) & 0xFF
        )

class AddPlayerEntry:
    def __init__(self,
                 uuid,
                 actor_unique_id: int,
                 player_name: str,
                 xuid: str,
                 platform_chat_id: str,
                 build_platform: int,
                 skin_data: bytes,  # Need skin?
                 is_teacher: bool,
                 is_host: bool,
                 is_subclient: bool,
                 player_color: Color):  
        self.uuid = uuid
        self.actor_unique_id = actor_unique_id
        self.player_name = player_name
        self.xuid = xuid
        self.platform_chat_id = platform_chat_id
        self.build_platform = build_platform
        self.skin_data = skin_data
        self.is_teacher = is_teacher
        self.is_host = is_host
        self.is_subclient = is_subclient
        self.player_color = player_color

    def serialize(self) -> bytes:
        data = bytearray()
        data.extend(self.uuid.bytes)
        data.extend(PacketEncoder.encode_varint(PacketEncoder.encode_zigzag64(self.actor_unique_id)))
        data.extend(PacketEncoder.encode_string(self.player_name))
        data.extend(PacketEncoder.encode_string(self.xuid))
        data.extend(PacketEncoder.encode_string(self.platform_chat_id))
        data.extend(PacketEncoder.encode_li32(self.build_platform))
        data.extend(self.skin_data)  # TODO: serialize full skin if needed
        data.append(1 if self.is_teacher else 0)
        data.append(1 if self.is_host else 0)
        data.append(1 if self.is_subclient else 0)
        data.extend(Color.serialize_icolor_rgba(self.player_color))
        return bytes(data)

    @classmethod
    def deserialize(cls, data: bytes, offset: int = 0) -> tuple["AddPlayerEntry", int]:
        uuid_ = PacketEncoder.decode_uuid(data, offset)
        offset += 16

        raw_id, size_id = PacketEncoder.decode_varint(data, offset)
        actor_unique_id = PacketEncoder.decode_zigzag64(raw_id)
        offset += size_id

        player_name, size_name = PacketEncoder.decode_string(data, offset)
        offset += size_name

        xuid, size_xuid = PacketEncoder.decode_string(data, offset)
        offset += size_xuid

        platform_chat_id, size_platform = PacketEncoder.decode_string(data, offset)
        offset += size_platform

        build_platform_id, _ = PacketEncoder.decode_li32(data, offset)
        build_platform = build_platform_id
        offset += 4

        skin_data = b""  # placeholder for future Skin deserialization

        is_teacher = bool(data[offset]); offset += 1
        is_host = bool(data[offset]); offset += 1
        is_subclient = bool(data[offset]); offset += 1

        player_color = Color.deserialize_icolor_rgba(data, offset)
        offset += 4

        return cls(uuid_, actor_unique_id, player_name, xuid, platform_chat_id,
                   build_platform, skin_data, is_teacher, is_host,
                   is_subclient, player_color), offset

class Packet(ABC):
    @abstractmethod
    def get_packet_id(self) -> 'MinecraftPacketIds':
        pass

    @abstractmethod
    def serialize(self) -> bytes:
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> None:
        pass

class AddPlayerPacket(Packet):
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
        """parts.append(PacketEncoder.encode_entity_properties(self.entity_properties))
        parts.append(struct.pack("<q", self.long_runtime_id))
        parts.append(PacketEncoder.encode_permission_level(self.permission_level))
        parts.append(PacketEncoder.encode_command_permission_level(self.command_permission))
        parts.append(PacketEncoder.encode_links(self.links))
        parts.append(PacketEncoder.encode_string(self.device_id))
        parts.append(PacketEncoder.encode_device_os(self.device_os))"""

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

"""
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

class UpdateBlockPacket(Packet):
    def __init__(self, 
                 x: int,
                 y: int,
                 z: int, 
                 block_runtime_id: int = 0, 
                 update_flag: int = 3, 
                 block_layer: int = 0):
        self.x = x
        self.y = y
        self.z = z
        self.block_runtime_id = block_runtime_id
        self.update_flag = update_flag
        self.block_layer = block_layer

    def get_packet_id(self) -> 'MinecraftPacketIds':
        return MinecraftPacketIds.UpdateBlock

    def serialize(self) -> bytes:
        return (
            PacketEncoder.encode_varint(PacketEncoder.encode_zigzag32(self.x)) +
            PacketEncoder.encode_varint(self.y) +
            PacketEncoder.encode_varint(PacketEncoder.encode_zigzag32(self.z)) +
            PacketEncoder.encode_varint(self.block_runtime_id) +
            PacketEncoder.encode_varint(self.update_flag) +
            PacketEncoder.encode_varint(self.block_layer)
        )

    def deserialize(self, data: bytes) -> None:
        offset = 0
        self.x, size_x = PacketEncoder.decode_varint(data, offset)
        offset += size_x

        self.y, size_y = PacketEncoder.decode_uvarint(data, offset)
        offset += size_y

        self.z, size_z = PacketEncoder.decode_varint(data, offset)
        offset += size_z

        # Decode varint first
        zigzag_encoded, size_runtime = PacketEncoder.decode_varint(data, offset)
        offset += size_runtime

        # Then decode zigzag to get the signed value
        self.block_runtime_id = PacketEncoder.decode_zigzag64(zigzag_encoded)

        self.update_flag, size_flag = PacketEncoder.decode_uvarint(data, offset)
        offset += size_flag

        self.block_layer, _ = PacketEncoder.decode_uvarint(data, offset)

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
        return (
            struct.pack("<bb", self.window_id, self.window_type) +
            PacketEncoder.encode_varint(PacketEncoder.encode_zigzag32(self.x)) +
            PacketEncoder.encode_varint(self.y) +
            PacketEncoder.encode_varint(PacketEncoder.encode_zigzag32(self.z)) +
            PacketEncoder.encode_varint(self.container_unique_id)
        )

    def deserialize(self, data: bytes) -> None:
        self.window_id, self.window_type = struct.unpack_from("<bb", data, 0)
        offset = struct.calcsize("<bb")

        (self.x, self.y, self.z), size_pos = PacketEncoder.decode_block_position(data, offset)
        offset += size_pos

        zigzag_val, size_id = PacketEncoder.decode_varint(data, offset)
        offset += size_id
        self.container_unique_id = PacketEncoder.decode_zigzag64(zigzag_val)

class CloseContainerPacket(Packet):
    def __init__(self, 
                 window_id: int = 2,
                 window_type: int = 0,
                 server: bool = False):
        self.window_id = window_id
        self.window_type = window_type
        self.server = server

    def get_packet_id(self) -> 'MinecraftPacketIds':
        return MinecraftPacketIds.ContainerClose

    def serialize(self) -> bytes:
        return struct.pack("<bb?", self.window_id, self.window_type, self.server)

    def deserialize(self, data: bytes) -> None:
        self.window_id, self.window_type, self.server = struct.unpack_from("<bb?", data, 0)

class InventoryContentPacket(Packet): # CURRENTLY BUGGED
    def __init__(self,
                 window_id: int = 0,
                 content: list = None,
                 container_name: str = "",
                 storage_item=None):
        self.window_id = window_id
        self.content = content if content is not None else []
        self.container_name = container_name
        self.storage_item = storage_item

    def get_packet_id(self) -> 'MinecraftPacketIds':
        return MinecraftPacketIds.InventoryContent

    def serialize(self) -> bytes:
        payload = PacketEncoder.encode_uvarint(self.window_id)
        payload += PacketEncoder.encode_varint(len(self.content))
        for item in self.content:
            payload += item.serialize()
        payload += PacketEncoder.encode_string(self.container_name)
        payload += self.storage_item.serialize() if self.storage_item else b"\x00"
        return payload

    def deserialize(self, data: bytes) -> None:
        offset = 0

        self.window_id, size_id = PacketEncoder.decode_uvarint(data, offset)
        offset += size_id

        length, size_len = PacketEncoder.decode_varint(data, offset)
        offset += size_len

        self.content = []
        for _ in range(length):
            item = ItemStack()
            item.deserialize(data[offset:])
            offset += item.get_size()
            self.content.append(item)

        self.container_name, size_name = PacketEncoder.decode_string(data, offset)
        offset += size_name

        self.storage_item = ItemStack()
        self.storage_item.deserialize(data[offset:])

class PlayerListPacket: # CURRENTLY BUGGED
    def __init__(self,
                 action_type: ActionType,
                 add_player_list: Optional[List[AddPlayerEntry]] = None,
                 trusted_skin_list: Optional[List[bool]] = None,
                 remove_player_list = None):
        self.action_type = action_type
        self.add_player_list = add_player_list or []
        self.trusted_skin_list = trusted_skin_list or []
        self.remove_player_list = remove_player_list or []

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.PlayerList

    def serialize(self) -> bytes:
        data = bytearray()
        data.append(self.action_type.value)

        if self.action_type == ActionType.ADD:
            data.extend(PacketEncoder.encode_varint(len(self.add_player_list)))
            for entry in self.add_player_list:
                data.extend(entry.serialize())

            data.extend(PacketEncoder.encode_varint(len(self.trusted_skin_list)))
            for trusted in self.trusted_skin_list:
                data.append(1 if trusted else 0)

        else: 
            data.extend(PacketEncoder.encode_varint(len(self.remove_player_list)))
            for player_uuid in self.remove_player_list:
                data.extend(player_uuid.bytes)

        return bytes(data)

    @classmethod
    def deserialize(cls, data: bytes) -> "PlayerListPacket":
        offset = 0
        action_type = ActionType(data[offset])
        offset += 1

        if action_type == ActionType.ADD:
            count, size_count = PacketEncoder.decode_varint(data, offset)
            offset += size_count

            add_list = []
            for _ in range(count):
                entry, offset = AddPlayerEntry.deserialize(data, offset)
                add_list.append(entry)

            trusted_count, size_trusted = PacketEncoder.decode_varint(data, offset)
            offset += size_trusted

            trusted_list = []
            for _ in range(trusted_count):
                trusted_list.append(bool(data[offset]))
                offset += 1

            return cls(action_type, add_list, trusted_list, None)

        else:
            count, size_count = PacketEncoder.decode_varint(data, offset)
            offset += size_count

            remove_list = []
            for _ in range(count):
                player_uuid = PacketEncoder.decode_uuid(data, offset)
                offset += 16
                remove_list.append(player_uuid)

            return cls(action_type, None, None, remove_list)

class RemoveEntityPacket(Packet):
    def __init__(self, actor_id):
        self.actor_id = actor_id

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.RemoveEntity
    
    def serialize(self) -> bytes:
        varint_bytes = PacketEncoder.encode_varint(PacketEncoder.encode_zigzag64(self.actor_id))
        return bytes(varint_bytes)
    
    def deserialize(self, data: bytes) -> None:
        raw_id, _ = PacketEncoder.decode_varint(data)
        self.actor_id = PacketEncoder.decode_zigzag64(raw_id)

class PacketEncoder:
    
    @staticmethod
    def decode_uuid(data: bytes, offset=0) -> tuple[str, int]:
        """
        Decode UUID represented as two 64-bit longs (most, least).
        Returns the UUID string and number of bytes read (16).
        """
        if len(data) < offset + 16:
            raise ValueError("Not enough bytes to decode UUID")

        most, least = struct.unpack_from(">QQ", data, offset)  # big-endian unsigned long long
        # Compose UUID from two 64-bit values
        # The standard UUID bytes are big-endian, so combine accordingly
        uuid_int = (most << 64) | least
        u = uuid.UUID(int=uuid_int)
        return str(u), 16

    @staticmethod
    def encode_uuid(u: uuid.UUID) -> bytes:
        """
        Encode UUID to two 64-bit longs (most, least).
        """
        # UUID int is 128-bit integer
        uuid_int = u.int
        most = (uuid_int >> 64) & ((1 << 64) - 1)
        least = uuid_int & ((1 << 64) - 1)
        return struct.pack(">QQ", most, least)

    @staticmethod
    def decode_block_position(data: bytes, offset: int = 0):
        start_offset = offset

        # Decode signed VarInt for X
        x, size_x = PacketEncoder.decode_varint(data, offset)
        offset += size_x

        # Decode unsigned VarInt for Y
        y, size_y = PacketEncoder.decode_uvarint(data, offset)
        offset += size_y

        # Decode signed VarInt for Z
        z, size_z = PacketEncoder.decode_varint(data, offset)
        offset += size_z

        total_size = offset - start_offset
        return (x, y, z), total_size

    @staticmethod
    def encode_uvarint(value: int) -> bytes:
        if value < 0:
            raise ValueError("Cannot encode negative number as unsigned varint")

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
    
    @staticmethod
    def decode_uvarint(data: bytes, offset: int = 0):
        value = 0
        shift = 0
        size = 0

        while True:
            byte = data[offset]
            offset += 1
            size += 1

            value |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7

        return value, size

    @staticmethod
    def encode_varint(value: int) -> bytes:
        buffer = bytearray()
        while True:
            temp = value & 0x7F
            value >>= 7
            if value != 0:
                buffer.append(temp | 0x80)
            else:
                buffer.append(temp)
                break
        return bytes(buffer)

    @staticmethod
    def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
        value = 0
        shift = 0
        pos = offset
        while True:
            byte = data[pos]
            value |= (byte & 0x7F) << shift
            shift += 7
            pos += 1
            if not (byte & 0x80):
                break
        return value, pos - offset

    @staticmethod
    def encode_uvarlong(value: int) -> bytes:
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

    @staticmethod
    def decode_uvarlong(data: bytes, offset: int = 0) -> tuple[int, int]:
        value = 0
        shift = 0
        pos = offset
        while True:
            byte = data[pos]
            value |= (byte & 0x7F) << shift
            shift += 7
            pos += 1
            if not (byte & 0x80):
                break
        return value, pos - offset

    @staticmethod
    def encode_string(s: str) -> bytes:
        encoded = s.encode("utf-8")
        return PacketEncoder.encode_varint(len(encoded)) + encoded

    @staticmethod
    def decode_string(data: bytes, offset: int = 0) -> tuple[str, int]:
        length, length_size = PacketEncoder.decode_varint(data, offset)
        start = offset + length_size
        end = start + length
        raw_bytes = data[start:end]
        try:
            decoded = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            decoded = raw_bytes.hex()  # fallback
        return decoded, length_size + length

    @staticmethod
    def encode_position(x: int, y: int, z: int) -> bytes:
        return struct.pack('<iii', x, y, z)

    @staticmethod
    def decode_position(data: bytes, offset: int = 0) -> tuple[tuple[int, int, int], int]:
        x, y, z = struct.unpack_from('<iii', data, offset)
        return (x, y, z), 12

    @staticmethod
    def encode_zigzag32(n: int) -> int:
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def decode_zigzag32(n: int) -> int:
        return (n >> 1) ^ -(n & 1)

    @staticmethod
    def encode_zigzag64(value: int) -> int:
        return (value << 1) ^ (value >> 63)

    @staticmethod
    def decode_zigzag64(value: int) -> int:
        return (value >> 1) ^ -(value & 1)

    @staticmethod
    def encode_li64(value: int) -> bytes:
        return struct.pack("<q", value)

    @staticmethod
    def decode_li64(data: bytes, offset: int = 0) -> tuple[int, int]:
        value = struct.unpack_from("<q", data, offset)[0]
        return value, 8

    @staticmethod
    def encode_li32(value: int) -> bytes:
        return struct.pack("<i", value)

    @staticmethod
    def decode_li32(data: bytes, offset: int = 0) -> tuple[int, int]:
        value = struct.unpack_from("<i", data, offset)[0]
        return value, 4
    
    @staticmethod
    def decode_uint8(data: bytes, offset: int = 0) -> tuple[int, int]:
        value = struct.unpack_from("<B", data, offset)[0]
        return value, 1

    @staticmethod
    def decode_bool(data: bytes, offset: int = 0) -> tuple[bool, int]:
        value = struct.unpack_from("<?", data, offset)[0]
        return value, 1

    @staticmethod
    def decode_int32(data: bytes, offset: int = 0) -> tuple[int, int]:
        value = struct.unpack_from("<i", data, offset)[0]
        return value, 4

    @staticmethod
    def decode_float(data: bytes, offset: int = 0) -> tuple[float, int]:
        value = struct.unpack_from("<f", data, offset)[0]
        return value, 4

    @staticmethod
    def decode_double(data: bytes, offset=0) -> tuple[float, int]:
        if offset + 8 > len(data):
            raise ValueError("Not enough bytes to decode double")
        value = struct.unpack_from("<d", data, offset)[0]
        return value, 8
    
    @staticmethod
    def decode_item(data: bytes, offset=0):
        # Decoding 'Item' from prismarine docs
        start_offset = offset

        # item id (zigzag varint)
        raw_id, size = PacketEncoder.decode_varint(data, offset)
        item_id = PacketEncoder.decode_zigzag32(raw_id)
        offset += size

        # aux (zigzag varint)
        raw_aux, size = PacketEncoder.decode_varint(data, offset)
        aux = PacketEncoder.decode_zigzag32(raw_aux)
        offset += size

        # count (byte)
        count = data[offset]
        offset += 1
        nbt_data = None

        return {"item_id": item_id, "aux": aux, "count": count, "nbt": nbt_data}, offset - start_offset

    @staticmethod
    def decode_metadata_dictionary(data: bytes, offset=0):
        start_offset = offset
        # metadata dictionary format (varint count + entries)
        metadata = []
        count, size = PacketEncoder.decode_varint(data, offset)
        offset += size

        for _ in range(count):
            if offset >= len(data):
                break
            # id (varint)
            key, size = PacketEncoder.decode_varint(data, offset)
            offset += size
            # type (varint)
            meta_type, size = PacketEncoder.decode_varint(data, offset)
            offset += size

            # value - parsing depends on meta_type
            # Here, we'll do some common types, others you can expand
            if meta_type == 0:  # Byte
                val = data[offset]
                offset += 1
            elif meta_type == 1:  # Int32
                val, s = PacketEncoder.decode_int32(data, offset)
                offset += s
            elif meta_type == 2:  # Float
                val, s = PacketEncoder.decode_float(data, offset)
                offset += s
            elif meta_type == 3:  # String
                val, s = PacketEncoder.decode_string(data, offset)
                offset += s
            else:
                # Unknown or complex type - skip or handle accordingly
                val = None
            metadata.append({"key": key, "type": meta_type, "value": val})

        return metadata, offset - start_offset

    @staticmethod
    def decode_entity_properties(data: bytes, offset=0):
        start_offset = offset
        properties = []

        # Read number of properties
        count, size = PacketEncoder.decode_varint(data, offset)
        offset += size

        for _ in range(count):
            if offset >= len(data):
                break  # Prevent buffer overflow if data ends unexpectedly

            # Decode property name (string)
            name, size = PacketEncoder.decode_string(data, offset)
            offset += size

            # Decode property value (double)
            if offset + 8 > len(data):
                raise ValueError("Not enough bytes to decode property value (double)")
            val, size = PacketEncoder.decode_double(data, offset)
            offset += size

            # Decode modifier count (varint)
            modifier_count, size = PacketEncoder.decode_varint(data, offset)
            offset += size

            modifiers = []
            for __ in range(modifier_count):
                if offset + 16 > len(data):
                    raise ValueError("Not enough bytes to decode modifier UUID")
                uuid_bytes = data[offset:offset + 16]
                modifier_uuid = PacketEncoder.decode_uuid(uuid_bytes)
                offset += 16

                if offset + 8 > len(data):
                    raise ValueError("Not enough bytes to decode modifier amount")
                amount, size = PacketEncoder.decode_double(data, offset)
                offset += size

                if offset + 1 > len(data):
                    raise ValueError("Not enough bytes to decode modifier operation")
                operation = data[offset]
                offset += 1

                modifiers.append({
                    "uuid": modifier_uuid,
                    "amount": amount,
                    "operation": operation,
                })

            properties.append({
                "name": name,
                "value": val,
                "modifiers": modifiers
            })

        return properties, offset - start_offset

    @staticmethod
    def decode_permission_level(data: bytes, offset=0):
        # uint8
        return PacketEncoder.decode_uint8(data, offset)

    @staticmethod
    def decode_command_permission_level(data: bytes, offset=0):
        # uint8
        return PacketEncoder.decode_uint8(data, offset)

    @staticmethod
    def decode_links(data: bytes, offset=0):
        start_offset = offset
        links = []

        count, size = PacketEncoder.decode_varint(data, offset)
        offset += size

        for _ in range(count):
            # entityUniqueIdA (varint)
            ent_a, size = PacketEncoder.decode_varint(data, offset)
            offset += size

            # entityUniqueIdB (varint)
            ent_b, size = PacketEncoder.decode_varint(data, offset)
            offset += size

            # type (varint)
            link_type, size = PacketEncoder.decode_varint(data, offset)
            offset += size

            # immediate (bool)
            immediate, size = PacketEncoder.decode_bool(data, offset)
            offset += size

            links.append({
                "entity_a": ent_a,
                "entity_b": ent_b,
                "type": link_type,
                "immediate": immediate
            })

        return links, offset - start_offset

    @staticmethod
    def decode_device_os(data: bytes, offset=0):
        return PacketEncoder.decode_int32(data, offset)

class PacketDebugger:
    @staticmethod
    def debug(packet_bytes: bytes):
        if not isinstance(packet_bytes, (bytes, bytearray)):
            raise TypeError("debug expects bytes or bytearray")

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
            print("Packet ends with multiple null bytes")
        print("Debug complete\n")

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
