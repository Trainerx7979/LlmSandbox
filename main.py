#!/usr/bin/env python3
# main.py — entry point: main loop, event routing, world bootstrap

import sys
import os
import time
import random
import logging
import pygame

import config
from world import World
from entity import Entity, Item
from scheduler import Scheduler
from renderer import Renderer, Camera
from ui_panel import DevPanel
from persistence import save_world, load_world, autosave

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


# ─────────────────────────────────────────────────────────────────────────────
#  Bootstrap world
# ─────────────────────────────────────────────────────────────────────────────
def create_new_world(num_npcs: int = 6) -> World:
    world = World(config.MAP_WIDTH, config.MAP_HEIGHT)
    world.generate()

    for _ in range(num_npcs):
        world.spawn_npc()

    # Scatter some starter items
    starter_items = [
        "apple","apple","bread","meat","sword","axe","bow","dagger",
        "potion","potion","gold","gold","torch","bed_roll","key",
    ]
    for item_name in starter_items:
        for _ in range(30):
            x = random.randint(4, world.width-4)
            y = random.randint(4, world.height-4)
            if not world.is_blocked(x, y):
                world.spawn_item_at(item_name, float(x), float(y))
                break

    world.log_event("World created. NPCs awakening...")
    return world


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.display.set_caption("NPC Sandbox — LLM-Driven Simulation")

    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    game_surf = pygame.Surface((config.GAME_AREA_WIDTH, config.SCREEN_HEIGHT))
    clock_pg  = pygame.time.Clock()

    # ── World ─────────────────────────────────────────────────────────────────
    world_path = config.SAVE_FILE
    if "--load" in sys.argv or os.path.exists(world_path):
        try:
            world = load_world(world_path)
            logger.info("Loaded existing world.")
        except Exception:
            logger.info("No save found, generating new world.")
            world = create_new_world()
    else:
        world = create_new_world()

    # ── Sub-systems ───────────────────────────────────────────────────────────
    scheduler = Scheduler(world)
    camera    = Camera()
    renderer  = Renderer(game_surf, camera)
    panel     = DevPanel(config.GAME_AREA_WIDTH, 0, config.PANEL_WIDTH, config.SCREEN_HEIGHT)

    # Centre camera on map
    camera.x  = (world.width  * config.TILE_SIZE) / 2 - config.GAME_AREA_WIDTH  / 2
    camera.y  = (world.height * config.TILE_SIZE) / 2 - config.SCREEN_HEIGHT / 2

    # ── State ─────────────────────────────────────────────────────────────────
    running      = True
    paused       = False
    show_debug   = False
    selected_id: str = None
    drag_last    = None
    inspector_window = None  # open tkinter inspector

    # Item name for spawning (simple list)
    item_names  = list(config.ITEM_TEMPLATES.keys())
    spawn_item_idx = 0

    prev_time = time.perf_counter()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def get_tile_at_mouse(mx, my) -> tuple:
        if mx >= config.GAME_AREA_WIDTH: return None, None
        tx, ty = camera.screen_to_tile(mx, my)
        return tx, ty

    def entity_at_mouse(mx, my):
        tx, ty = get_tile_at_mouse(mx, my)
        if tx is None: return None
        best, best_d = None, 1.2
        for e in world.entities.values():
            if not e.is_alive(): continue
            d = ((e.position["x"]-tx)**2 + (e.position["y"]-ty)**2)**0.5
            if d < best_d:
                best, best_d = e, d
        return best

    # ─────────────────────────────────────────────────────────────────────────
    #  Game loop
    # ─────────────────────────────────────────────────────────────────────────
    while running:
        now     = time.perf_counter()
        real_dt = min(now - prev_time, 0.1)
        prev_time = now

        # ── Events ───────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # ── Keyboard ─────────────────────────────────────────────────────
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if event.mod & pygame.KMOD_SHIFT:
                        paused = not paused
                        world.paused = paused
                        panel.console.add_line("PAUSED" if paused else "RUNNING",
                                               config.C_WARNING)
                    else:
                        panel.handle_event(event, world, scheduler)
                elif event.key == pygame.K_F5:
                    save_world(world)
                    panel.console.add_line("World saved (F5)", config.C_SUCCESS)
                elif event.key == pygame.K_F9:
                    try:
                        world = load_world()
                        scheduler = Scheduler(world)
                        panel.console.add_line("World loaded (F9)", config.C_SUCCESS)
                    except FileNotFoundError:
                        panel.console.add_line("No save file found", config.C_DANGER)

                elif event.key == pygame.K_d:
                    if event.mod & pygame.KMOD_SHIFT:
                        show_debug = not show_debug
                    else:
                        panel.handle_event(event, world, scheduler)
                elif event.key == pygame.K_i:
                    if event.mod & pygame.KMOD_SHIFT:
                        # Open inspector for selected entity
                        if selected_id and selected_id in world.entities:
                            _open_inspector(world.entities[selected_id], world, scheduler)
                    else:
                        panel.handle_event(event, world, scheduler)
                elif event.key == pygame.K_n:
                    if event.mod & pygame.KMOD_SHIFT:
                        e = world.spawn_npc()
                        panel.console.add_line(f"Spawned {e.name}", config.C_SUCCESS)
                    else:
                        panel.handle_event(event, world, scheduler)
                else:
                    # Pass to panel console
                    panel.handle_event(event, world, scheduler)

            # ── Mouse wheel (zoom) ────────────────────────────────────────────
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if mx < config.GAME_AREA_WIDTH:
                    factor = 1 + config.ZOOM_STEP * event.y
                    camera.zoom_at(mx, my, factor)

            # ── Mouse button ─────────────────────────────────────────────────
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if mx >= config.GAME_AREA_WIDTH:
                    # Panel click
                    action = panel.handle_event(event, world, scheduler)
                    if action == "run":
                        paused = False; world.paused = False
                    elif action == "pause":
                        paused = True;  world.paused = True
                    elif action == "save":
                        save_world(world)
                        panel.console.add_line("Saved.", config.C_SUCCESS)
                    elif action == "load":
                        try:
                            world = load_world()
                            scheduler = Scheduler(world)
                            panel.console.add_line("Loaded.", config.C_SUCCESS)
                        except FileNotFoundError:
                            panel.console.add_line("No save.", config.C_DANGER)
                    elif action == "add_npc":
                        e = world.spawn_npc()
                        panel.console.add_line(f"Spawned {e.name}", config.C_SUCCESS)
                    elif action == "debug":
                        show_debug = not show_debug

                else:
                    # Game area click
                    if event.button == 2 or (event.button == 1 and
                                              pygame.key.get_pressed()[pygame.K_LALT]):
                        # Middle click or Alt+Left = start pan drag
                        drag_last = (mx, my)

                    elif event.button == 1:
                        tool = panel.current_tool
                        tx, ty = get_tile_at_mouse(mx, my)

                        if tool == config.TOOL_SELECT:
                            hit = entity_at_mouse(mx, my)
                            if hit:
                                selected_id = hit.id
                                panel.selected_entity = hit
                            else:
                                selected_id = None
                                panel.selected_entity = None

                        elif tool == config.TOOL_ADD:
                            if tx is not None and not world.is_blocked(tx, ty):
                                e = Entity.create_random(world.width, world.height)
                                e.position = {"x": float(int(tx)), "y": float(int(ty))}
                                world.add_entity(e)
                                panel.console.add_line(f"Added {e.name}", config.C_SUCCESS)

                        elif tool == config.TOOL_DELETE:
                            hit = entity_at_mouse(mx, my)
                            if hit:
                                world.remove_entity(hit.id)
                                if selected_id == hit.id:
                                    selected_id = None
                                    panel.selected_entity = None
                                panel.console.add_line(f"Removed {hit.name}", config.C_WARNING)

                        elif tool == config.TOOL_SPAWN_ITEM:
                            if tx is not None and not world.is_blocked(tx, ty):
                                name = item_names[spawn_item_idx % len(item_names)]
                                world.spawn_item_at(name, float(int(tx)), float(int(ty)))
                                panel.console.add_line(f"Spawned {name} at ({int(tx)},{int(ty)})")

                        elif tool == config.TOOL_MOVE_NPC:
                            if selected_id and selected_id in world.entities:
                                e = world.entities[selected_id]
                                if tx is not None:
                                    e.destination = {"x": float(int(tx)), "y": float(int(ty))}
                                    e.status = "moving"
                                    e.action_queue.clear()

                    elif event.button == 3:
                        # Right-click: context menu → open inspector
                        hit = entity_at_mouse(mx, my)
                        if hit:
                            selected_id = hit.id
                            panel.selected_entity = hit
                            _open_inspector(hit, world, scheduler)

                    elif event.button == 4:
                        # Scroll up → cycle spawn item
                        spawn_item_idx = (spawn_item_idx + 1) % len(item_names)
                        panel.console.add_line(
                            f"Spawn item: {item_names[spawn_item_idx % len(item_names)]}")
                    elif event.button == 5:
                        spawn_item_idx = (spawn_item_idx - 1) % len(item_names)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 2):
                    drag_last = None

            elif event.type == pygame.MOUSEMOTION:
                if drag_last:
                    mx, my = event.pos
                    dx = mx - drag_last[0]
                    dy = my - drag_last[1]
                    camera.pan(dx, dy)
                    drag_last = (mx, my)
                # Pass motion to panel for hover
                panel.handle_event(event, world, scheduler)

        # ── Update ────────────────────────────────────────────────────────────
        if not paused:
            scheduler.update(real_dt)
            panel.sync_events(world)
            autosave(world, interval_real_seconds=180)

        # ── Render ────────────────────────────────────────────────────────────
        game_surf.fill((10, 10, 15))
        renderer.render(world, selected_id=selected_id, show_debug=show_debug)
        screen.blit(game_surf, (0, 0))

        panel.draw(screen, world, real_dt)

        # FPS counter
        fps_surf = pygame.font.SysFont("monospace", 11).render(
            f"FPS:{clock_pg.get_fps():.0f}  Zoom:{camera.zoom:.1f}x", True, (80,80,100))
        screen.blit(fps_surf, (4, config.SCREEN_HEIGHT - 16))

        pygame.display.flip()
        clock_pg.tick(config.FPS)

    # ── Shutdown ──────────────────────────────────────────────────────────────
    save_world(world)
    pygame.quit()
    logger.info("Simulation ended. World auto-saved.")


# ─────────────────────────────────────────────────────────────────────────────
#  Inspector helper (avoids importing at module level to keep tkinter optional)
# ─────────────────────────────────────────────────────────────────────────────
_open_inspectors = {}

def _open_inspector(entity, world, scheduler):
    eid = entity.id
    existing = _open_inspectors.get(eid)
    if existing and existing._running:
        return  # already open
    from inspector import EntityInspector
    def on_close():
        _open_inspectors.pop(eid, None)
    insp = EntityInspector(entity, world, scheduler, on_close=on_close)
    _open_inspectors[eid] = insp


# ─────────────────────────────────────────────────────────────────────────────
#  Entry
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
