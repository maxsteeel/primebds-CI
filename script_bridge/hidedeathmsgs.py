from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "hidedeathmsgs",
    "Hides death chat messages from your view!",
    ["/hidedeathmsgs"],
    ["primebds.command.hidedeathmsgs"],
    "true"
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, Player):
        target = self.server.get_player(sender.name)
        self.server.dispatch_command(self.server.command_sender,
                                     f"execute as \"{target.name}\" run scriptevent wmct:endstone mutedeath")
    else:
        sender.send_error_message("This command can only be executed by a player")
    return True
