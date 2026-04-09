# entity.py — NPC and Item data models

import uuid
import random
from dataclasses import dataclass, field
from typing import Optional
import config


# ─────────────────────────────────────────────────────────────────────────────
#  Item
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Item:
    id: str
    name: str
    item_type: str            # food | weapon | potion | bed | misc | currency
    position: Optional[dict]  # {"x":float,"y":float} — None when in inventory
    owner_id: Optional[str]   # None when on ground
    properties: dict = field(default_factory=dict)
    color: tuple = (160, 160, 160)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "item_type": self.item_type,
            "position": self.position, "owner_id": self.owner_id,
            "properties": self.properties, "color": list(self.color),
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d["id"], name=d["name"], item_type=d["item_type"],
            position=d.get("position"), owner_id=d.get("owner_id"),
            properties=d.get("properties", {}),
            color=tuple(d.get("color", [160, 160, 160])),
        )

    @staticmethod
    def create(name: str, x: float = 0, y: float = 0, owner_id: str = None) -> "Item":
        tmpl = config.ITEM_TEMPLATES.get(name, {"item_type": "misc", "properties": {}, "color": (160, 160, 160)})
        return Item(
            id=f"item_{uuid.uuid4().hex[:8]}",
            name=name,
            item_type=tmpl["item_type"],
            position={"x": x, "y": y} if owner_id is None else None,
            owner_id=owner_id,
            properties=dict(tmpl["properties"]),
            color=tuple(tmpl.get("color", (160, 160, 160))),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Bullet  (spawned by shooting NPCs)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Bullet:
    id: str
    owner_id: str
    position: dict    # {"x","y"}
    velocity: dict    # {"x","y"} — tiles/second
    damage: float
    max_range: float
    distance_travelled: float = 0.0
    active: bool = True

    def to_dict(self):
        return {k: getattr(self, k) for k in
                ["id","owner_id","position","velocity","damage","max_range","distance_travelled","active"]}

    @classmethod
    def from_dict(cls, d): return cls(**d)


# ─────────────────────────────────────────────────────────────────────────────
#  Entity  (NPC)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Entity:
    id: str
    name: str
    sprite_type: str
    position: dict          # {"x": float, "y": float}

    # Stats
    health: float = 100.0
    max_health: float = 100.0
    destination: Optional[dict] = None
    speed: float = 1.5
    hunger: float = 0.2     # 0=full → 1=starving
    energy: float = 0.9     # 0=exhausted → 1=rested

    # Inventory / combat
    inventory: list = field(default_factory=list)   # item IDs
    weapon_type: str = "hitting"

    # Goals / memory
    short_term_goals: list = field(default_factory=list)
    long_term_goals: list = field(default_factory=list)
    memories: list = field(default_factory=list)           # {"time":int,"text":str}
    short_term_memories: list = field(default_factory=list)
    relationships: dict = field(default_factory=dict)      # {npc_id: float -1..1}

    # AI state
    mood: str = "calm"
    perceptions: list = field(default_factory=list)        # {"id","pos","seen_at"}
    last_decision_time: float = 0.0
    status: str = "idle"    # idle | moving | acting | sleeping | dead
    action_queue: list = field(default_factory=list)
    pending_llm_call: bool = False

    # Timers
    sleep_until: Optional[float] = None
    stun_until: Optional[float] = None
    bleeding: bool = False
    last_damage_time: float = 0.0

    # Rendering
    facing: str = "down"
    anim_frame: int = 0
    anim_timer: float = 0.0

    # Speech bubble
    speech_text: Optional[str] = None
    speech_until: Optional[float] = None   # real-time timestamp

    # Pending command injected by scheduler
    pending_scheduler_message: Optional[str] = None

    # ── Helpers ───────────────────────────────────────────────────────────────
    def is_alive(self) -> bool:
        return self.status != "dead" and self.health > 0

    def add_memory(self, game_time: float, text: str):
        entry = {"time": int(game_time), "text": text}
        self.memories.append(entry)
        self.short_term_memories.append(entry)
        if len(self.short_term_memories) > config.SHORT_TERM_MEM_LIMIT:
            self.short_term_memories.pop(0)

    def say(self, text: str, real_time: float):
        self.speech_text = text[:80]
        self.speech_until = real_time + config.SPEECH_DISPLAY_TIME

    def enqueue_action(self, action: dict):
        if len(self.action_queue) < config.MAX_ACTION_QUEUE:
            self.action_queue.append(action)
            self.action_queue.sort(key=lambda a: a.get("priority", 99))

    def peek_action(self) -> Optional[dict]:
        return self.action_queue[0] if self.action_queue else None

    def pop_action(self) -> Optional[dict]:
        return self.action_queue.pop(0) if self.action_queue else None

    def needs_decision(self, game_time: float) -> bool:
        if not self.is_alive(): return False
        if self.pending_llm_call: return False
        if self.status == "sleeping": return False
        if self.stun_until and game_time < self.stun_until: return False
        # Moving NPCs only re-decide on arrival or periodic check
        if self.status == "moving":
            return (game_time - self.last_decision_time) >= config.PERIODIC_CHECK_INTERVAL
        return len(self.action_queue) == 0

    # ── Serialisation ─────────────────────────────────────────────────────────
    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "sprite_type": self.sprite_type,
            "position": self.position, "health": self.health, "max_health": self.max_health,
            "destination": self.destination, "speed": self.speed,
            "hunger": self.hunger, "energy": self.energy,
            "inventory": self.inventory, "weapon_type": self.weapon_type,
            "short_term_goals": self.short_term_goals,
            "long_term_goals": self.long_term_goals,
            "memories": self.memories[-300:],
            "relationships": self.relationships, "mood": self.mood,
            "perceptions": self.perceptions,
            "last_decision_time": self.last_decision_time,
            "status": self.status if self.status != "moving" else "idle",
            "sleep_until": self.sleep_until, "bleeding": self.bleeding,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Entity":
        e = cls(id=d["id"], name=d["name"], sprite_type=d["sprite_type"],
                position=d["position"])
        fields = ["health","max_health","destination","speed","hunger","energy",
                  "inventory","weapon_type","short_term_goals","long_term_goals",
                  "memories","relationships","mood","perceptions",
                  "last_decision_time","status","sleep_until","bleeding"]
        for f in fields:
            if f in d: setattr(e, f, d[f])
        e.short_term_memories = e.memories[-config.SHORT_TERM_MEM_LIMIT:] if e.memories else []
        return e

    @staticmethod
    def create_random(map_w: int, map_h: int, avoid_positions=None) -> "Entity":
        npc_id = f"npc_{uuid.uuid4().hex[:6]}"
        name = random.choice(config.FIRST_NAMES) + " " + random.choice(config.LAST_NAMES)
        sprite_type = random.choice(config.SPRITE_TYPES)

        # Try to place on walkable area
        for _ in range(50):
            x = float(random.randint(4, map_w - 4))
            y = float(random.randint(4, map_h - 4))
            if avoid_positions:
                if any(abs(x-ax) < 2 and abs(y-ay) < 2 for ax, ay in avoid_positions):
                    continue
            break

        goal_map = {
            "warrior":  (["find a worthy opponent"],   ["become the greatest fighter"]),
            "mage":     (["find spell components"],    ["master all schools of magic"]),
            "rogue":    (["find something valuable"],  ["amass wealth in secret"]),
            "peasant":  (["find food"],                ["live comfortably and safely"]),
            "merchant": (["find goods to trade"],      ["become the wealthiest merchant"]),
            "guard":    (["patrol the area"],          ["maintain peace and order"]),
            "healer":   (["help anyone injured"],      ["find a cure for all diseases"]),
            "bard":     (["find a good story"],        ["become a living legend"]),
        }
        st, lt = goal_map.get(sprite_type, (["explore the area"], ["survive and thrive"]))

        return Entity(
            id=npc_id, name=name, sprite_type=sprite_type,
            position={"x": x, "y": y},
            health=random.uniform(80, 100),
            speed=random.uniform(1.0, 2.2),
            hunger=random.uniform(0.05, 0.45),
            energy=random.uniform(0.55, 1.0),
            weapon_type=random.choice(config.WEAPON_TYPES),
            short_term_goals=list(st),
            long_term_goals=list(lt),
            mood=random.choice(["calm", "curious", "happy"]),
        )
