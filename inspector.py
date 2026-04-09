# inspector.py — Tkinter-based deep entity inspector popup

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import config


class EntityInspector:
    """
    Standalone Tkinter window that lets the developer deeply inspect
    and edit an NPC's attributes, memories, goals, and relationships.
    """

    def __init__(self, entity, world, scheduler, on_close=None):
        self.entity    = entity
        self.world     = world
        self.scheduler = scheduler
        self.on_close  = on_close
        self._root     = None
        self._running  = False
        self._thread   = threading.Thread(target=self._build, daemon=True)
        self._thread.start()

    def _build(self):
        self._root = tk.Tk()
        root = self._root
        root.title(f"Inspector — {self.entity.name}")
        root.geometry("600x700")
        root.configure(bg="#1a1a2a")
        root.protocol("WM_DELETE_WINDOW", self._close)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1a1a2a", borderwidth=0)
        style.configure("TNotebook.Tab", background="#252535", foreground="#cccccc",
                        padding=[8,4])
        style.map("TNotebook.Tab", background=[("selected","#3a3a5a")])
        style.configure("TFrame", background="#1a1a2a")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Tab: Overview ──────────────────────────────────────────────────────
        tab_ov = self._make_tab(notebook, "Overview")
        self._build_overview(tab_ov)
        notebook.add(tab_ov, text="Overview")

        # ── Tab: Goals ────────────────────────────────────────────────────────
        tab_g = self._make_tab(notebook, "Goals")
        self._build_goals(tab_g)
        notebook.add(tab_g, text="Goals")

        # ── Tab: Memories ─────────────────────────────────────────────────────
        tab_m = self._make_tab(notebook, "Memories")
        self._build_memories(tab_m)
        notebook.add(tab_m, text="Memories")

        # ── Tab: Relationships ────────────────────────────────────────────────
        tab_r = self._make_tab(notebook, "Relationships")
        self._build_relationships(tab_r)
        notebook.add(tab_r, text="Relations")

        # ── Tab: Send Message ─────────────────────────────────────────────────
        tab_msg = self._make_tab(notebook, "Message")
        self._build_message(tab_msg)
        notebook.add(tab_msg, text="Send Msg")

        self._running = True
        root.mainloop()
        self._running = False

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _make_tab(self, nb, _name):
        f = ttk.Frame(nb)
        f.configure(style="TFrame")
        return f

    def _label(self, parent, text, row=0, col=0, color="#cccccc", bold=False,
               sticky="w", padx=8, pady=2, columnspan=1):
        font = ("Courier", 10, "bold" if bold else "normal")
        lbl = tk.Label(parent, text=text, fg=color, bg="#1a1a2a", font=font,
                       anchor="w")
        lbl.grid(row=row, column=col, sticky=sticky, padx=padx, pady=pady,
                 columnspan=columnspan)
        return lbl

    def _entry(self, parent, var, row=0, col=1, width=30):
        e = tk.Entry(parent, textvariable=var, bg="#252540", fg="#e0e0e0",
                     insertbackground="white", relief="flat", font=("Courier",10),
                     width=width)
        e.grid(row=row, column=col, sticky="ew", padx=8, pady=2)
        return e

    def _btn(self, parent, text, cmd, row=0, col=0, color="#3355aa"):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="white", relief="flat",
                      font=("Courier",10), padx=6, pady=2)
        b.grid(row=row, column=col, padx=6, pady=4, sticky="w")
        return b

    # ── Overview tab ──────────────────────────────────────────────────────────
    def _build_overview(self, tab):
        e = self.entity
        tab.columnconfigure(1, weight=1)

        fields = [
            ("Name",       e.name,          "name_var"),
            ("Sprite type",e.sprite_type,   "sprite_var"),
            ("Mood",       e.mood,          "mood_var"),
            ("Health",     str(round(e.health,1)), "hp_var"),
            ("Max Health", str(round(e.max_health,1)), "maxhp_var"),
            ("Hunger",     f"{e.hunger:.3f}", "hunger_var"),
            ("Energy",     f"{e.energy:.3f}", "energy_var"),
            ("Speed",      str(round(e.speed,2)), "speed_var"),
            ("Weapon type",e.weapon_type,   "weapon_var"),
            ("Status",     e.status,        "status_var"),
            ("Pos X",      f"{e.position['x']:.1f}", "posx_var"),
            ("Pos Y",      f"{e.position['y']:.1f}", "posy_var"),
        ]

        self._ov_vars = {}
        for i, (label, value, var_name) in enumerate(fields):
            self._label(tab, label+":", row=i, col=0)
            var = tk.StringVar(value=value)
            self._ov_vars[var_name] = var
            self._entry(tab, var, row=i, col=1)

        def apply_changes():
            try:
                e.name         = self._ov_vars["name_var"].get()
                e.sprite_type  = self._ov_vars["sprite_var"].get()
                e.mood         = self._ov_vars["mood_var"].get()
                e.health       = float(self._ov_vars["hp_var"].get())
                e.max_health   = float(self._ov_vars["maxhp_var"].get())
                e.hunger       = float(self._ov_vars["hunger_var"].get())
                e.energy       = float(self._ov_vars["energy_var"].get())
                e.speed        = float(self._ov_vars["speed_var"].get())
                e.weapon_type  = self._ov_vars["weapon_var"].get()
                e.status       = self._ov_vars["status_var"].get()
                e.position["x"]= float(self._ov_vars["posx_var"].get())
                e.position["y"]= float(self._ov_vars["posy_var"].get())
                messagebox.showinfo("Saved", "Changes applied to NPC.")
            except ValueError as ex:
                messagebox.showerror("Error", str(ex))

        row = len(fields)
        self._btn(tab, "Apply Changes", apply_changes, row=row, col=0)
        self._btn(tab, "Kill NPC",
                  lambda: self.world.kill_entity(e.id),
                  row=row, col=1, color="#aa3333")

    # ── Goals tab ─────────────────────────────────────────────────────────────
    def _build_goals(self, tab):
        e = self.entity
        tab.columnconfigure(0, weight=1)

        self._label(tab, "Short-term goals:", row=0, col=0, color="#ffdd80", bold=True)
        self._st_goals = scrolledtext.ScrolledText(tab, height=5, bg="#1e1e30",
                                                    fg="#e0e0e0", font=("Courier",10))
        self._st_goals.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        self._st_goals.insert("end", "\n".join(e.short_term_goals))

        self._label(tab, "Long-term goals:", row=2, col=0, color="#80c8ff", bold=True)
        self._lt_goals = scrolledtext.ScrolledText(tab, height=5, bg="#1e1e30",
                                                    fg="#e0e0e0", font=("Courier",10))
        self._lt_goals.grid(row=3, column=0, sticky="ew", padx=8, pady=4)
        self._lt_goals.insert("end", "\n".join(e.long_term_goals))

        def save_goals():
            st = [g.strip() for g in self._st_goals.get("1.0","end").splitlines() if g.strip()]
            lt = [g.strip() for g in self._lt_goals.get("1.0","end").splitlines() if g.strip()]
            e.short_term_goals = st
            e.long_term_goals  = lt
            messagebox.showinfo("Saved", "Goals updated.")

        self._btn(tab, "Save Goals", save_goals, row=4, col=0)

    # ── Memories tab ─────────────────────────────────────────────────────────
    def _build_memories(self, tab):
        e = self.entity
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        self._label(tab, "All memories (newest last):", row=0, col=0, bold=True)
        self._mem_box = scrolledtext.ScrolledText(tab, height=20, bg="#1e1e30",
                                                   fg="#d0d0d0", font=("Courier",10))
        self._mem_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        for m in e.memories:
            self._mem_box.insert("end", f"[{m['time']:6d}] {m['text']}\n")

        self._label(tab, "Add memory:", row=2, col=0)
        self._new_mem_var = tk.StringVar()
        self._entry(tab, self._new_mem_var, row=3, col=0, width=60)

        def add_mem():
            text = self._new_mem_var.get().strip()
            if text:
                e.add_memory(self.world.game_time, text)
                self._mem_box.insert("end", f"[{int(self.world.game_time):6d}] {text}\n")
                self._new_mem_var.set("")

        def clear_mems():
            if messagebox.askyesno("Clear", "Delete all memories?"):
                e.memories.clear()
                e.short_term_memories.clear()
                self._mem_box.delete("1.0","end")

        bf = tk.Frame(tab, bg="#1a1a2a")
        bf.grid(row=4, column=0, sticky="w", padx=8, pady=4)
        self._btn(bf, "Add Memory", add_mem, row=0, col=0)
        self._btn(bf, "Clear All",  clear_mems, row=0, col=1, color="#aa3333")

    # ── Relationships tab ─────────────────────────────────────────────────────
    def _build_relationships(self, tab):
        e = self.entity
        tab.columnconfigure(1, weight=1)

        self._label(tab, "NPC ID", row=0, col=0, bold=True)
        self._label(tab, "Name",   row=0, col=1, bold=True)
        self._label(tab, "Affinity (-1..1)", row=0, col=2, bold=True)

        self._rel_rows = []
        for i, (npc_id, val) in enumerate(list(e.relationships.items())[:15], start=1):
            other = self.world.entities.get(npc_id)
            oname = other.name if other else "?"
            id_lbl  = tk.Label(tab, text=npc_id[:12], fg="#888", bg="#1a1a2a", font=("Courier",9))
            id_lbl.grid(row=i, column=0, padx=4, pady=1)
            nm_lbl  = tk.Label(tab, text=oname[:16], fg="#ccc", bg="#1a1a2a", font=("Courier",9))
            nm_lbl.grid(row=i, column=1, padx=4, pady=1)
            val_var = tk.StringVar(value=f"{val:.2f}")
            val_entry = tk.Entry(tab, textvariable=val_var, bg="#252540", fg="#e0e0e0",
                                 width=8, font=("Courier",9))
            val_entry.grid(row=i, column=2, padx=4, pady=1)
            self._rel_rows.append((npc_id, val_var))

        def save_rels():
            for npc_id, var in self._rel_rows:
                try:
                    e.relationships[npc_id] = max(-1.0, min(1.0, float(var.get())))
                except ValueError:
                    pass
            messagebox.showinfo("Saved","Relationships updated.")

        n = len(e.relationships)
        self._btn(tab, "Save Relations", save_rels, row=n+2, col=0)

    # ── Message tab ───────────────────────────────────────────────────────────
    def _build_message(self, tab):
        tab.columnconfigure(0, weight=1)
        self._label(tab, "Inject a message into this NPC's next decision prompt:",
                    row=0, col=0, color="#ffdd80", bold=True)
        self._msg_box = scrolledtext.ScrolledText(tab, height=8, bg="#1e1e30",
                                                   fg="#e0e0e0", font=("Courier",11))
        self._msg_box.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        self._msg_box.insert("end",
            "e.g. 'You smell smoke. Something is burning to the north.'")

        def send_msg():
            msg = self._msg_box.get("1.0","end").strip()
            if msg:
                self.scheduler.interrupt_entity(self.entity.id, msg)
                messagebox.showinfo("Sent", f"Message injected for {self.entity.name}.")

        self._btn(tab, "Send Message", send_msg, row=2, col=0, color="#335599")

        self._label(tab, "\nForce immediate LLM call with no queue:", row=3, col=0)
        def force_think():
            self.scheduler.interrupt_entity(self.entity.id, "Assess the situation and decide what to do.")
            messagebox.showinfo("Queued","NPC will think on next tick.")
        self._btn(tab, "Force Think", force_think, row=4, col=0, color="#225533")

    # ── Lifecycle ──────────────────────────────────────────────────────────────
    def _close(self):
        if self.on_close:
            self.on_close()
        if self._root:
            self._root.destroy()

    def close(self):
        if self._root and self._running:
            self._root.quit()
