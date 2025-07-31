from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "hidechat",
    "Hides player-sent chat messages from your view!",
    ["/hidechat"],
    ["primebds.command.hidechat"],
    "true"
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, Player):
        target = self.server.get_player(sender.name)
        self.server.dispatch_command(self.server.command_sender,
                                     f"execute as \"{target.name}\" run scriptevent wmct:endstone mute")
    else:
        sender.send_error_message("This command can only be executed by a player")
    return True
