"""Settings window with schedule management and codoll settings."""
import AppKit
import objc
from datetime import datetime
from Foundation import NSObject, NSMakeRect, NSMakeSize

from .schedule import (
    Schedule, ScheduleCategory, RepeatType, CATEGORY_ICONS,
    load_schedules, save_schedules, load_settings, save_settings,
)


REPEAT_TYPE_LABELS = {
    RepeatType.ONCE: "한 번",
    RepeatType.DAILY: "매일",
    RepeatType.WEEKDAYS: "평일",
    RepeatType.WEEKLY: "매주",
    RepeatType.CUSTOM: "커스텀",
    RepeatType.INTERVAL: "간격 반복",
}

CATEGORY_LABELS = {
    ScheduleCategory.WATER: f"{CATEGORY_ICONS[ScheduleCategory.WATER]} 물 마시기",
    ScheduleCategory.MEDICINE: f"{CATEGORY_ICONS[ScheduleCategory.MEDICINE]} 약 먹기",
    ScheduleCategory.TASK: f"{CATEGORY_ICONS[ScheduleCategory.TASK]} 할 일",
    ScheduleCategory.CUSTOM: f"{CATEGORY_ICONS[ScheduleCategory.CUSTOM]} 커스텀",
}

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

# Ordered lists for popup cell indices
CATS = list(ScheduleCategory)
REPS = list(RepeatType)


# ── Module-level ObjC callback target ────────────────────────

_callback_store = {}


class _ActionTarget(NSObject):
    """Reusable button action target that calls a stored Python callback."""

    @objc.python_method
    def initWithCallback_(self, callback):
        self = objc.super(_ActionTarget, self).init()
        if self is None:
            return None
        _callback_store[id(self)] = callback
        return self

    @objc.IBAction
    def perform_(self, sender):
        cb = _callback_store.get(id(self))
        if cb:
            cb()

    def dealloc(self):
        _callback_store.pop(id(self), None)
        objc.super(_ActionTarget, self).dealloc()


def _make_target(callback):
    """Create an _ActionTarget wired to the given callback."""
    return _ActionTarget.alloc().initWithCallback_(callback)


class SettingsWindowDelegate(NSObject):
    """Restore accessory policy when settings window closes."""

    @objc.python_method
    def init(self):
        self = objc.super(SettingsWindowDelegate, self).init()
        return self

    def windowWillClose_(self, notification):
        AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)


# ── Settings window ──────────────────────────────────────────

class SettingsWindowController:
    def __init__(self, schedule_manager, animator):
        self.schedule_manager = schedule_manager
        self.animator = animator
        self.window = None
        self._table = None
        self._table_delegate = None
        self._targets = []

    def show(self):
        if self.window and self.window.isVisible():
            self.window.makeKeyAndOrderFront_(None)
            AppKit.NSApp.activateIgnoringOtherApps_(True)
            return

        self._targets = []

        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(200, 200, 860, 480),
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskClosable
            | AppKit.NSWindowStyleMaskResizable,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("설정")
        self.window.setReleasedWhenClosed_(False)
        self.window.setMinSize_(NSMakeSize(820, 400))
        self.window.center()

        tab_view = AppKit.NSTabView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 860, 480)
        )

        # Schedule tab (repeating)
        schedule_tab = AppKit.NSTabViewItem.alloc().initWithIdentifier_("schedule")
        schedule_tab.setLabel_("반복 스케줄")
        schedule_tab.setView_(self._build_schedule_tab())
        tab_view.addTabViewItem_(schedule_tab)

        # Date schedule tab (plain text)
        date_tab = AppKit.NSTabViewItem.alloc().initWithIdentifier_("date_schedule")
        date_tab.setLabel_("날짜 일정")
        date_tab.setView_(self._build_date_schedule_tab())
        tab_view.addTabViewItem_(date_tab)

        # Codoll tab
        codoll_tab = AppKit.NSTabViewItem.alloc().initWithIdentifier_("codoll")
        codoll_tab.setLabel_("햄스터")
        codoll_tab.setView_(self._build_codoll_tab())
        tab_view.addTabViewItem_(codoll_tab)

        # General tab
        general_tab = AppKit.NSTabViewItem.alloc().initWithIdentifier_("general")
        general_tab.setLabel_("일반")
        general_tab.setView_(self._build_general_tab())
        tab_view.addTabViewItem_(general_tab)

        self.window.contentView().addSubview_(tab_view)

        # Restore accessory policy when settings window closes
        self._window_delegate = SettingsWindowDelegate.alloc().init()
        self.window.setDelegate_(self._window_delegate)

        self.window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
        self._setup_main_menu()
        AppKit.NSApp.activateIgnoringOtherApps_(True)

    def _setup_main_menu(self):
        """Create a minimal main menu with Edit menu for ⌘C/⌘V support."""
        main_menu = AppKit.NSMenu.alloc().initWithTitle_("MainMenu")

        # App menu (required)
        app_menu_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Codoll", None, ""
        )
        app_menu = AppKit.NSMenu.alloc().initWithTitle_("Codoll")
        app_menu_item.setSubmenu_(app_menu)
        main_menu.addItem_(app_menu_item)

        # Edit menu
        edit_menu_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "편집", None, ""
        )
        edit_menu = AppKit.NSMenu.alloc().initWithTitle_("편집")

        undo = edit_menu.addItemWithTitle_action_keyEquivalent_("실행 취소", "undo:", "z")
        redo = edit_menu.addItemWithTitle_action_keyEquivalent_("다시 실행", "redo:", "Z")
        edit_menu.addItem_(AppKit.NSMenuItem.separatorItem())
        edit_menu.addItemWithTitle_action_keyEquivalent_("잘라내기", "cut:", "x")
        edit_menu.addItemWithTitle_action_keyEquivalent_("복사", "copy:", "c")
        edit_menu.addItemWithTitle_action_keyEquivalent_("붙여넣기", "paste:", "v")
        edit_menu.addItem_(AppKit.NSMenuItem.separatorItem())
        edit_menu.addItemWithTitle_action_keyEquivalent_("모두 선택", "selectAll:", "a")

        edit_menu_item.setSubmenu_(edit_menu)
        main_menu.addItem_(edit_menu_item)

        AppKit.NSApp.setMainMenu_(main_menu)

    # ── Schedule tab (inline-editable table) ─────────────────

    def _build_schedule_tab(self):
        view = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 840, 430))

        scroll = AppKit.NSScrollView.alloc().initWithFrame_(
            NSMakeRect(15, 50, 820, 340)
        )
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(AppKit.NSBezelBorder)
        scroll.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
        )

        table = AppKit.NSTableView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 800, 340)
        )
        self._table = table

        # ── Columns ──────────────────────────────────────────
        # 1) enabled – checkbox
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("enabled")
        col.headerCell().setStringValue_("활성")
        col.setWidth_(36)
        col.setEditable_(True)
        cell = AppKit.NSButtonCell.alloc().init()
        cell.setButtonType_(AppKit.NSSwitchButton)
        cell.setTitle_("")
        col.setDataCell_(cell)
        table.addTableColumn_(col)

        # 2) category – popup
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("category")
        col.headerCell().setStringValue_("분류")
        col.setWidth_(90)
        col.setEditable_(True)
        cell = AppKit.NSPopUpButtonCell.alloc().init()
        cell.setBordered_(False)
        cell.setControlSize_(AppKit.NSControlSizeSmall)
        cell.setFont_(AppKit.NSFont.systemFontOfSize_(AppKit.NSFont.smallSystemFontSize()))
        for c in CATS:
            cell.addItemWithTitle_(CATEGORY_LABELS[c])
        col.setDataCell_(cell)
        table.addTableColumn_(col)

        # 3) title – editable text
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("title")
        col.headerCell().setStringValue_("제목")
        col.setWidth_(130)
        col.setEditable_(True)
        col.dataCell().setEditable_(True)
        table.addTableColumn_(col)

        # 4) time – editable text (HH:MM)
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("time")
        col.headerCell().setStringValue_("시간")
        col.setWidth_(55)
        col.setEditable_(True)
        col.dataCell().setEditable_(True)
        table.addTableColumn_(col)

        # 5) repeat – popup
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("repeat")
        col.headerCell().setStringValue_("반복")
        col.setWidth_(90)
        col.setEditable_(True)
        cell = AppKit.NSPopUpButtonCell.alloc().init()
        cell.setBordered_(False)
        cell.setControlSize_(AppKit.NSControlSizeSmall)
        cell.setFont_(AppKit.NSFont.systemFontOfSize_(AppKit.NSFont.smallSystemFontSize()))
        for r in REPS:
            cell.addItemWithTitle_(REPEAT_TYPE_LABELS[r])
        col.setDataCell_(cell)
        table.addTableColumn_(col)

        # 6) days – editable text (요일 선택, e.g. "월수금" or "목")
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("days")
        col.headerCell().setStringValue_("요일")
        col.setWidth_(70)
        col.setEditable_(True)
        col.dataCell().setEditable_(True)
        col.dataCell().setPlaceholderString_("월화수...")
        table.addTableColumn_(col)

        # 7) date – editable text (YYYY-MM-DD, for one-time schedules)
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("date")
        col.headerCell().setStringValue_("날짜")
        col.setWidth_(85)
        col.setEditable_(True)
        col.dataCell().setEditable_(True)
        table.addTableColumn_(col)

        # 8) interval – editable text (minutes, for interval repeat)
        col = AppKit.NSTableColumn.alloc().initWithIdentifier_("interval")
        col.headerCell().setStringValue_("간격(분)")
        col.setWidth_(55)
        col.setEditable_(True)
        col.dataCell().setEditable_(True)
        table.addTableColumn_(col)

        # ── Delegate / DataSource ────────────────────────────
        self._table_delegate = ScheduleTableDelegate.alloc().initWithManager_controller_(
            self.schedule_manager, self
        )
        table.setDelegate_(self._table_delegate)
        table.setDataSource_(self._table_delegate)
        table.setRowHeight_(24)

        scroll.setDocumentView_(table)
        view.addSubview_(scroll)

        # ── Buttons: 추가 / 삭제 / 저장 ─────────────────────
        add_btn = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(15, 12, 80, 28))
        add_btn.setTitle_("추가")
        add_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        add_btn.setTarget_(self._table_delegate)
        add_btn.setAction_(objc.selector(self._table_delegate.addSchedule_, signature=b"v@:@"))
        view.addSubview_(add_btn)

        del_btn = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(100, 12, 80, 28))
        del_btn.setTitle_("삭제")
        del_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        del_btn.setTarget_(self._table_delegate)
        del_btn.setAction_(objc.selector(self._table_delegate.removeSchedule_, signature=b"v@:@"))
        view.addSubview_(del_btn)

        save_target = _make_target(self._save_schedules)
        self._targets.append(save_target)
        save_btn = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(720, 12, 100, 28))
        save_btn.setTitle_("저장")
        save_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        save_btn.setTarget_(save_target)
        save_btn.setAction_(objc.selector(save_target.perform_, signature=b"v@:@"))
        view.addSubview_(save_btn)

        return view

    def _save_schedules(self):
        self.schedule_manager.save()

    # ── Date schedule tab (plain text) ───────────────────────

    def _build_date_schedule_tab(self):
        view = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 560, 430))

        # Hint labels
        hint1 = AppKit.NSTextField.labelWithString_(
            "#날짜 아래에 일정 입력  |  시간: \"14:30 제목\" 또는 \"14 제목\"  |  생략 시 09:00"
        )
        hint1.setFrame_(NSMakeRect(15, 400, 540, 16))
        hint1.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        hint1.setFont_(AppKit.NSFont.systemFontOfSize_(11))
        view.addSubview_(hint1)

        # Text view in scroll view
        scroll = AppKit.NSScrollView.alloc().initWithFrame_(
            NSMakeRect(15, 50, 540, 345)
        )
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(AppKit.NSBezelBorder)
        scroll.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
        )

        text_view = AppKit.NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 520, 345)
        )
        text_view.setFont_(AppKit.NSFont.monospacedSystemFontOfSize_weight_(13, 0))
        text_view.setAutoresizingMask_(AppKit.NSViewWidthSizable)
        text_view.setRichText_(False)
        text_view.setUsesFontPanel_(False)
        text_view.setAllowsUndo_(True)
        text_view.textContainer().setWidthTracksTextView_(True)
        self._date_text_view = text_view

        # Load existing date schedules into text
        text_view.setString_(self._date_schedules_to_text())

        scroll.setDocumentView_(text_view)
        view.addSubview_(scroll)

        # Save button
        save_target = _make_target(self._save_date_schedules)
        self._targets.append(save_target)
        save_btn = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(440, 12, 100, 28))
        save_btn.setTitle_("저장")
        save_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        save_btn.setTarget_(save_target)
        save_btn.setAction_(objc.selector(save_target.perform_, signature=b"v@:@"))
        view.addSubview_(save_btn)

        return view

    def _date_schedules_to_text(self):
        """Convert existing date-specific (ONCE+date) schedules to plain text."""
        date_scheds = [
            s for s in self.schedule_manager.schedules
            if s.repeat_type == RepeatType.ONCE and s.date
        ]
        # Group by date
        by_date = {}
        for s in date_scheds:
            by_date.setdefault(s.date, []).append(s)

        lines = []
        for date in sorted(by_date.keys()):
            lines.append(f"#{date}")
            for s in by_date[date]:
                if s.hour == 9 and s.minute == 0:
                    lines.append(s.title)
                else:
                    lines.append(f"{s.hour:02d}:{s.minute:02d} {s.title}")
        return "\n".join(lines)

    def _save_date_schedules(self):
        """Parse text → replace all date-specific schedules."""
        text = self._date_text_view.string()

        # Remove old date-specific schedules
        self.schedule_manager.schedules = [
            s for s in self.schedule_manager.schedules
            if not (s.repeat_type == RepeatType.ONCE and s.date)
        ]

        # Parse new ones
        current_date = None
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                current_date = _parse_date_header(line[1:].strip())
                continue
            if current_date is None:
                continue
            hour, minute, title = _parse_date_entry(line)
            sched = Schedule(
                title=title, hour=hour, minute=minute,
                repeat_type=RepeatType.ONCE,
                category=ScheduleCategory.TASK,
                date=current_date,
            )
            self.schedule_manager.schedules.append(sched)

        self.schedule_manager.save()

    # ── Codoll (hamster) tab ─────────────────────────────────

    def _build_codoll_tab(self):
        view = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 560, 430))
        settings = load_settings()

        y = 370

        label = AppKit.NSTextField.labelWithString_("활동 범위:")
        label.setFrame_(NSMakeRect(20, y, 100, 20))
        view.addSubview_(label)

        self._mode_popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(130, y - 2, 200, 26), False
        )
        self._mode_popup.addItemsWithTitles_(["화면 하단만", "화면 전체"])
        if settings.get("movement_mode") == "fullscreen":
            self._mode_popup.selectItemAtIndex_(1)
        else:
            self._mode_popup.selectItemAtIndex_(0)
        view.addSubview_(self._mode_popup)

        y -= 50

        label2 = AppKit.NSTextField.labelWithString_("이동 속도:")
        label2.setFrame_(NSMakeRect(20, y, 100, 20))
        view.addSubview_(label2)

        self._speed_slider = AppKit.NSSlider.alloc().initWithFrame_(
            NSMakeRect(130, y, 200, 26)
        )
        self._speed_slider.setMinValue_(0.3)
        self._speed_slider.setMaxValue_(3.0)
        self._speed_slider.setDoubleValue_(settings.get("movement_speed", 1.0))
        self._speed_slider.setContinuous_(True)

        slider_target = _make_target(self._on_speed_slider_changed)
        self._targets.append(slider_target)
        self._speed_slider.setTarget_(slider_target)
        self._speed_slider.setAction_(objc.selector(slider_target.perform_, signature=b"v@:@"))
        view.addSubview_(self._speed_slider)

        self._speed_label = AppKit.NSTextField.labelWithString_(
            f"{settings.get('movement_speed', 1.0):.1f}x"
        )
        self._speed_label.setFrame_(NSMakeRect(340, y, 50, 20))
        view.addSubview_(self._speed_label)

        y -= 60

        save_btn = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 120, 32))
        save_btn.setTitle_("저장")
        save_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)

        target = _make_target(self._save_codoll_settings)
        self._targets.append(target)
        save_btn.setTarget_(target)
        save_btn.setAction_(objc.selector(target.perform_, signature=b"v@:@"))
        view.addSubview_(save_btn)

        return view

    def _on_speed_slider_changed(self):
        speed = self._speed_slider.doubleValue()
        self._speed_label.setStringValue_(f"{speed:.1f}x")

    def _save_codoll_settings(self):
        mode_idx = self._mode_popup.indexOfSelectedItem()
        mode = "fullscreen" if mode_idx == 1 else "bottom"
        speed = self._speed_slider.doubleValue()

        settings = load_settings()
        settings["movement_mode"] = mode
        settings["movement_speed"] = round(speed, 1)
        save_settings(settings)

        self._speed_label.setStringValue_(f"{speed:.1f}x")
        self.animator.reload_settings()

    # ── General tab ──────────────────────────────────────────

    def _build_general_tab(self):
        view = AppKit.NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 560, 430))
        settings = load_settings()

        y = 370

        self._sound_check = AppKit.NSButton.alloc().initWithFrame_(
            NSMakeRect(20, y, 250, 20)
        )
        self._sound_check.setButtonType_(AppKit.NSSwitchButton)
        self._sound_check.setTitle_("알림 사운드")
        self._sound_check.setState_(
            AppKit.NSControlStateValueOn if settings.get("sound_enabled", True)
            else AppKit.NSControlStateValueOff
        )
        view.addSubview_(self._sound_check)

        y -= 50

        save_btn = AppKit.NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 120, 32))
        save_btn.setTitle_("저장")
        save_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)

        target = _make_target(self._save_general_settings)
        self._targets.append(target)
        save_btn.setTarget_(target)
        save_btn.setAction_(objc.selector(target.perform_, signature=b"v@:@"))
        view.addSubview_(save_btn)

        return view

    def _save_general_settings(self):
        settings = load_settings()
        settings["sound_enabled"] = (
            self._sound_check.state() == AppKit.NSControlStateValueOn
        )
        save_settings(settings)

    def refresh_table(self):
        if self._table:
            self._table.reloadData()


# ── Table delegate / datasource ──────────────────────────────

class ScheduleTableDelegate(NSObject):
    """NSTableView data source and delegate – all columns editable inline."""

    @objc.python_method
    def initWithManager_controller_(self, manager, controller):
        self = objc.super(ScheduleTableDelegate, self).init()
        if self is None:
            return None
        self._manager = manager
        self._controller = controller
        return self

    # ── DataSource: read ─────────────────────────────────────

    def numberOfRowsInTableView_(self, table):
        return len(self._manager.schedules)

    def tableView_objectValueForTableColumn_row_(self, table, col, row):
        if row >= len(self._manager.schedules):
            return ""
        s = self._manager.schedules[row]
        cid = col.identifier()

        if cid == "enabled":
            return s.is_enabled
        elif cid == "category":
            try:
                return CATS.index(s.category)
            except ValueError:
                return 0
        elif cid == "title":
            return s.title
        elif cid == "time":
            return f"{s.hour:02d}:{s.minute:02d}"
        elif cid == "repeat":
            try:
                return REPS.index(s.repeat_type)
            except ValueError:
                return 0
        elif cid == "days":
            if not s.custom_days:
                return ""
            return "".join(WEEKDAY_LABELS[d - 1] for d in sorted(s.custom_days) if 1 <= d <= 7)
        elif cid == "date":
            return s.date or ""
        elif cid == "interval":
            return str(s.interval_minutes or "")
        return ""

    # ── DataSource: write ────────────────────────────────────

    def tableView_setObjectValue_forTableColumn_row_(self, table, value, col, row):
        if row >= len(self._manager.schedules):
            return
        s = self._manager.schedules[row]
        cid = col.identifier()

        if cid == "enabled":
            s.is_enabled = bool(value)
        elif cid == "category":
            idx = int(value)
            if 0 <= idx < len(CATS):
                s.category = CATS[idx]
        elif cid == "title":
            s.title = str(value)
        elif cid == "time":
            _parse_time(s, str(value))
        elif cid == "repeat":
            idx = int(value)
            if 0 <= idx < len(REPS):
                s.repeat_type = REPS[idx]
        elif cid == "days":
            s.custom_days = _parse_days(str(value))
        elif cid == "date":
            _parse_date(s, str(value))
        elif cid == "interval":
            txt = str(value).strip()
            if txt.isdigit():
                s.interval_minutes = int(txt)
            elif not txt:
                s.interval_minutes = None

    # ── Actions ──────────────────────────────────────────────

    @objc.IBAction
    def addSchedule_(self, sender):
        new_sched = Schedule(
            title="새 스케줄", hour=9, minute=0,
            repeat_type=RepeatType.DAILY,
            category=ScheduleCategory.CUSTOM,
        )
        self._manager.schedules.append(new_sched)
        self._controller.refresh_table()

    @objc.IBAction
    def removeSchedule_(self, sender):
        row = self._controller._table.selectedRow()
        if row < 0 or row >= len(self._manager.schedules):
            AppKit.NSBeep()
            return
        del self._manager.schedules[row]
        self._controller.refresh_table()


def _parse_time(schedule, text):
    """Parse 'HH:MM', 'HHMM', or 'H' into schedule.hour / schedule.minute."""
    text = text.strip()
    if ":" in text:
        parts = text.split(":")
        try:
            schedule.hour = int(parts[0]) % 24
            schedule.minute = int(parts[1]) % 60
        except (ValueError, IndexError):
            pass
    else:
        try:
            val = int(text)
            if val >= 100:
                schedule.hour = (val // 100) % 24
                schedule.minute = (val % 100) % 60
            else:
                schedule.hour = val % 24
                schedule.minute = 0
        except ValueError:
            pass


def _parse_date(schedule, text):
    """Parse date string into schedule.date (YYYY-MM-DD).

    Accepts: 'YYYY-MM-DD', 'MM-DD', 'M/D', 'MM/DD', or empty to clear.
    """
    text = text.strip()
    if not text:
        schedule.date = None
        return

    year = datetime.now().year

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"):
        try:
            dt = datetime.strptime(text, fmt)
            if "%Y" not in fmt:
                dt = dt.replace(year=year)
            schedule.date = dt.strftime("%Y-%m-%d")
            return
        except ValueError:
            continue

    # Try bare digits: MMDD
    if text.isdigit() and len(text) == 4:
        try:
            dt = datetime(year, int(text[:2]), int(text[2:]))
            schedule.date = dt.strftime("%Y-%m-%d")
            return
        except ValueError:
            pass


def _parse_date_header(text):
    """Parse a date header (after #) into YYYY-MM-DD string, or None."""
    text = text.strip()
    year = datetime.now().year

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"):
        try:
            dt = datetime.strptime(text, fmt)
            if "%Y" not in fmt:
                dt = dt.replace(year=year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    if text.isdigit() and len(text) == 4:
        try:
            return datetime(year, int(text[:2]), int(text[2:])).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_date_entry(line):
    """Parse a schedule entry line. Returns (hour, minute, title).

    Formats:
        '14:30 점심식사'  → (14, 30, '점심식사')
        '9 회의'          → (9, 0, '회의')
        '재택'            → (9, 0, '재택')   ← default 09:00
    """
    import re
    # Try HH:MM prefix
    m = re.match(r"^(\d{1,2}):(\d{2})\s+(.+)$", line)
    if m:
        return int(m.group(1)) % 24, int(m.group(2)) % 60, m.group(3)

    # Try bare hour prefix (e.g. "14 회의")
    m = re.match(r"^(\d{1,2})\s+(.+)$", line)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return h, 0, m.group(2)

    # No time → default 09:00
    return 9, 0, line


def _parse_days(text):
    """Parse weekday text like '목', '월수금', '월화수목금' into isoweekday list.

    Accepts Korean day names (월=1, 화=2, ..., 일=7).
    """
    day_map = {"월": 1, "화": 2, "수": 3, "목": 4, "금": 5, "토": 6, "일": 7}
    days = []
    for ch in text.strip():
        if ch in day_map and day_map[ch] not in days:
            days.append(day_map[ch])
    return sorted(days)
