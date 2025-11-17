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

    pid = ev.packet_id

    SEND_HANDLERS = {
        MinecraftPacketIds.SubclientLogin: handle_subclient_login,
        MinecraftPacketIds.AddPlayer: handle_add_player_cache,
        MinecraftPacketIds.LevelSoundEvent: handle_laggy_sounds
    }

    handler = SEND_HANDLERS.get(pid)
    if handler:
        handler(self, ev)

    if self.monitor_intervals:
        self.packets_sent_count[pid] = self.packets_sent_count.get(pid, 0) + 1


def handle_packetrecieve_event(self: "PrimeBDS", ev: PacketReceiveEvent):
    pid = ev.packet_id

    RECEIVE_HANDLERS = {
        MinecraftPacketIds.Login: handle_login_crasher,
        MinecraftPacketIds.LevelSoundEvent: handle_laggy_sounds,
    }

    handler = RECEIVE_HANDLERS.get(pid)
    if handler:
        handler(self, ev)

    if self.monitor_intervals:
        self.packets_sent_count[pid] = self.packets_sent_count.get(pid, 0) + 1

def handle_login_crasher(self: "PrimeBDS", ev):
    if PACKET_SUPPORT == False:
        return

    return

def handle_subclient_login(self: "PrimeBDS", ev: PacketSendEvent):
    if not self.gamerules.get("subclient"):
        if ev.sub_client_id is not 0:
            ev.is_cancelled = True

def handle_add_player_cache(self: "PrimeBDS", ev):
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

def handle_laggy_sounds(self: "PrimeBDS", ev):
    packet = minecraft_packets.LevelSoundEventPacket()
    packet.deserialize(ev.payload)
    sound = packet.sound_type

    if mute and (sound in (42, 259, 290, 291, 292) or sound >= 566 or sound <= 0):
        ev.is_cancelled = True
        return

    if packet.entity_type == "minecraft:player":
        if self.vanish_state.get(packet.actor_unique_id, False):
            ev.is_cancelled = True
            return