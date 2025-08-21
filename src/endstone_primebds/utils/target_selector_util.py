import re
import random
import math
from typing import TYPE_CHECKING, Optional
from endstone import Player
from endstone.actor import Actor
from endstone.util import Vector
from endstone.command import BlockCommandSender
from endstone_primebds.utils.math_util import vector_dot, vector_length_squared, vector_mul_scalar, vector_sub

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

# Global selector cache
# Maps (selector, origin_key) -> list of Players
selector_cache = {}

# Reverse lookup: player -> set of cache keys
player_to_cache_keys = {}

def invalidate_player_cache(player: Player):
    """Remove all cached entries that involve this player."""
    keys = player_to_cache_keys.pop(player, set())
    for key in keys:
        selector_cache.pop(key, None)

def register_cache_for_players(result: list, cache_key):
    """Track which players are in this cache result."""
    for p in result:
        if p not in player_to_cache_keys:
            player_to_cache_keys[p] = set()
        player_to_cache_keys[p].add(cache_key)


def parse_coord(value, origin_coord):
    if isinstance(value, str) and value.startswith("~"):
        offset = value[1:]  # remove "~"
        offset = float(offset) if offset else 0.0
        return origin_coord + offset
    return float(value)

def split_args(arg_str: str):
    parts, depth, current = [], 0, []
    for ch in arg_str:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts

def parse_selector(selector: str) -> Optional[dict]:
    selector = selector.strip()
    if "[" in selector and "]" not in selector:
        selector += "]"
    match = re.match(r"@([aprs])(?:\[(.*?)\])?$", selector)
    if not match:
        return None
    selector_type = match.group(1)
    args_str = match.group(2)
    args = {}
    if args_str:
        for pair in split_args(args_str):
            pair = pair.strip()
            if pair.startswith("scores=") and pair[7:].startswith("{") and pair.endswith("}"):
                scores_dict = {}
                inner = pair[8:-1]
                for score_pair in split_args(inner):
                    score_pair = score_pair.strip()
                    negate = "=!" in score_pair
                    s_key, s_val = score_pair.split("=!" if negate else "=", 1)
                    s_key, s_val = s_key.strip(), s_val.strip()
                    if ".." in s_val:
                        start, end = s_val.split("..", 1)
                        start = int(start) if start else None
                        end = int(end) if end else None
                        scores_dict[s_key] = (("range", start, end), negate)
                    else:
                        if s_val.replace(".", "", 1).isdigit():
                            s_val = float(s_val) if "." in s_val else int(s_val)
                        scores_dict[s_key] = (("exact", s_val), negate)
                args["scores"] = scores_dict
                continue
            if "=!" in pair:
                key, value = pair.split("=!", 1)
                negate = True
            else:
                key, value = pair.split("=", 1)
                negate = False
            key, value = key.strip(), value.strip()
            if value.replace(".", "", 1).isdigit():
                value = float(value) if "." in value else int(value)
            args[key] = (value, negate)
    return {"type": selector_type, "args": args}

def get_arg_value(args, key, default):
    if key in args:
        val = args[key]
        if isinstance(val, tuple):
            return val[0]
        return val
    return default

def passes_filters(actor: Player, args: dict, origin: Vector) -> bool:
    x = parse_coord(get_arg_value(args, "x", origin.x), origin.x)
    y = parse_coord(get_arg_value(args, "y", origin.y), origin.y)
    z = parse_coord(get_arg_value(args, "z", origin.z), origin.z)
    center = Vector(x, y, z)

    dx, dy, dz = actor.location.x - center.x, actor.location.y - center.y, actor.location.z - center.z
    dist_sq = dx*dx + dy*dy + dz*dz

    r_min = get_arg_value(args, "rm", None)
    if r_min is not None and dist_sq < float(r_min)**2:
        return False
    r_max = get_arg_value(args, "r", None)
    if r_max is not None and dist_sq > float(r_max)**2:
        return False

    def check_value(key: str, actual_val: str) -> bool:
        if key not in args:
            return True
        val, negate = args[key]
        actual_val = str(actual_val)
        val = str(val)
        return (actual_val.lower() != val.lower()) if negate else (actual_val.lower() == val.lower())

    if not check_value("name", actor.name):
        return False
    if not check_value("type", actor.type.lower().removeprefix("minecraft:")):
        return False

    if "tag" in args:
        val, negate = args["tag"]
        val = str(val)
        if (negate and val in actor.scoreboard_tags) or (not negate and val not in actor.scoreboard_tags):
            return False

    if "scores" in args:
        for scoreboard_name, (value_data, negate) in args["scores"].items():
            obj = actor.scoreboard.get_objective(scoreboard_name)
            if not obj:
                return False
            score = obj.get_score(actor).value
            if score is None:
                return False
            if value_data[0] == "exact":
                matches = score == value_data[1]
            else:
                start, end = value_data[1], value_data[2]
                matches = True
                if start is not None and score < start:
                    matches = False
                if end is not None and score > end:
                    matches = False
            if (negate and matches) or (not negate and not matches):
                return False

    for axis in ("x","y","z"):
        d_key = "d"+axis
        if d_key in args and axis in args:
            min_val = parse_coord(get_arg_value(args, axis, getattr(origin, axis)), getattr(origin, axis))
            delta = parse_coord(get_arg_value(args, d_key, 0), getattr(origin, axis))
            max_val = min_val + delta
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            if not (min_val <= getattr(actor.location, axis) <= max_val):
                return False

    return True

def get_matching_actors(self: "PrimeBDS", selector: str, origin: BlockCommandSender):
    all_actors = self.server.online_players
    origin_loc = getattr(origin, "location", getattr(getattr(origin, "block", None), "location", Vector(0,0,0)))
    origin_key = (origin_loc.x, origin_loc.y, origin_loc.z)
    cache_key = (selector, origin_key)

    # Return cached result if available
    if cache_key in selector_cache:
        return selector_cache[cache_key]

    # Single player by name
    if not selector.startswith("@"):
        for actor in all_actors:
            if isinstance(actor, Player) and actor.name.lower() == selector.lower():
                selector_cache[cache_key] = [actor]
                register_cache_for_players([actor], cache_key)
                return [actor]
        selector_cache[cache_key] = []
        return []

    parsed = parse_selector(selector)
    if not parsed:
        selector_cache[cache_key] = []
        return []

    selector_type, args = parsed["type"], parsed["args"]

    result = [a for a in all_actors if isinstance(a, Player) and passes_filters(a, args, origin_loc)]

    # Apply special selector types
    if selector_type == "s":
        result = [origin] if passes_filters(origin, args, origin_loc) else []
    elif selector_type == "p":
        result.sort(key=lambda a: (a.location - origin_loc).length_squared())
        result = result[:1]
    elif selector_type == "r":
        result = [random.choice(result)] if result else []

    selector_cache[cache_key] = result
    register_cache_for_players(result, cache_key)
    return result

def get_target_entity(player: Player, max_distance: float = 10) -> Optional[Actor]:
    """Returns the closest actor in a 10-block range in front of the player."""
    if not player or not hasattr(player, "location"):
        return None

    origin = player.location
    yaw = player.location.yaw
    pitch = player.location.pitch

    rad_yaw = math.radians(-yaw)
    rad_pitch = math.radians(-pitch)

    forward = Vector(
        math.sin(rad_yaw) * math.cos(rad_pitch),
        math.sin(rad_pitch),
        math.cos(rad_yaw) * math.cos(rad_pitch)
    )

    closest_actor = None
    closest_dist_sq = max_distance * max_distance

    for actor in player.level.actors:
        if actor == player:
            continue

        delta = vector_sub(actor.location, origin)
        proj = vector_dot(delta, forward)

        if 0 <= proj <= max_distance:
            perp = vector_sub(delta, vector_mul_scalar(forward, proj))
            perp_sq = vector_length_squared(perp)
            if perp_sq < 1.0:
                dist_sq = vector_length_squared(delta)
                if dist_sq < closest_dist_sq:
                    closest_dist_sq = dist_sq
                    closest_actor = actor

    return closest_actor