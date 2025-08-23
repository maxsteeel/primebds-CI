from bedrock_protocol.packets import MinecraftPacketIds
from endstone_primebds.utils.packet_utils.level_sound import LevelSoundEventPacket
from endstone_primebds.utils.packet_utils.add_player import cache_add_player_packet, extract_player_name_from_addplayer
from endstone.event import PacketSendEvent, PacketReceiveEvent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_packetsend_event(self: "PrimeBDS", ev: PacketSendEvent):
    if ev.packet_id == MinecraftPacketIds.AddPlayer:
        target_player = self.server.get_player(extract_player_name_from_addplayer(ev.payload))
        cache_add_player_packet(self, target_player, ev.payload)

        user = self.db.get_online_user(target_player.xuid) if target_player else None
        if user is not None and getattr(user, "is_vanish", None):
            ev.is_cancelled = True

    elif ev.packet_id == MinecraftPacketIds.LevelSoundEvent:
        packet = LevelSoundEventPacket()
        packet.deserialize(ev.payload)
        entity_id = packet.actor_unique_id
        print(entity_id)
        user = self.db.get_online_user_by_unique_id(entity_id)
        if user is not None and getattr(user, "is_vanish", None):
            ev.is_cancelled = True
        
def handle_packetreceive_event(self: "PrimeBDS", ev: PacketReceiveEvent):
    return

            

