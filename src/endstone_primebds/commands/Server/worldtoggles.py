from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "worldtoggles",
    "Controls PrimeBDS & Vanilla internal gamerules!",
    ["/worldtoggles"],
    ["primebds.command.worldtoggles"]
)

# CONNECT COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    return True