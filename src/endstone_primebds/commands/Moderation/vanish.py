from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.config_util import load_config

try:
    from endstone_primebds.utils.packet_utils.add_player import return_cached_add_player_packet
    from bedrock_protocol.packets import RemoveActorPacket
    PACKET_SUPPORT = True
except Exception:
    PACKET_SUPPORT = False

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "vanish",
    "Completely hide your server visibility!",
    ["/vanish"],
    ["primebds.command.vanish"]
)

# VANISH COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_message("This command can only be executed by a player")
        return False

    if not PACKET_SUPPORT:
        sender.send_message("§cVanish is disabled due to missing protocol library")
        return False

    user = self.db.get_online_user(sender.xuid)
    if user is None:
        sender.send_message("§6User not found in database")
        return False

    new_vanish_status = 0 if user.is_vanish else 1
    self.db.update_user_data(sender.name, "is_vanish", new_vanish_status)
    user.is_vanish = new_vanish_status
    self.vanish_state[sender.unique_id] = bool(new_vanish_status)

    sender.send_message(f"§6Vanish {'§aEnabled' if new_vanish_status else '§cDisabled'}")

    if new_vanish_status == 0:
        reveal_player(self, sender)
    else:
        hide_player(self, sender)

    return True


def hide_player(self: "PrimeBDS", target: Player):
    """Hide a player from all other online players."""
    if not PACKET_SUPPORT:
        return

    packet = RemoveActorPacket(target.id)
    packet_id = packet.get_packet_id()
    payload = packet.serialize()

    config = load_config()
    send_on_vanish = config["modules"]["join_leave_messages"]["send_on_vanish"]
    leave_message = config["modules"]["join_leave_messages"]["leave_message"]

    for player in self.server.online_players:
        if player.xuid != target.xuid:
            player.send_packet(packet_id, payload)
        if send_on_vanish:
            player.send_message(f"{leave_message.replace('{player}', target.name)}")


def reveal_player(self: "PrimeBDS", target: Player):
    """Reveal a player to all other online players."""
    if not PACKET_SUPPORT:
        return

    add_player_packet_id = 12
    payload = return_cached_add_player_packet(self, target)
    if payload is None:
        return

    config = load_config()
    send_on_vanish = config["modules"]["join_leave_messages"]["send_on_vanish"]
    join_message = config["modules"]["join_leave_messages"]["join_message"]

    for player in self.server.online_players:
        if player.xuid != target.xuid:
            player.send_packet(add_player_packet_id, payload)
        if send_on_vanish:
            player.send_message(f"{join_message.replace('{player}', target.name)}")
