import struct
from typing import List, Optional
from endstone_primebds.utils.packet_utils.packet_util import Packet, MinecraftPacketIds
from enum import Enum
from uuid import UUID
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

class ActionType(Enum):
    ADD = 0
    REMOVE = 1
"""
class PlayerListPacket(Packet):
    def __init__(self,
                action_type: Optional[ActionType] = None,
                players: Optional[List[dict]] = None,
                trusted_skin_list: Optional[List[bool]] = None):
        self.action_type = action_type
        self.players = players or []
        self.trusted_skin_list = trusted_skin_list or []

    def get_packet_id(self) -> MinecraftPacketIds:
        return MinecraftPacketIds.PlayerList

    def serialize(self) -> bytes:
        data = bytearray()
        data.append(self.action_type.value)

        if self.action_type == ActionType.ADD:
            data.extend(PacketEncoder.encode_varint(len(self.players)))
            for player in self.players:
                uuid_bytes =  PacketEncoder.encode_uuid(player.unique_id)
                data.extend(uuid_bytes)
                data.extend(PacketEncoder.encode_varint(PacketEncoder.encode_zigzag64(player.id)))
                data.extend(PacketEncoder.encode_string(player.name))
                data.extend(PacketEncoder.encode_string(player.xuid))
                data.extend(PacketEncoder.encode_string(str("")))
                data.extend(PacketEncoder.encode_li32(0))
                data.extend(Skin(player.skin.id).serialize())
                data.append(0)
                data.append(0)
                data.append(0)
                data.extend(struct.pack("<i", 0))

            data.extend(PacketEncoder.encode_varint(len(self.trusted_skin_list)))
            for trusted in self.trusted_skin_list:
                data.append(1 if trusted else 0)

        else: 
            data.extend(PacketEncoder.encode_varint(len(self.players)))
            for player in self.players:
                uuid_bytes = PacketEncoder.encode_uuid(UUID(str(player["uuid"])))
                data.extend(uuid_bytes)

        return bytes(data)

    def deserialize(self, data: bytes) -> None:
        offset = 0
        self.action_type = ActionType(data[offset])
        offset += 1

        self.players = []

        if self.action_type == ActionType.ADD:
            count, size_count = PacketEncoder.decode_varint(data, offset)
            offset += size_count

            for _ in range(count):
                uuid_ = PacketEncoder.decode_uuid(data, offset)
                offset += 16

                raw_id, size_id = PacketEncoder.decode_varint(data, offset)
                entity_id = PacketEncoder.decode_zigzag64(raw_id)
                offset += size_id

                username, size_name = PacketEncoder.decode_string(data, offset)
                offset += size_name

                xuid, size_xuid = PacketEncoder.decode_string(data, offset)
                offset += size_xuid

                platform_chat_id, size_platform = PacketEncoder.decode_string(data, offset)
                offset += size_platform

                build_platform, _ = PacketEncoder.decode_li32(data, offset)
                offset += 4

                skin_data = ""

                is_teacher = bool(data[offset]); offset += 1
                is_host = bool(data[offset]); offset += 1
                is_subclient = bool(data[offset]); offset += 1

                (player_color,) = struct.unpack_from("<i", data, offset)
                offset += 4

                self.players.append({
                    "uuid": uuid_,
                    "entity_id": entity_id,
                    "username": username,
                    "xuid": xuid,
                    "platform_chat_id": platform_chat_id,
                    "build_platform": build_platform,
                    "skin_data": skin_data,
                    "is_teacher": is_teacher,
                    "is_host": is_host,
                    "is_subclient": is_subclient,
                    "player_color": player_color
                })

            trusted_count, size_trusted = PacketEncoder.decode_varint(data, offset)
            offset += size_trusted

            self.trusted_skin_list = [bool(data[offset + i]) for i in range(trusted_count)]
            offset += trusted_count

        else:
            count, size_count = PacketEncoder.decode_varint(data, offset)
            offset += size_count

            for _ in range(count):
                player_uuid = PacketEncoder.decode_uuid(data, offset)
                offset += 16
                self.players.append({"uuid": player_uuid})
"""