import re
from endstone.command import CommandSender, BlockCommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.internal_permissions_util import RANKS
from endstone_primebds.utils.config_util import load_permissions, save_permissions

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

command, permission = create_command(
    "rank",
    "Sets the internal rank for a player!",
    [
        "/rank (set)<rank_set: rank_set> <player: player> <rank: string>",
        "/rank (add|remove)<rank_perm: rank_perm> <rank: string> <perm: message>",
        "/rank (inherit)<rank_inherit: rank_inherit> <rank_child: string> <rank_parent: string>",
        "/rank (create|delete|list)<rank_action: rank_action> [rank: message]"
    ],
    ["primebds.command.rank"]
)

# RANK COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, BlockCommandSender):
        sender.send_message(f"§cThis command cannot be automated")
        return False
    
    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    target = args[1] if len(args) > 1 else None
    subaction = args[0].lower()
    
    perms = load_permissions()

    def find_rank(name: str, perms: dict[str, list[str]]) -> str | None:
        """Return the exact rank key matching `name` case-insensitively, or None if not found."""
        return next((r for r in perms if r.lower() == name.lower()), None)

    def rank_exists(name: str, perms: dict[str, list[str]]) -> bool:
        """Return True if rank exists (case-insensitive)."""
        return find_rank(name, perms) is not None

    def permission_exists(rank: str, perm: str, perms: dict[str, list[str]]) -> bool:
        """Check if `perm` exists in `rank`'s permissions case-insensitively."""
        rank_key = find_rank(rank, perms)
        if not rank_key:
            return False
        return any(p.lower() == perm.lower() for p in perms[rank_key])

    if subaction == "set":
        user = self.db.get_offline_user(target)
        if not user:
            sender.send_message(f"Player \"{target}\" not found")
            return False
        
        new_rank_lower = args[2].lower()
        ranks_map = {r.lower(): r for r in RANKS}

        if new_rank_lower == "op":
            new_rank_lower = "operator"

        if new_rank_lower not in ranks_map:
            sender.send_message(f"Invalid rank: {args[2]}. Valid ranks are: {', '.join(RANKS)}")
            return False

        proper_rank = ranks_map[new_rank_lower]
        self.db.update_user_data(target, 'internal_rank', proper_rank)

        player = self.server.get_player(target)
        if player:
            if proper_rank.lower() == "operator":
                self.server.dispatch_command(self.server.command_sender, f"op \"{target}\"")
            else:
                self.server.dispatch_command(self.server.command_sender, f"deop \"{target}\"")

            self.reload_custom_perms(player)

        sender.send_message(f"Player §e{target}'s §frank was updated to §e{proper_rank}")
        return True

    elif subaction == "create":
        rank_name = args[1]

        if rank_exists(rank_name, perms):
            sender.send_message(f"§cRank \"{rank_name}\" already exists")
            return False

        perms[rank_name] = []
        save_permissions(perms)
        sender.send_message(f"Created rank §e\"{rank_name}\" §rsuccessfully")
        return True

    elif subaction == "delete":
        rank_name = args[1]

        if not rank_exists(rank_name, perms):
            sender.send_message(f"§cRank \"{rank_name}\" does not exist")
            return False

        actual_rank = find_rank(rank_name, perms)
        del perms[actual_rank]
        save_permissions(perms)
        updatePermissionsFiltered(self, {actual_rank})
        sender.send_message(f"Deleted rank §e\"{actual_rank}\" §rsuccessfully")
        return True

    elif subaction == "add":
        rank_name = args[1]
        permission = args[2]

        if rank_name == "op":
            rank_name = "operator"

        if not rank_exists(rank_name, perms):
            sender.send_message(f"§cRank \"{rank_name}\" does not exist")
            return False
        
        actual_rank = find_rank(rank_name, perms)
        if permission_exists(actual_rank, permission, perms):
            sender.send_message(f"Rank §e\"{actual_rank}\" §ralready has permission §e\"{permission}\"")
            return False
        
        perms[actual_rank].append(permission)
        save_permissions(perms)
        updatePermissionsFiltered(self, {actual_rank})
        sender.send_message(f"Added permission §e\"{permission}\" §rto rank §e\"{actual_rank}\"")
        return True

    elif subaction == "remove":
        rank_name = args[1]
        permission = args[2]

        if rank_name == "op":
            rank_name = "operator"

        if not rank_exists(rank_name, perms):
            sender.send_message(f"§cRank \"{rank_name}\" does not exist")
            return False
        
        actual_rank = find_rank(rank_name, perms)
        if not permission_exists(actual_rank, permission, perms):
            sender.send_message(f"Rank §e\"{actual_rank}\" §rdoes not have permission §e\"{permission}\"")
            return False
        
        perms[actual_rank] = [p for p in perms[actual_rank] if p.lower() != permission.lower()]
        save_permissions(perms)
        updatePermissionsFiltered(self, {actual_rank})
        sender.send_message(f"Removed permission §e\"{permission}\" §rfrom rank §e\"{actual_rank}\"")
        return True

    elif subaction == "list":
        if not perms:
            sender.send_message("§eNo ranks available.")
            return True

        sender.send_message("§eAvailable ranks:")
        for rank in perms:
            sender.send_message(f" §7- §e{rank}")
        return True

    elif subaction == "inherit":
        child_rank = args[1]
        parent_rank = args[2]

        if child_rank == "op":
            child_rank = "operator"

        if parent_rank == "op":
            parent_rank = "operator"

        child = find_rank(child_rank, perms)
        parent = find_rank(parent_rank, perms).lower()

        if not child:
            sender.send_message(f"§cChild rank \"{child_rank}\" does not exist")
            return False
        if not parent:
            sender.send_message(f"§cParent rank \"{parent_rank}\" does not exist")
            return False

        inherit_perm = f"primebds.rank.{parent}"

        if permission_exists(child, inherit_perm, perms):
            sender.send_message(f"Rank §e\"{child}\" §ralready inherits from §e\"{parent}\"")
            return False

        perms[child].append(inherit_perm)
        save_permissions(perms)
        updatePermissionsFiltered(self, {child})
        sender.send_message(f"Rank §e\"{child}\" §rnow inherits permissions from §e\"{parent}\"")
        return True

    return True

def updatePermissionsFiltered(self: "PrimeBDS", affected_ranks: set):
    """Reload permissions only for players whose rank is in affected_ranks"""
    for player in self.server.online_players:
        user_data = self.db.get_online_user(player.xuid)
        if user_data and user_data.internal_rank in affected_ranks:
            self.reload_custom_perms(player)