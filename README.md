# NPC Sandbox — LLM-Driven Simulation

**Why does this exist?**
The "Interactive Simulcra of Human Behavior" experiment was an amazing proof-of-concept
toward agentic behavior research. It was an excellent "first-step" toward exploring the
potential, and dangers, in having agent layers of protection as part of any system.
It also explored inter-agent interactions allowing for new goals/plans to be made.
But it was limited in true autonomy. The agents could interact, but could not make any
real changes to their world. That is why this exists. These agents can interact, can
change their world, can drive entire storylines.

A real-time 2D RPG sandbox where procedurally named NPCs live, move, act, and
remember — with every decision powered by a live LLM call returning structured JSON.

Npcs move and live in real-time, LLM calls are triggered and queued.
Result from LLM call is acted on in real time, as it is processed.
If your Ollama or LM Studio model is capable of very large contexts,

You can run multiple calls simultaneously by changing the value in
Config.Py Which is also where you set up your LLM model name and URL.
\---
Purpose:
To learn. For us all to learn. And to have fun. I designed this to be as open for
potential as possible. And hopefully, easy to addon/tune to your own needs.
Whether you want to watch a mini world live, or want to learn more about how LLMs
and sometimes we think, any setup should be just a few *minor* adjustments away.
Expect some bugs. I'm working as fast as I can... :)
<img width="1828" height="928" alt="Screenshot" src="https://github.com/user-attachments/assets/f66de4cc-7235-4998-b42c-6cc29748c915" />

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your specific Ollama or LM Studio base URL and chosen model in config.py

# 3. Run
python main.py

# Load from save (or it auto-loads if saves/world_save.json exists)
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
|**Shift+Space**|Pause / resume|
|**F5**|Quick save|
|**F9**|Quick load|
|**Shift+D**|Toggle debug overlay (paths, action queues)|
|**Shift+I**|Open inspector for selected NPC|
|**Shift+N**|Spawn a random NPC|
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
Interruption event          ─┘          │                      │
                                        │                      ▼
                                        │     Open AI compatible API call (async thread)
                                        │                      │   You can supply this with
                                        │◀──── JSON response ──┘   LM Studio or Ollama.
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

Saves to `saves/world_save.json`.  Auto-saves every 3 real-minutes.
Backup of previous save kept as `world_save.json.bak`.

