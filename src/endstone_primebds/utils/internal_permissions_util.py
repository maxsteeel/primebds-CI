import time

from endstone import Player
from endstone_primebds.utils.config_util import load_permissions, load_config

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

RANKS = list(load_permissions().keys())
PERMISSIONS = load_permissions()

MANAGED_PERMISSIONS_LIST = []

MINECRAFT_PERMISSIONS = [
    "minecraft",
    "minecraft.command",
    "minecraft.command.aimassist",
    "minecraft.command.allowlist",
    "minecraft.command.camera",
    "minecraft.command.camerashake",
    "minecraft.command.clear",
    "minecraft.command.clearspawnpoint",
    "minecraft.command.clone",
    "minecraft.command.controlscheme",
    "minecraft.command.damage",
    "minecraft.command.daylock",
    "minecraft.command.deop",
    "minecraft.command.dialogue",
    "minecraft.command.effect",
    "minecraft.command.enchant",
    "minecraft.command.event",
    "minecraft.command.execute",
    "minecraft.command.fill",
    "minecraft.command.function",
    "minecraft.command.fog",
    "minecraft.command.gamemode",
    "minecraft.command.gametest",
    "minecraft.command.gamerule",
    "minecraft.command.give",
    "minecraft.command.help",
    "minecraft.command.inputpermission",
    "minecraft.command.kill",
    "minecraft.command.locate",
    "minecraft.command.list",
    "minecraft.command.loot",
    "minecraft.command.music",
    "minecraft.command.me",
    "minecraft.command.mobevent",
    "minecraft.command.op",
    "minecraft.command.particle",
    "minecraft.command.place",
    "minecraft.command.playanimation",
    "minecraft.command.playsound",
    "minecraft.command.permissionslist",
    "minecraft.command.recipe",
    "minecraft.command.replaceitem",
    "minecraft.command.ride",
    "minecraft.command.reload",
    "minecraft.command.save",
    "minecraft.command.say",
    "minecraft.command.schedule",
    "minecraft.command.scoreboard",
    "minecraft.command.script",
    "minecraft.command.scriptevent",
    "minecraft.command.sendshowstoreoffer",
    "minecraft.command.setblock",
    "minecraft.command.setworldspawn",
    "minecraft.command.spawnpoint",
    "minecraft.command.spreadplayers",
    "minecraft.command.stop",
    "minecraft.command.stopsound",
    "minecraft.command.tag",
    "minecraft.command.teleport",
    "minecraft.command.tell",
    "minecraft.command.tellraw",
    "minecraft.command.time",
    "minecraft.command.title",
    "minecraft.command.titleraw",
    "minecraft.command.tickingarea",
    "minecraft.command.transfer",
    "minecraft.command.toggledownfall",
    "minecraft.command.weather",
    "minecraft.command.wsserver",
    "minecraft.command.xp",
    "minecraft.command.summon",
    "minecraft.command.structure",
    "minecraft.command.testfor",
    "minecraft.command.testforblock",
    "minecraft.command.testforblocks",
    "minecraft.command.transfer",
    "minecraft.command.ride",
]

EXTRA_PERMS = [
    "primebds.exempt.msgtoggle",
    "primebds.exempt.globalmute",
    "primebds.exempt.mute",
    "primebds.exempt.ban",
    "primebds.exempt.kick",
    "primebds.exempt.warn",
    "primebds.exempt.jail",
    "primebds.command.heal.other",
    "primebds.command.feed.other",
    "primebds.command.repair.other"
]

def reload_rank_list():
    global RANKS
    RANKS = list(load_permissions().keys())

def get_ranks() -> list[str]:
    return RANKS

def load_perms(self: "PrimeBDS"):
    config = load_config()
    modules = config.get("modules", {})
    perms_manager = modules.get("permissions_manager", {})
    minecraft_enabled = perms_manager.get("minecraft", True)
    primebds_enabled = perms_manager.get("primebds", True)
    endstone_enabled = perms_manager.get("endstone", True)
    wildcard_enabled = perms_manager.get("*", True)

    plugin_perms = set()
    for plugin in self.server.plugin_manager.plugins:
        plugin_perm_set = set()
        data = getattr(plugin, "_get_description", lambda: None)()
        if not data:
            continue
        
        perms = getattr(data, "permissions", [])
        commands = getattr(data, "commands", [])

        if perms:
            for attachment in perms:
                perm_lower = attachment.name.lower()
                if perm_lower in {"endstone.command.banip", "endstone.command.unbanip", "endstone.command.banlist"}:
                    continue

                prefix = perm_lower.split(".")[0]
                if (prefix == "minecraft" and minecraft_enabled) or \
                (prefix == "primebds" and primebds_enabled) or \
                (prefix == "endstone" and endstone_enabled) or \
                (prefix not in {"minecraft", "primebds", "endstone"} and wildcard_enabled):
                    plugin_perms.add(perm_lower)
                    plugin_perm_set.add(perm_lower)
        elif commands and wildcard_enabled:
            for cmd in commands:
                perms = cmd.permissions
                for perm in perms:
                    perm_lower = perm.lower()
                    plugin_perms.add(perm_lower)
                    plugin_perm_set.add(perm_lower)

        if getattr(plugin, "name", "") == "primebds":
            for perm in EXTRA_PERMS:
                plugin_perms.add(perm)
                plugin_perm_set.add(perm)

        plugin_name = getattr(plugin, "name", None)
        if plugin_name == None:
            if plugin_perm_set:
                first_perm = next(iter(plugin_perm_set))
                plugin_name = first_perm.split(".")[0]
            else:
                plugin_name = "unnamed plugin"

        if plugin_perm_set:
            first_prefix = next(iter(plugin_perm_set)).split(".")[0]
            if (first_prefix == "minecraft" and minecraft_enabled) or \
                (first_prefix == "primebds" and primebds_enabled) or \
                (first_prefix == "endstone" and endstone_enabled) or \
                (first_prefix not in {"minecraft", "primebds", "endstone"} and wildcard_enabled):
                print(f"[PrimeBDS] {plugin_name}: Loaded {len(plugin_perm_set)} permissions")

    server_registered = {str(p.name).lower() for p in self.server.plugin_manager.permissions}

    for perm in server_registered:
        prefix = perm.split(".")[0]
        if (prefix == "minecraft" and minecraft_enabled) or \
        (prefix == "primebds" and primebds_enabled) or \
        (prefix == "endstone" and endstone_enabled) or \
        (prefix not in {"minecraft", "endstone"} and wildcard_enabled):
            plugin_perms.add(perm)

    if minecraft_enabled:
        plugin_perms |= {p.lower() for p in MINECRAFT_PERMISSIONS}

    MANAGED_PERMISSIONS_LIST.clear()
    MANAGED_PERMISSIONS_LIST.extend(plugin_perms)

    for perm in EXTRA_PERMS:
        if perm not in MANAGED_PERMISSIONS_LIST and primebds_enabled:
            MANAGED_PERMISSIONS_LIST.append(perm)

    endstone_filtered = [perm for perm in plugin_perms if "endstone" in perm]
    if endstone_filtered:
        print(f"[PrimeBDS] endstone: Loaded {len(endstone_filtered)} permissions")

    minecraft_filtered = [perm for perm in plugin_perms if perm in {p.lower() for p in MINECRAFT_PERMISSIONS}]
    print(f"[PrimeBDS] minecraft: Loaded {len(minecraft_filtered)} permissions")
    print(f"[PrimeBDS] Total managed permissions: {len(MANAGED_PERMISSIONS_LIST)}")

def normalize_rank_name(rank: str) -> str:
    rank = rank.lower()
    if rank.startswith("primebds.rank."):
        rank = rank[len("primebds.rank."):]

    for r in RANKS:
        if r.lower() == rank:
            return r
        
    return "Default"

def get_rank_group(rank_name: str) -> dict | None:
    rank_lower = rank_name.lower()
    for key, value in PERMISSIONS.items():
        if key.lower() == rank_lower:
            return value
    return None

def check_rank_exists(self: "PrimeBDS", target: Player, rank: str) -> str:
    """Ensure a rank exists; fallback to Default if missing or invalid. Case-insensitive."""
    try:
        ranks_map = {r.lower(): r for r in PERMISSIONS.keys()}

        rank_lower = rank.lower()
        if rank_lower not in ranks_map:
            raise ValueError("Rank missing or invalid")

        proper_rank = ranks_map[rank_lower]
        group = get_rank_group(proper_rank)

        if not isinstance(group, dict) or "permissions" not in group or not isinstance(group["permissions"], (dict, list)):
            raise ValueError("Rank permissions invalid")

        return proper_rank
    except Exception as e:
        print(f"Invalid rank '{rank}' for {target.name}, resetting to Default: {e}")
        self.db.update_user_data(target.name, 'internal_rank', "Default")
        return "Default"

def get_rank_permissions(rank: str) -> dict[str, bool]:
    
    global PERMISSIONS
    PERMISSIONS = load_permissions(None, True)

    base_rank = normalize_rank_name(rank)
    seen_ranks = set()
    result: dict[str, bool] = {p: False for p in MANAGED_PERMISSIONS_LIST}

    def gather_permissions(r):
        r_norm = normalize_rank_name(r)
        if r_norm in seen_ranks:
            return
        seen_ranks.add(r_norm)

        group = get_rank_group(r_norm)
        if not group or not isinstance(group, dict):
            return

        perms = group.get("permissions", {})
        fixed_perms: dict[str, bool] = {}

        if isinstance(perms, dict):
            fixed_perms = {k.lower(): bool(v) for k, v in perms.items()}
        elif isinstance(perms, list):
            fixed_perms = {p.lower(): True for p in perms if isinstance(p, str)}
        else:
            return
        
        print(fixed_perms)

        # Wildcard handling: only set True for missing permissions
        if "*" in fixed_perms:
            wildcard_value = fixed_perms["*"]
            for p in MANAGED_PERMISSIONS_LIST:
                if p not in fixed_perms:
                    result[p] = wildcard_value

        # Apply explicit permissions from this rank
        for perm, allowed in fixed_perms.items():
            if perm == "*":
                continue
            result[perm] = allowed

        # Recurse on inherited ranks
        inherits = group.get("inherits", [])
        if isinstance(inherits, list):
            for parent in inherits:
                if isinstance(parent, str):
                    gather_permissions(parent)

    gather_permissions(base_rank)
    return result

perm_cache = {}
def check_perms(self: "PrimeBDS", player_or_user, perm: str, check_rank=False) -> bool:
    now = time.time()
    xuid = getattr(player_or_user, "xuid", None)

    if hasattr(player_or_user, "has_permission") and not check_rank:
        return player_or_user.has_permission(perm)

    if xuid is None:
        return False

    cached = perm_cache.get(xuid)
    if cached:
        perms, ts = cached
        return perm in perms

    user = self.db.get_offline_user(self.db.get_name_by_xuid(xuid))
    if not user:
        return False

    rank = getattr(user, "internal_rank", "").lower() if hasattr(user, "internal_rank") else ""
    final_perms = set(get_rank_permissions(rank))

    user_permissions = self.db.get_permissions(xuid)
    for perm_name, allowed in user_permissions.items():
        if allowed:
            final_perms.add(perm_name)
        else:
            final_perms.discard(perm_name)

    perm_cache[xuid] = (final_perms, now)

    return perm in final_perms

_prefix_cache = {}
_suffix_cache = {}
def get_prefix(rank: str, permissions=None) -> str:
    """
    Returns the prefix for a given rank, using cache if available.
    """
    global _prefix_cache
    if rank in _prefix_cache:
        return _prefix_cache[rank]

    if permissions is None:
        permissions = load_permissions(cache=True)

    prefix = get_rank_group(rank, {}).get("prefix", "")
    _prefix_cache[rank] = prefix
    return prefix

def get_suffix(rank: str, permissions=None) -> str:
    """
    Returns the suffix for a given rank, using cache if available.
    """
    global _suffix_cache
    if rank in _suffix_cache:
        return _suffix_cache[rank]

    if permissions is None:
        permissions = load_permissions(cache=True)

    suffix = get_rank_group(rank, {}).get("suffix", "")
    _suffix_cache[rank] = suffix
    return suffix

def clear_prefix_suffix_cache():
    """
    Clears the prefix/suffix caches (useful if permissions are reloaded).
    """
    global _prefix_cache, _suffix_cache
    _prefix_cache.clear()
    _suffix_cache.clear()

def invalidate_perm_cache(self, xuid: str):
    perm_cache.pop(xuid, None)
            
def check_internal_rank(user1_rank: str, user2_rank: str) -> bool:
    if user1_rank not in RANKS or user2_rank not in RANKS:
        return False
    return RANKS.index(user1_rank) < RANKS.index(user2_rank)
