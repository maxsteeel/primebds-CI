from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "attribute",
    "Modifies internal player NBT data!",
    ["/attribute <player: player> (flyspeed)<attribute: type_1> <value: float>",
     "/attribute <player: player> (fly)<attribute: type> <value: bool>"],
    ["primebds.command.attribute"]
)

# ATTRIBUTE COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if len(args) < 3:
        sender.send_message("Usage: /attribute <player> <flyspeed|walkspeed|fly> <value>")
        return False

    targets = get_matching_actors(self, args[0], sender)
    if not targets:
        sender.send_message(f"Player(s) {args[0]} not found!")
        return False

    attr = args[1].lower()
    value_str = args[2]

    for player in targets:
        if attr == "flyspeed":
            try:
                new_fly_speed = float(value_str)
                original_fly_speed = player.fly_speed
                player.fly_speed = new_fly_speed
                player.send_message(f"Flyspeed changed: {ColorFormat.RED}{original_fly_speed} {ColorFormat.GRAY}-> {ColorFormat.GREEN}{new_fly_speed}")
                sender.send_message(f"Player {player.name}'s flyspeed changed: {ColorFormat.RED}{original_fly_speed} {ColorFormat.GRAY}-> {ColorFormat.GREEN}{new_fly_speed}")
            except ValueError:
                sender.send_message(f"Invalid fly speed value: {value_str}")
                return False

        elif attr == "walkspeed":
            try:
                new_walk_speed = float(value_str)
                original_walk_speed = player.walk_speed
                player.walk_speed = new_walk_speed
                player.send_message(f"Walkspeed changed: {ColorFormat.RED}{original_walk_speed} {ColorFormat.GRAY}-> {ColorFormat.GREEN}{new_walk_speed}")
                sender.send_message(f"Player {player.name}'s walkspeed changed: {ColorFormat.RED}{original_walk_speed} {ColorFormat.GRAY}-> {ColorFormat.GREEN}{new_walk_speed}")
            except ValueError:
                sender.send_message(f"Invalid walk speed value: {value_str}")
                return False

        elif attr == "fly":
            try:
                new_fly_state = value_str.lower() == "true"
                original_fly_state = player.is_flying
                player.allow_flight = new_fly_state
                player.send_message(f"Fly state changed: {ColorFormat.RED}{original_fly_state} {ColorFormat.GRAY}-> {ColorFormat.GREEN}{new_fly_state}")
                sender.send_message(f"Player {player.name}'s fly state changed: {ColorFormat.RED}{original_fly_state} {ColorFormat.GRAY}-> {ColorFormat.GREEN}{new_fly_state}")
            except ValueError:
                sender.send_message(f"Invalid fly state value: {value_str}")
                return False

        else:
            sender.send_message(f"Unknown attribute: {attr}")
            return False

    return True
