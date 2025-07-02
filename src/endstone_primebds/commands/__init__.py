import importlib
import pkgutil
import os

import endstone_primebds

from endstone_primebds.utils.configUtil import load_config, save_config
from collections import defaultdict, OrderedDict

# Global storage for preloaded commands
moderation_commands = set() # MOD SYSTEM REQ
preloaded_commands = {}
preloaded_permissions = {}
preloaded_handlers = {}

def preload_settings():
    """Preload all plugin settings with defaults if missing, preserving key order."""
    config = load_config()

    def merge_ordered(default: dict, actual: dict):
        """Merge default into actual, preserving key order without overwriting existing keys."""
        for key, value in default.items():
            if key not in actual:
                actual[key] = value
            elif isinstance(value, dict) and isinstance(actual[key], dict):
                merge_ordered(value, actual[key])
        # Re-insert keys to maintain default order + existing keys
        reordered = OrderedDict()
        for k in list(default.keys()) + [k for k in actual.keys() if k not in default]:
            if k in actual:
                reordered[k] = actual[k]
        actual.clear()
        actual.update(reordered)

    default_modules = OrderedDict({
        "discord_logging": OrderedDict({
            "embed": OrderedDict({
                "color": 781919,
                "title": "Logger"
            }),
            "commands": OrderedDict({
                "enabled": False,
                "webhook": ""
            }),
            "moderation": OrderedDict({
                "enabled": False,
                "webhook": ""
            }),
            "chat": OrderedDict({
                "enabled": False,
                "webhook": ""
            }),
            "griefing": OrderedDict({
                "enabled": False,
                "webhook": ""
            })
        }),
        "game_logging": OrderedDict({
            "custom_tags": [],
            "moderation": OrderedDict({
                "enabled": True
            }),
            "commands": OrderedDict({
                "enabled": False
            })
        }),
        "spectator_check": OrderedDict({
            "check_gamemode": True,
            "check_tags": False,
            "allow_tags": [],
            "ignore_tags": []
        }),
        "me_crasher_patch": OrderedDict({
            "enabled": True,
            "ban": False
        }),
        "grieflog": OrderedDict({
            "enabled": False
        }),
        "grieflog_storage_auto_delete": OrderedDict({
            "enabled": False,
            "removal_time_in_seconds": 1209600
        }),
        "check_prolonged_death_screen": OrderedDict({
            "enabled": False,
            "kick": False,
            "time_in_seconds": 10
        }),
        "check_afk": OrderedDict({
            "enabled": False,
            "kick": False,
            "time_in_seconds": 180
        }),
        "combat": OrderedDict({
            "hit_cooldown_in_seconds": 0.0,
            "base_damage": 1.0,
            "horizontal_knockback_modifier": 0.0,
            "vertical_knockback_modifier": 0.0,
            "horizontal_sprint_knockback_modifier": 0.0,
            "vertical_sprint_knockback_modifier": 0.0,
            "resisted_knockback_percentage": 0.0,
            "fall_damage_height": 3.5,
            "disable_fire_damage": False,
            "disable_explosion_damage": False,
            "disable_sprint_hits": False,
            "tag_overrides": OrderedDict({
                "example_tag": OrderedDict({
                    "hit_cooldown_in_seconds": 1,
                    "base_damage": 5,
                    "horizontal_knockback_modifier": 2,
                    "vertical_knockback_modifier": 2,
                    "horizontal_sprint_knockback_modifier": 0,
                    "vertical_sprint_knockback_modifier": 0,
                    "resisted_knockback_percentage": 0.0,
                    "fall_damage_height": 7.0,
                    "disable_fire_damage": True,
                    "disable_explosion_damage": True,
                    "disable_sprint_hits": True,
                })
            })
        }),
        "allowlist": OrderedDict({
            "profile": "default",
            "WARNING": "DO NOT EDIT 'profile' AS IT CAN RESULT IN UNEXPECTED BEHAVIOR"
        })
    })

    config.setdefault("modules", OrderedDict())

    for module, settings in default_modules.items():
        if module not in config["modules"]:
            config["modules"][module] = settings
        else:
            merge_ordered(settings, config["modules"][module])

    save_config(config)

def preload_commands():
    """Preload all command modules before PrimeBDS is instantiated, respecting the config."""
    global preloaded_commands, preloaded_permissions, preloaded_handlers, moderation_commands

    commands_base_path = os.path.join(os.path.dirname(endstone_primebds.__file__), 'commands')
    config = load_config()

    grouped_commands = defaultdict(list)
    found_commands = set()  # Track commands that are found

    print("[PrimeBDS] Registering commands...")

    # Recursively find all submodules
    for root, _, _ in os.walk(commands_base_path):
        rel_path = os.path.relpath(root, commands_base_path)
        package_path = rel_path.replace(os.sep, ".") if rel_path != "." else ""

        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_import_path = f"endstone_primebds.commands{('.' + package_path) if package_path else ''}.{module_name}"
            module = importlib.import_module(module_import_path)

            if hasattr(module, 'command') and hasattr(module, 'handler'):
                for cmd, details in module.command.items():
                    found_commands.add(cmd)  # Mark command as found

                    # Ensure command exists in config, default to enabled
                    if cmd not in config["commands"]:
                        config["commands"][cmd] = {"enabled": True}

                    if config["commands"][cmd]["enabled"]:
                        preloaded_commands[cmd] = details
                        preloaded_handlers[cmd] = module.handler

                        # Check if the command belongs to "Moderation"
                        if package_path.lower() == "moderation":
                            moderation_commands.add(cmd)  # Add main command
                            aliases = details.get("aliases", [])  # Get aliases if available
                            moderation_commands.update(aliases)  # Add aliases to the set

                        grouped_commands[package_path].append((cmd, details.get('description', 'No description')))
                    else:
                        grouped_commands[package_path].append((cmd, "Disabled by config"))

                if hasattr(module, 'permission'):
                    for perm, details in module.permission.items():
                        preloaded_permissions[perm] = details

    # Remove commands that are no longer found
    removed_commands = set(config["commands"].keys()) - found_commands
    for cmd in removed_commands:
        del config["commands"][cmd]

    # Print grouped commands
    for category, commands in grouped_commands.items():
        if category or commands:  # Only print "Root" if it has commands
            clean_category = category.replace("_", " ") if category else "Root"
            print(f"\n[{clean_category}]")
            for cmd, desc in commands:
                status = "✓" if "Disabled by config" not in desc else "✗"
                print(f"{status} {cmd} - {desc}")

    # Print removed commands
    if removed_commands:
        print("\n[PrimeBDS] Removed missing commands:")
        for cmd in removed_commands:
            print(f"✗ {cmd}")

    print("\n")
    save_config(config)

# Run preload automatically when this file is imported
preload_settings()
preload_commands()

__all__ = [preloaded_commands, preloaded_permissions, preloaded_handlers, moderation_commands]
