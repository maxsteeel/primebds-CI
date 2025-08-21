from endstone.command import CommandSender, BlockCommandSender
from endstone_primebds.utils.command_util import create_command

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "globalmute",
    "Mutes the server globally!",
    ["/globalmute"],
    ["primebds.command.globalmute"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:

    if isinstance(sender, BlockCommandSender):
        sender.send_message(f"§cThis command cannot be automated")
        return False

    toggle = "unmuted"
    if self.globalmute == 0:
        self.globalmute = 1
        toggle = "muted"
    else:
        self.globalmute = 0
        toggle = "unmuted"
    
    for player in self.server.online_players:
        player.send_message(f"§cServer has been globally §e{toggle}")
