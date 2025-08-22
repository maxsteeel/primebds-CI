from endstone import Player
from endstone.command import CommandSender

from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.config_util import load_config, save_config
from endstone_primebds.utils.form_wrapper_util import ModalFormData, ModalFormResponse, ActionFormData, ActionFormResponse

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

command, permission = create_command(
    "primebds",
    "An all-in-one primebds manager!",
    ["/primebds (config|info)[primebds_subaction: primebds_subaction]"],
    ["primebds.command.primebds"]
)

# PRIMEBDS FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player")
        return True
    
    if len(args) == 0:
        sender.send_message(f"§dPrimeBDS\n§d{self.description}\n\n§dIf this plugin has helped you at all, consider leaving a star:\n§e@ https://github.com/PrimeStrat/primebds\n\n§dConfused on how something works?\nVisit the wiki:\n§e@ https://github.com/PrimeStrat/primebds/wiki")
        return True

    if args[0].lower() == "config":
        open_config_categories(sender)
    elif args[0].lower() == "info":
        sender.send_message(f"§dPrimeBDS\n§d{self.description}\n\n§dIf this plugin has helped you at all, consider leaving a star:\n§e@ https://github.com/PrimeStrat/primebds\n\n§dConfused on how something works?\nVisit the wiki:\n§e@ https://github.com/PrimeStrat/primebds/wiki")

    return True

def open_config_categories(player: Player):
    config = load_config()

    form = ActionFormData()
    form.title("PrimeBDS Config")
    form.body("Select a category to edit:")

    keys = config.keys()
    for category in keys:
        form.button(f"§4{category.capitalize()}")

    form.button("Close")

    def submit(player: Player, result: ActionFormResponse):
        if not result.canceled and 0 <= result.selection < len(keys):
            category = list(keys)[result.selection]
            open_category_editor(player, category, config)

    form.show(player).then(lambda player=player, result=ActionFormResponse: submit(player, result))

def open_category_editor(player: Player, category: str, config: dict):
    if category not in config:
        player.send_message(f"§cCategory '{category}' not found.")
        return

    settings = config[category]

    if category.lower() == "commands":
        form = ModalFormData()
        form.title("Commands Configuration")
        field_map = []

        for cmd, value_dict in settings.items():
            enabled = value_dict.get("enabled", False)
            field_map.append((cmd, bool))
            form.toggle(f"/{cmd}", enabled)

        form.submit_button("Save Changes")

        def submit(player: Player, response: ModalFormResponse):
            if response.canceled:
                open_config_categories(player)
                return

            new_values = response.formValues
            updated = {}

            for i, (cmd, _) in enumerate(field_map):
                new_enabled = bool(new_values[i])
                settings[cmd]["enabled"] = new_enabled
                updated[cmd] = new_enabled

            config[category] = settings
            save_config(config, True)

            player.send_message("§aCommands updated!")
            player.send_message("§aRun §e/reload §ato apply changes!")

        form.show(player).then(lambda player=player, response=ModalFormResponse: submit(player, response))
        return

    else:
        if any(isinstance(v, dict) for v in settings.values()):
            open_module_editor(player, category, settings, config)
            return

def open_module_editor(player: Player, module_name: str, settings: dict, config: dict, parent_name: str = None):
    subkeys = [k for k, v in settings.items() if isinstance(v, dict)]
    primitive_keys = [k for k, v in settings.items() if not isinstance(v, dict)]

    if "combat" in module_name:
        return

    if primitive_keys:
        form = ModalFormData()
        form.title(f"{format_label(module_name)} Configuration")
        field_map = []

        for key in primitive_keys:
            value = settings[key]
            value_type = type(value)
            field_map.append((key, value_type))

            if isinstance(value, bool):
                form.toggle(format_label(key), value)
            else:
                form.text_field(format_label(key), str(value), str(value))

        form.submit_button("Save Changes")

        def submit_modal(player: Player, response: ModalFormResponse):
            if response.canceled:
                open_config_categories(player)
                return

            new_values = response.formValues
            updated = {}

            for i, (key, value_type) in enumerate(field_map):
                old_value = settings[key]
                new_value = new_values[i]

                if value_type == bool:
                    new_value = bool(new_value)
                if value_type == int:
                    try:
                        new_value = int(new_value)
                    except ValueError:
                        new_value = old_value
                elif value_type == float:
                    try:
                        new_value = float(new_value)
                    except ValueError:
                        new_value = old_value
                elif value_type == list:
                    new_value = [x.strip() for x in str(new_value).split(",") if x.strip()]
                else:
                    if not isinstance(new_value, bool):
                        new_value = str(new_value)

                settings[key] = new_value
                updated[key] = new_value

            save_config(config, True)

            if updated:
                player.send_message(f"§aUpdated values for {format_label(module_name)}")

            if subkeys:
                open_module_editor(player, module_name, settings, config, parent_name)

        form.show(player).then(lambda player=player, response=ModalFormResponse: submit_modal(player, response))
        return

    if subkeys:
        form = ActionFormData()
        form.title(f"{format_label(module_name)} Subcategories")
        form.body("Select a subcategory to edit:")

        for sub in subkeys:
            form.button(f"§4{format_label(sub)}")

        form.button("Back")
        form.button("Close")

        def submit_action(player: Player, result: ActionFormResponse):
            if result.canceled:
                open_config_categories(player)
                return

            selected_index = result.selection
            if selected_index is None:
                open_config_categories(player)
                return

            if selected_index == len(subkeys):
                if parent_name:
                    open_module_editor(player, parent_name, config[parent_name], config)
                else:
                    open_config_categories(player)
                return

            if selected_index == len(subkeys) + 1:
                return

            chosen_key = subkeys[selected_index]
            open_module_editor(player, chosen_key, settings[chosen_key], config, module_name)

        form.show(player).then(lambda player=player, result=ActionFormResponse: submit_action(player, result))

def format_label(key: str) -> str:
    return " ".join(word.capitalize() for word in key.split("_"))
