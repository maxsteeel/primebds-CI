from endstone_primebds.utils.packets.add_player import cache_add_player_packet
from endstone_primebds.utils.packets.packetUtil import extract_player_name_from_addplayer
from endstone.event import PacketSendEvent, PacketReceiveEvent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_packetsend_event(self: "PrimeBDS", ev: PacketSendEvent):
    if ev.packet_id == 12:  # AddPlayerActor
        target_player = self.server.get_player(extract_player_name_from_addplayer(ev.payload))
        cache_add_player_packet(self, target_player, ev.payload)
        
        if self.db.get_online_user(target_player.xuid).is_vanish:
            ev.is_cancelled = True