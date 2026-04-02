"""Speech bubble view for schedule alerts."""
import os
import math
import AppKit
import Quartz
from Foundation import NSMakeRect, NSString, NSMutableDictionary

from .schedule import ScheduleCategory, CATEGORY_ICONS, CATEGORY_MESSAGES


BUBBLE_PADDING = 12
BUBBLE_RADIUS = 12
BUBBLE_TAIL_SIZE = 8
BUBBLE_BG = (1.0, 1.0, 1.0, 0.95)
BUBBLE_BORDER = (0.8, 0.8, 0.8, 1.0)
BUBBLE_SHADOW = (0.0, 0.0, 0.0, 0.15)

IMAGE_BUBBLE_SIZE = 140  # image display size in the bubble


class SpeechBubble:
    def __init__(self):
        self.visible = False
        self.text = ""
        self.icon = ""
        self.opacity = 0.0
        self.target_opacity = 0.0
        self.timer = 0.0
        self.duration = 30.0  # seconds
        self.category = ScheduleCategory.CUSTOM
        self.schedule_id = None
        self._on_dismiss = None
        self._image = None  # NSImage for image bubble mode

    def show(self, title: str, category: ScheduleCategory, schedule_id: str,
             on_dismiss=None):
        icon = CATEGORY_ICONS.get(category, "")
        self.text = f"{icon} {title}"
        self.icon = icon
        self.category = category
        self.schedule_id = schedule_id
        self.visible = True
        self.target_opacity = 1.0
        self.opacity = 0.0
        self.timer = 0.0
        self._on_dismiss = on_dismiss

    def show_message(self, text, duration=5.0):
        """Show a simple text bubble (not tied to a schedule)."""
        self.text = text
        self.icon = ""
        self.category = ScheduleCategory.CUSTOM
        self.schedule_id = None
        self.visible = True
        self.target_opacity = 1.0
        self.opacity = 0.0
        self.timer = 0.0
        self.duration = duration
        self._on_dismiss = None
        self._image = None

    def show_image(self, image_path, duration=5.0):
        """Show a larger bubble with an image inside."""
        img = AppKit.NSImage.alloc().initWithContentsOfFile_(image_path)
        if img is None:
            return
        self._image = img
        self.text = ""
        self.icon = ""
        self.category = ScheduleCategory.CUSTOM
        self.schedule_id = None
        self.visible = True
        self.target_opacity = 1.0
        self.opacity = 0.0
        self.timer = 0.0
        self.duration = duration
        self._on_dismiss = None

    def dismiss(self, completed=False):
        self.target_opacity = 0.0
        self.visible = False
        if self._on_dismiss:
            self._on_dismiss(self.schedule_id, completed)
        self.schedule_id = None

    def update(self, dt: float):
        if not self.visible and self.opacity <= 0:
            return

        # Fade animation
        if self.opacity < self.target_opacity:
            self.opacity = min(self.opacity + dt * 4, self.target_opacity)
        elif self.opacity > self.target_opacity:
            self.opacity = max(self.opacity - dt * 4, self.target_opacity)

        if self.visible:
            self.timer += dt
            if self.timer >= self.duration:
                self.dismiss(completed=False)

    def hit_test(self, px: float, py: float, bubble_x: float, bubble_y: float) -> bool:
        """Check if point (px, py) is inside the bubble."""
        if self.opacity <= 0:
            return False
        w, h = self._content_size()
        bw = w + BUBBLE_PADDING * 2
        bh = h + BUBBLE_PADDING * 2
        bx = bubble_x - bw / 2
        by = bubble_y
        return bx <= px <= bx + bw and by <= py <= by + bh

    def _content_size(self):
        if self._image:
            return IMAGE_BUBBLE_SIZE, IMAGE_BUBBLE_SIZE
        font = AppKit.NSFont.systemFontOfSize_(13)
        attrs = NSMutableDictionary.alloc().init()
        attrs[AppKit.NSFontAttributeName] = font
        ns_str = NSString.stringWithString_(self.text)
        size = ns_str.sizeWithAttributes_(attrs)
        return size.width, size.height

    def draw(self, ctx, center_x: float, above_y: float):
        """Draw speech bubble centered at center_x, above above_y."""
        if self.opacity <= 0.01:
            return

        Quartz.CGContextSaveGState(ctx)
        Quartz.CGContextSetAlpha(ctx, self.opacity)

        w, h = self._content_size()
        bw = w + BUBBLE_PADDING * 2
        bh = h + BUBBLE_PADDING * 2
        bx = center_x - bw / 2
        by = above_y + BUBBLE_TAIL_SIZE

        # Shadow
        Quartz.CGContextSetShadowWithColor(
            ctx,
            Quartz.CGSizeMake(0, -2),
            6,
            Quartz.CGColorCreateGenericRGB(*BUBBLE_SHADOW),
        )

        # Bubble background
        radius = BUBBLE_RADIUS + (4 if self._image else 0)
        Quartz.CGContextSetRGBFillColor(ctx, *BUBBLE_BG)
        path = Quartz.CGPathCreateMutable()
        Quartz.CGPathAddRoundedRect(
            path, None, Quartz.CGRectMake(bx, by, bw, bh),
            radius, radius
        )
        Quartz.CGContextAddPath(ctx, path)
        Quartz.CGContextFillPath(ctx)

        # Tail triangle pointing down to codoll
        tail_path = Quartz.CGPathCreateMutable()
        Quartz.CGPathMoveToPoint(tail_path, None, center_x - 6, by)
        Quartz.CGPathAddLineToPoint(tail_path, None, center_x, above_y)
        Quartz.CGPathAddLineToPoint(tail_path, None, center_x + 6, by)
        Quartz.CGPathCloseSubpath(tail_path)
        Quartz.CGContextSetRGBFillColor(ctx, *BUBBLE_BG)
        Quartz.CGContextAddPath(ctx, tail_path)
        Quartz.CGContextFillPath(ctx)

        # Remove shadow for content
        Quartz.CGContextSetShadowWithColor(ctx, Quartz.CGSizeMake(0, 0), 0, None)

        # Border
        Quartz.CGContextSetRGBStrokeColor(ctx, *BUBBLE_BORDER)
        Quartz.CGContextSetLineWidth(ctx, 1.0)
        Quartz.CGContextAddPath(ctx, path)
        Quartz.CGContextStrokePath(ctx)

        if self._image:
            # Draw image centered in bubble
            img_rect = NSMakeRect(
                bx + BUBBLE_PADDING, by + BUBBLE_PADDING,
                IMAGE_BUBBLE_SIZE, IMAGE_BUBBLE_SIZE
            )
            self._image.drawInRect_fromRect_operation_fraction_(
                img_rect, AppKit.NSZeroRect,
                AppKit.NSCompositeSourceOver, self.opacity
            )
        else:
            # Text
            font = AppKit.NSFont.systemFontOfSize_(13)
            attrs = {
                AppKit.NSFontAttributeName: font,
                AppKit.NSForegroundColorAttributeName: AppKit.NSColor.colorWithRed_green_blue_alpha_(
                    0.15, 0.15, 0.15, 1.0
                ),
            }
            ns_str = AppKit.NSAttributedString.alloc().initWithString_attributes_(
                self.text, attrs
            )
            ns_str.drawAtPoint_(AppKit.NSMakePoint(bx + BUBBLE_PADDING, by + BUBBLE_PADDING))

        Quartz.CGContextRestoreGState(ctx)
