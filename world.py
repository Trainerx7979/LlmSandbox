# world.py — map, entity registry, items, procedural generation

import random
import math
import uuid
import time
from typing import Optional, Dict, List, Tuple
import config
from entity import Entity, Item, Bullet


# ─────────────────────────────────────────────────────────────────────────────
#  Simple noise helper (no external dep)
# ─────────────────────────────────────────────────────────────────────────────
def _smooth_noise(w: int, h: int, seed: int = 42) -> list:
    rng = random.Random(seed)
    base = [[rng.random() for _ in range(w)] for _ in range(h)]
    out  = [[0.0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            total = 0.0
            cnt   = 0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ny, nx = (y+dy) % h, (x+dx) % w
                    total += base[ny][nx]
                    cnt   += 1
            out[y][x] = total / cnt
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  World
# ─────────────────────────────────────────────────────────────────────────────
class World:
    def __init__(self, width: int = config.MAP_WIDTH, height: int = config.MAP_HEIGHT, seed: int = None):
        self.width  = width
        self.height = height
        self.seed   = seed or random.randint(0, 99999)

        # Time (game-minutes since epoch)
        self.game_time: float = 0.0
        self.paused: bool = False

        # Tile map: 2D list of tile IDs
        self.tiles: List[List[int]] = []

        # Registries
        self.entities: Dict[str, Entity] = {}   # id → Entity
        self.items:    Dict[str, Item]   = {}   # id → Item
        self.bullets:  Dict[str, Bullet] = {}   # id → Bullet
        self.corpses:  List[dict] = []           # {"name","pos","killed_by","time"}

        # Events log (used by scheduler / debug overlay)
        self.events: List[dict] = []            # {"time","text","pos"}
        self._event_limit = 200

        # Global command queue (developer console → scheduler)
        self.pending_commands: List[str] = []

    # ── Map generation ────────────────────────────────────────────────────────
    def generate(self):
        w, h = self.width, self.height
        noise = _smooth_noise(w, h, self.seed)
        self.tiles = [[config.TILE_GRASS]*w for _ in range(h)]

        # Water (low noise areas)
        for y in range(h):
            for x in range(w):
                v = noise[y][x]
                if v < 0.38:
                    self.tiles[y][x] = config.TILE_WATER
                elif v < 0.44:
                    self.tiles[y][x] = config.TILE_SAND
                elif v > 0.72:
                    self.tiles[y][x] = config.TILE_TREE

        # Stamp a few building footprints
        rng = random.Random(self.seed + 1)
        for _ in range(6):
            bx = rng.randint(8, w - 16)
            by = rng.randint(8, h - 16)
            bw = rng.randint(4, 9)
            bh = rng.randint(4, 9)
            self._stamp_building(bx, by, bw, bh)

        # Paths between buildings (simple horizontal/vertical runs)
        for _ in range(12):
            x1 = rng.randint(2, w-2)
            y1 = rng.randint(2, h-2)
            x2 = rng.randint(2, w-2)
            y2 = rng.randint(2, h-2)
            self._stamp_path(x1, y1, x2, y2)

        # Border walls (map edge)
        for x in range(w):
            self.tiles[0][x] = config.TILE_WALL
            self.tiles[h-1][x] = config.TILE_WALL
        for y in range(h):
            self.tiles[y][0] = config.TILE_WALL
            self.tiles[y][w-1] = config.TILE_WALL

    def _stamp_building(self, bx, by, bw, bh):
        for dy in range(bh):
            for dx in range(bw):
                x, y = bx+dx, by+dy
                if 0 < x < self.width-1 and 0 < y < self.height-1:
                    if dx == 0 or dx == bw-1 or dy == 0 or dy == bh-1:
                        self.tiles[y][x] = config.TILE_WALL
                    else:
                        self.tiles[y][x] = config.TILE_FLOOR
        # Door
        doorx = bx + bw // 2
        doory = by + bh - 1
        if 0 < doorx < self.width-1 and 0 < doory < self.height-1:
            self.tiles[doory][doorx] = config.TILE_FLOOR

    def _stamp_path(self, x1, y1, x2, y2):
        # L-shaped path
        x, y = x1, y1
        while x != x2:
            if 0 < x < self.width-1 and 0 < y < self.height-1:
                if self.tiles[y][x] not in (config.TILE_WALL, config.TILE_FLOOR):
                    self.tiles[y][x] = config.TILE_PATH
            x += 1 if x2 > x else -1
        while y != y2:
            if 0 < x < self.width-1 and 0 < y < self.height-1:
                if self.tiles[y][x] not in (config.TILE_WALL, config.TILE_FLOOR):
                    self.tiles[y][x] = config.TILE_PATH
            y += 1 if y2 > y else -1

    # ── Tile queries ──────────────────────────────────────────────────────────
    def tile_at(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return config.TILE_WALL

    def is_blocked(self, x: float, y: float) -> bool:
        ix, iy = int(x), int(y)
        return self.tile_at(ix, iy) in config.BLOCKING_TILES

    def is_entity_blocked(self, x: float, y: float, exclude_id: str = None) -> bool:
        if self.is_blocked(x, y): return True
        for eid, e in self.entities.items():
            if eid == exclude_id: continue
            if not e.is_alive(): continue
            if abs(e.position["x"]-x) < 0.6 and abs(e.position["y"]-y) < 0.6:
                return True
        return False

    def find_walkable_near(self, x: float, y: float, radius: int = 3) -> Optional[Tuple[float,float]]:
        for r in range(1, radius+1):
            for dy in range(-r, r+1):
                for dx in range(-r, r+1):
                    nx, ny = round(x)+dx, round(y)+dy
                    if not self.is_blocked(nx, ny):
                        return float(nx), float(ny)
        return None

    # ── Entity management ─────────────────────────────────────────────────────
    def add_entity(self, e: Entity):
        # Make sure it's on a walkable tile
        if self.is_blocked(e.position["x"], e.position["y"]):
            result = self.find_walkable_near(e.position["x"], e.position["y"])
            if result:
                e.position["x"], e.position["y"] = result
        self.entities[e.id] = e

    def remove_entity(self, eid: str):
        e = self.entities.pop(eid, None)
        if e:
            # Drop inventory
            for item_id in e.inventory:
                item = self.items.get(item_id)
                if item:
                    item.position = dict(e.position)
                    item.owner_id = None

    def kill_entity(self, eid: str, killer_id: str = None):
        e = self.entities.get(eid)
        if not e: return
        e.status = "dead"
        e.health = 0
        killer_name = self.entities[killer_id].name if killer_id and killer_id in self.entities else "unknown"
        self.corpses.append({
            "name": e.name + " (Dead Body)", "pos": dict(e.position),
            "killed_by": killer_name, "killed_by_id": killer_id,
            "time": self.game_time,
        })
        self.log_event(f"{e.name} has died (killed by {killer_name})", e.position)
        # Nearby NPCs witness the death
        for other in self.entities.values():
            if other.id == eid or other.id == killer_id: continue
            if not other.is_alive(): continue
            dist = self._dist(other.position, e.position)
            if dist <= config.PERCEPTION_RADIUS:
                other.add_memory(self.game_time,
                    f"Witnessed {e.name} killed by {killer_name} at ({int(e.position['x'])},{int(e.position['y'])})")
                other.pending_scheduler_message = (
                    f"You just witnessed {e.name} being killed by {killer_name} nearby! React appropriately.")
        # Drop loot
        for item_id in e.inventory:
            item = self.items.get(item_id)
            if item:
                item.position = dict(e.position)
                item.owner_id = None
        e.inventory.clear()

    # ── Item management ───────────────────────────────────────────────────────
    def add_item(self, item: Item):
        self.items[item.id] = item

    def remove_item(self, item_id: str):
        self.items.pop(item_id, None)

    def items_at(self, x: float, y: float, radius: float = 0.8) -> List[Item]:
        return [it for it in self.items.values()
                if it.position and it.owner_id is None
                and abs(it.position["x"]-x) <= radius
                and abs(it.position["y"]-y) <= radius]

    def nearest_item(self, x: float, y: float, item_type: str = None) -> Optional[Item]:
        candidates = [it for it in self.items.values()
                      if it.position and it.owner_id is None
                      and (item_type is None or it.item_type == item_type)]
        if not candidates: return None
        return min(candidates, key=lambda it: self._dist(it.position, {"x":x,"y":y}))

    # ── Perception ────────────────────────────────────────────────────────────
    def get_perceptions(self, e: Entity) -> List[dict]:
        """Return visible entities and items within PERCEPTION_RADIUS."""
        perceptions = []
        ex, ey = e.position["x"], e.position["y"]
        for other in self.entities.values():
            if other.id == e.id: continue
            d = self._dist(other.position, e.position)
            if d <= config.PERCEPTION_RADIUS:
                perceptions.append({
                    "id": other.id, "name": other.name, "type": "npc",
                    "pos": dict(other.position), "status": other.status,
                    "health": round(other.health, 1), "mood": other.mood,
                    "seen_at": self.game_time,
                })
        for item in self.items.values():
            if item.position and item.owner_id is None:
                d = self._dist(item.position, e.position)
                if d <= config.PERCEPTION_RADIUS:
                    perceptions.append({
                        "id": item.id, "name": item.name, "type": "item",
                        "item_type": item.item_type,
                        "pos": dict(item.position), "seen_at": self.game_time,
                    })
        for corpse in self.corpses:
            d = self._dist(corpse["pos"], e.position)
            if d <= config.PERCEPTION_RADIUS:
                perceptions.append({
                    "id": f"corpse_{corpse['name']}", "name": f"corpse of {corpse['name']}",
                    "type": "corpse", "killed_by": corpse["killed_by"],
                    "pos": dict(corpse["pos"]), "seen_at": self.game_time,
                })
        return perceptions

    # ── Event log ─────────────────────────────────────────────────────────────
    def log_event(self, text: str, pos: dict = None, entity_id: str = None):
        self.events.append({
            "time": self.game_time, "text": text,
            "pos": dict(pos) if pos else None,
            "entity_id": entity_id,
        })
        if len(self.events) > self._event_limit:
            self.events.pop(0)

    def recent_events(self, seconds: float = 30) -> List[dict]:
        cutoff = self.game_time - seconds
        return [ev for ev in self.events if ev["time"] >= cutoff]

    # ── Spawn helpers ─────────────────────────────────────────────────────────
    def spawn_npc(self) -> Entity:
        positions = [(e.position["x"], e.position["y"]) for e in self.entities.values()]
        e = Entity.create_random(self.width, self.height, positions)
        # Ensure walkable
        for _ in range(30):
            if not self.is_blocked(e.position["x"], e.position["y"]): break
            e.position["x"] = float(random.randint(4, self.width-4))
            e.position["y"] = float(random.randint(4, self.height-4))
        self.add_entity(e)
        self.log_event(f"{e.name} ({e.sprite_type}) appeared", e.position)
        return e

    def spawn_item_at(self, name: str, x: float, y: float) -> Item:
        it = Item.create(name, x, y)
        self.add_item(it)
        return it

    # ── Utility ───────────────────────────────────────────────────────────────
    @staticmethod
    def _dist(a: dict, b: dict) -> float:
        return math.sqrt((a["x"]-b["x"])**2 + (a["y"]-b["y"])**2)

    def entities_near(self, x: float, y: float, radius: float) -> List[Entity]:
        return [e for e in self.entities.values()
                if e.is_alive() and self._dist(e.position, {"x":x,"y":y}) <= radius]

    def time_of_day(self) -> str:
        hour = (self.game_time / 60) % 24
        if   hour < 6:  return "night"
        elif hour < 12: return "morning"
        elif hour < 18: return "afternoon"
        else:           return "evening"

    def clock_str(self) -> str:
        total_mins = int(self.game_time)
        days  = total_mins // (24*60)
        hour  = (total_mins // 60) % 24
        mins  = total_mins % 60
        return f"Day {days+1}  {hour:02d}:{mins:02d}  ({self.time_of_day()})"

    # ── Serialisation ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "width": self.width, "height": self.height, "seed": self.seed,
            "game_time": self.game_time,
            "tiles": self.tiles,
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "items":    {iid: it.to_dict() for iid, it in self.items.items()},
            "corpses":  self.corpses,
            "events":   self.events[-50:],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "World":
        w = cls(d["width"], d["height"], d["seed"])
        w.tiles     = d["tiles"]
        w.game_time = d.get("game_time", 0.0)
        w.corpses   = d.get("corpses", [])
        w.events    = d.get("events", [])
        for eid, ed in d.get("entities", {}).items():
            w.entities[eid] = Entity.from_dict(ed)
        for iid, id_ in d.get("items", {}).items():
            w.items[iid] = Item.from_dict(id_)
        return w
