"""Main Pet desktop pet application."""
import os
import sys
import shutil
import math
import random
import objc
import AppKit
import Quartz
from pathlib import Path
from Foundation import NSObject, NSMakeRect, NSTimer


def _bundle_dir():
    """Return the base directory for bundled resources (PyInstaller or dev)."""
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent

from .state import CodollState, FacingDirection
from .renderer import draw_codoll, CHAR_WIDTH, CHAR_HEIGHT, PIXEL
from .animator import CodollAnimator
from .bubble import SpeechBubble
from .schedule import ScheduleCategory, CATEGORY_MESSAGES, load_settings
from .schedule_manager import ScheduleManager
from .settings_window import SettingsWindowController


# ── Interaction messages ─────────────────────────────────────
# cherry-todo

CHEER_MESSAGES = [
    "오늘도 수고했어!",
]

AEGYO_MESSAGES = [
    ">_<",
]

DANCING_MESSAGES = [
    "우!예!예!",
]

WINKING_MESSAGES = [
    "ㅎㅎ"
]


# ── Emoji particle system ────────────────────────────────────

class Particle:
    __slots__ = ("emoji", "x", "y", "vx", "vy", "alpha", "age", "max_age")

    def __init__(self, emoji, x, y):
        self.emoji = emoji
        self.x = x
        self.y = y
        self.vx = random.uniform(-40, 40)
        self.vy = random.uniform(40, 80)
        self.alpha = 1.0
        self.age = 0.0
        self.max_age = random.uniform(1.0, 1.8)


class ParticleSystem:
    def __init__(self):
        self._particles = []

    def spawn(self, emoji, cx, cy, count=6, spread=10):
        """Spawn particles around (cx, cy)."""
        for _ in range(count):
            px = cx + random.uniform(-spread, spread)
            py = cy + random.uniform(-5, 5)
            self._particles.append(Particle(emoji, px, py))

    def update(self, dt):
        alive = []
        for p in self._particles:
            p.age += dt
            if p.age >= p.max_age:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy -= 20 * dt  # gentle gravity
            p.alpha = max(0, 1.0 - (p.age / p.max_age))
            alive.append(p)
        self._particles = alive

    @property
    def active(self):
        return len(self._particles) > 0

    def draw(self, ctx):
        if not self._particles:
            return
        font = AppKit.NSFont.systemFontOfSize_(16)
        for p in self._particles:
            attrs = {
                AppKit.NSFontAttributeName: font,
                AppKit.NSForegroundColorAttributeName:
                    AppKit.NSColor.colorWithRed_green_blue_alpha_(1, 1, 1, p.alpha),
            }
            ns_str = AppKit.NSAttributedString.alloc().initWithString_attributes_(
                p.emoji, attrs
            )
            Quartz.CGContextSaveGState(ctx)
            Quartz.CGContextSetAlpha(ctx, p.alpha)
            ns_str.drawAtPoint_(AppKit.NSMakePoint(p.x - 8, p.y - 8))
            Quartz.CGContextRestoreGState(ctx)


# ── View ─────────────────────────────────────────────────────

class CodollView(AppKit.NSView):
    """Custom view that draws the pet and handles mouse events."""

    @objc.python_method
    def initWithAnimator_bubble_particles_(self, animator, bubble, particles):
        frame = AppKit.NSScreen.mainScreen().frame()
        self = objc.super(CodollView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._animator = animator
        self._bubble = bubble
        self._particles = particles
        self._dragging = False
        self._did_double_click = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        return self

    def isFlipped(self):
        return False

    def drawRect_(self, rect):
        ctx = AppKit.NSGraphicsContext.currentContext().CGContext()
        if ctx is None:
            return

        Quartz.CGContextClearRect(ctx, rect)

        # Draw pet
        draw_codoll(
            ctx,
            self._animator.state,
            self._animator.facing,
            self._animator.frame,
            self._animator.x,
            self._animator.y,
        )

        # Draw particles
        self._particles.draw(ctx)

        # Draw bubble
        if self._bubble.opacity > 0.01:
            bubble_x = self._animator.x + CHAR_WIDTH / 2
            bubble_y = self._animator.y + CHAR_HEIGHT + 5
            self._bubble.draw(ctx, bubble_x, bubble_y)

    def hitTest_(self, point):
        """Only accept clicks on the codoll or bubble area."""
        px, py = point.x, point.y
        ax, ay = self._animator.x, self._animator.y

        if ax <= px <= ax + CHAR_WIDTH and ay <= py <= ay + CHAR_HEIGHT:
            return self

        if self._bubble.opacity > 0.01:
            bubble_x = ax + (CHAR_WIDTH - 15 * PIXEL if self._animator.facing == FacingDirection.LEFT else 15 * PIXEL)
            bubble_y = ay + CHAR_HEIGHT + 5
            if self._bubble.hit_test(px, py, bubble_x, bubble_y):
                return self

        return None

    def mouseDown_(self, event):
        loc = event.locationInWindow()
        ax, ay = self._animator.x, self._animator.y

        if self._bubble.opacity > 0.01:
            bubble_x = ax + (CHAR_WIDTH - 15 * PIXEL if self._animator.facing == FacingDirection.LEFT else 15 * PIXEL)
            bubble_y = ay + CHAR_HEIGHT + 5
            if self._bubble.hit_test(loc.x, loc.y, bubble_x, bubble_y):
                self._bubble.dismiss(completed=True)
                self._animator.trigger_happy()
                return

        on_codoll = ax <= loc.x <= ax + CHAR_WIDTH and ay <= loc.y <= ay + CHAR_HEIGHT

        if on_codoll and event.clickCount() == 2:
            self._dragging = False
            self._did_double_click = True
            delegate = AppKit.NSApp.delegate()
            if delegate:
                delegate.aegyo()
            return

        if on_codoll:
            self._dragging = True
            self._did_double_click = False
            self._drag_offset_x = loc.x - ax
            self._drag_offset_y = loc.y - ay

    def mouseDragged_(self, event):
        if self._dragging:
            loc = event.locationInWindow()
            self._animator.set_position(
                loc.x - self._drag_offset_x,
                loc.y - self._drag_offset_y,
            )

    def mouseUp_(self, event):
        if self._dragging:
            self._dragging = False
        elif self._did_double_click:
            self._did_double_click = False
        else:
            self._animator.trigger_happy()

    def rightMouseDown_(self, event):
        """Show context menu on right-click."""
        delegate = AppKit.NSApp.delegate()
        if delegate:
            menu = delegate.buildContextMenu()
            AppKit.NSMenu.popUpContextMenu_withEvent_forView_(menu, event, self)

    def acceptsFirstResponder(self):
        return True


# ── App delegate ─────────────────────────────────────────────

class CodollAppDelegate(NSObject):
    """Main application delegate."""

    @objc.python_method
    def setup(self):
        self._animator = CodollAnimator()
        self._bubble = SpeechBubble()
        self._particles = ParticleSystem()
        self._schedule_manager = ScheduleManager(on_alert=self._on_schedule_alert)
        self._settings_controller = SettingsWindowController(
            self._schedule_manager, self._animator
        )
        self._window = None
        self._codoll_view = None
        self._timer = None
        self._cheer_idx = 0
        self._aegyo_idx = 0
        self._dancing_idx = 0
        self._winking_idx = 0
        self._dblclick_mode = 0  # 0=aegyo, 1=dancing, 2=winking
        self._install_assets()
        return self

    @objc.python_method
    def _install_assets(self):
        """Copy bundled image assets to Application Support/Codoll/image/."""
        image_dir = Path.home() / "Library" / "Application Support" / "Codoll" / "image"
        image_dir.mkdir(parents=True, exist_ok=True)
        src_dir = _bundle_dir() / "codoll" / "assets" / "image"
        if src_dir.is_dir():
            for src_file in src_dir.iterdir():
                if src_file.is_file():
                    dst_file = image_dir / src_file.name
                    if not dst_file.exists():
                        shutil.copy2(src_file, dst_file)

    def applicationDidFinishLaunching_(self, notification):
        NSObject.applicationDidFinishLaunching_(self, notification) if False else None
        AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

        self._setup_window()
        self._start_animation_loop()

    @objc.python_method
    def _setup_window(self):
        screen = AppKit.NSScreen.mainScreen()
        frame = screen.frame() if screen else NSMakeRect(0, 0, 1920, 1080)

        self._window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self._window.setHasShadow_(False)
        self._window.setLevel_(AppKit.NSFloatingWindowLevel)
        self._window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
        )
        self._window.setIgnoresMouseEvents_(True)

        self._codoll_view = CodollView.alloc().initWithAnimator_bubble_particles_(
            self._animator, self._bubble, self._particles
        )
        self._window.setContentView_(self._codoll_view)
        self._window.orderFront_(None)

    @objc.python_method
    def buildContextMenu(self):
        menu = AppKit.NSMenu.alloc().init()

        # Interaction items
        for title, sel in [
            ("쓰다듬기", self.petAction_),
            ("응원받기", self.cheerAction_),
            ("낸나💖", self.junsuAction_),
        ]:
            item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                title, objc.selector(sel, signature=b"v@:@"), ""
            )
            item.setTarget_(self)
            menu.addItem_(item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        settings_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "설정...", objc.selector(self.openSettings_, signature=b"v@:@"), ""
        )
        settings_item.setTarget_(self)
        menu.addItem_(settings_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "종료", objc.selector(self.quitApp_, signature=b"v@:@"), ""
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        return menu

    @objc.python_method
    def _start_animation_loop(self):
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / 30.0,
            self,
            objc.selector(self.tick_, signature=b"v@:@"),
            None,
            True,
        )

    @objc.IBAction
    def tick_(self, timer):
        dt = 1.0 / 30.0
        self._animator.update(dt)
        self._bubble.update(dt)
        self._particles.update(dt)
        self._schedule_manager.update(dt)
        self._codoll_view.setNeedsDisplay_(True)
        self._update_mouse_passthrough()

    @objc.python_method
    def _update_mouse_passthrough(self):
        mouse_loc = AppKit.NSEvent.mouseLocation()
        window_point = self._window.convertPointFromScreen_(mouse_loc)

        ax, ay = self._animator.x, self._animator.y
        px, py = window_point.x, window_point.y

        over_codoll = (ax <= px <= ax + CHAR_WIDTH and ay <= py <= ay + CHAR_HEIGHT)

        over_bubble = False
        if not over_codoll and self._bubble.opacity > 0.01:
            bubble_x = ax + (CHAR_WIDTH - 15 * PIXEL if self._animator.facing == FacingDirection.LEFT else 15 * PIXEL)
            bubble_y = ay + CHAR_HEIGHT + 5
            over_bubble = self._bubble.hit_test(px, py, bubble_x, bubble_y)

        self._window.setIgnoresMouseEvents_(not (over_codoll or over_bubble))

    # ── Interaction actions ──────────────────────────────────

    @objc.python_method
    def _pet_center_x(self):
        if self._animator.facing == FacingDirection.LEFT:
            return self._animator.x + CHAR_WIDTH - 15 * PIXEL
        return self._animator.x + 15 * PIXEL

    @objc.python_method
    def _pet_center(self):
        return (self._pet_center_x(),
                self._animator.y + CHAR_HEIGHT / 2)

    @objc.IBAction
    def petAction_(self, sender):
        """쓰다듬기 — PETTING state with hand animation + heart particles."""
        self._animator.trigger_petting()
        cx, cy = self._pet_center()
        self._particles.spawn("\u2764\uFE0F", cx, cy + 20, count=7)

    @objc.IBAction
    def cheerAction_(self, sender):
        """응원받기 — HAPPY + star particles + rotating message."""
        self._animator.trigger_happy()
        cx, cy = self._pet_center()
        self._particles.spawn("\u2B50", cx, cy + 20, count=7)
        msg = CHEER_MESSAGES[self._cheer_idx % len(CHEER_MESSAGES)]
        self._cheer_idx += 1
        self._bubble.show_message(msg, duration=5.0)

    @objc.IBAction
    def junsuAction_(self, sender):
        """낸나💖 — JUNSU state with heart eyes + random image from image folder."""
        self._animator.trigger_junsu()
        cx, cy = self._pet_center()
        self._particles.spawn("\U0001F496", cx, cy + 20, count=8, spread=40)
        image_dir = Path.home() / "Library" / "Application Support" / "Codoll" / "image"
        images = [
            f for f in image_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp")
        ] if image_dir.is_dir() else []
        if images:
            image_path = str(random.choice(images))
            self._bubble.show_image(image_path, duration=5.0)

    @objc.python_method
    def aegyo(self):
        """더블클릭 — 애교/춤추기/윙크를 순환."""
        cx, cy = self._pet_center()
        mode = self._dblclick_mode % 3
        self._dblclick_mode += 1

        if mode == 0:
            self._animator.trigger_aegyo()
            self._particles.spawn("\U0001F352", cx, cy + 20, count=8, spread=40)
            msg = AEGYO_MESSAGES[self._aegyo_idx % len(AEGYO_MESSAGES)]
            self._aegyo_idx += 1
        elif mode == 1:
            self._animator.trigger_dancing()
            self._particles.spawn("\U0001F496", cx, cy + 20, count=8, spread=40)
            msg = DANCING_MESSAGES[self._dancing_idx % len(DANCING_MESSAGES)]
            self._dancing_idx += 1
        else:
            self._animator.trigger_winking()
            self._particles.spawn("\U0001F49D", cx, cy + 20, count=6, spread=40)
            msg = WINKING_MESSAGES[self._winking_idx % len(WINKING_MESSAGES)]
            self._winking_idx += 1

        self._bubble.show_message(msg, duration=4.0)

    # ── Schedule alerts ──────────────────────────────────────

    @objc.python_method
    def _on_schedule_alert(self, schedule):
        self._animator.trigger_alert()
        self._bubble.show(
            title=schedule.title,
            category=schedule.category,
            schedule_id=schedule.id,
            on_dismiss=self._on_bubble_dismiss,
        )
        settings = load_settings()
        if settings.get("sound_enabled", True):
            AppKit.NSSound.soundNamed_("Purr").play()

    @objc.python_method
    def _on_bubble_dismiss(self, schedule_id, completed):
        if schedule_id:
            self._schedule_manager.mark_completed(schedule_id)
        if completed:
            self._animator.trigger_happy()

    @objc.IBAction
    def openSettings_(self, sender):
        self._settings_controller.show()

    @objc.IBAction
    def quitApp_(self, sender):
        AppKit.NSApp.terminate_(None)


def main():
    app = AppKit.NSApplication.sharedApplication()
    delegate = CodollAppDelegate.alloc().init().setup()
    app.setDelegate_(delegate)
    app.run()
