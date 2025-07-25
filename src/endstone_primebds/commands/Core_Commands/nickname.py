from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "nickname",
    "Sets a display nickname!",
    ["/nickname [nick: string] [player: player]", "/nickname (remove)[remove_nick:remove_nick] [player: player]"],
    ["primebds.command.nickname"],
    "op",
    ["nick"]
)

# NICK COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player.")
        return False

    targets = [self.server.get_player(sender.name)]

    if len(args) > 1:
        possible_target_arg = args[-1]
        matched_players = get_matching_actors(self, possible_target_arg, sender)
        if matched_players:
            targets = matched_players
            nick_arg_index = len(args) - 1  
            new_nick = " ".join(args[:nick_arg_index]).strip()
            if not new_nick:
                sender.send_message(f"{targets[0].name}'s current nickname is: {ColorFormat.YELLOW}{targets[0].name_tag}")
                return True
        else:
            new_nick = " ".join(args).strip()
    elif len(args) == 1:
        new_nick = args[0]
    else:
        sender.send_message(f"Your current nickname is: {ColorFormat.YELLOW}{targets[0].name_tag}")
        return True

    for target in targets:
        if new_nick.lower() == "remove":
            target.name_tag = target.name 
            sender.send_message(f"{target.name}'s nickname has been reset to original name: {ColorFormat.YELLOW}{target.name}")
        else:
            if new_nick:
                target.name_tag = new_nick 
                sender.send_message(f"{target.name}'s nickname was set to: {ColorFormat.YELLOW}{new_nick}")
            else:
                sender.send_error_message("Nickname cannot be empty.")
                return False

    return True
