from endstone.command import CommandSender, BlockCommandSender
from endstone_primebds.utils.command_util import create_command
from endstone_primebds.utils.internal_permissions_util import check_perms

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

command, permission = create_command(
    "permissions",
    "Sets the internal permissions for a player!",
    [
        "/permissions <player: player> (settrue|setfalse|setneutral)<set_perm: set_perm> <perm: string>"
     ],
    ["primebds.command.permissions", "primebds.command.perms"],
    "op",
    ["perms"]
)

# PERMISSIONS COMMAND FUNCTIONALITY
def handler(self: "PrimeBDS", sender: CommandSender, args: list[str]) -> bool:
    if isinstance(sender, BlockCommandSender):
        sender.send_message(f"§cThis command cannot be automated")
        return False
    
    if any("@" in arg for arg in args):
        sender.send_message(f"§cTarget selectors are invalid for this command")
        return False

    target = args[0]
    subaction = args[1].lower()

    user = self.db.get_offline_user(target)
    if not user:
        sender.send_message(f"Player \"{target}\" not found")
        return False

    if subaction in "settrue":
        permission = args[2]
        player = self.server.get_player(target)
        if player:
            player.add_attachment(self, permission, True)
            player.update_commands()
            player.recalculate_permissions()

        self.db.set_permission(user.xuid, permission, True)
        sender.send_message(f"§e{permission} §fpermission for §e{target} §fwas set to §atrue")

    elif subaction == "setfalse":
        permission = args[2]
        player = self.server.get_player(target)
        if player:
            player.add_attachment(self, permission, False)
            player.update_commands()
            player.recalculate_permissions()

        self.db.set_permission(user.xuid, permission, False)
        sender.send_message(f"§e{permission} §fpermission for §e{target} §fwas set to §cfalse")

    elif subaction == "setneutral":
        permission = args[2]
        player = self.server.get_player(target)
        self.db.delete_permission(user.xuid, permission)

        if player:
            if player.permission_level.name == "DEFAULT":
                player.add_attachment(self, permission, check_perms(self, player, permission, True))
            else:
                player.add_attachment(self, permission, True)

        sender.send_message(f"§e{permission} §fpermission for §e{target} §fwas set to §7neutral")
    
    player.recalculate_permissions()
    player.update_commands()

    return True