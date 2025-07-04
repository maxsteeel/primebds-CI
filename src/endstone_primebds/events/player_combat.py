from typing import TYPE_CHECKING
from time import time

from endstone import GameMode, Player
from endstone._internal.endstone_python import Vector
from endstone.event import ActorDamageEvent, ActorKnockbackEvent

from endstone_primebds.utils.configUtil import load_config

if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def handle_damage_event(self: "PrimeBDS", ev: ActorDamageEvent):

    config = load_config()

    entity = ev.actor  # Entity taking damage
    entity_key = f"{entity.type}:{entity.id}"
    current_time = time()
    last_hit_time = self.entity_damage_cooldowns.get(entity_key, 0)

    tags = []
    if hasattr(ev, 'damage_source') and ev.damage_source:
        actor = getattr(ev.damage_source, 'actor', None)
        if actor and hasattr(actor, 'scoreboard_tags'):
            tags = actor.scoreboard_tags or []

    # Get tag-aware values
    modifier = get_custom_tag(config, tags, "base_damage")
    kb_cooldown = get_custom_tag(config, tags, "hit_cooldown_in_seconds")
    fall_damage_height = get_custom_tag(config, tags, "fall_damage_height")
    disable_fire_dmg = get_custom_tag(config, tags, "disable_fire_damage")
    disable_explosion_dmg = get_custom_tag(config, tags, "disable_explosion_damage")

    if ev.damage_source is not None:
        actor = ev.actor

        # Fire damage check
        if disable_fire_dmg and ev.damage_source.type == "fire_tick" or ev.damage_source.type == "fire" or ev.damage_source.type == "lava":
            ev.is_cancelled = True

        # Explosion damage check
        if disable_explosion_dmg and ev.damage_source.type == "entity_explosive":
            ev.is_cancelled = True

    if fall_damage_height != 3.5:
        if ev.damage_source.type == "fall":
            fall_height = ev.damage * 2
            if fall_height < fall_damage_height:
                ev.is_cancelled = True
                return
    
    # Apply bonus damage
    if modifier != 1:
        ev.damage += modifier

    # Apply cooldown logic
    if current_time - last_hit_time >= kb_cooldown:
        self.entity_damage_cooldowns[entity_key] = current_time
    else:
        ev.is_cancelled = True

    return

def handle_kb_event(self: "PrimeBDS", ev: ActorKnockbackEvent):
    config = load_config()
    source = ev.source
    source_player = self.server.get_player(source.name) if source.name else None

    tags = source_player.scoreboard_tags if source_player else []

    kb_h_modifier = get_custom_tag(config, tags, "horizontal_knockback_modifier")
    kb_v_modifier = get_custom_tag(config, tags, "vertical_knockback_modifier")
    kb_sprint_h_modifier = get_custom_tag(config, tags, "horizontal_sprint_knockback_modifier")
    kb_sprint_v_modifier = get_custom_tag(config, tags, "vertical_sprint_knockback_modifier")
    disable_sprint_hits = get_custom_tag(config, tags, "disable_sprint_hits")
    resisted_kb_percentage = get_custom_tag(config, tags, "resisted_knockback_percentage")

    # If all modifiers are 0, skip
    if kb_h_modifier == 0 and kb_v_modifier == 0 and kb_sprint_h_modifier == 0 and kb_sprint_v_modifier == 0:
        return

    kb_h_modifier = kb_h_modifier or 1.0
    kb_v_modifier = kb_v_modifier or 1.0
    kb_sprint_h_modifier = kb_sprint_h_modifier or 1.0
    kb_sprint_v_modifier = kb_sprint_v_modifier or 1.0

    is_player_sprinting = isinstance(source_player, Player) and source_player.is_sprinting

    # Sprint hit cancel logic (players only)
    if is_player_sprinting and disable_sprint_hits and ev.knockback.y <= 0:
        ev.is_cancelled = True
        return

    newx = ev.knockback.x * kb_h_modifier
    newy = ev.knockback.y * kb_v_modifier
    newz = ev.knockback.z * kb_h_modifier

    if ev.knockback.x == 0 or ev.knockback.z == 0:
        velocity = getattr(source_player or source, "velocity", Vector(0, 0, 0))
        newx = velocity.x * kb_h_modifier
        newz = velocity.z * kb_h_modifier

    if is_player_sprinting and kb_sprint_h_modifier != 0.0:
        newx *= kb_sprint_h_modifier
        newz *= kb_sprint_h_modifier

    if ev.knockback.y < 0:
        newy = (newy * kb_sprint_v_modifier) / 2

    if resisted_kb_percentage != 0:
        reduction = 1.0 - resisted_kb_percentage
        newx *= reduction
        newy *= reduction
        newz *= reduction

    ev.knockback = Vector(newx, abs(newy), newz)

def get_custom_tag(config, tags, key):
    """
    Returns the custom KB modifiers, prioritizing tag-specific modifiers.
    If no matching tag or key is found, falls back to global value.
    """
    default = config["modules"]["combat"].get(key)

    tag_mods = config["modules"]["combat"].get("tag_overrides", {})
    for tag in tags:
        if tag in tag_mods and key in tag_mods[tag]:
            return tag_mods[tag][key]

    return default
