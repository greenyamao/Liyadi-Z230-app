import json
import os
from core.database import (
    init_database, get_all_settings, get_all_schedules,
    set_setting, replace_all_schedules, DB_PATH
)

CONFIG_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

# Initialize database schema and initial migration
init_database()

def load_config() -> dict:
    """Loads all settings and schedules from SQLite database."""
    cfg = get_all_settings()
    cfg["schedules"] = get_all_schedules()
    return cfg

def save_config(cfg: dict):
    """Saves settings and schedules to SQLite database, and creates JSON backup."""
    # 1. Persist schedules to SQLite
    if "schedules" in cfg:
        replace_all_schedules(cfg["schedules"])

    # 2. Persist key-value settings to SQLite
    for k, v in cfg.items():
        if k != "schedules":
            set_setting(k, v)

    # 3. Synchronize config.json backup
    try:
        with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving config.json backup: {e}")
