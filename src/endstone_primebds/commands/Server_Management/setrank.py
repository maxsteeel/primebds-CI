from endstone import ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.dbUtil import UserDB
from endstone_primebds.utils.internalPermissionsUtil import RANKS
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "setrank",
    "Sets the internal permissions for a player!",
    ["/setrank <player: player> (default|helper|mod|operator)<rank: rank>"],
    ["primebds.command.setrank"]
)

# SETRANK COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) < 2:
        sender.send_message("Usage: /setrank <player> <rank>")
        return False

    targets = get_matching_actors(self, args[0], sender)
    new_rank = args[1].lower()

    if new_rank not in [r.lower() for r in RANKS]:
        sender.send_message(f"Invalid rank: {new_rank}. Valid ranks are: {', '.join(RANKS)}")
        return False

    db = UserDB("users.db")

    for target in targets:
        player_name = target.name
        user = db.get_offline_user(player_name)

        if not user:
            sender.send_message(f"Could not find user data for player {player_name}.")
            continue

        current_rank = user.internal_rank
        if current_rank.lower() == new_rank:
            sender.send_message(f"Player {player_name} already has the rank {new_rank}. No changes made.")
            continue

        for rank in RANKS:
            if rank.lower() == new_rank:
                db.update_user_data(player_name, 'internal_rank', rank)

                if new_rank == "operator":
                    self.server.dispatch_command(self.server.command_sender, f"op {player_name}")
                else:
                    self.server.dispatch_command(self.server.command_sender, f"deop {player_name}")
                    if target.is_op:
                        sender.send_message(
                            f"Warning: internal OP level is currently set to 4, and {player_name}'s OP status could not be revoked."
                        )
                self.reload_custom_perms(target)

                sender.send_message(
                    f"Player §e{player_name}'s {ColorFormat.WHITE}rank was updated to §e{rank.upper()}"
                )

    db.close_connection()
    return True
