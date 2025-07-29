from typing import TYPE_CHECKING
from endstone_primebds.utils.dbUtil import UserDB

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Define ranks in order of hierarchy
RANKS = ["Default", "Helper", "Mod", "Operator"]

# Define permissions associated with each rank
MANAGED_PERMISSIONS_LIST = [
    "minecraft.command.kick",
    "endstone.command.ban",
    "endstone.command.unban",
    "primebds.globalmute.exempt",
    "primebds.mute.exempt",
    "primebds.ban.exempt",
    "primebds.kick.exempt"
]

def load_perms(self: "PrimeBDS"):
    primebds_perms = [
        perm_name
        for perm_name in self.permissions.keys()
        if perm_name.startswith("primebds.command.")
    ]

    MANAGED_PERMISSIONS_LIST.extend(primebds_perms)

PERMISSIONS = {
    "Default": [
        "primebds.command.spectate",
        "primebds.command.ping",
        "primebds.command.playtime",
        "primebds.command.refresh",
    ],
    "Helper": [
        "primebds.command.check",
        "primebds.command.monitor",
        "primebds.command.activity",
        "primebds.command.activitylist",
        "primebds.command.inspect",
        "primebds.command.grieflog",
        "primebds.command.socialspy",
        "primebds.command.invsee",
        "primebds.command.enderchest",
    ],
    "Mod": [
        "primebds.command.ipban",
        "primebds.command.mute",
        "primebds.command.permban",
        "primebds.command.punishments",
        "primebds.command.removeban",
        "primebds.command.tempban",
        "primebds.command.tempmute",
        "primebds.command.unmute",
        "primebds.command.nickname",
        "primebds.command.modspy",
        "primebds.command.offlinetp",
        "primebds.command.plist",
        "primebds.command.kick",
        "primebds.command.ban",
        "primebds.command.unban",
    ],
    "Operator": ["*"],
}

def get_permissions(rank: str) -> list[str]:
    """Returns a list of all permissions for a given rank, including inherited ones."""
    if rank.lower() == "operator":
        return list(set(MANAGED_PERMISSIONS_LIST))

    inherited_permissions = []
    seen = set()

    for r in RANKS:
        for perm in PERMISSIONS.get(r, []):
            if perm not in seen:
                inherited_permissions.append(perm)
                seen.add(perm)

        if r.lower() == rank.lower():
            break

    return inherited_permissions


def check_perms(player_or_user, perm: str) -> bool:
    """Check if a player object or DB user has a given permission, including inherited perms."""
    db = None
    rank = None

    try:
        if hasattr(player_or_user, "internal_rank"):
            rank = getattr(player_or_user, "internal_rank", "").lower()

        elif hasattr(player_or_user, "xuid"):
            db = UserDB("users.db")
            user = db.get_online_user(player_or_user.xuid)
            if user and hasattr(user, "internal_rank"):
                rank = user.internal_rank.lower()

        if rank:
            rank_perms = get_permissions(rank)
            return "*" in rank_perms or perm in rank_perms

        return False
    finally:
        if db:
            db.close_connection()

def check_internal_rank(user1_rank: str, user2_rank: str) -> bool:
    """
    Checks if user1 has a lower rank than user2.
    Returns True if user1_rank is lower, otherwise False.
    """
    if user1_rank not in RANKS or user2_rank not in RANKS:
        return False  # Handle cases where the rank is not found
    return RANKS.index(user1_rank) < RANKS.index(user2_rank)
