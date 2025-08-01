from endstone_primebds.utils.packet_utils.packet_util import (cache_add_player_packet, extract_player_name_from_addplayer, MinecraftPacketIds,
                                                 CloseContainerPacket, AddPlayerPacket)
from endstone_primebds.commands.Moderation.invsee import closeChestView
from endstone.event import PacketSendEvent, PacketReceiveEvent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_packetsend_event(self: "PrimeBDS", ev: PacketSendEvent):
    if ev.packet_id == MinecraftPacketIds.AddPlayer:

        target_player = self.server.get_player(extract_player_name_from_addplayer(ev.payload))
        cache_add_player_packet(self, target_player, ev.payload)
        if self.db.get_online_user(target_player.xuid).is_vanish:
            ev.is_cancelled = True

    elif ev.packet_id == MinecraftPacketIds.CloseContainer:
        packet = CloseContainerPacket()
        packet.deserialize(ev.payload)
        closeChestView(self, ev.player)
