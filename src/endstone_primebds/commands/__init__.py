import importlib
import json
import pkgutil
import os

import endstone_primebds

from endstone_primebds.utils.config_util import load_config, save_config, load_permissions, load_rules, find_and_load_config, PERMISSIONS_DEFAULT
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
        "broadcast": OrderedDict({
            "prefix": "§l§8[§c!§8] §r§e",
            "playsound": "random.toast"
        }),
        "permissions_manager": OrderedDict({
            "primebds": True,
            "endstone": True,
            "minecraft": True,
            "*": True
        }),
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
        "join_leave_messages": OrderedDict({
            "send_on_nick": False,
            "send_on_vanish": False,
            "send_on_connection": False,
            "join_message": "§e{player} joined the game",
            "leave_message": "§e{player} left the game",
            "shutdown": "Server has shutdown!"
        }),
        "server_optimizer": OrderedDict({
            "chunk_loading": True,
            "mute_laggy_sounds": True,
            "set_optimized_limit_config": False
        }),
        "server_messages": OrderedDict({
            "enhanced_whispers": True,
            "enhanced_chat": True,
            "rank_meta_data": True,
            "chat_prefix": "§r: ",
            "whisper_prefix": "§8[§bWhisper§8]§r ",
            "social_spy_prefix": "§8[§bSocial Spy§8]§r ",
            "staff_chat_prefix": "§8[§bStaff Chat§8]§r ",
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
        "worlds": OrderedDict({
            "example": OrderedDict({
                    "enabled": False,
                    "linked": False,
                    "server-port": 19134,
                    "server-portv6": 19135,
                    "level-name": "example",
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
                    "allow-list": True,
                    "allow-cheats": True
                })
            })
        })
    })

    config.setdefault("modules", OrderedDict())

    for module, default_settings in default_modules.items():
        if module not in config["modules"]:
            config["modules"][module] = default_settings
        else:
            merge_clean_ordered(default_settings, config["modules"][module])

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
    found_commands = set()

    print("[PrimeBDS] Registering commands...")

    for root, _, _ in os.walk(commands_base_path):
        rel_path = os.path.relpath(root, commands_base_path)
        package_path = rel_path.replace(os.sep, ".") if rel_path != "." else ""

        for _, module_name, _ in pkgutil.iter_modules([root]):
            module_import_path = f"endstone_primebds.commands{('.' + package_path) if package_path else ''}.{module_name}"
            module = importlib.import_module(module_import_path)

            if hasattr(module, 'command') and hasattr(module, 'handler'):
                for cmd, details in module.command.items():
                    found_commands.add(cmd) 

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

def preload_permissions():
    """Preload permissions.json with defaults if missing, preserving key order and removing unknown keys."""
    load_permissions(PERMISSIONS_DEFAULT, False)

def preload_packetlimitconfig():
    default_config = {
        "limitGroups": [
            {
                "minecraftPacketIds": [4, 193],
                "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 0.0013, "maxBucketSize": 1}}
            },
            {"minecraftPacketIds": [40], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 3, "maxBucketSize": 3}}},
            {"minecraftPacketIds": [6], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 10, "maxBucketSize": 20}}},
            {"minecraftPacketIds": [2, 3, 19], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 20, "maxBucketSize": 50}}},
            {"minecraftPacketIds": [9], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 20, "maxBucketSize": 50}}},
            {"minecraftPacketIds": [322], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 40, "maxBucketSize": 60}}},
            {"minecraftPacketIds": [5], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 40, "maxBucketSize": 80}}},
            {"minecraftPacketIds": [123], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 50, "maxBucketSize": 100}}},
            {"minecraftPacketIds": [13], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 50, "maxBucketSize": 100}}},
            {"minecraftPacketIds": [21, 110, 172, 174, 175], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 60, "maxBucketSize": 120}}},
            {"minecraftPacketIds": [33], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 60, "maxBucketSize": 120}}},
            {"minecraftPacketIds": [161], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 100, "maxBucketSize": 200}}},
            {"minecraftPacketIds": [16, 18, 23, 27, 40, 111, 326], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 250, "maxBucketSize": 500}}},
            {"minecraftPacketIds": [58, 144, 157], "algorithm": {"name": "BucketPacketLimitAlgorithm", "params": {"drainRatePerSec": 300, "maxBucketSize": 600}}}
        ]
    }

    start_path = os.path.dirname(os.path.abspath(__file__))
    root_path = start_path

    while root_path and root_path != os.path.dirname(root_path):
        if os.path.isdir(os.path.join(root_path, "plugins")):
            break
        root_path = os.path.dirname(root_path)

    if not root_path or not os.path.isdir(os.path.join(root_path, "plugins")):
        raise FileNotFoundError("Could not locate 'plugins' folder from: " + start_path)

    config_path = os.path.join(root_path, "packetlimitconfig.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=2)

    return default_config

config = load_config()
setlimitconfig = config.get("modules", {}).get("server_optimizer", {}).get("set_optimized_limit_config", False)
if setlimitconfig:
    preload_packetlimitconfig()


# Run preload automatically when this file is imported
preload_permissions()
preload_settings()
preload_commands()
print(f"\n[PrimeBDS] Loaded {len(preloaded_commands)} commands")

# ADDITIONAL DEFAULTS
RULES_DEFAULT = [
    "§6Rules:"
    "§7-------------------------"
    "§b1. §fBe respectful to others.",
    "§b2. §fNo griefing or stealing.",
    "§b3. §fNo cheating or exploiting bugs.",
]

load_rules(RULES_DEFAULT)

__all__ = [preloaded_commands, preloaded_permissions, preloaded_handlers]
