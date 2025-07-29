import importlib
import pkgutil
import os

import endstone_primebds

from endstone_primebds.utils.configUtil import load_config, save_config
from collections import defaultdict, OrderedDict

# Global storage for preloaded commands
preloaded_commands = {}
preloaded_permissions = {}
preloaded_handlers = {}

def preload_settings():
    """Preload all plugin settings with defaults if missing, preserving key order and removing unknown keys."""
    config = load_config()

    def merge_clean_ordered(default: dict, actual: dict, skip_keys: set = None):
        """
        Merge default into actual, preserving order, removing unknown keys,
        but skips modifying inside 'worlds' and 'tag_overrides' subtrees.
        """
        if skip_keys is None:
            skip_keys = set()

        keys_to_remove = [key for key in actual if key not in default]
        for key in keys_to_remove:
            if key not in ('worlds', 'tag_overrides'):
                del actual[key]

        for key, value in default.items():
            if key in skip_keys:
                continue

            if key in ('worlds', 'tag_overrides'):
                if key not in actual:
                    actual[key] = value
                continue

            if key not in actual:
                actual[key] = value
            elif isinstance(value, dict) and isinstance(actual[key], dict):
                merge_clean_ordered(value, actual[key], skip_keys=set())

        reordered = OrderedDict()
        for key in default.keys():
            if key in actual:
                reordered[key] = actual[key]

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
            "custom_tags": []
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
        "allowlist": OrderedDict({
            "profile": "default",
            "WARNING": "DO NOT EDIT 'profile' AS IT CAN RESULT IN UNEXPECTED BEHAVIOR"
        }),
        "combat": OrderedDict({
            "hit_cooldown_in_seconds": 0.0,
            "base_damage": 1.0,
            "horizontal_knockback_modifier": 0.0,
            "vertical_knockback_modifier": 0.0,
            "horizontal_sprint_knockback_modifier": 0.0,
            "vertical_sprint_knockback_modifier": 0.0,
            "fall_damage_height": 3.5,
            "projectiles": OrderedDict({
                "horizontal_knockback_modifier": 0.0,
                "vertical_knockback_modifier": 0.0,
            }),
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
                    "fall_damage_height": 7.0,
                    "projectiles": OrderedDict({
                        "horizontal_knockback_modifier": 0.0,
                        "vertical_knockback_modifier": 0.0
                    }),
                    "disable_fire_damage": True,
                    "disable_explosion_damage": True,
                    "disable_sprint_hits": True,
                })
            })
        }),
        "multiworld": OrderedDict({
        "enabled": False,
        "main_ip": "127.0.0.1",
        "worlds": OrderedDict({
            "example_world_folder": OrderedDict({
                    "ip": "127.0.0.1",
                    "server-port": 19134,
                    "server-portv6": 19135,
                    "level-name": "Bedrock level",
                    "server-name": "Dedicated Server",
                    "gamemode": "survival",
                    "difficulty": "easy",
                    "default-player-permission-level": "member",
                    "max-players": 10,
                    "view-distance": 12,
                    "tick-distance": 4,
                    "max-threads": 0,
                    "level-seed": "",
                    "compression-threshold": 30000,
                    "texturepack-required": False,
                    "allow-list": False,
                    "allow-cheats": True
                })
            })
        })
    })

    config.setdefault("modules", OrderedDict())

    # Sync each module
    for module, default_settings in default_modules.items():
        if module not in config["modules"]:
            config["modules"][module] = default_settings
        else:
            merge_clean_ordered(default_settings, config["modules"][module])

    # Remove obsolete modules
    for module in list(config["modules"].keys()):
        if module not in default_modules:
            del config["modules"][module]

    save_config(config)

def preload_commands():
    """Preload all command modules before PrimeBDS is instantiated, respecting the config."""
    global preloaded_commands, preloaded_permissions, preloaded_handlers

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

__all__ = [preloaded_commands, preloaded_permissions, preloaded_handlers]
