import sqlite3
import json
import os
import sys
from typing import Any, Dict, List, Optional

def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_data_dir() -> str:
    app_dir = get_app_dir()
    # If portable.txt or light_data.db is present next to app, use local folder (portable mode)
    if os.path.exists(os.path.join(app_dir, "portable.txt")) or os.path.exists(os.path.join(app_dir, "light_data.db")):
        return app_dir
    
    # Otherwise use standard Windows AppData folder
    appdata = os.getenv("APPDATA")
    if appdata:
        target = os.path.join(appdata, "LiadiLight")
    else:
        target = os.path.join(os.path.expanduser("~"), ".liadilight")
    os.makedirs(target, exist_ok=True)
    return target

DB_PATH = os.path.join(get_data_dir(), "light_data.db")
CONFIG_JSON_PATH = os.path.join(get_data_dir(), "config.json")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initializes SQLite schema and migrates from config.json if needed."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Settings table (key-value store for app settings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Circadian / Sun schedules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                interval_min INTEGER NOT NULL DEFAULT 10,
                step_brightness INTEGER NOT NULL DEFAULT 5,
                step_kelvin INTEGER NOT NULL DEFAULT 200,
                target_brightness INTEGER NOT NULL DEFAULT 80,
                target_kelvin INTEGER NOT NULL DEFAULT 5600,
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        # Event logs table for auditing and tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                details TEXT
            )
        """)
        
        conn.commit()

        # Migrate from config.json if settings table is empty
        cursor.execute("SELECT COUNT(*) FROM settings")
        if cursor.fetchone()[0] == 0:
            _migrate_from_json(cursor)
            conn.commit()

def _migrate_from_json(cursor: sqlite3.Cursor):
    """Imports initial data from existing config.json if available, or uses fresh defaults."""
    default_config = {
        "device_name": "LTF_MWRGB",
        "device_mac": "12:22:33:44:D6:55",
        "last_power": True,
        "last_brightness": 1,
        "last_kelvin": 4500,
        "autostart": False,
        "minimize_to_tray": True,
        "close_to_tray": True,
        "theme": "Dark",
        "language": "en"
    }
    
    schedules = []

    if os.path.exists(CONFIG_JSON_PATH):
        try:
            with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default_config.update({k: v for k, v in data.items() if k != "schedules"})
                    if "schedules" in data and isinstance(data["schedules"], list):
                        schedules = data["schedules"]
        except Exception as e:
            print(f"Error reading config.json for SQLite migration: {e}")

    for k, v in default_config.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, json.dumps(v)))

    for s in schedules:
        cursor.execute("""
            INSERT OR REPLACE INTO schedules (
                id, name, start_time, interval_min, step_brightness, step_kelvin,
                target_brightness, target_kelvin, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s.get("id"),
            s.get("name", "Правило"),
            s.get("start_time", "12:00"),
            int(s.get("interval_min", 10)),
            int(s.get("step_brightness", 5)),
            int(s.get("step_kelvin", 200)),
            int(s.get("target_brightness", 80)),
            int(s.get("target_kelvin", 5600)),
            1 if s.get("enabled", True) else 0
        ))

# --- Public API Functions ---

def get_setting(key: str, default: Any = None) -> Any:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["value"])
    except Exception as e:
        print(f"DB get_setting error: {e}")
    return default

def set_setting(key: str, value: Any):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))
            conn.commit()
    except Exception as e:
        print(f"DB set_setting error: {e}")

def get_all_settings() -> Dict[str, Any]:
    res = {}
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            for row in cursor.fetchall():
                res[row["key"]] = json.loads(row["value"])
    except Exception as e:
        print(f"DB get_all_settings error: {e}")
    return res

def get_all_schedules() -> List[Dict[str, Any]]:
    rules = []
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedules")
            for row in cursor.fetchall():
                rules.append({
                    "id": row["id"],
                    "name": row["name"],
                    "start_time": row["start_time"],
                    "interval_min": row["interval_min"],
                    "step_brightness": row["step_brightness"],
                    "step_kelvin": row["step_kelvin"],
                    "target_brightness": row["target_brightness"],
                    "target_kelvin": row["target_kelvin"],
                    "enabled": bool(row["enabled"])
                })
    except Exception as e:
        print(f"DB get_all_schedules error: {e}")
    return rules

def replace_all_schedules(rules: List[Dict[str, Any]]):
    """Atomically replaces the entire schedule table with the provided list of rules."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules")
            for rule in rules:
                cursor.execute("""
                    INSERT INTO schedules (
                        id, name, start_time, interval_min, step_brightness, step_kelvin,
                        target_brightness, target_kelvin, enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule["id"],
                    rule["name"],
                    rule["start_time"],
                    int(rule.get("interval_min", 10)),
                    int(rule.get("step_brightness", 5)),
                    int(rule.get("step_kelvin", 200)),
                    int(rule.get("target_brightness", 80)),
                    int(rule.get("target_kelvin", 5600)),
                    1 if rule.get("enabled", True) else 0
                ))
            conn.commit()
    except Exception as e:
        print(f"DB replace_all_schedules error: {e}")

def save_schedule(rule: Dict[str, Any]):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO schedules (
                    id, name, start_time, interval_min, step_brightness, step_kelvin,
                    target_brightness, target_kelvin, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule["id"],
                rule["name"],
                rule["start_time"],
                int(rule.get("interval_min", 10)),
                int(rule.get("step_brightness", 5)),
                int(rule.get("step_kelvin", 200)),
                int(rule.get("target_brightness", 80)),
                int(rule.get("target_kelvin", 5600)),
                1 if rule.get("enabled", True) else 0
            ))
            conn.commit()
    except Exception as e:
        print(f"DB save_schedule error: {e}")

def delete_schedule(rule_id: str):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules WHERE id = ?", (rule_id,))
            conn.commit()
    except Exception as e:
        print(f"DB delete_schedule error: {e}")

def log_event(event_type: str, details: str = ""):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO event_logs (event_type, details) VALUES (?, ?)", (event_type, details))
            conn.commit()
    except Exception as e:
        print(f"DB log_event error: {e}")
