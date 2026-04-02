"""Pixel-art renderer for coconut doll character (40x40 grid, 2x scale)."""
import math
import AppKit
import Quartz

from .state import CodollState, FacingDirection

# Grid and display
PIXEL = 2
GRID = 40
CHAR_WIDTH = GRID * PIXEL    # 80
CHAR_HEIGHT = GRID * PIXEL   # 80

# ── Coconut doll palette ────────────────────────────────────
OUTLINE   = (0.20, 0.14, 0.08, 1.0)
SHELL     = (0.68, 0.46, 0.26, 1.0)   # coconut brown shell
SHELL_DK  = (0.52, 0.34, 0.18, 1.0)   # darker shell accent
SHELL_LT  = (0.78, 0.56, 0.34, 1.0)   # lighter shell highlight
FACE      = (1.00, 0.96, 0.88, 1.0)   # cream face
FACE_LT   = (1.00, 0.98, 0.93, 1.0)   # lighter face highlight
BLUSH     = (1.00, 0.68, 0.68, 1.0)   # pink blush
BLACK     = (0.08, 0.06, 0.05, 1.0)
WHITE     = (1.00, 1.00, 1.00, 1.0)
LEAF_GRN  = (0.40, 0.72, 0.30, 1.0)   # leaf green
LEAF_DK   = (0.28, 0.56, 0.20, 1.0)   # dark leaf
MOUTH_COL = (0.55, 0.30, 0.18, 1.0)
PINK      = (1.00, 0.58, 0.62, 1.0)


# ── Grid helpers ─────────────────────────────────────────────

def _px(g, x, y, c):
    if 0 <= x < GRID and 0 <= y < GRID:
        g[(x, y)] = c


def _rect(g, x, y, w, h, c):
    for dy in range(h):
        for dx in range(w):
            _px(g, x + dx, y + dy, c)


def _ellipse(g, cx, cy, rx, ry, c):
    for ey in range(cy - ry, cy + ry + 1):
        for ex in range(cx - rx, cx + rx + 1):
            dx = (ex - cx) / max(rx, 0.5)
            dy = (ey - cy) / max(ry, 0.5)
            if dx * dx + dy * dy <= 1.0:
                _px(g, ex, ey, c)


def _line(g, x0, y0, x1, y1, c):
    """Bresenham line."""
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        _px(g, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def _add_outline(g):
    """Add 1px outline around all filled pixels."""
    border = set()
    for (x, y) in list(g.keys()):
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) not in g and 0 <= nx < GRID and 0 <= ny < GRID:
                border.add((nx, ny))
    for pos in border:
        g[pos] = OUTLINE


# ── Coconut doll parts (y=0 bottom, y=39 top) ──────────────

def _sq(state):
    """Vertical squash offset for sitting/sleeping."""
    if state == CodollState.SITTING:
        return -1
    if state == CodollState.SLEEPING:
        return -2
    return 0


def _body_shape(g, state, by):
    """Round coconut-shaped body: brown shell with cream face."""
    sq = _sq(state)

    # Main body - wide round coconut shape
    bcy = 14 + by + sq
    brx = 16
    bry = max(12 + sq, 9)
    _ellipse(g, 19, bcy, brx, bry, SHELL)

    # Lighter shell highlight (top-right area)
    for y in range(bcy + 2, bcy + bry - 1):
        for x in range(25, 30):
            if (x, y) in g and g[(x, y)] == SHELL:
                _px(g, x, y, SHELL_LT)

    # Face area (cream oval on front)
    face_cy = 15 + by + sq
    face_rx = 11
    face_ry = max(8 + sq, 6)
    _ellipse(g, 19, face_cy, face_rx, face_ry, FACE)

    # Face highlight (subtle lighter area)
    _ellipse(g, 18, face_cy + 2, 4, 3, FACE_LT)


def _leaf(g, state, frame, by):
    """Small leaf/sprout on top of the coconut."""
    sq = _sq(state)
    top_y = 26 + by + sq

    if state == CodollState.SLEEPING:
        # Leaf droops a bit when sleeping
        _px(g, 19, top_y, LEAF_GRN)
        _px(g, 19, top_y + 1, LEAF_GRN)
        _px(g, 18, top_y + 2, LEAF_GRN)
        _px(g, 17, top_y + 2, LEAF_DK)
        _px(g, 20, top_y + 2, LEAF_GRN)
        _px(g, 21, top_y + 2, LEAF_DK)
        return

    # Leaf sway
    sway = 0
    if state in (CodollState.WALKING, CodollState.RUNNING, CodollState.DANCING):
        sway = int(math.sin(frame * 0.3) * 1)
    elif state == CodollState.HAPPY:
        sway = int(math.sin(frame * 0.5) * 1)

    # Stem
    _px(g, 19 + sway, top_y, LEAF_DK)
    _px(g, 19 + sway, top_y + 1, LEAF_DK)

    # Left leaf
    _px(g, 18 + sway, top_y + 2, LEAF_GRN)
    _px(g, 17 + sway, top_y + 3, LEAF_GRN)
    _px(g, 16 + sway, top_y + 3, LEAF_GRN)
    _px(g, 17 + sway, top_y + 2, LEAF_DK)

    # Right leaf
    _px(g, 20 + sway, top_y + 2, LEAF_GRN)
    _px(g, 21 + sway, top_y + 3, LEAF_GRN)
    _px(g, 22 + sway, top_y + 3, LEAF_GRN)
    _px(g, 21 + sway, top_y + 2, LEAF_DK)


def _eyes(g, state, frame, by):
    """Cute dot eyes for coconut doll."""
    sq = _sq(state)
    ey = 16 + by + sq

    if state == CodollState.SLEEPING:
        # Closed eyes: gentle horizontal lines
        for x in range(14, 17):
            _px(g, x, ey, BLACK)
        for x in range(22, 25):
            _px(g, x, ey, BLACK)

    elif state in (CodollState.HAPPY, CodollState.PETTING):
        # Happy squint: ^ ^
        _px(g, 13, ey, BLACK)
        _px(g, 14, ey + 1, BLACK)
        _px(g, 15, ey + 2, BLACK)
        _px(g, 16, ey + 1, BLACK)
        _px(g, 17, ey, BLACK)

        _px(g, 22, ey, BLACK)
        _px(g, 23, ey + 1, BLACK)
        _px(g, 24, ey + 2, BLACK)
        _px(g, 25, ey + 1, BLACK)
        _px(g, 26, ey, BLACK)

    elif state == CodollState.AEGYO:
        # Aegyo: ^ ^ happy squint (same as HAPPY)
        _px(g, 13, ey, BLACK)
        _px(g, 14, ey + 1, BLACK)
        _px(g, 15, ey + 2, BLACK)
        _px(g, 16, ey + 1, BLACK)
        _px(g, 17, ey, BLACK)

        _px(g, 22, ey, BLACK)
        _px(g, 23, ey + 1, BLACK)
        _px(g, 24, ey + 2, BLACK)
        _px(g, 25, ey + 1, BLACK)
        _px(g, 26, ey, BLACK)

    elif state == CodollState.DANCING:
        # Dancing: ~ ~ wavy eyes
        _px(g, 14, ey + 1, BLACK)
        _px(g, 15, ey + 2, BLACK)
        _px(g, 16, ey + 1, BLACK)
        _px(g, 17, ey + 2, BLACK)

        _px(g, 22, ey + 1, BLACK)
        _px(g, 23, ey + 2, BLACK)
        _px(g, 24, ey + 1, BLACK)
        _px(g, 25, ey + 2, BLACK)

    elif state == CodollState.WINKING:
        # Left eye: > shape
        _px(g, 14, ey + 2, BLACK)
        _px(g, 15, ey + 1, BLACK)
        _px(g, 16, ey, BLACK)
        _px(g, 15, ey - 1, BLACK)
        _px(g, 14, ey - 2, BLACK)

        # Right eye: < shape
        _px(g, 24, ey + 2, BLACK)
        _px(g, 23, ey + 1, BLACK)
        _px(g, 22, ey, BLACK)
        _px(g, 23, ey - 1, BLACK)
        _px(g, 24, ey - 2, BLACK)

    elif state == CodollState.JUNSU:
        # Heart eyes
        HEART = (1.00, 0.30, 0.40, 1.0)
        # Left heart
        _px(g, 13, ey + 2, HEART)
        _px(g, 14, ey + 3, HEART)
        _px(g, 15, ey + 2, HEART)
        _px(g, 16, ey + 3, HEART)
        _px(g, 17, ey + 2, HEART)
        _px(g, 14, ey + 1, HEART)
        _px(g, 15, ey + 1, HEART)
        _px(g, 16, ey + 1, HEART)
        _px(g, 15, ey, HEART)
        # Right heart
        _px(g, 22, ey + 2, HEART)
        _px(g, 23, ey + 3, HEART)
        _px(g, 24, ey + 2, HEART)
        _px(g, 25, ey + 3, HEART)
        _px(g, 26, ey + 2, HEART)
        _px(g, 23, ey + 1, HEART)
        _px(g, 24, ey + 1, HEART)
        _px(g, 25, ey + 1, HEART)
        _px(g, 24, ey, HEART)

    else:
        # Default: round dot eyes with highlight
        wide = 1 if state == CodollState.ALERT else 0

        _ellipse(g, 15, ey + 1, 2, 2 + wide, BLACK)
        _px(g, 16, ey + 2 + wide, WHITE)

        _ellipse(g, 24, ey + 1, 2, 2 + wide, BLACK)
        _px(g, 25, ey + 2 + wide, WHITE)


def _nose_mouth(g, state, frame, by):
    """Small nose and cute mouth."""
    sq = _sq(state)
    ny = 13 + by + sq

    # Small dot nose (hidden for happy/aegyo)
    if state not in (CodollState.DANCING, CodollState.HAPPY, CodollState.PETTING,
                     CodollState.AEGYO, CodollState.JUNSU):
        _px(g, 19, ny + 1, MOUTH_COL)
        _px(g, 20, ny + 1, MOUTH_COL)

    if state in (CodollState.HAPPY, CodollState.PETTING, CodollState.JUNSU):
        # Dot mouth: .
        _px(g, 19, ny - 1, MOUTH_COL)
    elif state == CodollState.DANCING:
        # w-shaped mouth
        _px(g, 17, ny, MOUTH_COL)
        _px(g, 18, ny - 1, MOUTH_COL)
        _px(g, 19, ny, MOUTH_COL)
        _px(g, 20, ny - 1, MOUTH_COL)
        _px(g, 21, ny, MOUTH_COL)
    elif state == CodollState.AEGYO:
        # Dot mouth: .
        _px(g, 19, ny - 1, MOUTH_COL)
    else:
        # Simple smile (small arc)
        _px(g, 18, ny - 1, MOUTH_COL)
        _px(g, 19, ny - 2, MOUTH_COL)
        _px(g, 20, ny - 1, MOUTH_COL)


def _cheeks(g, state, by):
    """Rosy pink blush circles."""
    sq = _sq(state)
    cy = 14 + by + sq

    _ellipse(g, 10, cy, 2, 2, BLUSH)
    _ellipse(g, 28, cy, 2, 2, BLUSH)


def _zzz(g, frame, by):
    """Floating ZZZ for sleeping."""
    off = (frame * 0.05) % 3
    for i, (zx, zy, sz) in enumerate([(28, 24, 2), (30, 26, 3), (32, 28, 3)]):
        a = max(0.2, 0.7 - abs(off - i) * 0.2)
        fy = int(math.sin(frame * 0.03 + i) * 1)
        c = (0.55, 0.50, 0.40, a)
        zy2 = zy + by + fy
        for d in range(sz):
            _px(g, zx + d, zy2 + sz - 1, c)
            _px(g, zx + d, zy2, c)
            _px(g, zx + sz - 1 - d, zy2 + d, c)


def _petting_hand(g, frame, by):
    """Placeholder -- actual hand is drawn as emoji in draw_codoll."""
    pass


# ── Main draw ────────────────────────────────────────────────

def draw_codoll(ctx, state: CodollState, facing: FacingDirection, frame: int,
               x: float, y: float):
    """Draw 40x40 pixel-art coconut doll at (x, y)."""
    Quartz.CGContextSaveGState(ctx)
    Quartz.CGContextTranslateCTM(ctx, x, y)

    if facing == FacingDirection.LEFT:
        Quartz.CGContextTranslateCTM(ctx, CHAR_WIDTH, 0)
        Quartz.CGContextScaleCTM(ctx, -1, 1)

    # Dancing: tilt body + sway left-right
    if state == CodollState.DANCING:
        sway_x = math.sin(frame * 0.2) * 6
        tilt = math.sin(frame * 0.25) * 0.3
        Quartz.CGContextTranslateCTM(ctx, CHAR_WIDTH / 2 + sway_x, CHAR_HEIGHT / 4)
        Quartz.CGContextRotateCTM(ctx, tilt)
        Quartz.CGContextTranslateCTM(ctx, -CHAR_WIDTH / 2, -CHAR_HEIGHT / 4)

    # Bounce offset (in grid pixels)
    by = 0
    if state == CodollState.IDLE:
        by = int(math.sin(frame * 0.12) * 1)
    elif state == CodollState.WALKING:
        by = int(abs(math.sin(frame * 0.2)) * 2)
    elif state == CodollState.RUNNING:
        by = int(abs(math.sin(frame * 0.35)) * 3)
    elif state == CodollState.HAPPY:
        by = int(abs(math.sin(frame * 0.45)) * 4)
    elif state == CodollState.ALERT:
        by = int(math.sin(frame * 0.3) * 1)
    elif state == CodollState.PETTING:
        by = int(math.sin(frame * 0.12) * 1)
    elif state == CodollState.AEGYO:
        by = int(abs(math.sin(frame * 0.3)) * 3)
    elif state == CodollState.DANCING:
        by = int(abs(math.sin(frame * 0.4)) * 4)
    elif state == CodollState.WINKING:
        by = int(abs(math.sin(frame * 0.2)) * 2)
    elif state == CodollState.JUNSU:
        by = int(abs(math.sin(frame * 0.3)) * 3)

    # Build pixel grid
    g = {}
    _body_shape(g, state, by)
    _leaf(g, state, frame, by)
    _eyes(g, state, frame, by)
    _nose_mouth(g, state, frame, by)
    _cheeks(g, state, by)
    if state == CodollState.SLEEPING:
        _zzz(g, frame, by)

    # Auto-outline around silhouette
    _add_outline(g)

    # Render pixel grid
    Quartz.CGContextSetShouldAntialias(ctx, False)
    for (gx, gy), c in g.items():
        if 0 <= gx < GRID and 0 <= gy < GRID:
            Quartz.CGContextSetRGBFillColor(ctx, *c)
            Quartz.CGContextFillRect(
                ctx, Quartz.CGRectMake(gx * PIXEL, gy * PIXEL, PIXEL, PIXEL)
            )

    # Draw hand emoji above head for petting state
    if state == CodollState.PETTING:
        Quartz.CGContextSetShouldAntialias(ctx, True)
        sway = math.sin(frame * 0.12) * 8
        emoji_x = CHAR_WIDTH / 2 - 20 + sway
        emoji_y = 38 + by * PIXEL
        font = AppKit.NSFont.systemFontOfSize_(28)
        attrs = {AppKit.NSFontAttributeName: font}
        ns_str = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            "\U0001FAF3", attrs
        )
        ns_str.drawAtPoint_(AppKit.NSMakePoint(emoji_x, emoji_y))

    Quartz.CGContextRestoreGState(ctx)
