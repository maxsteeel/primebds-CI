try:
    from bedrock_protocol.packets import minecraft_packets, MinecraftPacketIds
    from endstone_primebds.utils.packet_utils.add_player import (
        cache_add_player_packet,
        extract_player_name_from_addplayer,
    )
    PACKET_SUPPORT = True
except Exception as e:
    print(e)
    PACKET_SUPPORT = False

from endstone.event import PacketSendEvent
from endstone_primebds.utils.config_util import load_config
from collections import defaultdict
from time import time

CACHED_PACKETS = defaultdict(dict)
CACHE_METADATA = {} 

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

config = load_config()
mute = config["modules"]["server_optimizer"]["mute_laggy_sounds"]
packet_cache = config["modules"]["server_optimizer"]["cache_simple_packets"]

def handle_packetsend_event(self: "PrimeBDS", ev: PacketSendEvent):
    if not PACKET_SUPPORT:
        return

    pid = ev.packet_id

    if pid == MinecraftPacketIds.AddPlayer:
        player_name = extract_player_name_from_addplayer(ev.payload)
        target_player = self.server.get_player(player_name)
        if not target_player:
            return

        xuid = target_player.xuid
        if xuid in self.cached_players:
            return

        cache_add_player_packet(self, target_player, ev.payload)
        self.cached_players.add(xuid)

        if self.vanish_state.get(target_player.unique_id, False):
            ev.is_cancelled = True
        return

    elif pid == MinecraftPacketIds.LevelSoundEvent:
        packet = minecraft_packets.LevelSoundEventPacket()
        packet.deserialize(ev.payload)
        sound = packet.sound_type

        if mute and sound in (259, 42):
            ev.is_cancelled = True
            return

        if packet.entity_type == "minecraft:player":
            if self.vanish_state.get(packet.actor_unique_id, False):
                ev.is_cancelled = True
                return

    if packet_cache:
        if pid == MinecraftPacketIds.BiomeDefinitionList:
            if cached := get_cached_packet(pid, "biomes"):
                ev.payload = cached
            else:
                cache_packet(pid, "biomes", ev.payload, source="biomes")
    
    if self.monitor_intervals:
        self.packets_sent_count[pid] = self.packets_sent_count.get(pid, 0) + 1

def cache_packet(packet_id: int, key: str, payload: bytes, source: str = ""):
    CACHED_PACKETS[packet_id][key] = payload
    CACHE_METADATA[(packet_id, key)] = {
        "timestamp": time(),
        "source": source,
    }

def get_cached_packet(packet_id: int, key: str):
    packet_map = CACHED_PACKETS.get(packet_id)
    if not packet_map:
        return None
    return packet_map.get(key)

def invalidate_cached_packet(packet_id: int, key: str):
    if packet_id in CACHED_PACKETS and key in CACHED_PACKETS[packet_id]:
        del CACHED_PACKETS[packet_id][key]
        CACHE_METADATA.pop((packet_id, key), None)