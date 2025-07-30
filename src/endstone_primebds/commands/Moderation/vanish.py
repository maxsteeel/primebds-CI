from endstone import GameMode, Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors
from endstone_primebds.utils.packetUtil import build_add_player_packet, build_remove_actor_packet, build_add_actor_packet
from endstone_primebds.utils.dbUtil import UserDB

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
    if len(args) == 0:
        if not isinstance(sender, Player):
            sender.send_message("This command can only be executed by a player")
            return False
        
        user = self.db.get_online_user(sender.xuid)
        if user is None:
            sender.send_message("§6User not found in database")
            
            return False

        new_vanish_status = 0 if user.is_vanish else 1
        self.db.update_user_data(sender.name, "is_vanish", new_vanish_status)
        user.is_vanish = new_vanish_status
        sender.send_message(f"§6Vanish {'§aEnabled' if new_vanish_status else '§cDisabled'}.")
        
        if new_vanish_status == 0:

            cmd_perm = 0
            if sender.is_op:
                cmd_perm = 1

            id, payload = build_add_player_packet(
                sender.name,
                sender.unique_id.bytes,
                sender.runtime_id,
                (sender.location.x, sender.location.y, sender.location.z),
                (sender.velocity.x, sender.velocity.y, sender.velocity.z),
                sender.location.pitch,
                sender.location.yaw,
                0,
                sender.game_mode.value,
                0,
                0,
                sender.permission_level.value,
                cmd_perm,
                [],
                [],
                sender.device_id
            )
            

            for player in self.server.online_players:
                if player.xuid != sender.xuid:
                    player.send_packet(id, payload)

        else:
            id, payload = build_remove_actor_packet(sender.id)
            
            for player in self.server.online_players:
                if player.xuid != sender.xuid:
                    player.send_packet(id, payload)

        return True
