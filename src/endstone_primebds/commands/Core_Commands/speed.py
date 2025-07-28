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
    if not isinstance(sender, Player) and len(args) < 3:
        sender.send_error_message("This command can only be executed by a player if no player is specified.")
        return False

    if len(args) < 1:
        sender.send_message("Usage: /speed <flyspeed|walkspeed> <value> [player] or /speed reset <flyspeed|walkspeed> [player]")
        return False

    is_reset = args[0].lower() == "reset"

    if is_reset:
        if len(args) < 2:
            sender.send_message("Usage: /speed reset <flyspeed|walkspeed> [player]")
            return False

        attr = args[1].lower()
        if attr not in ("flyspeed", "walkspeed"):
            sender.send_message(f"Unknown speed attribute: {attr}")
            return False

        targets = get_matching_actors(self, args[2], sender) if len(args) >= 3 else [sender]
        if not targets:
            sender.send_message(f"Player(s) {args[2]} not found!")
            return False

        for player in targets:
            if attr == "flyspeed":
                player.fly_speed = 0.05
                player.send_message("§aFlyspeed reset to default§r")
            else:
                player.walk_speed = 0.1
                player.send_message("§aWalkspeed reset to default§r")

        if len(targets) == 1:
            sender.send_message(f"§e{targets[0].name}'s§r {attr} was reset to default.")
        else:
            sender.send_message(f"§e{len(targets)}§r players had their {attr} reset to default.")

        return True

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

    targets = get_matching_actors(self, args[2], sender) if len(args) >= 3 else [sender]
    if not targets:
        sender.send_message(f"Player(s) {args[2]} not found!")
        return False

    for player in targets:
        if attr == "flyspeed":
            original = player.fly_speed
            player.fly_speed = new_speed
            player.send_message(f"Flyspeed changed: §c{original} §7→ §a{new_speed}§r")
        else:
            original = player.walk_speed
            player.walk_speed = new_speed
            player.send_message(f"Walkspeed changed: §c{original} §7→ §a{new_speed}§r")

    if len(targets) == 1:
        sender.send_message(f"{targets[0].name}'s {attr} changed to: §a{new_speed}")
    else:
        sender.send_message(f"§e{len(targets)}§r players had their {attr} changed to: §a{new_speed}")

    return True
