"""Codoll position and animation controller."""
import random
import AppKit

from .state import CodollStateMachine, CodollState, FacingDirection
from .schedule import load_settings


class CodollAnimator:
    def __init__(self):
        self.state_machine = CodollStateMachine()
        self.x = 400.0
        self.y = 40.0
        self.target_x = None  # For alert movement
        self.target_y = None

        screen = AppKit.NSScreen.mainScreen()
        if screen:
            frame = screen.frame()
            self.screen_width = frame.size.width
            self.screen_height = frame.size.height
        else:
            self.screen_width = 1920
            self.screen_height = 1080

        self.settings = load_settings()
        self._walking_speed = 30.0
        self._running_speed = 80.0

    def reload_settings(self):
        self.settings = load_settings()

    @property
    def state(self) -> CodollState:
        return self.state_machine.current_state

    @property
    def facing(self) -> FacingDirection:
        return self.state_machine.facing

    @property
    def frame(self) -> int:
        return self.state_machine.frame_counter

    def update(self, dt: float):
        expired = self.state_machine.update(dt)

        speed_mult = self.settings.get("movement_speed", 1.0)
        state = self.state_machine.current_state

        # Move towards target (alert)
        if self.target_x is not None:
            dx = self.target_x - self.x
            if abs(dx) > 2:
                self.x += (dx * 0.05)
                self.state_machine.facing = (
                    FacingDirection.RIGHT if dx > 0 else FacingDirection.LEFT
                )
            else:
                self.target_x = None

        if self.target_y is not None:
            dy = self.target_y - self.y
            if abs(dy) > 2:
                self.y += (dy * 0.05)
            else:
                self.target_y = None

        # Movement based on state
        if state == CodollState.WALKING:
            speed = self._walking_speed * speed_mult
            if self.state_machine.facing == FacingDirection.RIGHT:
                self.x += speed * dt
            else:
                self.x -= speed * dt

        elif state == CodollState.RUNNING:
            speed = self._running_speed * speed_mult
            if self.state_machine.facing == FacingDirection.RIGHT:
                self.x += speed * dt
            else:
                self.x -= speed * dt

        # Boundary checks
        margin = 64
        mode = self.settings.get("movement_mode", "bottom")

        if self.x < margin:
            self.x = margin
            self.state_machine.facing = FacingDirection.RIGHT
        elif self.x > self.screen_width - margin:
            self.x = self.screen_width - margin
            self.state_machine.facing = FacingDirection.LEFT

        if mode == "bottom":
            self.y = max(20, min(self.y, 100))
        else:
            self.y = max(20, min(self.y, self.screen_height - 100))

        # Transition if state expired
        if expired and state not in (CodollState.ALERT, CodollState.HAPPY,
                                     CodollState.PETTING,
                                     CodollState.AEGYO, CodollState.DANCING,
                                     CodollState.WINKING, CodollState.JUNSU):
            self.state_machine.transition_to_random()
        elif expired and state in (CodollState.HAPPY, CodollState.PETTING,
                                   CodollState.AEGYO,
                                   CodollState.DANCING, CodollState.WINKING,
                                   CodollState.JUNSU):
            self.state_machine.transition_to_random()

    def trigger_alert(self):
        """Move towards center and enter alert state."""
        self.state_machine.transition_to(CodollState.ALERT)
        center_x = self.screen_width / 2
        self.target_x = center_x + random.uniform(-100, 100)
        mode = self.settings.get("movement_mode", "bottom")
        if mode == "fullscreen":
            self.target_y = self.screen_height / 3
        else:
            self.target_y = 40

    def trigger_happy(self):
        self.state_machine.transition_to(CodollState.HAPPY)

    def trigger_petting(self):
        self.state_machine.transition_to(CodollState.PETTING)

    def trigger_aegyo(self):
        self.state_machine.transition_to(CodollState.AEGYO)

    def trigger_dancing(self):
        self.state_machine.transition_to(CodollState.DANCING)

    def trigger_winking(self):
        self.state_machine.transition_to(CodollState.WINKING)

    def trigger_junsu(self):
        self.state_machine.transition_to(CodollState.JUNSU)

    def set_position(self, x: float, y: float):
        self.x = x
        self.y = y
