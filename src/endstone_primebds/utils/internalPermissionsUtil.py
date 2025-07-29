from endstone import Player
from endstone_primebds.utils.dbUtil import UserDB

# Define ranks in order of hierarchy
RANKS = ["default", "helper", "mod", "operator"]

# Define permissions associated with each rank
PERMISSIONS_LIST = [
    "primebds.command.bottom",
    "primebds.command.check",
    "primebds.command.fly",
    "primebds.command.nickname",
    "primebds.command.ping",
    "primebds.command.playtime",
    "primebds.command.popup",
    "primebds.command.refresh",
    "primebds.command.spectate",
    "primebds.command.speed",
    "primebds.command.tip",
    "primebds.command.toast",
    "primebds.command.top",
    "primebds.command.ipban",
    "primebds.command.mute",
    "primebds.command.permban",
    "primebds.command.punishments",
    "primebds.command.removeban",
    "primebds.command.tempban",
    "primebds.command.tempmute",
    "primebds.command.unmute",
    "primebds.command.activity",
    "primebds.command.activitylist",
    "primebds.command.bossbar",
    "primebds.command.grieflog",
    "primebds.command.inspect",
    "primebds.command.levelscores",
    "primebds.command.monitor",
    "primebds.command.primebds",
    "primebds.command.reloadscripts",
    "primebds.command.setrank",
    "primebds.command.updatepacks",
    "primebds.command.viewscriptprofiles",
    "primebds.command.world",
    "primebds.command.alist",
    "primebds.command.gma",
    "primebds.command.gmc",
    "primebds.command.gms",
    "primebds.command.gmsp",
    "primebds.command.send",
    "primebds.command.offlinetp",
    "primebds.command.feed",
    "primebds.command.heal",
    "primebds.command.modspy",
    "primebds.command.plist",
    "primebds.command.socialspy",
    "primebds.command.invsee",
    "primebds.command.enderchest",
    "primebds.command.globalmute",
    "primebds.globalmute.exempt",
    "primebds.mute.exempt",
    "primebds.ban.exempt",
    "primebds.kick.exempt"
]

def perm(name: str) -> str:
    """Helper to safely get the string from PERMISSIONS_LIST."""
    return next((p for p in PERMISSIONS_LIST if p.endswith(name)), name)

PERMISSIONS = {
    "default": [
        perm("spectate"),
        perm("ping"),
        perm("playtime"),
        perm("refresh"),
    ],
    "helper": [
        perm("check"),
        perm("monitor"),
        perm("activity"),
        perm("activitylist"),
        perm("inspect"),
        perm("grieflog"),
        perm("socialspy"),
        perm("invsee"),
        perm("enderchest"),
    ],
    "mod": [
        perm("ipban"),
        perm("mute"),
        perm("permban"),
        perm("punishments"),
        perm("removeban"),
        perm("tempban"),
        perm("tempmute"),
        perm("unmute"),
        perm("nickname"),
        perm("modspy"),
        perm("offlinetp"),
        perm("plist"),
        perm("globalmute.exempt"),

    ],
    "operator": ["*"],
}

def get_permissions(rank: str) -> list[str]:
    """Returns a list of all permissions for a given rank, including inherited ones."""
    inherited_permissions = []
    rank_order = RANKS

    for r in rank_order:
        inherited_permissions.extend(PERMISSIONS.get(r, []))
        if r == rank:
            break  # Stop once we reach the requested rank

    return inherited_permissions

def check_perms(player: Player, perm: str) -> bool:
    """Check if a rank has a given permission."""
    db = UserDB("users.db")
    rank = db.get_online_user(player.xuid).internal_rank.lower()
    db.close_connection()
    rank_perms = PERMISSIONS.get(rank, [])

    # If admin or '*' is present, they have all permissions
    if "*" in rank_perms:
        return True

    return perm in rank_perms

def check_internal_rank(user1_rank: str, user2_rank: str) -> bool:
    """
    Checks if user1 has a lower rank than user2.
    Returns True if user1_rank is lower, otherwise False.
    """
    if user1_rank not in RANKS or user2_rank not in RANKS:
        return False  # Handle cases where the rank is not found
    return RANKS.index(user1_rank) < RANKS.index(user2_rank)
