# settings.py
import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "db_config.json")

DEFAULT_DB = {
    "DB_HOST": "127.0.0.1",
    "DB_PORT": 7586,
    "DB_NAME": "casetech",
    "DB_USER": "postgres",
    "DB_PASS": "teste55",
}

def load_db_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return DEFAULT_DB.copy()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}

    merged = DEFAULT_DB.copy()
    merged.update({k: data.get(k, merged[k]) for k in DEFAULT_DB.keys()})
    # garante tipos
    try:
        merged["DB_PORT"] = int(merged["DB_PORT"])
    except Exception:
        merged["DB_PORT"] = int(DEFAULT_DB["DB_PORT"])
    return merged

def save_db_settings(cfg: dict) -> None:
    data = DEFAULT_DB.copy()
    data.update(cfg)
    data["DB_PORT"] = int(data["DB_PORT"])
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)