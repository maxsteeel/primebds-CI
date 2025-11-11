from endstone import Player
from endstone_primebds.utils.form_wrapper_util import (
    ActionFormData,
    ActionFormResponse,
)
from endstone.command import CommandSender
from endstone_primebds.utils.command_util import create_command
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Register command
command, permission = create_command(
    "worldtoggles",
    "Toggles internal gamerules handled by PrimeBDS through Endstone!",
    ["/worldtoggles"],
    ["primebds.command.worldtoggles"]
)

def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_message("§cOnly players can use this command.")
        return True

    show_gamerule_form(self, sender)
    return True

def show_gamerule_form(self: "PrimeBDS", player):
    buttons = []

    keys = list(self.gamerules.keys())
    for key in keys:
        value = self.gamerules[key]
        state = "§aON§r" if value else "§cOFF§r"
        label = key.replace("_", " ").title()
        buttons.append(f"§r{label}: {state}")

    form = ActionFormData()
    form.title("World Gamerule Toggles")
    for button in buttons:
        form.button(button)
    form.button("Close")

    def submit(player: Player, result: ActionFormResponse):
        if not result or result.selection is None:
            return True

        if result.selection >= len(buttons):
            return True
        
        clicked_key = keys[result.selection]
        self.gamerules[clicked_key] ^= 1

        self.serverdb.execute(
            f"UPDATE server_info SET {clicked_key} = ? WHERE id = 1",
            (self.gamerules[clicked_key],)
        )

        show_gamerule_form(self, player)

    form.show(player).then(lambda player=player, result=ActionFormResponse: submit(player, result))
