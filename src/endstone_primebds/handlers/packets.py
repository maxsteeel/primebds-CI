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

from collections import defaultdict
from ctypes import c_int32
from binarystream import BinaryStream
from endstone.event import PacketSendEvent, PacketReceiveEvent
from endstone_primebds.utils.config_util import load_config

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

config = load_config()
modules = config.get("modules", {})
optimizer = modules.get("server_optimizer", {})

SKIN_MAX_SIZE = 2000 * 1024
mute_sounds = optimizer.get("mute_laggy_sounds", False)
mute_block_updates = optimizer.get("mute_laggy_block_events", False)
mute_movement_updates = optimizer.get("mute_laggy_movement_updates", False)

def handle_packetsend_event(self: "PrimeBDS", ev: PacketSendEvent):
    if not PACKET_SUPPORT:
        return

    pid = ev.packet_id

    if pid == MinecraftPacketIds.SubclientLogin:
        handle_subclient_login(self, ev)

    elif pid == MinecraftPacketIds.TileEvent and mute_block_updates:
        mute_redundant_block_events(self, ev)

    elif pid == MinecraftPacketIds.MovePlayer and mute_movement_updates:
        mute_redundant_move_events(self, ev)

    elif pid == MinecraftPacketIds.AddPlayer:
        handle_add_player_cache(self, ev)

    elif pid == MinecraftPacketIds.LevelSoundEvent and mute_sounds:
        handle_laggy_sounds(self, ev)

    if self.monitor_intervals:
        self.packets_sent_count[pid] = self.packets_sent_count.get(pid, 0) + 1

def handle_packetreceive_event(self: "PrimeBDS", ev: PacketReceiveEvent):
    pid = ev.packet_id

    if pid == MinecraftPacketIds.SubclientLogin:
        handle_subclient_login(self, ev)
        return

    elif pid == MinecraftPacketIds.LevelSoundEvent and mute_sounds:
        handle_laggy_sounds(self, ev)

    if self.monitor_intervals:
        self.packets_sent_count[pid] = self.packets_sent_count.get(pid, 0) + 1

def mute_redundant_move_events(self: "PrimeBDS", ev):
    stream = BinaryStream(ev.payload)

    runtime_id = stream.get_varint()
    x = stream.get_float()
    y = stream.get_float()
    z = stream.get_float()

    pitch = stream.get_float()
    yaw = stream.get_float()
    head_yaw = stream.get_float()

    mode = stream.get_unsigned_varint64()
    if mode == 2:
        ev.is_cancelled = True

received_open = defaultdict(set)
def make_key(x: int, y: int, z: int) -> str:
    return f"{x},{y},{z}"

def mute_redundant_block_events(self: "PrimeBDS", ev):
    stream = BinaryStream(ev.payload)
    x = stream.get_varint()
    y = c_int32(stream.get_unsigned_varint()).value
    z = stream.get_varint()
    type = stream.get_varint()
    data = stream.get_varint()

    if type not in (0, 1):
        return

    uuid = str(ev.player.unique_id)
    key = make_key(x, y, z)

    if type == 1:
        dx = ev.player.location.x - x
        dy = ev.player.location.y - y
        dz = ev.player.location.z - z
        dist = (dx*dx + dy*dy + dz*dz) ** 0.5

        if dist > 50.0:
            ev.is_cancelled = True
            return

        received_open[key].add(uuid)
        return

    elif type == 0:
        if key not in received_open or uuid not in received_open[key]:
            ev.is_cancelled = True
            return

        received_open.pop(key, None)
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

    if (sound in (42, 259, 290, 291, 292) or sound >= 566 or sound <= 0):
        ev.is_cancelled = True
        return

    if packet.entity_type == "minecraft:player":
        if self.vanish_state.get(packet.actor_unique_id, False):
            ev.is_cancelled = True
            return