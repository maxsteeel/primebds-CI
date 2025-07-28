from endstone import Player, boss, ColorFormat
from endstone.command import CommandSender
from endstone_primebds.utils.commandUtil import create_command
from endstone_primebds.utils.targetSelectorUtil import get_matching_actors

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

boss_bar_cache = {}

command, permission = create_command(
    "bossbar",
    "Sets or clears a client-sided bossbar display!",
    [
        "/bossbar <player: player> (red|blue|green|yellow|pink|purple|rebecca_purple|white)<color: set_color> <percent: float> <title: string>",
        "/bossbar <player: player> clear"
    ],
    ["primebds.command.bossbar"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    global boss_bar_cache

    if not args:
        sender.send_message("Usage: /bossbar <player> <color> <percent> <title> OR /bossbar <player> clear")
        return False

    if len(args) == 2 and args[1].lower() == "clear":
        targets = get_matching_actors(self, args[0], sender)
        if not targets:
            sender.send_message(f"No matching players found for {args[0]}!")
            return False

        removed_count = 0
        for target in targets:
            if target in boss_bar_cache:
                bar = boss_bar_cache[target]
                bar.remove_player(target)
                if not bar.players:
                    # Remove from cache if empty
                    del boss_bar_cache[target]
                removed_count += 1
        sender.send_message(f"Removed boss bar from {removed_count} player(s).")
        return True

    if len(args) < 4:
        sender.send_message("Usage: /bossbar <player> <color> <percent> <title>")
        return False

    color_name = args[1].upper()
    try:
        color = getattr(boss.BarColor, color_name)
    except AttributeError:
        sender.send_message(f"Invalid color '{args[1]}'. Using RED as default.")
        color = boss.BarColor.RED

    try:
        percent = float(args[2])
        percent = max(0.0, min(100.0, percent))
    except ValueError:
        sender.send_message(f"Invalid percent value '{args[2]}'. Must be a number 0-100.")
        return False

    # Title can be multiple words, so join the rest of args starting from index 3
    title = " ".join(args[3:])

    # Optional: style and is_dark not provided in the original command spec - skipping for now
    style = boss.BarStyle.SOLID
    flags = []

    # Create boss bar once, then assign to players
    bar = self.server.create_boss_bar(title, color, style, flags)
    bar.progress = percent / 100  # scale to 0-1

    targets = get_matching_actors(self, args[0], sender)
    if not targets:
        sender.send_message(f"No matching players found for {args[0]}!")
        return False

    def remove_existing_bossbar(player: Player):
        if player in boss_bar_cache:
            existing_bar = boss_bar_cache[player]
            existing_bar.remove_player(player)
            if not existing_bar.players:
                del boss_bar_cache[player]

    for target in targets:
        remove_existing_bossbar(target)
        bar.add_player(target)
        boss_bar_cache[target] = bar

    sender.send_message(
        f"{ColorFormat.AQUA}Bossbar Set For {len(targets)} player(s):\n"
        f"{ColorFormat.DARK_GRAY}---------------\n"
        f"§eColor: {ColorFormat.RESET}{args[1]}\n"
        f"§epercent: {ColorFormat.RESET}{percent}%\n"
        f"§eTitle: {ColorFormat.RESET}{title}\n"
        f"{ColorFormat.DARK_GRAY}---------------"
    )
    return True
