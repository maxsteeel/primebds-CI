try:
    from bedrock_protocol.packets import MinecraftPacketIds, LevelSoundEventPacket, LevelSoundEventType
    from endstone_primebds.utils.packet_utils.add_player import (
        cache_add_player_packet,
        extract_player_name_from_addplayer,
    )
    PACKET_SUPPORT = True
except Exception as e:
    print(e)
    PACKET_SUPPORT = False

from endstone.event import PacketSendEvent, PacketReceiveEvent
from endstone_primebds.utils.config_util import load_config

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

config = load_config()
mute = config["modules"]["server_optimizer"]["mute_laggy_sounds"]
def handle_packetsend_event(self: "PrimeBDS", ev: PacketSendEvent):
    if not PACKET_SUPPORT:
        return 

    if ev.packet_id == MinecraftPacketIds.AddPlayer:
        player_name = extract_player_name_from_addplayer(ev.payload)
        target_player = self.server.get_player(player_name)
        if not target_player:
            return

        if target_player.xuid not in self.cached_players:
            cache_add_player_packet(self, target_player, ev.payload)
            self.cached_players.add(target_player.xuid)

        if self.vanish_state.get(target_player.unique_id, False):
            ev.is_cancelled = True
        return

    elif ev.packet_id == MinecraftPacketIds.LevelSoundEvent:
        packet = LevelSoundEventPacket()
        packet.deserialize(ev.payload)
        sound = packet.sound_type
        if mute and (sound == 259 or sound == 42):
            ev.is_cancelled = True
            return

        if packet.entity_type == "minecraft:player":
            if self.vanish_state.get(packet.actor_unique_id, False):
                ev.is_cancelled = True
                return
            
    self.packets_sent_count[ev.packet_id] = self.packets_sent_count.get(ev.packet_id, 0) + 1