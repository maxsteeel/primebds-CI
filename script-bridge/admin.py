from endstone import Player
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.prefixUtil import infoLog, errorLog

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "admin",
    "Opens the WMCT admin menu!!",
    ["/admin"],
    ["primebds.command.admin"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, Player):
        target = self.server.get_player(sender.name)
        self.server.dispatch_command(self.server.command_sender,
                                     f"execute as \"{target.name}\" run scriptevent wmct:endstone admin")
    else:
        sender.send_error_message("This command can only be executed by a player")
    return True
