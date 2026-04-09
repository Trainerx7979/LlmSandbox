# config.py — global constants and configuration

# ── Display ───────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1400
SCREEN_HEIGHT = 900
GAME_AREA_WIDTH = 980          # left pane (game canvas)
PANEL_WIDTH  = SCREEN_WIDTH - GAME_AREA_WIDTH   # right pane (dev panel)
TILE_SIZE    = 32
FPS          = 60
MAP_WIDTH    = 64              # tiles
MAP_HEIGHT   = 64
MIN_ZOOM     = 0.4
MAX_ZOOM     = 3.5
ZOOM_STEP    = 0.12

# ── Game time ─────────────────────────────────────────────────────────────────
GAME_MINUTES_PER_SECOND = 1.0  # 1 real-second = x game-minutes
PERIODIC_CHECK_INTERVAL = 5    # game-minutes between NPC heartbeat checks

# ── NPC simulation ────────────────────────────────────────────────────────────
DEFAULT_SPEED          = 2.5   # tiles/second
HUNGER_DECAY_RATE      = 0.0002  # per game-minute
ENERGY_DECAY_RATE      = 0.0006
HUNGER_DAMAGE_THRESHOLD = 0.98
HUNGER_DAMAGE_RATE     = 0.2   # HP/game-minute while starving
SHORT_TERM_MEM_LIMIT   = 15
PERCEPTION_RADIUS      = 20.0   # tiles
SPEECH_DISPLAY_TIME    = 5.0   # real-seconds
SLEEP_DURATION         = 360   # game-minutes (6 game-hours)
MAX_ACTION_QUEUE       = 10

# ── LLM ───────────────────────────────────────────────────────────────────────
# Points at the OpenAI-compatible endpoint exposed by Ollama / LM Studio.
# Change LLM_MODEL to whatever model you have pulled/loaded locally.
#
#   Ollama examples   : "llama3.2", "mistral", "gemma3:12b", "qwen2.5:14b"
#   LM Studio example : the model identifier shown in the LM Studio UI
#
LLM_BASE_URL     = "http://127.0.0.1:11434/v1"
LLM_MODEL        = "gemma-4-e4b-uncensored-hauhaucs-aggressive"       # ← change to your loaded model name
LLM_MAX_TOKENS   = 8000
LLM_TIMEOUT      = 30               # local models can be slower
MAX_LLM_CONCURRENT = 1              # keep lower for local hardware

# ── Paths ─────────────────────────────────────────────────────────────────────
SAVE_DIR  = "saves"
SAVE_FILE = "saves/world_save.json"

# ── Colours ───────────────────────────────────────────────────────────────────
C_GRASS        = (86,  125,  70)
C_GRASS_ALT    = (76,  115,  62)
C_WATER        = (64,  120, 180)
C_WATER_DARK   = (44,   90, 150)
C_TREE         = (34,   85,  34)
C_TREE_DARK    = (24,   65,  24)
C_WALL         = (110,  90,  70)
C_FLOOR        = (155, 135, 115)
C_PATH         = (175, 155, 125)
C_SAND         = (195, 180, 130)

C_PANEL_BG     = (22,  22,  32)
C_PANEL_BORDER = (55,  55,  80)
C_PANEL_SECTION= (35,  35,  50)
C_TEXT         = (220, 220, 220)
C_TEXT_DIM     = (130, 130, 155)
C_TEXT_LABEL   = (180, 180, 200)
C_ACCENT       = (100, 185, 255)
C_WARNING      = (255, 185,  60)
C_DANGER       = (255,  80,  80)
C_SUCCESS      = (80,  220, 120)
C_SELECTION    = (255, 255,   0)
C_HOVER        = (200, 200,   0)
C_CONSOLE_BG   = (15,  15,  25)
C_CONSOLE_TEXT = (160, 255, 140)
C_BULLET       = (255, 230,  50)
C_BLOOD        = (180,  20,  20)
C_CORPSE       = (80,   60,  50)
C_SPEECH_BG    = (255, 255, 220)
C_SPEECH_TEXT  = (10,  10,  10)

# ── Tile IDs ─────────────────────────────────────────────────────────────────
TILE_GRASS  = 0
TILE_WATER  = 1
TILE_TREE   = 2
TILE_WALL   = 3
TILE_FLOOR  = 4
TILE_PATH   = 5
TILE_SAND   = 6
BLOCKING_TILES = {TILE_WATER, TILE_TREE, TILE_WALL}

# ── Tool modes ────────────────────────────────────────────────────────────────
TOOL_SELECT     = "select"
TOOL_ADD        = "add"
TOOL_DELETE     = "delete"
TOOL_SPAWN_ITEM = "spawn_item"
TOOL_MOVE_NPC   = "move_npc"

# ── Sprite palette sets (procedural drawing) ──────────────────────────────────
SPRITE_PALETTES = {
    "warrior":  {"skin":(220,180,140),"hair":(80, 50, 30),"clothes":(55, 55,135),"accent":(200, 50, 50)},
    "mage":     {"skin":(200,160,120),"hair":(175,95,200),"clothes":(75, 20,115),"accent":(145,195,255)},
    "rogue":    {"skin":(170,130,100),"hair":(30, 20, 10),"clothes":(28, 28, 28),"accent":(175,155, 45)},
    "peasant":  {"skin":(210,175,135),"hair":(140,100, 60),"clothes":(125, 95, 65),"accent":(175,135, 75)},
    "merchant": {"skin":(195,155,115),"hair":(155,115, 75),"clothes":(145, 75, 18),"accent":(220,175, 38)},
    "guard":    {"skin":(200,165,125),"hair":(55, 38, 18),"clothes":(78, 78, 78),"accent":(175,145, 45)},
    "healer":   {"skin":(230,195,160),"hair":(195,175, 95),"clothes":(215,215,235),"accent":(75,195, 75)},
    "bard":     {"skin":(215,175,130),"hair":(195,155, 75),"clothes":(175, 55,155),"accent":(255,195, 75)},
}
SPRITE_TYPES = list(SPRITE_PALETTES.keys())

# ── Weapon types ──────────────────────────────────────────────────────────────
WEAPON_TYPES = ["hitting", "stabbing", "shooting"]
WEAPON_DAMAGE = {"hitting": (8, 18), "stabbing": (12, 22), "shooting": (10, 20)}
WEAPON_RANGE  = {"hitting": 1.5,     "stabbing": 1.8,      "shooting": 12.0}

# ── Action types (LLM-returnable) ─────────────────────────────────────────────
ACTION_MOVE      = "move"
ACTION_SAY       = "say"
ACTION_ATTACK    = "attack"
ACTION_PICK_UP   = "pick_up"
ACTION_DROP      = "drop"
ACTION_USE       = "use"
ACTION_WAIT      = "wait"
ACTION_SLEEP     = "sleep"
ACTION_GIVE      = "give"
VALID_ACTIONS    = {ACTION_MOVE, ACTION_SAY, ACTION_ATTACK, ACTION_PICK_UP,
                    ACTION_DROP, ACTION_USE, ACTION_WAIT, ACTION_SLEEP, ACTION_GIVE}

MOODS = ["calm","happy","sad","angry","fearful","curious","bored","excited","tired","hungry"]

# ── NPC name pools ────────────────────────────────────────────────────────────
FIRST_NAMES = [
    "Aldric","Bram","Cora","Dwyn","Elsa","Finn","Greta","Holt","Iris","Jorn",
    "Kira","Lars","Mira","Noel","Ora","Penn","Quinn","Rafe","Sera","Tove",
    "Ulric","Vera","Wren","Xan","Yara","Zev","Aric","Bea","Cal","Dex",
    "Edda","Fray","Gull","Hana","Idun","Jak","Keld","Lund","Mab","Nyx",
]
LAST_NAMES = [
    "Stone","Brook","Field","Wood","Hill","Vale","Marsh","Glen","Ford","Cross",
    "Smith","Miller","Cooper","Fisher","Hunter","Tanner","Weaver","Mason",
    "Thatcher","Fletcher","Bower","Harper","Sawyer","Turner","Walker","Ward",
]

# ── Item templates ─────────────────────────────────────────────────────────────
ITEM_TEMPLATES = {
    "apple":     {"item_type":"food",   "properties":{"restore_hunger":0.25}, "color":(220,60,40)},
    "bread":     {"item_type":"food",   "properties":{"restore_hunger":0.40}, "color":(200,160,80)},
    "meat":      {"item_type":"food",   "properties":{"restore_hunger":0.55}, "color":(180,80,60)},
    "axe":       {"item_type":"weapon", "properties":{"damage":14,"weapon_type":"hitting"}, "color":(140,120,100)},
    "sword":     {"item_type":"weapon", "properties":{"damage":16,"weapon_type":"stabbing"}, "color":(180,180,200)},
    "bow":       {"item_type":"weapon", "properties":{"damage":12,"weapon_type":"shooting"}, "color":(160,120,60)},
    "dagger":    {"item_type":"weapon", "properties":{"damage":10,"weapon_type":"stabbing"}, "color":(160,160,180)},
    "potion":    {"item_type":"potion", "properties":{"restore_health":40}, "color":(180,40,180)},
    "gold":      {"item_type":"currency","properties":{"value":10}, "color":(220,180,40)},
    "bed_roll":  {"item_type":"bed",    "properties":{"restore_energy":1.0}, "color":(100,100,160)},
    "torch":     {"item_type":"misc",   "properties":{"light":True}, "color":(220,140,20)},
    "key":       {"item_type":"misc",   "properties":{}, "color":(200,200,50)},
}
