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

def load_perms(self: "PrimeBDS"):
    config = load_config()
    modules = config.get("modules", {})
    perms_manager = modules.get("permissions_manager", {})
    minecraft_enabled = perms_manager.get("minecraft", True)
    primebds_enabled = perms_manager.get("primebds", True)
    endstone_enabled = perms_manager.get("endstone", True)
    wildcard_enabled = perms_manager.get("*", True)

    plugin_perms = set()
    try:
        server_registered = {str(p.name).lower() for p in self.server.plugin_manager.permissions}
    except RuntimeError:
        server_registered = set()

    plugin_perms = set()

    for perm in server_registered:
        prefix = perm.split(".")[0]
        if (prefix == "minecraft" and minecraft_enabled) or \
        (prefix == "primebds" and primebds_enabled) or \
        (prefix == "endstone" and endstone_enabled) or \
        (prefix not in {"minecraft", "endstone"} and wildcard_enabled):
            plugin_perms.add(perm)

    if primebds_enabled:
        primebds_filtered = [perm for perm in plugin_perms if "primebds" in perm]
        print(f"[PrimeBDS] PrimeBDS: Loaded {len(primebds_filtered)} permissions")

    if wildcard_enabled:
        other_perms_by_prefix = {}
        for perm in plugin_perms:
            prefix = perm.split(".")[0]
            if prefix not in {"minecraft", "primebds", "endstone"}:
                other_perms_by_prefix.setdefault(prefix, []).append(perm)

        for prefix, perms in other_perms_by_prefix.items():
            print(f"[PrimeBDS] {prefix}: Loaded {len(perms)} permissions")

    if minecraft_enabled:
        plugin_perms |= {p.lower() for p in MINECRAFT_PERMISSIONS}

    MANAGED_PERMISSIONS_LIST.clear()
    MANAGED_PERMISSIONS_LIST.extend(plugin_perms)

    for perm in EXTRA_PERMS:
        if perm not in MANAGED_PERMISSIONS_LIST and primebds_enabled:
            MANAGED_PERMISSIONS_LIST.append(perm)

    endstone_filtered = [perm for perm in plugin_perms if "endstone" in perm]
    if endstone_filtered:
        print(f"[PrimeBDS] Endstone: Loaded {len(endstone_filtered)} permissions")

    minecraft_filtered = [perm for perm in plugin_perms if perm in {p.lower() for p in MINECRAFT_PERMISSIONS}]
    print(f"[PrimeBDS] Minecraft: Loaded {len(minecraft_filtered)} permissions")
    print(f"[PrimeBDS] Total managed permissions: {len(MANAGED_PERMISSIONS_LIST)}")

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
        return "Default"
    return rank

def get_rank_permissions(rank: str) -> dict[str, bool]:
    base_rank = normalize_rank_name(rank)
    seen_ranks = set()
    result: dict[str, bool] = {}

    def gather_permissions(r):
        r_norm = normalize_rank_name(r)
        if r_norm in seen_ranks:
            return
        seen_ranks.add(r_norm)

        group = PERMISSIONS.get(r_norm)
        if not group:
            return

        perms = group.get("permissions", {})
        if "*" in perms:
            if perms["*"]:
                for p in MANAGED_PERMISSIONS_LIST:
                    result[p] = True
            else:
                for p in MANAGED_PERMISSIONS_LIST:
                    result[p] = False

        for perm, allowed in perms.items():
            if perm == "*":
                continue
            result[perm] = allowed  # True/False as stored

        for parent in group.get("inherits", []):
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

def invalidate_perm_cache(self, xuid: str):
    perm_cache.pop(xuid, None)
            
def check_internal_rank(user1_rank: str, user2_rank: str) -> bool:
    if user1_rank not in RANKS or user2_rank not in RANKS:
        return False  # Handle cases where the rank is not found
    return RANKS.index(user1_rank) < RANKS.index(user2_rank)

def reload_ranks():
    RANKS = list(load_permissions().keys())