import re
import random
import numpy as np
from typing import TYPE_CHECKING, List, Optional
from endstone import Player
from endstone.actor import Actor
from endstone.util import Vector

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

selector_cache = {}
player_to_cache_keys = {}

def invalidate_player_cache(player: Player):
    for key in player_to_cache_keys.pop(player, ()):
        selector_cache.pop(key, None)

def register_cache_for_players(result: list, cache_key):
    for p in result:
        player_to_cache_keys.setdefault(p, set()).add(cache_key)

def parse_coord(value, origin_coord):
    if isinstance(value, str) and value.startswith("~"):
        offset = float(value[1:] or 0.0)
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

from typing import List, Optional
import numpy as np

def passes_filters(players: List[object], args: dict, origin: Optional[object] = None) -> np.ndarray:
    """
    Returns a boolean mask of players/command-senders passing the filters.
    Safely handles missing origin or missing player.location by using (0,0,0).
    """
    n = len(players)
    if n == 0:
        return np.array([], dtype=bool)

    # origin fallback to (0,0,0)
    origin_arr = np.array([
        getattr(origin, "x", 0.0) if origin is not None else 0.0,
        getattr(origin, "y", 0.0) if origin is not None else 0.0,
        getattr(origin, "z", 0.0) if origin is not None else 0.0,
    ], dtype=np.float32)

    # Build arrays of positions (safe: default to 0,0,0 if missing)
    positions = np.array([
        (
            getattr(getattr(p, "location", None), "x", 0.0),
            getattr(getattr(p, "location", None), "y", 0.0),
            getattr(getattr(p, "location", None), "z", 0.0),
        )
        for p in players
    ], dtype=np.float32)


    # Distance squared
    deltas = positions - origin_arr
    dist_sq = np.sum(deltas**2, axis=1)

    # Mask start
    mask = np.ones(n, dtype=bool)
    r_min = args.get("rm", (None, False))[0]
    r_max = args.get("r", (None, False))[0]

    if r_min is not None:
        mask &= dist_sq >= float(r_min)**2
    if r_max is not None:
        mask &= dist_sq <= float(r_max)**2

    # Name filter (safe fallback to empty string)
    if "name" in args:
        val, negate = args["name"]
        val = str(val).lower()
        player_names = np.array([str(getattr(p, "name", "")).lower() for p in players])
        if negate:
            mask &= player_names != val
        else:
            mask &= player_names == val

    # Type filter (safe fallback to empty string)
    if "type" in args:
        val, negate = args["type"]
        val = str(val).lower().removeprefix("minecraft:")
        player_types = np.array([str(getattr(p, "type", "")).lower().removeprefix("minecraft:") for p in players])
        if negate:
            mask &= player_types != val
        else:
            mask &= player_types == val

    # Tag filter (safe fallback to empty iterable)
    if "tag" in args:
        val, negate = args["tag"]
        tag_check = np.array([val in getattr(p, "scoreboard_tags", []) for p in players], dtype=bool)
        mask &= tag_check != negate  # if negate True -> invert

    # dX/dY/dZ axis filters (safe origin & player location handling)
    for axis in ("x", "y", "z"):
        d_key = "d" + axis
        if d_key in args and axis in args:
            origin_val = getattr(origin, axis, 0.0) if origin is not None else 0.0
            min_val = parse_coord(args[axis][0], origin_val)
            delta_val = parse_coord(args[d_key][0], origin_val)
            max_val = min_val + delta_val
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            axis_vals = np.array([
                getattr(getattr(p, "location", None), axis, 0.0) if getattr(p, "location", None) is not None else 0.0
                for p in players
            ], dtype=np.float32)
            mask &= (axis_vals >= min_val) & (axis_vals <= max_val)

    # Scores filter (robustly handle missing scoreboard/objective/score -> treat as no match)
    if "scores" in args:
        for scoreboard_name, (value_data, negate) in args["scores"].items():
            # collect scores (None if missing)
            raw_scores = []
            for p in players:
                board = getattr(p, "scoreboard", None)
                if board is None:
                    raw_scores.append(None)
                    continue
                obj = board.get_objective(scoreboard_name) if callable(getattr(board, "get_objective", None)) else None
                if obj is None:
                    raw_scores.append(None)
                    continue
                try:
                    score_obj = obj.get_score(p)
                    s = getattr(score_obj, "value", None)
                except Exception:
                    s = None
                raw_scores.append(s)

            # convert to float array with NaN for missing values
            scores_arr = np.array([float(s) if s is not None else np.nan for s in raw_scores], dtype=float)

            valid = np.ones(n, dtype=bool)
            exact_type = value_data[0] == "exact"
            if exact_type:
                target = float(value_data[1])
                valid &= (~np.isnan(scores_arr)) & (scores_arr == target)
            else:
                start, end = value_data[1], value_data[2]
                if start is not None:
                    valid &= (~np.isnan(scores_arr)) & (scores_arr >= float(start))
                if end is not None:
                    valid &= (~np.isnan(scores_arr)) & (scores_arr <= float(end))

            if negate:
                valid = ~valid
            mask &= valid

    return mask

def get_matching_actors(self: "PrimeBDS", selector: str, origin):
    all_actors = [a for a in self.server.online_players if isinstance(a, Player)]
    origin_loc = getattr(origin, "location", getattr(getattr(origin, "block", None), "location", Vector(0,0,0)))
    origin_key = (origin_loc.x, origin_loc.y, origin_loc.z)
    cache_key = (selector, origin_key)

    if cache_key in selector_cache:
        return selector_cache[cache_key]

    if not selector.startswith("@"):
        lower_name = selector.lower()
        for actor in all_actors:
            if actor.name.lower() == lower_name:
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

    mask = passes_filters(all_actors, args, origin_loc)
    result = list(np.array(all_actors)[mask])

    if selector_type == "s":
        result = [origin] if passes_filters([origin], args, origin_loc)[0] else []
    elif selector_type == "p":
        if result:
            positions = np.array([[a.location.x, a.location.y, a.location.z] for a in result], dtype=np.float32)
            origin_arr = np.array([origin_loc.x, origin_loc.y, origin_loc.z], dtype=np.float32)
            dist_sq = np.sum((positions - origin_arr)**2, axis=1)
            closest_idx = np.argmin(dist_sq)
            result = [result[closest_idx]]
    elif selector_type == "r":
        result = [random.choice(result)] if result else []

    selector_cache[cache_key] = result
    register_cache_for_players(result, cache_key)
    return result

def get_target_entity(player: Player, max_distance: float = 10) -> Optional[Actor]:
    if not player or not hasattr(player, "location"):
        return None

    origin = np.array([player.location.x, player.location.y, player.location.z], dtype=np.float32)
    rad_yaw = np.radians(-player.location.yaw)
    rad_pitch = np.radians(-player.location.pitch)
    forward = np.array([
        np.sin(rad_yaw) * np.cos(rad_pitch),
        np.sin(rad_pitch),
        np.cos(rad_yaw) * np.cos(rad_pitch)
    ], dtype=np.float32)

    actors = [a for a in player.level.actors if a != player]
    if not actors:
        return None

    positions = np.array([[a.location.x, a.location.y, a.location.z] for a in actors], dtype=np.float32)

    deltas = positions - origin       
    projs = deltas @ forward   

    mask = (projs >= 0) & (projs <= max_distance)

    if not np.any(mask):
        return None
    
    perps = deltas[mask] - np.outer(projs[mask], forward)
    perp_sq = np.sum(perps**2, axis=1)
    in_range_mask = perp_sq < 1.0

    if not np.any(in_range_mask):
        return None

    deltas_in_range = deltas[mask][in_range_mask]
    dist_sq = np.sum(deltas_in_range**2, axis=1)
    closest_idx = np.argmin(dist_sq)

    actors_in_range = np.array(actors)[mask][in_range_mask]
    return actors_in_range[closest_idx]