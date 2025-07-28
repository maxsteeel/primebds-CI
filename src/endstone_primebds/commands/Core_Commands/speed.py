from endstone import Player, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

command, permission = create_command(
    "speed",
    "Modifies player's flyspeed or walkspeed!",
    [
        "/speed (flyspeed|walkspeed)<attribute: attribute> <value: float> [player: player]",
        "/speed (reset)<reset_attribute: reset_attribute> (flyspeed|walkspeed)<attribute_target: attribute_target> [player: player]"
    ],
    ["primebds.command.speed"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player if no player is specified.")
        return False

    if len(args) < 1:
        sender.send_message("Usage: /speed <flyspeed|walkspeed> <value> [player] or /speed reset <flyspeed|walkspeed> [player]")
        return False

    if args[0].lower() == "reset":
        if len(args) < 2:
            sender.send_message("Usage: /speed reset <flyspeed|walkspeed> [player]")
            return False

        attr = args[1].lower()
        if attr not in ("flyspeed", "walkspeed"):
            sender.send_message(f"Unknown speed attribute: {attr}")
            return False

        # Determine targets
        if len(args) >= 3:
            targets = get_matching_actors(self, args[2], sender)
            if not targets:
                sender.send_message(f"Player(s) {args[2]} not found!")
                return False
        else:
            targets = [sender]

        for player in targets:
            if attr == "flyspeed":
                player.fly_speed = 0.05  # Default fly speed is 0.05
                player.send_message("§aFlyspeed reset to default§r")
            else:
                player.walk_speed = 0.1  # Assuming default walk speed is 0.1
                player.send_message("§aWalkspeed reset to default§r")

        sender.send_message(f"§e{len(targets)} §rplayer's {attr} was reset")

        return True

    else:
        if len(args) < 2:
            sender.send_message("Usage: /speed <flyspeed|walkspeed> <value> [player]")
            return False

        attr = args[0].lower()
        value_str = args[1]

        if attr not in ("flyspeed", "walkspeed"):
            sender.send_message(f"Unknown speed attribute: {attr}")
            return False

        try:
            new_speed = float(value_str)
        except ValueError:
            sender.send_message(f"Invalid speed value: {value_str}")
            return False

        if len(args) >= 3:
            targets = get_matching_actors(self, args[2], sender)
            if not targets:
                sender.send_message(f"Player(s) {args[2]} not found!")
                return False
        else:
            targets = [sender]

        for player in targets:
            if attr == "flyspeed":
                original = player.fly_speed
                player.fly_speed = new_speed
                player.send_message(f"Flyspeed changed: §c{original} §7-> §a{new_speed}§r")
                sender.send_message(f"Player {player.name}'s flyspeed changed: §c{original} §7-> §a{new_speed}§r")
            else:
                original = player.walk_speed
                player.walk_speed = new_speed
                player.send_message(f"Walkspeed changed: §c{original} §7-> §a{new_speed}§r")
                sender.send_message(f"Player {player.name}'s walkspeed changed: §c{original} §7-> §a{new_speed}§r")

        return True
