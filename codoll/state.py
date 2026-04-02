"""Codoll animation state machine."""
import random
from enum import Enum, auto


class CodollState(Enum):
    IDLE = auto()
    WALKING = auto()
    RUNNING = auto()
    SITTING = auto()
    SLEEPING = auto()
    ALERT = auto()
    HAPPY = auto()
    PETTING = auto()
    AEGYO = auto()
    DANCING = auto()
    WINKING = auto()
    JUNSU = auto()


class FacingDirection(Enum):
    LEFT = auto()
    RIGHT = auto()


# Duration ranges per state (min, max) in seconds
STATE_DURATIONS = {
    CodollState.IDLE: (3.0, 6.0),
    CodollState.WALKING: (3.0, 8.0),
    CodollState.RUNNING: (2.0, 4.0),
    CodollState.SITTING: (4.0, 8.0),
    CodollState.SLEEPING: (8.0, 15.0),
    CodollState.ALERT: (30.0, 30.0),
    CodollState.HAPPY: (2.0, 2.0),
    CodollState.PETTING: (3.0, 3.0),
    CodollState.AEGYO: (3.0, 3.0),
    CodollState.DANCING: (3.5, 3.5),
    CodollState.WINKING: (2.5, 2.5),
    CodollState.JUNSU: (5.0, 5.0),
}

# Probabilities for random transitions
TRANSITION_WEIGHTS = {
    CodollState.IDLE: 0.35,
    CodollState.WALKING: 0.25,
    CodollState.RUNNING: 0.15,
    CodollState.SITTING: 0.15,
    CodollState.SLEEPING: 0.10,
}


class CodollStateMachine:
    def __init__(self):
        self.current_state = CodollState.IDLE
        self.facing = FacingDirection.RIGHT
        self.state_timer = 0.0
        self.state_duration = random.uniform(*STATE_DURATIONS[CodollState.IDLE])
        self.frame_counter = 0

    def update(self, dt: float) -> bool:
        """Update timer. Returns True if state expired."""
        self.state_timer += dt
        self.frame_counter += 1
        return self.state_timer >= self.state_duration

    def transition_to_random(self):
        states = list(TRANSITION_WEIGHTS.keys())
        weights = list(TRANSITION_WEIGHTS.values())
        chosen = random.choices(states, weights=weights, k=1)[0]
        self.transition_to(chosen)

    def transition_to(self, state: CodollState):
        self.current_state = state
        self.state_timer = 0.0
        self.frame_counter = 0
        dur_range = STATE_DURATIONS[state]
        self.state_duration = random.uniform(*dur_range)
        if state in (CodollState.WALKING, CodollState.RUNNING):
            self.facing = random.choice([FacingDirection.LEFT, FacingDirection.RIGHT])
