# scheduler.py — NPC scheduler, action executor, physics, needs decay

import math
import random
import time
import threading
import logging
from typing import Optional
import config
import llm as llm_module
from entity import Entity, Item, Bullet

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Core simulation brain. Called every frame with delta_time.
    Responsibilities:
      - Advance game time
      - Move NPCs along their paths
      - Decay hunger / energy
      - Detect arrivals and trigger LLM calls
      - Apply LLM response actions (move, say, attack, pick_up, ...)
      - Process bullets
      - Process developer global commands via scheduler LLM
    """

    def __init__(self, world):
        self.world = world
        self._lock = threading.Lock()   # protects world state writes from LLM threads

    # ─────────────────────────────────────────────────────────────────────────
    #  Main update  (called from game loop at ~60 FPS)
    # ─────────────────────────────────────────────────────────────────────────
    def update(self, real_dt: float):
        """real_dt: real-time seconds since last frame."""
        if self.world.paused:
            return

        game_dt = real_dt * config.GAME_MINUTES_PER_SECOND

        with self._lock:
            self.world.game_time += game_dt

            for entity in list(self.world.entities.values()):
                if not entity.is_alive():
                    continue
                self._update_entity(entity, real_dt, game_dt)

            self._update_bullets(real_dt)

        # Process pending developer commands (outside lock to avoid deadlock with LLM thread)
        if self.world.pending_commands:
            cmd = self.world.pending_commands.pop(0)
            self._dispatch_global_command(cmd)

    # ─────────────────────────────────────────────────────────────────────────
    #  Per-entity update
    # ─────────────────────────────────────────────────────────────────────────
    def _update_entity(self, e: Entity, real_dt: float, game_dt: float):
        gt = self.world.game_time

        # ── Sleep ─────────────────────────────────────────────────────────────
        if e.status == "sleeping":
            e.energy = min(1.0, e.energy + 0.003 * game_dt)
            if e.sleep_until and gt >= e.sleep_until:
                e.status = "idle"
                e.sleep_until = None
                e.add_memory(gt, "Woke up feeling rested.")
            return

        # ── Stun ──────────────────────────────────────────────────────────────
        if e.stun_until and gt < e.stun_until:
            return

        # ── Needs decay ───────────────────────────────────────────────────────
        e.hunger = min(1.0, e.hunger + config.HUNGER_DECAY_RATE * game_dt)
        e.energy = max(0.0, e.energy - config.ENERGY_DECAY_RATE * game_dt)

        if e.hunger >= config.HUNGER_DAMAGE_THRESHOLD:
            e.health -= config.HUNGER_DAMAGE_RATE * game_dt
            if e.health <= 0:
                self.world.kill_entity(e.id)
                return

        # Bleeding
        if e.bleeding:
            e.health -= 0.3 * game_dt
            if gt - e.last_damage_time > 60:   # stop bleeding after 1 game-hour
                e.bleeding = False
            if e.health <= 0:
                self.world.kill_entity(e.id)
                return

        # ── Mood hint from needs ───────────────────────────────────────────────
        # Auto-eat: use food from inventory when hungry enough.
        # No LLM needed — a person with food in their pocket just eats it.
        if e.hunger >= 0.60:
            self._try_auto_eat(e, gt)

        # Auto-potion: use a potion when health is critically low.
        if e.health < e.max_health * 0.25:
            self._try_auto_potion(e, gt)

        if e.hunger > 0.75 and e.mood not in ("angry", "fearful"):
            e.mood = "hungry"
        elif e.energy < 0.2 and e.mood not in ("angry",):
            e.mood = "tired"

        # ── Movement ──────────────────────────────────────────────────────────
        arrived = False
        if e.destination and e.status == "moving":
            arrived = self._step_towards(e, real_dt)
            if arrived:
                e.status = "idle"
                e.destination = None

        # ── Animation ─────────────────────────────────────────────────────────
        if e.status == "moving":
            e.anim_timer += real_dt
            if e.anim_timer >= 0.2:
                e.anim_frame = (e.anim_frame + 1) % 4
                e.anim_timer = 0.0

        # ── Consume top of action queue ───────────────────────────────────────
        if e.status == "idle" and e.action_queue:
            action = e.pop_action()
            self._execute_action(e, action)
            return

        # ── LLM decision trigger ──────────────────────────────────────────────
        if e.needs_decision(gt) or arrived:
            inj = e.pending_scheduler_message
            e.pending_scheduler_message = None
            llm_module.call_npc_llm_async(
                entity=e, world=self.world, injected_message=inj,
                callback=self._on_npc_response,
            )
            e.last_decision_time = gt

    # ─────────────────────────────────────────────────────────────────────────
    #  Movement step
    # ─────────────────────────────────────────────────────────────────────────
    def _step_towards(self, e: Entity, real_dt: float) -> bool:
        """Move entity one step toward destination. Returns True if arrived."""
        dest = e.destination
        dx = dest["x"] - e.position["x"]
        dy = dest["y"] - e.position["y"]
        dist = math.sqrt(dx*dx + dy*dy)

        if dist < 0.15:
            e.position["x"] = dest["x"]
            e.position["y"] = dest["y"]
            return True

        step = e.speed * real_dt
        move_x = (dx / dist) * step
        move_y = (dy / dist) * step

        new_x = e.position["x"] + move_x
        new_y = e.position["y"] + move_y

        # Obstacle avoidance
        if not self.world.is_blocked(new_x, new_y):
            e.position["x"] = new_x
            e.position["y"] = new_y
        elif not self.world.is_blocked(new_x, e.position["y"]):
            e.position["x"] = new_x
        elif not self.world.is_blocked(e.position["x"], new_y):
            e.position["y"] = new_y
        else:
            # Stuck — pick a random walkable destination nearby and retry
            result = self.world.find_walkable_near(e.position["x"], e.position["y"])
            if result:
                e.destination = {"x": result[0], "y": result[1]}
            else:
                e.destination = None
                return True  # give up

        # Facing direction
        if abs(move_x) > abs(move_y):
            e.facing = "right" if move_x > 0 else "left"
        else:
            e.facing = "down" if move_y > 0 else "up"

        return False

    # ─────────────────────────────────────────────────────────────────────────
    #  Action executor
    # ─────────────────────────────────────────────────────────────────────────
    def _execute_action(self, e: Entity, action: dict):
        gt = self.world.game_time
        atype = action.get("type")

        if atype == config.ACTION_MOVE:
            dest = action.get("to", {})
            tx = max(0.0, min(float(dest.get("x", e.position["x"])), config.MAP_WIDTH - 1))
            ty = max(0.0, min(float(dest.get("y", e.position["y"])), config.MAP_HEIGHT - 1))
            if not self.world.is_blocked(tx, ty):
                e.destination = {"x": tx, "y": ty}
                e.status = "moving"
            else:
                result = self.world.find_walkable_near(tx, ty)
                if result:
                    e.destination = {"x": result[0], "y": result[1]}
                    e.status = "moving"

        elif atype == config.ACTION_SAY:
            text = action.get("text", "")
            target_id = action.get("target")
            e.say(text, time.time())
            self.world.log_event(f'{e.name} says: "{text}"', e.position, e.id)
            if target_id and target_id in self.world.entities:
                target = self.world.entities[target_id]
                target.add_memory(gt, f'{e.name} said to me: "{text}"')

        elif atype == config.ACTION_ATTACK:
            target_id = action.get("target")
            if target_id and target_id in self.world.entities:
                target = self.world.entities[target_id]
                if target.is_alive():
                    self._perform_attack(e, target)

        elif atype == config.ACTION_PICK_UP:
            item_id = action.get("item_id")
            item = self.world.items.get(item_id)
            if item and item.position and item.owner_id is None:
                dist = self.world._dist(e.position, item.position)
                if dist <= 2.0:
                    item.position = None
                    item.owner_id = e.id
                    e.inventory.append(item_id)
                    e.add_memory(gt, f"Picked up {item.name}")
                    self.world.log_event(f"{e.name} picked up {item.name}", e.position, e.id)
                else:
                    # Move toward item first
                    e.enqueue_action({"type": config.ACTION_MOVE, "to": item.position, "priority": 1})
                    e.enqueue_action(action)

        elif atype == config.ACTION_DROP:
            item_id = action.get("item_id")
            if item_id in e.inventory:
                e.inventory.remove(item_id)
                item = self.world.items.get(item_id)
                if item:
                    item.position = dict(e.position)
                    item.owner_id = None
                    self.world.log_event(f"{e.name} dropped {item.name}", e.position, e.id)

        elif atype == config.ACTION_USE:
            item_id = action.get("item_id")
            if item_id in e.inventory:
                item = self.world.items.get(item_id)
                if item:
                    self._use_item(e, item)

        elif atype == config.ACTION_GIVE:
            item_id = action.get("item_id")
            target_id = action.get("target")
            if item_id in e.inventory and target_id in self.world.entities:
                target = self.world.entities[target_id]
                dist = self.world._dist(e.position, target.position)
                if dist <= 2.0:
                    e.inventory.remove(item_id)
                    target.inventory.append(item_id)
                    item = self.world.items.get(item_id)
                    item_name = item.name if item else "item"
                    item.owner_id = target_id
                    e.add_memory(gt, f"Gave {item_name} to {target.name}")
                    target.add_memory(gt, f"Received {item_name} from {e.name}")
                    e.relationships[target_id] = e.relationships.get(target_id, 0) + 0.05
                    self.world.log_event(f"{e.name} gave {item_name} to {target.name}", e.position, e.id)
                else:
                    e.enqueue_action({"type": config.ACTION_MOVE, "to": target.position, "priority": 1})
                    e.enqueue_action(action)

        elif atype == config.ACTION_WAIT:
            dur = float(action.get("duration", 5))
            e.stun_until = gt + dur   # reuse stun timer as wait timer

        elif atype == config.ACTION_SLEEP:
            e.status = "sleeping"
            e.sleep_until = gt + config.SLEEP_DURATION
            e.add_memory(gt, "Went to sleep.")
            self.world.log_event(f"{e.name} went to sleep", e.position, e.id)

    # ─────────────────────────────────────────────────────────────────────────
    #  Combat
    # ─────────────────────────────────────────────────────────────────────────
    def _perform_attack(self, attacker: Entity, target: Entity):
        gt = self.world.game_time
        wt = attacker.weapon_type
        reach = config.WEAPON_RANGE.get(wt, 1.5)
        dist  = self.world._dist(attacker.position, target.position)

        if dist > reach:
            # Move closer first
            attacker.enqueue_action({"type": config.ACTION_MOVE, "to": dict(target.position), "priority": 1})
            attacker.enqueue_action({"type": config.ACTION_ATTACK, "target": target.id, "priority": 1})
            return

        # Check weapon damage bonus from inventory
        bonus = 0
        for iid in attacker.inventory:
            it = self.world.items.get(iid)
            if it and it.item_type == "weapon":
                bonus = it.properties.get("damage", 0)
                break

        base_min, base_max = config.WEAPON_DAMAGE.get(wt, (8, 16))
        damage = random.uniform(base_min + bonus * 0.3, base_max + bonus * 0.5)

        if wt == "shooting":
            # Spawn bullet
            dx = target.position["x"] - attacker.position["x"]
            dy = target.position["y"] - attacker.position["y"]
            d  = math.sqrt(dx*dx + dy*dy)
            if d > 0:
                import uuid as _uuid
                bullet = Bullet(
                    id=f"blt_{_uuid.uuid4().hex[:6]}",
                    owner_id=attacker.id,
                    position=dict(attacker.position),
                    velocity={"x": (dx/d)*15, "y": (dy/d)*15},
                    damage=damage,
                    max_range=config.WEAPON_RANGE["shooting"],
                )
                self.world.bullets[bullet.id] = bullet
        else:
            self._apply_damage(target, damage, attacker.id)

        attacker.add_memory(gt, f"Attacked {target.name} ({wt})")
        self.world.log_event(f"{attacker.name} attacks {target.name} ({wt}, {damage:.1f} dmg)",
                             attacker.position, attacker.id)

        # Target reaction
        if target.is_alive():
            target.pending_scheduler_message = (
                f"You are being attacked by {attacker.name}! Defend yourself or flee!")
            target.relationships[attacker.id] = max(-1.0,
                target.relationships.get(attacker.id, 0) - 0.3)

    def _apply_damage(self, target: Entity, damage: float, source_id: str):
        gt = self.world.game_time
        target.health -= damage
        target.last_damage_time = gt
        if random.random() < 0.25:
            target.bleeding = True
        if target.health <= 0:
            self.world.kill_entity(target.id, source_id)
        else:
            target.stun_until = gt + 0.5   # brief stun

    # ─────────────────────────────────────────────────────────────────────────
    #  Item use
    # ─────────────────────────────────────────────────────────────────────────
    def _use_item(self, e: Entity, item: Item):
        gt = self.world.game_time
        props = item.properties

        if item.item_type == "food":
            was_starving = e.hunger >= config.HUNGER_DAMAGE_THRESHOLD
            restore      = props.get("restore_hunger", 0.3)
            e.hunger     = max(0.0, e.hunger - restore)
            # Eating while starving also recovers a small amount of health
            if was_starving:
                hp_gain = restore * 15          # e.g. bread (0.40) → +6 HP
                e.health = min(e.max_health, e.health + hp_gain)
            e.inventory.remove(item.id)
            self.world.remove_item(item.id)
            e.add_memory(gt, f"Ate {item.name}, felt better.")
            self.world.log_event(f"{e.name} ate {item.name}", e.position, e.id)

        elif item.item_type == "potion":
            e.health = min(e.max_health, e.health + props.get("restore_health", 30))
            e.inventory.remove(item.id)
            self.world.remove_item(item.id)
            e.add_memory(gt, f"Used {item.name}, health restored.")

        elif item.item_type == "bed":
            e.status = "sleeping"
            e.sleep_until = gt + config.SLEEP_DURATION
            e.add_memory(gt, f"Used {item.name} to sleep.")

        elif item.item_type == "weapon":
            e.weapon_type = props.get("weapon_type", e.weapon_type)
            e.add_memory(gt, f"Equipped {item.name}.")

        else:
            # Unknown item — ask scheduler what it does
            e.pending_scheduler_message = (
                f"You are about to use a '{item.name}' (type: {item.item_type}). "
                f"Decide what effect it has on you and act accordingly.")

    # -------------------------------------------------------------------------
    #  Auto-use helpers  (physics-driven, no LLM call needed)
    # -------------------------------------------------------------------------
    def _try_auto_eat(self, e: Entity, gt: float):
        """Eat the most restorative food item in inventory, if any."""
        best_item = None
        best_restore = 0.0
        for iid in e.inventory:
            item = self.world.items.get(iid)
            if item and item.item_type == "food":
                restore = item.properties.get("restore_hunger", 0.3)
                if restore > best_restore:
                    best_item, best_restore = item, restore
        if best_item:
            self._use_item(e, best_item)

    def _try_auto_potion(self, e: Entity, gt: float):
        """Use a health potion if one is in inventory."""
        for iid in list(e.inventory):
            item = self.world.items.get(iid)
            if item and item.item_type == "potion":
                self._use_item(e, item)
                return  # one potion per check is enough

    # ─────────────────────────────────────────────────────────────────────────
    #  Bullet update
    # ─────────────────────────────────────────────────────────────────────────
    def _update_bullets(self, real_dt: float):
        for blt in list(self.world.bullets.values()):
            if not blt.active:
                del self.world.bullets[blt.id]
                continue

            blt.position["x"] += blt.velocity["x"] * real_dt
            blt.position["y"] += blt.velocity["y"] * real_dt
            step = math.sqrt(blt.velocity["x"]**2 + blt.velocity["y"]**2) * real_dt
            blt.distance_travelled += step

            # Wall collision
            if self.world.is_blocked(blt.position["x"], blt.position["y"]):
                blt.active = False
                continue

            # Entity collision
            for e in self.world.entities.values():
                if e.id == blt.owner_id or not e.is_alive(): continue
                if (abs(e.position["x"] - blt.position["x"]) < 0.5 and
                        abs(e.position["y"] - blt.position["y"]) < 0.5):
                    self._apply_damage(e, blt.damage, blt.owner_id)
                    blt.active = False
                    break

            if blt.distance_travelled >= blt.max_range:
                blt.active = False

        # Clean up
        self.world.bullets = {k: v for k, v in self.world.bullets.items() if v.active}

    # ─────────────────────────────────────────────────────────────────────────
    #  LLM response callback  (called from worker thread → needs lock)
    # ─────────────────────────────────────────────────────────────────────────
    def _on_npc_response(self, entity_id: str, result: Optional[dict]):
        with self._lock:
            e = self.world.entities.get(entity_id)
            if not e:
                return
            e.pending_llm_call = False

            if result is None:
                # Fallback: wander
                import random as _r
                e.enqueue_action({"type": config.ACTION_MOVE, "to": {
                    "x": float(_r.randint(2, config.MAP_WIDTH-2)),
                    "y": float(_r.randint(2, config.MAP_HEIGHT-2)),
                }, "priority": 5})
                return

            gt = self.world.game_time

            # Apply mood
            if result.get("mood"):
                e.mood = result["mood"]

            # Apply goal updates
            if result.get("long_term_goals"):
                e.long_term_goals = result["long_term_goals"][:5]
            if result.get("short_term_goals"):
                e.short_term_goals = result["short_term_goals"][:5]

            # Memory updates
            for mem_text in result.get("memory_updates", []):
                e.add_memory(gt, str(mem_text)[:200])

            # Relationship changes
            for npc_id, delta in result.get("relationship_changes", {}).items():
                current = e.relationships.get(npc_id, 0.0)
                e.relationships[npc_id] = max(-1.0, min(1.0, current + float(delta)))

            # Queue actions
            for action in result.get("actions", []):
                e.enqueue_action(action)

    # ─────────────────────────────────────────────────────────────────────────
    #  Global developer command
    # ─────────────────────────────────────────────────────────────────────────
    def _dispatch_global_command(self, command: str):
        """Ask the scheduler LLM to translate the command into NPC messages."""
        self.world.log_event(f"[COMMAND] {command}")
        llm_module.call_scheduler_llm_async(
            command=command, world=self.world,
            callback=self._on_scheduler_response,
        )

    def _on_scheduler_response(self, result: Optional[dict]):
        if result is None:
            return
        with self._lock:
            # Inject per-NPC messages
            for msg_info in result.get("messages", []):
                npc_id  = msg_info.get("npc_id")
                message = msg_info.get("message", "")
                e = self.world.entities.get(npc_id)
                if e and e.is_alive():
                    e.pending_scheduler_message = message
                    # Interrupt any current LLM call is handled naturally by pending flag

            # Apply direct world effects
            for effect in result.get("world_effects", []):
                self._apply_world_effect(effect)

            reasoning = result.get("reasoning", "")
            if reasoning:
                self.world.log_event(f"[SCHEDULER] {reasoning}")

    def _apply_world_effect(self, effect: dict):
        etype = effect.get("type")
        w = self.world
        npc_id = effect.get("npc_id")

        if etype == "set_status" and npc_id in w.entities:
            w.entities[npc_id].status = effect.get("status", "idle")
        elif etype == "set_health" and npc_id in w.entities:
            w.entities[npc_id].health = float(effect.get("health", 100))
        elif etype == "set_mood" and npc_id in w.entities:
            mood = effect.get("mood", "calm")
            if mood in config.MOODS:
                w.entities[npc_id].mood = mood
        elif etype == "teleport" and npc_id in w.entities:
            w.entities[npc_id].position = {"x": float(effect.get("x", 10)), "y": float(effect.get("y", 10))}
            w.entities[npc_id].destination = None
            w.entities[npc_id].status = "idle"
        elif etype == "spawn_item":
            from entity import Item
            item = Item.create(effect.get("name", "apple"),
                               float(effect.get("x", 10)), float(effect.get("y", 10)))
            w.add_item(item)
        elif etype == "log_event":
            w.log_event(effect.get("text", ""), None)

    # ─────────────────────────────────────────────────────────────────────────
    #  Developer interrupt (immediate event for a specific NPC)
    # ─────────────────────────────────────────────────────────────────────────
    def interrupt_entity(self, entity_id: str, message: str):
        with self._lock:
            e = self.world.entities.get(entity_id)
            if e and e.is_alive() and not e.pending_llm_call:
                e.pending_scheduler_message = message
                e.action_queue.clear()
                e.destination = None
                e.status = "idle"
