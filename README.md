# NPC Sandbox — LLM-Driven Simulation

A real-time 2D RPG sandbox where procedurally named NPCs live, move, act, and
remember — with every decision powered by a live LLM call returning structured JSON.

\---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your specific Ollama or LM Studio base URL and chosen model in config.py

\# 3. Run
python main.py

# Load from save (or it auto-loads if saves/world\_save.json exists)
python main.py --load
```

\---

## Controls

|Input|Action|
|-|-|
|**WASD / Arrow keys**|— (camera pan with mouse drag)|
|**Mouse drag (middle btn / Alt+Left)**|Pan camera|
|**Scroll wheel**|Zoom in/out at cursor|
|**Left-click** (Select tool)|Select NPC, inspect in right panel|
|**Right-click** on NPC|Open deep Tkinter inspector window|
|**Left-click** (Add tool)|Spawn new NPC at cursor|
|**Left-click** (Delete tool)|Remove NPC under cursor|
|**Left-click** (Item tool)|Place item at cursor|
|**Scroll** (Item tool)|Cycle through item types|
|**Left-click** (Move tool)|Teleport selected NPC to cursor|
|**Space**|Pause / resume|
|**F5**|Quick save|
|**F9**|Quick load|
|**D**|Toggle debug overlay (paths, action queues)|
|**I**|Open inspector for selected NPC|
|**N**|Spawn a random NPC|
|**Escape**|Quit (auto-saves)|

### Developer Console (bottom-right)

Type any natural language command and press **Enter** to inject it as a
high-priority event into the scheduler, which will translate it into targeted
NPC messages.

**Examples:**

```
Ray and Gary should fight to the death
All NPCs drop what they're carrying and gather in the center
Make Cora become suspicious of everyone around her
Spawn a fire at 30 32    →  scheduler handles interpretation
/spawn sword 25 20       →  direct item spawn command
/tp 30 30                →  teleport selected NPC
```

\---

## Architecture

```
main.py          Entry point, game loop, event routing
├── world.py     Map, entity/item registry, procedural generation, event log
├── entity.py    Entity (NPC) + Item + Bullet dataclasses
├── scheduler.py Physics, needs decay, movement, action execution, LLM triggers
├── llm.py       Prompt builder, response parser, async API calls (threaded)
├── renderer.py  Pygame camera, tilemap, procedural sprites, overlays
├── ui\_panel.py  Right-side developer panel (tools, console, entity inspector)
├── inspector.py Tkinter deep-inspector popup (memories, goals, relationships)
├── persistence.py JSON save/load with auto-backup
└── config.py    All constants: display, gameplay, colors, schemas
```

### LLM Decision Flow

```
NPC arrives at destination  ─┐
Periodic check (5 game-min) ─┼─▶  scheduler.py  ──▶  llm.py (build\_npc\_prompt)
Interruption event          ─┘         │                      │
                                        │                      ▼
                                        │           Anthropic API call (async thread)
                                        │                      │
                                        │◀──── JSON response ──┘
                                        │
                                        ▼
                              Apply: mood, goals, memories,
                              relationships, action queue
```

### Global Command Flow

```
Developer types command in console
        │
        ▼
scheduler LLM call  (build\_scheduler\_prompt)
        │
        ▼
Returns: per-NPC messages + optional direct world effects
        │
        ├── Each NPC gets .pending\_scheduler\_message
        │   → injected into their next decision prompt as URGENT\_DIRECTIVE
        │
        └── World effects applied immediately (teleport, health, spawn, etc.)
```

\---

## NPC Schema

Each NPC carries:

* **Stats**: health, hunger, energy, speed
* **Goals**: short-term (immediate tasks) + long-term (life ambitions)
* **Memory**: append-only long-term log + rolling 15-entry short-term buffer
* **Relationships**: per-NPC affinity float (-1 hostile → +1 trusted)
* **Perceptions**: visible entities/items at time of last decision
* **Action queue**: prioritised list of pending actions

\---

## Save File

Saves to `saves/world\_save.json`.  Auto-saves every 3 real-minutes.
Backup of previous save kept as `world\_save.json.bak`.

