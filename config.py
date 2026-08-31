"""
Smjrifle Desktop Reminder - Configuration & Wellness Engine
Cross-platform persistence, multi-reminder management, character selection, and daily streak tracker.
Licensed under MIT License - Copyright (c) 2026 Smjrifle.
"""

import json
import os
import sys
import uuid
import random
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

APP_NAME = "Smjrifle Desktop Reminder"
APP_DIR_NAME = "SmjrifleReminder"

AVAILABLE_CHARACTERS = [
    {
        "id": "tennis",
        "name": "Hydration Athlete (Tennis)",
        "tag": "Original Pixel Art",
        "description": "Authentic hand-drawn pixel tennis athlete in yellow visor walking 4 steps and drinking water from bottle.",
        "icon": "🎾",
    },
    {
        "id": "striker",
        "name": "Striker #7 (CR7 Tribute)",
        "tag": "Football Legend",
        "description": "Inspired by Cristiano Ronaldo in an iconic #7 red & white kit walking and drinking water.",
        "icon": "⚽",
    },
]

DEFAULT_REMINDERS = [
    {
        "id": "hydration",
        "title": "Hydration Time",
        "message": "Time to stay hydrated! Take a refreshing drink of water.",
        "icon": "💧",
        "category": "Hydration",
        "enabled": True,
        "interval_minutes": 30,
    },
    {
        "id": "posture",
        "title": "Posture Check",
        "message": "Straighten your spine, roll your shoulders back, and relax your neck.",
        "icon": "🧘",
        "category": "Ergonomics",
        "enabled": True,
        "interval_minutes": 45,
    },
    {
        "id": "eyes",
        "title": "20-20-20 Eye Break",
        "message": "Look at an object 20 feet away for 20 seconds to ease eye strain.",
        "icon": "👀",
        "category": "Vision",
        "enabled": True,
        "interval_minutes": 20,
    },
    {
        "id": "movement",
        "title": "Quick Stretch & Walk",
        "message": "Stand up, stretch your body, or take a quick 1-minute walk.",
        "icon": "🚶",
        "category": "Activity",
        "enabled": True,
        "interval_minutes": 60,
    },
    {
        "id": "mindfulness",
        "title": "Mindful Breath",
        "message": "Take a slow deep breath in... hold for 3 seconds... and exhale slowly.",
        "icon": "🌬️",
        "category": "Mindfulness",
        "enabled": True,
        "interval_minutes": 90,
    },
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 2,
    "app_name": APP_NAME,
    "active_character": "tennis",
    "interval_seconds": 30 * 60,  # 30 minutes
    "snooze_seconds": 10 * 60,   # 10 minutes
    "rotation_mode": "cycle",    # "cycle" or "random"
    "position_mode": "auto",     # "auto", "top-right", "bottom-right", "top-left", "bottom-left", "center"
    "sound_enabled": True,
    "show_in_dock": True,
    "theme": "dark_acrylic",
    "stats": {
        "today_date": str(datetime.date.today()),
        "breaks_completed_today": 0,
        "total_breaks_completed": 0,
        "streak_days": 1,
        "last_active_date": str(datetime.date.today()),
    },
    "reminders": DEFAULT_REMINDERS,
}


def get_config_dir() -> Path:
    """Returns the platform-standard configuration directory for Smjrifle Desktop Reminder."""
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library" / "Application Support" / APP_DIR_NAME
    elif sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        base = Path(appdata) / APP_DIR_NAME if appdata else home / f".{APP_DIR_NAME.lower()}"
    else:  # Linux / Unix
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        base = Path(xdg_config) / APP_DIR_NAME.lower() if xdg_config else home / ".config" / APP_DIR_NAME.lower()

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_file_path() -> Path:
    """Returns the full path to settings.json."""
    return get_config_dir() / "settings.json"


class SmjrifleConfig:
    def __init__(self):
        self.file_path = get_config_file_path()
        self.data: Dict[str, Any] = {}
        self.current_cycle_index = 0
        self.load()
        self._check_daily_reset()

    def load(self) -> None:
        """Loads configuration from JSON file or initializes defaults."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data = {**DEFAULT_CONFIG, **loaded}
                    if not isinstance(self.data.get("reminders"), list) or len(self.data["reminders"]) == 0:
                        self.data["reminders"] = [dict(r) for r in DEFAULT_REMINDERS]
                    return
            except Exception as e:
                print(f"[Smjrifle Reminder] Warning: Failed to load config from {self.file_path}: {e}")

        self.data = json.loads(json.dumps(DEFAULT_CONFIG))
        self.save()

    def save(self) -> None:
        """Saves current configuration to JSON file."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Smjrifle Reminder] Warning: Failed to save config to {self.file_path}: {e}")

    def _check_daily_reset(self) -> None:
        """Checks and resets daily stats at midnight while tracking consecutive streaks."""
        stats = self.data.setdefault("stats", dict(DEFAULT_CONFIG["stats"]))
        today_str = str(datetime.date.today())
        last_date_str = stats.get("today_date", today_str)

        if last_date_str != today_str:
            try:
                last_d = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
                today_d = datetime.date.today()
                diff = (today_d - last_d).days
                if diff == 1:
                    stats["streak_days"] = stats.get("streak_days", 1) + 1
                elif diff > 1:
                    stats["streak_days"] = 1
            except Exception:
                stats["streak_days"] = 1

            stats["today_date"] = today_str
            stats["breaks_completed_today"] = 0
            self.save()

    def log_completed_break(self) -> int:
        """Increments today's completed break count and total count."""
        self._check_daily_reset()
        stats = self.data["stats"]
        stats["breaks_completed_today"] = stats.get("breaks_completed_today", 0) + 1
        stats["total_breaks_completed"] = stats.get("total_breaks_completed", 0) + 1
        self.save()
        return stats["breaks_completed_today"]

    @property
    def stats(self) -> Dict[str, Any]:
        self._check_daily_reset()
        return self.data.get("stats", DEFAULT_CONFIG["stats"])

    @property
    def active_character(self) -> str:
        return self.data.get("active_character", "tennis")

    @active_character.setter
    def active_character(self, value: str):
        valid = [c["id"] for c in AVAILABLE_CHARACTERS]
        if value in valid:
            self.data["active_character"] = value
            self.save()

    @property
    def interval_seconds(self) -> int:
        return int(self.data.get("interval_seconds", 30 * 60))

    @interval_seconds.setter
    def interval_seconds(self, value: int):
        self.data["interval_seconds"] = max(5, int(value))

    @property
    def snooze_seconds(self) -> int:
        return int(self.data.get("snooze_seconds", 10 * 60))

    @snooze_seconds.setter
    def snooze_seconds(self, value: int):
        self.data["snooze_seconds"] = max(60, int(value))

    @property
    def rotation_mode(self) -> str:
        return self.data.get("rotation_mode", "cycle")

    @rotation_mode.setter
    def rotation_mode(self, value: str):
        self.data["rotation_mode"] = value if value in ("cycle", "random") else "cycle"

    @property
    def position_mode(self) -> str:
        return self.data.get("position_mode", "auto")

    @position_mode.setter
    def position_mode(self, value: str):
        valid = ("auto", "top-right", "bottom-right", "top-left", "bottom-left", "center")
        self.data["position_mode"] = value if value in valid else "auto"

    @property
    def sound_enabled(self) -> bool:
        return bool(self.data.get("sound_enabled", True))

    @sound_enabled.setter
    def sound_enabled(self, value: bool):
        self.data["sound_enabled"] = bool(value)
        self.save()

    @property
    def show_in_dock(self) -> bool:
        return bool(self.data.get("show_in_dock", True))

    @show_in_dock.setter
    def show_in_dock(self, value: bool):
        self.data["show_in_dock"] = bool(value)
        self.save()

    @property
    def reminders(self) -> List[Dict[str, Any]]:
        return self.data.get("reminders", [])

    def get_active_reminders(self) -> List[Dict[str, Any]]:
        active = [r for r in self.reminders if r.get("enabled", True)]
        return active if active else self.reminders

    def get_reminder_by_id(self, rem_id: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self.reminders if r.get("id") == rem_id), None)

    def get_reminder_interval_seconds(self, reminder: Dict[str, Any]) -> int:
        """Each reminder can run on its own cadence; falls back to the
        global default interval for reminders saved before this existed."""
        minutes = reminder.get("interval_minutes", self.interval_seconds // 60)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = self.interval_seconds // 60
        return max(60, minutes * 60)

    def get_next_reminder(self) -> Dict[str, Any]:
        """Returns the next reminder according to the active rotation mode."""
        active = self.get_active_reminders()
        if not active:
            return DEFAULT_REMINDERS[0]

        if self.rotation_mode == "random":
            return random.choice(active)

        self.current_cycle_index = self.current_cycle_index % len(active)
        reminder = active[self.current_cycle_index]
        self.current_cycle_index = (self.current_cycle_index + 1) % len(active)
        return reminder

    def add_reminder(self, title: str, message: str, icon: str = "💧", category: str = "Custom",
                      enabled: bool = True, interval_minutes: int = 30) -> Dict[str, Any]:
        new_item = {
            "id": str(uuid.uuid4())[:8],
            "title": title.strip() or "Custom Reminder",
            "message": message.strip() or "Take a moment for your health & wellness!",
            "icon": icon.strip() or "💧",
            "category": category.strip() or "Custom",
            "enabled": enabled,
            "interval_minutes": max(1, int(interval_minutes)),
        }
        self.data.setdefault("reminders", []).append(new_item)
        self.save()
        return new_item

    def update_reminder(self, rem_id: str, title: str, message: str, icon: str, category: str,
                         enabled: bool, interval_minutes: int) -> bool:
        for r in self.reminders:
            if r.get("id") == rem_id:
                r["title"] = title.strip()
                r["message"] = message.strip()
                r["icon"] = icon.strip()
                r["category"] = category.strip() or "Custom"
                r["enabled"] = enabled
                r["interval_minutes"] = max(1, int(interval_minutes))
                self.save()
                return True
        return False

    def delete_reminder(self, rem_id: str) -> bool:
        initial_len = len(self.reminders)
        self.data["reminders"] = [r for r in self.reminders if r.get("id") != rem_id]
        if len(self.data["reminders"]) < initial_len:
            if not self.data["reminders"]:
                self.data["reminders"] = [dict(DEFAULT_REMINDERS[0])]
            self.save()
            return True
        return False

    def reset_reminders_to_default(self) -> None:
        self.data["reminders"] = [dict(r) for r in DEFAULT_REMINDERS]
        self.save()
