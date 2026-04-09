# persistence.py — JSON save / load

import json
import os
import time
import logging
import config
from world import World

logger = logging.getLogger(__name__)


def save_world(world: World, path: str = config.SAVE_FILE) -> bool:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Backup previous save
    if os.path.exists(path):
        backup = path + ".bak"
        try:
            os.replace(path, backup)
        except OSError:
            pass
    try:
        data = world.to_dict()
        data["saved_at"] = time.time()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"World saved to {path}  (time={world.game_time:.0f})")
        return True
    except Exception as ex:
        logger.error(f"Save failed: {ex}")
        return False


def load_world(path: str = config.SAVE_FILE) -> World:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Save file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    world = World.from_dict(data)
    logger.info(f"World loaded from {path}  (time={world.game_time:.0f})")
    return world


def autosave(world: World, interval_real_seconds: float = 120.0):
    """Call periodically from main loop with current real time."""
    now = time.time()
    if not hasattr(autosave, "_last"):
        autosave._last = now
    if now - autosave._last >= interval_real_seconds:
        save_world(world, config.SAVE_FILE.replace(".json", "_auto.json"))
        autosave._last = now
