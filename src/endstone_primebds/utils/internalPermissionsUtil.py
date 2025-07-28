# Define ranks in order of hierarchy
RANKS = ["Default", "Helper", "Mod", "Operator"]

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
    "primebds.command.enderchest"
]

def cmd(name: str) -> str:
    """Helper to safely get the string from PERMISSIONS_LIST."""
    return next((p for p in PERMISSIONS_LIST if p.endswith(name)), name)

PERMISSIONS = {
    "Default": [
        cmd("spectate"),
        cmd("ping"),
        cmd("playtime"),
        cmd("refresh"),
    ],
    "Helper": [
        cmd("check"),
        cmd("monitor"),
        cmd("activity"),
        cmd("activitylist"),
        cmd("inspect"),
        cmd("grieflog"),
        cmd("socialspy"),
        cmd("invsee"),
        cmd("enderchest"),
    ],
    "Mod": [
        cmd("ipban"),
        cmd("mute"),
        cmd("permban"),
        cmd("punishments"),
        cmd("removeban"),
        cmd("tempban"),
        cmd("tempmute"),
        cmd("unmute"),
        cmd("nickname"),
        cmd("modspy"),
        cmd("offlinetp"),
        cmd("plist")
    ],
    "Operator": ["*"],
}

def get_permissions(rank: str) -> list[str]:
    """Returns a list of all permissions for a given rank, including inherited ones."""
    inherited_permissions = []
    rank_order = ["Default", "Helper", "Mod", "Operator"]

    for r in rank_order:
        inherited_permissions.extend(PERMISSIONS.get(r, []))
        if r == rank:
            break  # Stop once we reach the requested rank

    return inherited_permissions

def check_perms(rank: str, perm: str) -> bool:
    """Check if a rank has a given permission."""
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
