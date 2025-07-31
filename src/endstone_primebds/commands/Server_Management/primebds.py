from endstone import Player
from endstone.command import CommandSender

from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.config_util import load_config, save_config

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def generate_command_usages():
    key_mapping = {}  # maps sanitized -> original dot key

    def flatten_config(prefix, data, out, skip_keys=None):
        """Recursively flatten config dictionary with dot notation keys"""
        if skip_keys is None:
            skip_keys = ["allowlist_profile"]

        if isinstance(data, dict):
            for k, v in data.items():
                # Skip uppercase keys or explicitly skipped keys
                if any(c.isupper() for c in k) or k in skip_keys:
                    continue
                new_key = f"{prefix}.{k}" if prefix else k
                flatten_config(new_key, v, out, skip_keys)
        else:
            out[prefix] = data

    def sanitize_key(key: str) -> str:
        """Make keys safe for Minecraft command usage"""
        return key.replace(".", "_").replace("-", "_")

    config = load_config()
    command_keys = list(config.get("commands", {}).keys())

    flat_modules = {}
    flatten_config("", config.get("modules", {}), flat_modules)

    cmd_bool, cmd_int, cmd_string, cmd_list = [], [], [], []
    mod_bool, mod_int, mod_string, mod_list = [], [], [], []

    def detect_type(value):
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, (int, float)):
            return "int"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "list"
        return None

    for key in command_keys:
        val = config["commands"].get(key)
        check_val = val["enabled"] if isinstance(val, dict) and "enabled" in val else val
        key_type = detect_type(check_val)

        safe_key = sanitize_key(key)
        key_mapping[safe_key] = key

        if key_type == "bool":
            cmd_bool.append(safe_key)
        elif key_type == "int":
            cmd_int.append(safe_key)
        elif key_type == "string":
            cmd_string.append(safe_key)
        elif key_type == "list":
            cmd_list.append(safe_key)

    for flat_key, val in flat_modules.items():
        key_type = detect_type(val)
        safe_key = sanitize_key(flat_key)
        key_mapping[safe_key] = flat_key

        if key_type == "bool":
            mod_bool.append(safe_key)
        elif key_type == "int":
            mod_int.append(safe_key)
        elif key_type == "string":
            mod_string.append(safe_key)
        elif key_type == "list":
            mod_list.append(safe_key)

    patterns = []
    if cmd_bool:
        patterns.append(
            f"/primebds (command_toggle)<primebds_cmds: primebds_cmds> "
            f"({'|'.join(cmd_bool)})<primebds_bools: primebds_bools> <toggle_cmd: bool>"
        )

    if mod_bool:
        patterns.append(
            f"/primebds (module_toggle)<primebds_b_settings: primebds_mb_settings> "
            f"({'|'.join(mod_bool)})<primebds_bools: primebds_bools_1> <toggle_module: bool>"
        )
    if mod_int:
        patterns.append(
            f"/primebds (module_value)<primebds_i_settings: primebds_i_settings> "
            f"({'|'.join(mod_int)})<primebds_nums: primebds_nums> <value: int>"
        )
    if mod_string:
        patterns.append(
            f"/primebds (module_string)<primebds_s_settings: primebds_s_settings> "
            f"({'|'.join(mod_string)})<primebds_strings: primebds_strings> <text: string>"
        )
    if mod_list:
        patterns.append(
            f"/primebds (module_list)<primebds_l_settings: primebds_l_settings> "
            f"({'|'.join(mod_list)})<primebds_lists: primebds_lists> "
            f"(add|remove|clear)<tag_set: tag_set> [text: string]"
        )

    return patterns, key_mapping

patterns, key_mapping = generate_command_usages()
command, permission = create_command(
    "primebds",
    "An all-in-one primebds manager!",
    patterns,
    ["primebds.command.primebds"]
)

# PRIMEBDS SETTINGS COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if not isinstance(sender, Player):
        sender.send_error_message("This command can only be executed by a player")
        return True

    if len(args) < 3:
        sender.send_error_message("Usage: /primebds <action> <key> ...")
        return True

    config = load_config()
    action = args[0]
    key = args[1]

    if key not in key_mapping:
        sender.send_error_message(f"Unknown setting: {key}")
        return True
    dot_key = key_mapping[key]

    if action.startswith("module_"):
        target = config.get("modules", {})
        action_type = action[len("module_"):]
    else:
        target = config.get("commands", {})
        action_type = action[len("command_"):] 

    parts = dot_key.split(".")
    for p in parts[:-1]:
        if p not in target or not isinstance(target[p], dict):
            target[p] = {}
        target = target[p]
    final_key = parts[-1]

    try:
        if action_type == "toggle":
            if len(args) < 3:
                sender.send_error_message("Usage: settoggle/module_toggle <key> <true|false>")
                return True
            value = args[2].lower() in ("true", "1", "yes", "on")

            # For boolean commands under "commands", wrap with "enabled"
            if not action.startswith("module_") and key in config.get("commands", {}):
                if final_key not in target or not isinstance(target[final_key], dict):
                    target[final_key] = {}
                target[final_key]["enabled"] = value
            else:
                target[final_key] = value

        elif action_type == "value":
            if len(args) < 3:
                sender.send_error_message("Usage: setvalue/module_value <key> <number>")
                return True
            try:
                value = int(args[2])
            except ValueError:
                sender.send_error_message("Value must be an integer")
                return True
            target[final_key] = value

        elif action_type == "string":
            if len(args) < 3:
                sender.send_error_message("Usage: setstring/module_string <key> <text>")
                return True
            text = " ".join(args[2:])
            target[final_key] = text

        elif action_type == "list":
            if len(args) < 3:
                sender.send_error_message("Usage: setlist/module_list <key> <add|remove|clear> [item]")
                return True
            subaction = args[2].lower()
            item = " ".join(args[3:]) if len(args) > 3 else None

            if final_key not in target or not isinstance(target[final_key], list):
                target[final_key] = []

            if subaction == "add":
                if not item:
                    sender.send_error_message("Missing item to add")
                    return True
                if item not in target[final_key]:
                    target[final_key].append(item)

            elif subaction == "remove":
                if not item:
                    sender.send_error_message("Missing item to remove")
                    return True
                if item in target[final_key]:
                    target[final_key].remove(item)

            elif subaction == "clear":
                target[final_key] = []

            else:
                sender.send_error_message("Invalid list action (add/remove/clear)")
                return True

        else:
            sender.send_error_message("Unknown action")
            return True

        save_config(config)
        sender.send_message(f"Updated: §e{dot_key} §7-> §e{target[final_key]}\n§rUse §e/reload §rto apply changes")

    except Exception as e:
        sender.send_error_message(f"Error updating config: {e}")
        return True

    return True
