import re
from typing import TYPE_CHECKING
from endstone import Player
from endstone._internal.endstone_python import Vector

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def parse_selector(selector: str) -> dict | None:
    """
    Parses a selector like @a[name=test] into a dictionary.
    Handles missing closing bracket gracefully.
    Returns None if invalid.
    """
    selector = selector.strip()

    # Auto-close missing closing bracket
    if "[" in selector and "]" not in selector:
        selector += "]"

    match = re.match(r"@([aprs])(?:\[(.*?)\])?$", selector)
    if not match:
        return None

    selector_type = match.group(1)
    args_str = match.group(2)
    args = {}

    if args_str:
        for pair in args_str.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value.replace(".", "", 1).isdigit():
                    args[key] = float(value) if "." in value else int(value)
                else:
                    args[key] = value

    return {"type": selector_type, "args": args}

def get_matching_actors(self: "PrimeBDS", selector: str, origin: Player):
    """
    Returns a list of actors that match the target selector or player name.
    Supports:
      - @a, @p, @r, @s
      - Direct player name string
      - Filters currently do not work due to Endstone limitations
    """

    all_actors = self.server.online_players

    # Direct name match (not a selector)
    if not selector.startswith("@"):
        for actor in all_actors:
            if isinstance(actor, Player) and actor.name.lower() == selector.lower():
                return [actor]
        return []

    parsed = parse_selector(selector)
    if not parsed:
        return []

    selector_type = parsed["type"]
    args = parsed["args"]
    origin_loc = origin.location

    result = []

    # Evaluate @s (self) early
    if selector_type == "s":
        return [origin] if passes_filters(origin, args, origin_loc) else []

    # @a: nearest player / general filters
    for actor in all_actors:
        if not isinstance(actor, Player):
            continue
        if not passes_filters(actor, args, origin_loc):
            continue
        result.append(actor)

    # @p: nearest player
    if selector_type == "p":
        result.sort(key=lambda a: (
            (a.location.x - origin_loc.x) ** 2 +
            (a.location.y - origin_loc.y) ** 2 +
            (a.location.z - origin_loc.z) ** 2
        ))
        return result[:1]

    # @r: random player
    elif selector_type == "r":
        import random
        return [random.choice(result)] if result else []

    return result

def passes_filters(actor: Player, args: dict, origin: Vector) -> bool:
    # Radius filter
    if "r" in args:
        center = Vector(
            args.get("x", origin.x),
            args.get("y", origin.y),
            args.get("z", origin.z)
        )
        dx = actor.location.x - center.x
        dy = actor.location.y - center.y
        dz = actor.location.z - center.z
        dist_sq = dx * dx + dy * dy + dz * dz
        if dist_sq > args["r"] * args["r"]:
            return False

    # Name match
    if "name" in args and actor.name != args["name"]:
        return False

    return True
