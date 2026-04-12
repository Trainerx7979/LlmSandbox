# ui_panel.py — right-side developer panel rendered in pygame

import pygame
import time
import config

# ─────────────────────────────────────────────────────────────────────────────
#  Tiny UI primitives
# ─────────────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect: tuple, label: str, key: str = None,
                 color=config.C_PANEL_SECTION, hover=config.C_PANEL_BORDER,
                 active_color=config.C_ACCENT):
        self.rect  = pygame.Rect(rect)
        self.label = label
        self.key   = key or label.lower()
        self.color = color
        self.hover = hover
        self.active_color = active_color
        self.is_hovered = False
        self.is_active  = False

    def draw(self, surf: pygame.Surface, font: pygame.font.Font):
        c = self.active_color if self.is_active else (self.hover if self.is_hovered else self.color)
        pygame.draw.rect(surf, c, self.rect, border_radius=4)
        pygame.draw.rect(surf, config.C_PANEL_BORDER, self.rect, 1, border_radius=4)
        lbl = font.render(self.label, True, config.C_TEXT)
        lx  = self.rect.centerx - lbl.get_width()//2
        ly  = self.rect.centery - lbl.get_height()//2
        surf.blit(lbl, (lx, ly))

    def contains(self, pos) -> bool:
        return self.rect.collidepoint(pos)


# ─────────────────────────────────────────────────────────────────────────────
#  Console  (scrollable event/command log)
# ─────────────────────────────────────────────────────────────────────────────
class Console:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font):
        self.rect   = rect
        self.font   = font
        self.lines: list = []
        self._input = ""
        self._cursor_blink = 0.0
        self._show_cursor  = True
        self._max_lines    = 200

    def add_line(self, text: str, color=None):
        self.lines.append((text, color or config.C_CONSOLE_TEXT))
        if len(self.lines) > self._max_lines:
            self.lines.pop(0)

    def handle_key(self, event: pygame.event.Event) -> str:
        """Returns completed command string (if Enter pressed) or empty string."""
        if event.key == pygame.K_RETURN:
            cmd = self._input.strip()
            self._input = ""
            return cmd
        elif event.key == pygame.K_BACKSPACE:
            self._input = self._input[:-1]
        elif event.key == pygame.K_ESCAPE:
            self._input = ""
        elif event.unicode and len(self._input) < 200:
            self._input += event.unicode
        return ""

    def update(self, dt: float):
        self._cursor_blink += dt
        if self._cursor_blink >= 0.5:
            self._show_cursor = not self._show_cursor
            self._cursor_blink = 0.0

    def draw(self, surf: pygame.Surface):
        pygame.draw.rect(surf, config.C_CONSOLE_BG, self.rect)
        pygame.draw.rect(surf, config.C_PANEL_BORDER, self.rect, 1)

        lh    = self.font.get_linesize()
        # Input bar at bottom
        input_rect = pygame.Rect(self.rect.x, self.rect.bottom - lh - 6, self.rect.width, lh+6)
        pygame.draw.rect(surf, (25, 30, 45), input_rect)
        pygame.draw.rect(surf, config.C_ACCENT, input_rect, 1)
        cursor = "|" if self._show_cursor else " "
        inp_txt = self.font.render("> " + self._input + cursor, True, config.C_ACCENT)
        surf.blit(inp_txt, (self.rect.x + 4, input_rect.y + 3))

        # Scrollable log
        log_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height - lh - 8)
        visible_lines = log_rect.height // lh
        display_lines = self.lines[-visible_lines:]
        for i, (text, color) in enumerate(display_lines):
            # Wrap long lines
            max_chars = self.rect.width // 7
            text = text[:max_chars*2]
            if len(text) > max_chars:
                parts = [text[j:j+max_chars] for j in range(0, len(text), max_chars)]
            else:
                parts = [text]
            for p in parts:
                rendered = self.font.render(p, True, color)
                y = log_rect.y + i * lh
                if y + lh <= log_rect.bottom:
                    surf.blit(rendered, (self.rect.x + 3, y))


# ─────────────────────────────────────────────────────────────────────────────
#  DevPanel
# ─────────────────────────────────────────────────────────────────────────────
class DevPanel:
    """Full developer panel rendered on the right side of the screen."""

    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect   = pygame.Rect(x, y, width, height)
        self.font_s = pygame.font.SysFont("monospace", 11)
        self.font_m = pygame.font.SysFont("monospace", 13)
        self.font_l = pygame.font.SysFont("monospace", 14, bold=True)

        # Tool mode buttons
        btn_w, btn_h = 72, 26
        bx = x + 8
        by = y + 36
        self.tool_buttons = [
            Button((bx + i*(btn_w+4), by, btn_w, btn_h), lbl, key)
            for i, (lbl, key) in enumerate([
                ("Select", config.TOOL_SELECT),
                ("Add",    config.TOOL_ADD),
                ("Delete", config.TOOL_DELETE),
                ("Item",   config.TOOL_SPAWN_ITEM),
                ("Move",   config.TOOL_MOVE_NPC),
            ])
        ]

        # Control buttons (bottom area)
        self.ctrl_buttons = []
        ctrl_labels = [
            ("▶ Run",    "run"),
            ("⏸ Pause",  "pause"),
            ("💾 Save",   "save"),
            ("📂 Load",   "load"),
            ("+ NPC",    "add_npc"),
            ("⬛ Debug",  "debug"),
        ]
        cbx = x + 8
        cby = y + height - 250
        for i, (lbl, key) in enumerate(ctrl_labels):
            col = i % 2
            row = i // 2
            self.ctrl_buttons.append(
                Button((cbx + col*(btn_w+8+4), cby + row*32, btn_w+8, 26), lbl, key)
            )

        # Console
        console_rect = pygame.Rect(x+4, y+height-132, width-8, 128)
        self.console = Console(console_rect, self.font_s)

        # State
        self.current_tool = config.TOOL_SELECT
        self.selected_entity = None
        self.show_debug = False
        self._active_console = True  # console always captures keys

        # Add NPC dialog state
        self.add_npc_pending = False
        self.spawn_item_pending = False
        self.spawn_item_name = ""

    # ─────────────────────────────────────────────────────────────────────────
    #  Update tool button states
    # ─────────────────────────────────────────────────────────────────────────
    def _sync_tool_buttons(self):
        for btn in self.tool_buttons:
            btn.is_active = (btn.key == self.current_tool)

    # ─────────────────────────────────────────────────────────────────────────
    #  Draw
    # ─────────────────────────────────────────────────────────────────────────
    def draw(self, surf: pygame.Surface, world, dt: float):
        self.console.update(dt)
        self._sync_tool_buttons()

        # Background
        pygame.draw.rect(surf, config.C_PANEL_BG, self.rect)
        pygame.draw.line(surf, config.C_PANEL_BORDER,
                         (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)

        px = self.rect.x
        py = self.rect.y

        # ── Title / clock ──────────────────────────────────────────────────────
        title = self.font_l.render("NPC Sandbox", True, config.C_ACCENT)
        surf.blit(title, (px + 8, py + 8))
        clock_surf = self.font_s.render(world.clock_str(), True, config.C_TEXT_DIM)
        surf.blit(clock_surf, (px + 8, py + 24))

        # ── Tool buttons ───────────────────────────────────────────────────────
        for btn in self.tool_buttons:
            btn.draw(surf, self.font_s)

        # ── World stats ────────────────────────────────────────────────────────
        alive = sum(1 for e in world.entities.values() if e.is_alive())
        stats_y = self.rect.y + 76
        stats = [
            f"NPCs alive : {alive}",
            f"Items world: {sum(1 for it in world.items.values() if it.position)}",
            f"Events log : {len(world.events)}",
            f"Bullets    : {len(world.bullets)}",
        ]
        for i, s in enumerate(stats):
            txt = self.font_s.render(s, True, config.C_TEXT_LABEL)
            surf.blit(txt, (px + 8, stats_y + i*15))

        # ── Selected entity inspector ──────────────────────────────────────────
        insp_y = stats_y + len(stats)*15 + 10
        self._draw_inspector(surf, world, px, insp_y)

        # ── Control buttons ────────────────────────────────────────────────────
        for btn in self.ctrl_buttons:
            btn.draw(surf, self.font_s)

        # ── Console ────────────────────────────────────────────────────────────
        self.console.draw(surf)

        # ── Tool hint ─────────────────────────────────────────────────────────
        hints = {
            config.TOOL_SELECT:     "Click NPC to inspect/select",
            config.TOOL_ADD:        "Click map to spawn new NPC",
            config.TOOL_DELETE:     "Click NPC to remove",
            config.TOOL_SPAWN_ITEM: "Click map to place item",
            config.TOOL_MOVE_NPC:   "Select NPC, then click dest",
        }
        hint = hints.get(self.current_tool, "")
        hint_surf = self.font_s.render(hint, True, config.C_TEXT_DIM)
        surf.blit(hint_surf, (px + 4, self.rect.bottom - 148))

    # ─────────────────────────────────────────────────────────────────────────
    #  Entity inspector
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_inspector(self, surf: pygame.Surface, world, px: int, py: int):
        e = self.selected_entity
        if not e or not e.is_alive():
            lbl = self.font_m.render("No entity selected", True, config.C_TEXT_DIM)
            surf.blit(lbl, (px+8, py))
            return

        max_y = self.rect.y + self.rect.height - 220
        lh = 14
        x = px + 8

        def line(text, color=config.C_TEXT, indent=0):
            nonlocal py
            if py + lh > max_y: return
            s = self.font_s.render(text, True, color)
            surf.blit(s, (x + indent, py))
            py += lh

        # Header
        line(f"── {e.name} ──", config.C_ACCENT)
        line(f"Role: {e.sprite_type}  Mood: {e.mood}", config.C_TEXT_LABEL)
        line(f"Pos : ({e.position['x']:.1f}, {e.position['y']:.1f})  Status: {e.status}")
        line(f"HP  : {e.health:.0f}/{e.max_health:.0f}", config.C_SUCCESS if e.health > 50 else config.C_WARNING)

        # Needs bars
        def bar(label, value, w=80, h=8, good=(80,200,100), bad=(220,60,60)):
            nonlocal py
            if py + h + 2 > max_y: return
            lbl_s = self.font_s.render(label, True, config.C_TEXT_LABEL)
            surf.blit(lbl_s, (x, py))
            bx = x + 55
            pygame.draw.rect(surf, (40,40,55), (bx, py, w, h))
            color = good if value < 0.5 else bad
            pygame.draw.rect(surf, color, (bx, py, int(w*value), h))
            py += h + 3

        bar("Hunger", e.hunger)
        bar("Energy", 1.0 - e.energy, good=(80,150,220), bad=(220,140,40))

        # Weapon
        line(f"Weapon : {e.weapon_type}", config.C_TEXT_LABEL)

        # Goals
        if e.short_term_goals:
            line("Short goals:", config.C_WARNING)
            for g in e.short_term_goals[:2]:
                line(f"  • {g[:38]}", indent=4)
        if e.long_term_goals:
            line("Long goals:", config.C_ACCENT)
            for g in e.long_term_goals[:1]:
                line(f"  • {g[:38]}", indent=4)

        # Inventory
        if e.inventory:
            line("Inventory:", config.C_TEXT_LABEL)
            inv_names = []
            for iid in e.inventory[:4]:
                it = world.items.get(iid)
                if it: inv_names.append(it.name)
            line(f"  {', '.join(inv_names)}", indent=4)

        # Recent memories
        if e.short_term_memories:
            line("Recent memories:", config.C_TEXT_LABEL)
            for mem in e.short_term_memories[-3:]:
                text = mem["text"][:40]
                line(f"  {text}", config.C_TEXT_DIM, indent=4)

        # Relationships
        if e.relationships:
            line("Relations:", config.C_TEXT_LABEL)
            for nid, val in list(e.relationships.items())[:3]:
                other = world.entities.get(nid)
                oname = other.name.split()[0] if other else nid
                color = config.C_SUCCESS if val > 0 else config.C_DANGER
                line(f"  {oname}: {val:+.2f}", color, indent=4)

        # Action queue
        if e.action_queue:
            line(f"Actions queued: {len(e.action_queue)}", config.C_TEXT_DIM)

        if e.pending_llm_call:
            line("⟳ Thinking...", config.C_ACCENT)

    # ─────────────────────────────────────────────────────────────────────────
    #  Event handling
    # ─────────────────────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event, world, scheduler) -> str:
        """
        Process panel-side events.
        Returns action string: "run","pause","save","load","add_npc","debug","" etc.
        """
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEMOTION:
            for btn in self.tool_buttons + self.ctrl_buttons:
                btn.is_hovered = btn.contains(mouse_pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.tool_buttons:
                if btn.contains(mouse_pos):
                    self.current_tool = btn.key
                    return ""
            for btn in self.ctrl_buttons:
                if btn.contains(mouse_pos):
                    return btn.key

        elif event.type == pygame.KEYDOWN:
            cmd = self.console.handle_key(event)
            if cmd:
                self.console.add_line(f"> {cmd}", config.C_ACCENT)
                if cmd.lower().startswith("/spawn "):
                    # Direct item spawn command e.g. /spawn apple 20 30
                    parts = cmd.split()
                    if len(parts) >= 4:
                        try:
                            name = parts[1]
                            ix, iy = float(parts[2]), float(parts[3])
                            world.spawn_item_at(name, ix, iy)
                            self.console.add_line(f"Spawned {name} at ({ix},{iy})")
                        except ValueError:
                            self.console.add_line("Usage: /spawn <name> <x> <y>", config.C_DANGER)
                    return ""
                elif cmd.lower().startswith("/teleport ") or cmd.lower().startswith("/tp "):
                    parts = cmd.split()
                    if len(parts) >= 3 and self.selected_entity:
                        try:
                            tx, ty = float(parts[-2]), float(parts[-1])
                            self.selected_entity.position = {"x": tx, "y": ty}
                            self.selected_entity.destination = None
                            self.selected_entity.status = "idle"
                            self.console.add_line(f"Teleported {self.selected_entity.name}")
                        except ValueError:
                            pass
                    return ""
                else:
                    # Global command → scheduler
                    world.pending_commands.append(cmd)
                    self.console.add_line(f"[CMD dispatched to scheduler]", config.C_WARNING)
                    return ""

        return ""

    def sync_events(self, world):
        """Pull new world events into the console."""
        # We keep track with a simple count
        if not hasattr(self, "_last_event_count"):
            self._last_event_count = 0
        new_events = world.events[self._last_event_count:]
        for ev in new_events:
            color = config.C_CONSOLE_TEXT
            text  = ev["text"]
            if "killed" in text or "attack" in text.lower():
                color = config.C_DANGER
            elif "picked up" in text or "gave" in text:
                color = config.C_SUCCESS
            elif "says:" in text:
                color = (255, 255, 180)
            elif "[COMMAND]" in text:
                color = config.C_WARNING
            elif "[SCHEDULER]" in text:
                color = config.C_ACCENT
            self.console.add_line(f"[{int(world.game_time):05d}] {text}", color)
        self._last_event_count = len(world.events)
