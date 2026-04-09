# renderer.py — pygame rendering: tilemap, sprites, camera, overlays

import math
import pygame
import time
import config
from entity import Entity, Item, Bullet


# ─────────────────────────────────────────────────────────────────────────────
#  Sprite factory  (procedural pixel-art style)
# ─────────────────────────────────────────────────────────────────────────────
class SpriteFactory:
    """Generates and caches pygame.Surface sprites."""

    def __init__(self, tile_size: int = config.TILE_SIZE):
        self.ts = tile_size
        self._cache: dict = {}

    def get_npc(self, sprite_type: str, facing: str = "down", frame: int = 0) -> pygame.Surface:
        key = (sprite_type, facing, frame)
        if key in self._cache:
            return self._cache[key]
        surf = self._draw_npc(sprite_type, facing, frame)
        self._cache[key] = surf
        return surf

    def get_tile(self, tile_id: int) -> pygame.Surface:
        if tile_id in self._cache:
            return self._cache[tile_id]
        surf = self._draw_tile(tile_id)
        self._cache[tile_id] = surf
        return surf

    def get_item(self, item_name: str) -> pygame.Surface:
        key = f"item_{item_name}"
        if key in self._cache:
            return self._cache[key]
        color = config.ITEM_TEMPLATES.get(item_name, {}).get("color", (160,160,160))
        surf  = self._draw_item(item_name, color)
        self._cache[key] = surf
        return surf

    # ── Tile drawing ──────────────────────────────────────────────────────────
    def _draw_tile(self, tile_id: int) -> pygame.Surface:
        ts = self.ts
        surf = pygame.Surface((ts, ts))

        if tile_id == config.TILE_GRASS:
            surf.fill(config.C_GRASS)
            # Subtle variation dots
            for _ in range(4):
                import random
                x, y = random.randint(0, ts-2), random.randint(0, ts-2)
                pygame.draw.rect(surf, config.C_GRASS_ALT, (x, y, 2, 2))

        elif tile_id == config.TILE_WATER:
            surf.fill(config.C_WATER)
            pygame.draw.line(surf, config.C_WATER_DARK, (0, ts//3), (ts, ts//3), 1)
            pygame.draw.line(surf, config.C_WATER_DARK, (0, ts*2//3), (ts, ts*2//3), 1)

        elif tile_id == config.TILE_TREE:
            surf.fill(config.C_GRASS)
            # Trunk
            pygame.draw.rect(surf, (100, 70, 40), (ts//2-2, ts*2//3, 4, ts//3))
            # Canopy
            pygame.draw.circle(surf, config.C_TREE, (ts//2, ts//3), ts//3)
            pygame.draw.circle(surf, config.C_TREE_DARK, (ts//2-3, ts//3-2), ts//5)

        elif tile_id == config.TILE_WALL:
            surf.fill(config.C_WALL)
            pygame.draw.line(surf, (80, 65, 50), (0, ts//2), (ts, ts//2), 1)
            pygame.draw.line(surf, (80, 65, 50), (ts//2, 0), (ts//2, ts), 1)

        elif tile_id == config.TILE_FLOOR:
            surf.fill(config.C_FLOOR)
            pygame.draw.rect(surf, (135, 115, 95), (0, 0, ts, ts), 1)

        elif tile_id == config.TILE_PATH:
            surf.fill(config.C_PATH)
            pygame.draw.line(surf, (160, 140, 110), (0, ts//2), (ts, ts//2), 1)

        elif tile_id == config.TILE_SAND:
            surf.fill(config.C_SAND)
            for _ in range(3):
                import random
                x, y = random.randint(0, ts-2), random.randint(0, ts-2)
                pygame.draw.rect(surf, (180, 165, 115), (x, y, 2, 1))
        else:
            surf.fill(config.C_GRASS)

        return surf

    # ── NPC sprite drawing ────────────────────────────────────────────────────
    def _draw_npc(self, sprite_type: str, facing: str, frame: int) -> pygame.Surface:
        ts = self.ts
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pal  = config.SPRITE_PALETTES.get(sprite_type, config.SPRITE_PALETTES["peasant"])

        skin    = pal["skin"]
        hair    = pal["hair"]
        clothes = pal["clothes"]
        accent  = pal["accent"]

        # Body
        pygame.draw.rect(surf, clothes, (ts//4, ts//3, ts//2, ts//2))
        # Head
        pygame.draw.ellipse(surf, skin, (ts//4+1, ts//8, ts//2-2, ts//3))
        # Hair
        pygame.draw.ellipse(surf, hair, (ts//4, ts//8-1, ts//2, ts//4))

        # Legs (animated)
        leg_y = ts * 5 // 6
        if frame % 2 == 0:
            pygame.draw.line(surf, clothes, (ts//3, ts*2//3), (ts//3-2, leg_y), 3)
            pygame.draw.line(surf, clothes, (ts*2//3, ts*2//3), (ts*2//3+2, leg_y), 3)
        else:
            pygame.draw.line(surf, clothes, (ts//3, ts*2//3), (ts//3+2, leg_y), 3)
            pygame.draw.line(surf, clothes, (ts*2//3, ts*2//3), (ts*2//3-2, leg_y), 3)

        # Accent (belt / trim)
        pygame.draw.line(surf, accent, (ts//4, ts//2+2), (ts*3//4, ts//2+2), 2)

        # Eyes (facing indicator)
        if facing == "down":
            pygame.draw.circle(surf, (30,20,10), (ts//3+1, ts//4+2), 2)
            pygame.draw.circle(surf, (30,20,10), (ts*2//3-1, ts//4+2), 2)
        elif facing == "up":
            pygame.draw.circle(surf, hair, (ts//3+1, ts//5), 2)
            pygame.draw.circle(surf, hair, (ts*2//3-1, ts//5), 2)
        elif facing == "left":
            pygame.draw.circle(surf, (30,20,10), (ts//3, ts//4+2), 2)
        elif facing == "right":
            pygame.draw.circle(surf, (30,20,10), (ts*2//3, ts//4+2), 2)

        return surf

    # ── Item sprite ───────────────────────────────────────────────────────────
    def _draw_item(self, name: str, color: tuple) -> pygame.Surface:
        ts = self.ts
        surf = pygame.Surface((ts//2, ts//2), pygame.SRCALPHA)
        cx, cy = ts//4, ts//4

        if "apple" in name or "meat" in name or "bread" in name:
            pygame.draw.ellipse(surf, color, (2, 4, ts//2-4, ts//2-6))
            pygame.draw.line(surf, (60,100,40), (cx, 2), (cx, 5), 2)
        elif "sword" in name or "axe" in name or "dagger" in name:
            pygame.draw.line(surf, color, (2, cy+4), (cx+6, 2), 3)
            pygame.draw.line(surf, (180,150,50), (cx-4, cy+2), (cx+4, cy-2), 2)
        elif "bow" in name:
            pygame.draw.arc(surf, color, (2, 2, ts//2-4, ts//2-4), 0.5, 2.6, 2)
            pygame.draw.line(surf, (180,140,80), (ts//4, 3), (ts//4, ts//2-3), 1)
        elif "potion" in name:
            pygame.draw.ellipse(surf, color, (cx-4, cy-2, 9, 9))
            pygame.draw.rect(surf, (180,180,220), (cx-2, cy-6, 5, 5))
        elif "gold" in name:
            pygame.draw.circle(surf, color, (cx, cy), ts//6)
            pygame.draw.circle(surf, (255,255,100), (cx-1, cy-1), ts//8)
        else:
            pygame.draw.rect(surf, color, (3, 3, ts//2-6, ts//2-6))

        return surf


# ─────────────────────────────────────────────────────────────────────────────
#  Camera
# ─────────────────────────────────────────────────────────────────────────────
class Camera:
    def __init__(self):
        self.x: float = 0.0   # world-pixel offset
        self.y: float = 0.0
        self.zoom: float = 1.0
        self._drag_start = None

    def tile_to_screen(self, tx: float, ty: float) -> tuple:
        sx = (tx * config.TILE_SIZE - self.x) * self.zoom
        sy = (ty * config.TILE_SIZE - self.y) * self.zoom
        return int(sx), int(sy)

    def screen_to_tile(self, sx: float, sy: float) -> tuple:
        wx = sx / self.zoom + self.x
        wy = sy / self.zoom + self.y
        return wx / config.TILE_SIZE, wy / config.TILE_SIZE

    def zoom_at(self, sx: float, sy: float, factor: float):
        tx, ty = self.screen_to_tile(sx, sy)
        self.zoom = max(config.MIN_ZOOM, min(config.MAX_ZOOM, self.zoom * factor))
        # Keep cursor point stationary
        new_sx = tx * config.TILE_SIZE * self.zoom
        new_sy = ty * config.TILE_SIZE * self.zoom
        self.x = (new_sx - sx) / self.zoom
        self.y = (new_sy - sy) / self.zoom

    def pan(self, dx: float, dy: float):
        self.x -= dx / self.zoom
        self.y -= dy / self.zoom

    def clamp(self, map_w: int, map_h: int, view_w: int, view_h: int):
        max_x = max(0.0, map_w * config.TILE_SIZE - view_w / self.zoom)
        max_y = max(0.0, map_h * config.TILE_SIZE - view_h / self.zoom)
        self.x = max(0.0, min(self.x, max_x))
        self.y = max(0.0, min(self.y, max_y))

    def visible_tile_range(self, view_w: int, view_h: int) -> tuple:
        tx0, ty0 = self.screen_to_tile(0, 0)
        tx1, ty1 = self.screen_to_tile(view_w, view_h)
        return (max(0, int(tx0)-1), max(0, int(ty0)-1),
                min(config.MAP_WIDTH,  int(tx1)+2),
                min(config.MAP_HEIGHT, int(ty1)+2))


# ─────────────────────────────────────────────────────────────────────────────
#  Renderer
# ─────────────────────────────────────────────────────────────────────────────
class Renderer:
    def __init__(self, surface: pygame.Surface, camera: Camera):
        self.surf    = surface
        self.camera  = camera
        self.factory = SpriteFactory(config.TILE_SIZE)
        self.font_sm = pygame.font.SysFont("monospace", 11)
        self.font_md = pygame.font.SysFont("monospace", 13)
        self.font_lg = pygame.font.SysFont("monospace", 16, bold=True)
        self._tile_cache: dict = {}   # (tile_id, scaled_ts) → Surface

    def render(self, world, selected_id: str = None, show_debug: bool = False):
        vw = config.GAME_AREA_WIDTH
        vh = config.SCREEN_HEIGHT
        cam = self.camera
        cam.clamp(world.width, world.height, vw, vh)

        scaled_ts = max(1, int(config.TILE_SIZE * cam.zoom))

        x0, y0, x1, y1 = cam.visible_tile_range(vw, vh)

        # ── Tiles ──────────────────────────────────────────────────────────────
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                tile_id = world.tiles[ty][tx]
                sx, sy  = cam.tile_to_screen(tx, ty)
                cache_key = (tile_id, scaled_ts)
                if cache_key not in self._tile_cache:
                    base = self.factory.get_tile(tile_id)
                    self._tile_cache[cache_key] = pygame.transform.scale(base, (scaled_ts, scaled_ts))
                self.surf.blit(self._tile_cache[cache_key], (sx, sy))

        # ── Corpses ────────────────────────────────────────────────────────────
        for corpse in world.corpses:
            sx, sy = cam.tile_to_screen(corpse["pos"]["x"], corpse["pos"]["y"])
            r = max(3, scaled_ts // 4)
            pygame.draw.ellipse(self.surf, config.C_CORPSE, (sx, sy+scaled_ts//2, scaled_ts, r))
            pygame.draw.ellipse(self.surf, config.C_BLOOD,  (sx+2, sy+scaled_ts//2+1, scaled_ts-4, r-2))

        # ── Items ──────────────────────────────────────────────────────────────
        for item in world.items.values():
            if item.position is None: continue
            sx, sy = cam.tile_to_screen(item.position["x"], item.position["y"])
            hs = max(8, scaled_ts // 2)
            base = self.factory.get_item(item.name)
            scaled_item = pygame.transform.scale(base, (hs, hs))
            self.surf.blit(scaled_item, (sx + scaled_ts//4, sy + scaled_ts//4))

        # ── Bullets ───────────────────────────────────────────────────────────
        for blt in world.bullets.values():
            sx, sy = cam.tile_to_screen(blt.position["x"], blt.position["y"])
            pygame.draw.circle(self.surf, config.C_BULLET, (sx + scaled_ts//2, sy + scaled_ts//2),
                               max(2, scaled_ts // 8))

        # ── Entities ──────────────────────────────────────────────────────────
        real_now = time.time()
        for entity in world.entities.values():
            if not entity.is_alive(): continue
            sx, sy = cam.tile_to_screen(entity.position["x"], entity.position["y"])

            # Sprite
            sprite = self.factory.get_npc(entity.sprite_type, entity.facing, entity.anim_frame)
            scaled_sprite = pygame.transform.scale(sprite, (scaled_ts, scaled_ts))
            self.surf.blit(scaled_sprite, (sx, sy))

            # Selection ring
            if entity.id == selected_id:
                pygame.draw.ellipse(self.surf, config.C_SELECTION,
                                    (sx-2, sy-2, scaled_ts+4, scaled_ts+4), 2)

            # Health bar
            if entity.health < entity.max_health:
                bar_w = scaled_ts
                bar_h = max(3, scaled_ts // 8)
                hp_ratio = entity.health / entity.max_health
                pygame.draw.rect(self.surf, config.C_DANGER,    (sx, sy-bar_h-2, bar_w, bar_h))
                pygame.draw.rect(self.surf, config.C_SUCCESS,   (sx, sy-bar_h-2, int(bar_w*hp_ratio), bar_h))

            # Name tag
            if scaled_ts >= 20:
                name_surf = self.font_sm.render(entity.name.split()[0], True, config.C_TEXT)
                self.surf.blit(name_surf, (sx, sy - name_surf.get_height() - (3 if entity.health == entity.max_health else bar_h + 5)))

            # Mood indicator (emoji-like dot)
            mood_color = self._mood_color(entity.mood)
            pygame.draw.circle(self.surf, mood_color,
                               (sx + scaled_ts - 4, sy + 4), max(3, scaled_ts//8))

            # LLM thinking indicator
            if entity.pending_llm_call:
                dots = "..." [:int(time.time()*3) % 4]
                think_surf = self.font_sm.render(dots, True, config.C_ACCENT)
                self.surf.blit(think_surf, (sx + scaled_ts + 2, sy))

            # Speech bubble
            if entity.speech_text and entity.speech_until and real_now < entity.speech_until:
                self._draw_speech_bubble(entity.speech_text, sx, sy, scaled_ts)

        # ── Debug overlay ──────────────────────────────────────────────────────
        if show_debug:
            for entity in world.entities.values():
                if not entity.is_alive(): continue
                if entity.destination:
                    sx0, sy0 = cam.tile_to_screen(entity.position["x"], entity.position["y"])
                    sx1, sy1 = cam.tile_to_screen(entity.destination["x"], entity.destination["y"])
                    pygame.draw.line(self.surf, config.C_ACCENT,
                                     (sx0+scaled_ts//2, sy0+scaled_ts//2),
                                     (sx1+scaled_ts//2, sy1+scaled_ts//2), 1)
                if entity.action_queue:
                    q_text = f"Q:{len(entity.action_queue)}"
                    sx, sy = cam.tile_to_screen(entity.position["x"], entity.position["y"])
                    qs = self.font_sm.render(q_text, True, config.C_WARNING)
                    self.surf.blit(qs, (sx, sy + scaled_ts))

        # ── Perception radius (selected) ───────────────────────────────────────
        if selected_id and selected_id in world.entities:
            e = world.entities[selected_id]
            sx, sy = cam.tile_to_screen(e.position["x"], e.position["y"])
            r_px = int(config.PERCEPTION_RADIUS * config.TILE_SIZE * cam.zoom)
            cx, cy = sx + scaled_ts//2, sy + scaled_ts//2
            pygame.draw.circle(self.surf, (100,200,255), (cx, cy), r_px, 1)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _draw_speech_bubble(self, text: str, sx: int, sy: int, scaled_ts: int):
        words = text[:60]
        txt_surf = self.font_sm.render(words, True, config.C_SPEECH_TEXT)
        w, h = txt_surf.get_width() + 8, txt_surf.get_height() + 6
        bx = max(0, min(sx - w//2, config.GAME_AREA_WIDTH - w - 2))
        by = max(0, sy - h - scaled_ts//2 - 4)
        pygame.draw.rect(self.surf, config.C_SPEECH_BG, (bx, by, w, h), border_radius=4)
        pygame.draw.rect(self.surf, (100,100,80), (bx, by, w, h), 1, border_radius=4)
        self.surf.blit(txt_surf, (bx+4, by+3))
        # Tail
        tail_x = sx + scaled_ts//2
        pygame.draw.polygon(self.surf, config.C_SPEECH_BG,
                            [(tail_x-4, by+h), (tail_x+4, by+h), (tail_x, by+h+6)])

    @staticmethod
    def _mood_color(mood: str) -> tuple:
        return {
            "calm":    (150, 200, 255),
            "happy":   (255, 230,  80),
            "sad":     ( 80, 120, 200),
            "angry":   (255,  60,  60),
            "fearful": (200, 100, 220),
            "curious": (100, 230, 180),
            "bored":   (160, 160, 160),
            "excited": (255, 180,  40),
            "tired":   (120, 120, 100),
            "hungry":  (220, 140,  40),
        }.get(mood, (180, 180, 180))
