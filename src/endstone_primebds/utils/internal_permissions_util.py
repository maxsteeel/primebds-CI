import time

from endstone import Player

from endstone_primebds.utils.config_util import load_permissions

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Define ranks in order of hierarchy
RANKS = list(load_permissions().keys())
PERMISSIONS = load_permissions()

MANAGED_PERMISSIONS_LIST = []

MINECRAFT_PERMISSIONS = [
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

EXCLUDED_PERMISSIONS = [
    "minecraft",
    "minecraft.command",
    "minecraft.command.permission",
    "endstone.command.devtools",
    "endstone.command.banip",
    "endstone.command.unbanip",
    "endstone.command.banlist"
]

exempt_perms = [
    "primebds.exempt.msgtoggle",
    "primebds.exempt.globalmute",
    "primebds.exempt.mute",
    "primebds.exempt.ban",
    "primebds.exempt.kick",
    "primebds.exempt.warn",
    "primebds.exempt.jail"
]

def load_perms(self: "PrimeBDS"):
    plugin_perms = set()
    
    for plugin in self.server.plugin_manager.plugins:
        if not hasattr(plugin, "commands"):
            continue
        for cmd_name, cmd_data in plugin.commands.items():
            perms = cmd_data.get("permissions", [])
            for perm in perms:
                plugin_perms.add(perm.lower())

    plugin_perms |= {str(p.name).lower() for p in self.server.plugin_manager.permissions}
    combined = plugin_perms | {p.lower() for p in MINECRAFT_PERMISSIONS}

    excluded_lower = {p.lower() for p in EXCLUDED_PERMISSIONS}
    filtered = [perm for perm in combined if perm not in excluded_lower]

    MANAGED_PERMISSIONS_LIST.clear()
    MANAGED_PERMISSIONS_LIST.extend(filtered)
    # print(MANAGED_PERMISSIONS_LIST)

    for perm in exempt_perms:
        if perm not in MANAGED_PERMISSIONS_LIST:
            MANAGED_PERMISSIONS_LIST.append(perm)

    print(f"[PrimeBDS] Loaded {len(MANAGED_PERMISSIONS_LIST)} permissions from {len(self.server.plugin_manager.plugins)} plugins")

def normalize_rank_name(rank: str) -> str:
    rank = rank.lower()
    if rank.startswith("primebds.rank."):
        rank = rank[len("primebds.rank."):]

    for r in RANKS:
        if r.lower() == rank:
            return r
    return "Default"

def check_rank_exists(self: "PrimeBDS", target: Player, rank: str):
    if rank not in PERMISSIONS:
        self.db.update_user_data(target.name, 'internal_rank', "Default")

def get_rank_permissions(rank: str) -> list[str]:
    base_rank = normalize_rank_name(rank)
    seen_ranks = set()
    seen_perms = set()
    result = []

    def gather_permissions(r):
        r_norm = normalize_rank_name(r)
        if r_norm in seen_ranks:
            return
        seen_ranks.add(r_norm)

        perms = PERMISSIONS.get(r_norm, [])

        if "*" in perms:
            for perm in MANAGED_PERMISSIONS_LIST:
                if perm not in seen_perms:
                    result.append(perm)
                    seen_perms.add(perm)

        for perm in perms:
            perm = perm.lower()
            if perm.startswith("primebds.rank."):
                inherited_rank = perm[len("primebds.rank."):]
                gather_permissions(inherited_rank)
            elif perm != "*" and perm not in seen_perms:
                if perm not in MANAGED_PERMISSIONS_LIST:
                    MANAGED_PERMISSIONS_LIST.append(perm)
                result.append(perm)
                seen_perms.add(perm)

    gather_permissions(base_rank)
    return result

perm_cache = {}

def check_perms(self: "PrimeBDS", player_or_user, perm: str) -> bool:
    now = time.time()
    xuid = getattr(player_or_user, "xuid", None)

    if hasattr(player_or_user, "has_permission"):
        return player_or_user.has_permission(perm)

    if xuid is None:
        return False

    cached = perm_cache.get(xuid)
    if cached:
        perms, ts = cached
        return perm in perms or "*" in perms

    user = self.db.get_offline_user(self.db.get_name_by_xuid(xuid))
    if not user:
        return False

    rank = getattr(user, "internal_rank", "").lower() if hasattr(user, "internal_rank") else ""
    final_perms = set(get_rank_permissions(rank) or [])

    user_permissions = self.db.get_permissions(xuid)  
    for perm_name, allowed in user_permissions.items():
        if allowed:
            final_perms.add(perm_name)
        else:
            final_perms.discard(perm_name) 

    perm_cache[xuid] = (final_perms, now)

    return perm in final_perms

def invalidate_perm_cache(self, xuid: str):
    """Call this after updating permissions to clear cache for a user."""
    perm_cache.pop(xuid, None)
            
def check_internal_rank(user1_rank: str, user2_rank: str) -> bool:
    """
    Checks if user1 has a lower rank than user2.
    Returns True if user1_rank is lower, otherwise False.
    """
    if user1_rank not in RANKS or user2_rank not in RANKS:
        return False  # Handle cases where the rank is not found
    return RANKS.index(user1_rank) < RANKS.index(user2_rank)
