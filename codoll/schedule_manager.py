"""Schedule manager - checks schedules and triggers alerts."""
from datetime import datetime
from typing import Optional, Callable

from .schedule import Schedule, load_schedules, save_schedules, RepeatType


class ScheduleManager:
    def __init__(self, on_alert: Callable[[Schedule], None]):
        self.schedules: list[Schedule] = load_schedules()
        self.on_alert = on_alert
        self._last_check_minute: Optional[int] = None
        self._last_triggered: dict[str, datetime] = {}
        self._check_timer = 0.0

    def reload(self):
        self.schedules = load_schedules()

    def update(self, dt: float):
        self._check_timer += dt
        if self._check_timer < 10.0:  # Check every 10 seconds
            return
        self._check_timer = 0.0

        now = datetime.now()
        current_minute = now.hour * 60 + now.minute

        # Avoid duplicate triggers in the same minute (for non-interval types)
        for schedule in self.schedules:
            if not schedule.is_enabled:
                continue

            last = self._last_triggered.get(schedule.id)

            # For non-interval: skip if already triggered this minute
            if schedule.repeat_type != RepeatType.INTERVAL:
                if last and last.hour == now.hour and last.minute == now.minute:
                    continue

            if schedule.should_trigger(now, last):
                self._last_triggered[schedule.id] = now
                self.on_alert(schedule)

    def mark_completed(self, schedule_id: str):
        """Mark a schedule alert as completed/dismissed."""
        self._last_triggered[schedule_id] = datetime.now()

    def add_schedule(self, schedule: Schedule):
        self.schedules.append(schedule)
        save_schedules(self.schedules)

    def remove_schedule(self, schedule_id: str):
        self.schedules = [s for s in self.schedules if s.id != schedule_id]
        save_schedules(self.schedules)

    def update_schedule(self, schedule: Schedule):
        for i, s in enumerate(self.schedules):
            if s.id == schedule.id:
                self.schedules[i] = schedule
                break
        save_schedules(self.schedules)

    def save(self):
        save_schedules(self.schedules)
