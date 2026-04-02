"""Schedule data model and storage."""
import json
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class RepeatType(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKLY = "weekly"
    CUSTOM = "custom"
    INTERVAL = "interval"


class ScheduleCategory(Enum):
    WATER = "water"
    MEDICINE = "medicine"
    TASK = "task"
    CUSTOM = "custom"


CATEGORY_ICONS = {
    ScheduleCategory.WATER: "\U0001F4A7",      # droplet
    ScheduleCategory.MEDICINE: "\U0001F48A",    # pill
    ScheduleCategory.TASK: "\U0001F4DD",        # memo
    ScheduleCategory.CUSTOM: "\U0000270F",      # pencil
}

CATEGORY_MESSAGES = {
    ScheduleCategory.WATER: "물 마실 시간이야!",
    ScheduleCategory.MEDICINE: "약 먹을 시간이야!",
    ScheduleCategory.TASK: "할 일이 있어!",
    ScheduleCategory.CUSTOM: "알림이야!",
}


class Schedule:
    def __init__(self, title: str, hour: int, minute: int,
                 repeat_type: RepeatType = RepeatType.DAILY,
                 custom_days: Optional[list[int]] = None,
                 interval_minutes: Optional[int] = None,
                 is_enabled: bool = True,
                 category: ScheduleCategory = ScheduleCategory.CUSTOM,
                 schedule_id: Optional[str] = None,
                 date: Optional[str] = None):
        self.id = schedule_id or str(uuid.uuid4())
        self.title = title
        self.hour = hour
        self.minute = minute
        self.repeat_type = repeat_type
        self.custom_days = custom_days or []
        self.interval_minutes = interval_minutes
        self.is_enabled = is_enabled
        self.category = category
        self.date = date  # "YYYY-MM-DD" for one-time date-specific schedules

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "title": self.title,
            "hour": self.hour,
            "minute": self.minute,
            "repeat_type": self.repeat_type.value,
            "custom_days": self.custom_days,
            "interval_minutes": self.interval_minutes,
            "is_enabled": self.is_enabled,
            "category": self.category.value,
        }
        if self.date:
            d["date"] = self.date
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        return cls(
            title=data["title"],
            hour=data["hour"],
            minute=data["minute"],
            repeat_type=RepeatType(data["repeat_type"]),
            custom_days=data.get("custom_days", []),
            interval_minutes=data.get("interval_minutes"),
            is_enabled=data.get("is_enabled", True),
            category=ScheduleCategory(data["category"]),
            schedule_id=data["id"],
            date=data.get("date"),
        )

    def should_trigger(self, now: datetime, last_triggered: Optional[datetime] = None) -> bool:
        if not self.is_enabled:
            return False

        if self.repeat_type == RepeatType.INTERVAL:
            if self.interval_minutes and last_triggered:
                return now >= last_triggered + timedelta(minutes=self.interval_minutes)
            if self.interval_minutes and not last_triggered:
                # First trigger: if we're past the start time, trigger immediately
                if now.hour > self.hour or (now.hour == self.hour and now.minute >= self.minute):
                    return True
                return False
            return False

        if now.hour != self.hour or now.minute != self.minute:
            return False

        weekday = now.isoweekday()  # 1=Mon ... 7=Sun

        if self.repeat_type == RepeatType.ONCE:
            if last_triggered is not None:
                return False
            if self.date:
                return now.strftime("%Y-%m-%d") == self.date
            return True
        elif self.repeat_type == RepeatType.DAILY:
            return True
        elif self.repeat_type == RepeatType.WEEKDAYS:
            return weekday <= 5
        elif self.repeat_type == RepeatType.WEEKLY:
            return len(self.custom_days) == 0 or weekday in self.custom_days
        elif self.repeat_type == RepeatType.CUSTOM:
            return weekday in self.custom_days
        return False


def _storage_path() -> Path:
    support_dir = Path.home() / "Library" / "Application Support" / "Codoll"
    support_dir.mkdir(parents=True, exist_ok=True)
    return support_dir / "schedules.json"


def _settings_path() -> Path:
    support_dir = Path.home() / "Library" / "Application Support" / "Codoll"
    support_dir.mkdir(parents=True, exist_ok=True)
    return support_dir / "settings.json"


def load_schedules() -> list[Schedule]:
    path = _storage_path()
    if not path.exists():
        return _create_default_schedules()
    with open(path, "r") as f:
        data = json.load(f)
    return [Schedule.from_dict(d) for d in data]


def save_schedules(schedules: list[Schedule]):
    path = _storage_path()
    with open(path, "w") as f:
        json.dump([s.to_dict() for s in schedules], f, ensure_ascii=False, indent=2)


def load_settings() -> dict:
    path = _settings_path()
    defaults = {
        "movement_mode": "fullscreen",  # "bottom" or "fullscreen"
        "movement_speed": 1.5,
        "sound_enabled": True,
        "launch_at_login": False,
    }
    if not path.exists():
        save_settings(defaults)
        return defaults
    with open(path, "r") as f:
        saved = json.load(f)
    defaults.update(saved)
    return defaults


def save_settings(settings: dict):
    path = _settings_path()
    with open(path, "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def _create_default_schedules() -> list[Schedule]:
    defaults = [
        Schedule("물 마시기", 9, 0, RepeatType.INTERVAL,
                 interval_minutes=120, category=ScheduleCategory.WATER),
        Schedule("약 먹기", 8, 30, RepeatType.DAILY,
                 category=ScheduleCategory.MEDICINE),
        Schedule("주간보고 쓰기", 17, 0, RepeatType.WEEKLY,
                 custom_days=[4], category=ScheduleCategory.TASK),
        Schedule("회의", 10, 0, RepeatType.ONCE,
                 category=ScheduleCategory.TASK, date="2026-04-10"),
    ]
    save_schedules(defaults)
    return defaults
