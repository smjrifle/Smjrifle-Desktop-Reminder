"""
Smjrifle Desktop Reminder
Cross-Platform Floating Wellness Companion & Productivity Assistant.
Features customizable multi-reminders, authentic hand-drawn pixel walking companion,
floating speech bubble notifications, and daily streak tracking.

Licensed under MIT License - Copyright (c) 2026 Smjrifle.
"""

import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, QSize, pyqtSignal
)
from PyQt6.QtGui import (
    QMovie, QIcon, QFont, QFontMetrics, QColor, QPixmap, QCursor, QAction, QPainter
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox, QListWidget,
    QListWidgetItem, QDialog, QLineEdit, QTextEdit, QTabWidget,
    QSystemTrayIcon, QMenu, QFrame, QGraphicsOpacityEffect,
    QMessageBox, QSizePolicy
)

from config import (
    SmjrifleConfig, get_config_dir, APP_NAME, AVAILABLE_CHARACTERS, DEFAULT_REMINDERS
)
import autostart


def get_asset_path(filename: str) -> str:
    """Resolve asset paths reliably across frozen binaries, bundled apps, and source files."""
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidate = os.path.join(base_dir, filename)
        if os.path.exists(candidate):
            return candidate
        exe_dir = os.path.dirname(sys.executable)
        candidate = os.path.join(exe_dir, filename)
        if os.path.exists(candidate):
            return candidate

    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(current_dir, filename)
    if os.path.exists(candidate):
        return candidate

    return filename


def get_character_asset_path(char_id: str, filename: str) -> str:
    """Resolves asset paths for specific character folders."""
    char_subpath = os.path.join("assets", "characters", char_id, filename)
    resolved = get_asset_path(char_subpath)
    if os.path.exists(resolved):
        return resolved

    fallback = get_asset_path(filename)
    if os.path.exists(fallback):
        return fallback

    return char_subpath


FONT_FAMILY = (
    '"SF Pro Text", "Segoe UI", "Inter", "Ubuntu", "DejaVu Sans", "Helvetica Neue", sans-serif'
)


def elide(text: str, max_chars: int) -> str:
    """Truncate with an ellipsis rather than letting a long custom title,
    category, or message hard-clip mid-word against the speech bubble's
    fixed-size card (title/category are free-text in the reminder editor,
    with no length limit enforced there)."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


class WalkingCompanion(QWidget):
    """
    100% Borderless, Floating Desktop Mascot Sprite.
    Just the pixel art character on its own transparent window, free to walk
    across the desktop independently of any notification card.
    """

    def __init__(self, char_id: str, fallback_icon: str):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setFixedSize(160, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.char_label = QLabel(self)
        self.char_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.char_label.setStyleSheet("background: transparent; border: none;")
        self.char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.char_label)

        gif_path = get_character_asset_path(char_id, "character.gif")
        self.movie = QMovie(gif_path)
        if self.movie.isValid():
            self.movie.setScaledSize(QSize(155, 195))
            self.char_label.setMovie(self.movie)
            self.movie.start()
        else:
            self.char_label.setText(fallback_icon)
            self.char_label.setStyleSheet("font-size: 54px; background: transparent;")

    def paintEvent(self, event):
        # Explicit empty paint event to guarantee 100% transparent background on macOS
        pass

    def stop_movie(self):
        if self.movie.isValid():
            self.movie.stop()

    def walk(self, start_pos: QPoint, end_pos: QPoint, duration: int, on_finished=None):
        self.move(start_pos)
        self.show()
        self.raise_()
        self._walk_anim = QPropertyAnimation(self, b"pos")
        self._walk_anim.setDuration(duration)
        self._walk_anim.setStartValue(start_pos)
        self._walk_anim.setEndValue(end_pos)
        self._walk_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        if on_finished:
            self._walk_anim.finished.connect(on_finished)
        self._walk_anim.start()


class SpeechBubble(QWidget):
    """Standalone floating notification card. Appears beside the companion
    once it finishes walking in — never glued to the character itself.

    The top-level window itself stays a plain transparent shell; the visible
    dark-glass card is a *child* QFrame. A top-level widget with
    WA_TranslucentBackground does not reliably paint its own QSS background
    (rounded corners end up fully see-through even with WA_StyledBackground
    set) -- a child widget paints its styled background just fine."""

    def __init__(self, config, reminder_data: Dict[str, Any]):
        super().__init__(None)
        self.config = config
        self.reminder = reminder_data
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setFixedSize(300, 208)
        self.init_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(18, 18, 24, 0.94);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 12px;
                font-family: {FONT_FAMILY};
            }}
        """)
        outer_layout.addWidget(self.card)

        b_layout = QVBoxLayout(self.card)
        b_layout.setContentsMargins(14, 12, 14, 12)
        b_layout.setSpacing(8)

        # Header Row
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        icon_char = self.reminder.get("icon", "💧")
        cat_name = self.reminder.get("category", "Wellness").upper()
        title_text = self.reminder.get("title", "Hydration Time")

        # Pixel-accurate eliding, not a character-count guess: the card is a
        # fixed 300x208 and a long free-text title/category (no length limit
        # in the reminder editor) will otherwise hard-clip mid-word with no
        # "...". Budget = card width minus margins, close button, spacing.
        badge_font = QFont()
        badge_font.setBold(True)
        badge_font.setPixelSize(10)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPixelSize(12)

        header_budget = 300 - 28 - 18 - 12  # card - margins - close_btn - spacings
        badge_full = f"{icon_char}  {cat_name}"
        badge_display = QFontMetrics(badge_font).elidedText(badge_full, Qt.TextElideMode.ElideRight, 100)
        badge_px = QFontMetrics(badge_font).horizontalAdvance(badge_display) + 16  # + padding/border
        title_budget = max(50, header_budget - badge_px)
        title_display = QFontMetrics(title_font).elidedText(title_text, Qt.TextElideMode.ElideRight, title_budget)

        self.cat_badge = QLabel(badge_display, self.card)
        self.cat_badge.setFont(badge_font)
        self._badge_style = """
            background-color: rgba(14, 165, 233, 0.18);
            color: #38bdf8;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(56, 189, 248, 0.25);
        """
        self.cat_badge.setStyleSheet(self._badge_style)
        top_row.addWidget(self.cat_badge)

        self.title_lbl = QLabel(title_display, self.card)
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        close_btn = QPushButton("✕", self.card)
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {{
                background: rgba(255, 255, 255, 0.08);
                color: #a1a1aa;
                border: none;
                border-radius: 9px;
                font-size: 9px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.2);
                color: #ffffff;
            }}
        """)
        self.close_btn = close_btn
        top_row.addWidget(close_btn)
        b_layout.addLayout(top_row)

        # Message Body
        msg_text = elide(self.reminder.get("message", "Time for your wellness break! Stay hydrated."), 140)
        self.msg_lbl = QLabel(msg_text, self.card)
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setStyleSheet("""
            color: #f4f4f5;
            font-size: 12px;
            font-weight: 500;
            line-height: 1.35;
            background: transparent;
            border: none;
        """)
        self.msg_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        b_layout.addWidget(self.msg_lbl)

        # Action Buttons Row
        self.btn_row_widget = QWidget(self.card)
        self.btn_row_widget.setStyleSheet("background: transparent; border: none;")
        btn_row = QHBoxLayout(self.btn_row_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(6)

        is_water = "hydration" in self.reminder.get("category", "").lower() or "water" in self.reminder.get("title", "").lower()
        btn_text = "✓ I Drank Water!" if is_water else "✓ Completed"

        self.done_btn = QPushButton(btn_text, self.card)
        self.done_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.done_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0ea5e9);
                color: #ffffff;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 700;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0284c7);
            }
        """)
        btn_row.addWidget(self.done_btn)

        snooze_mins = max(1, self.config.snooze_seconds // 60)
        self.snooze_btn = QPushButton(f"⏰ Snooze ({snooze_mins}m)", self.card)
        self.snooze_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.snooze_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #e4e4e7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.16);
                color: #ffffff;
            }
        """)
        btn_row.addWidget(self.snooze_btn)

        self.settings_btn = QPushButton("⚙", self.card)
        self.settings_btn.setFixedSize(26, 26)
        self.settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_btn.setToolTip("Open Smjrifle Reminder Settings")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #a1a1aa;
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
            }
        """)
        btn_row.addWidget(self.settings_btn)

        b_layout.addWidget(self.btn_row_widget)

    def appear_at(self, pos: QPoint):
        self.move(pos.x(), pos.y() + 14)
        self.show()
        self.raise_()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in.setDuration(220)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_in.start()

        self._slide_in = QPropertyAnimation(self, b"pos")
        self._slide_in.setDuration(220)
        self._slide_in.setStartValue(QPoint(pos.x(), pos.y() + 14))
        self._slide_in.setEndValue(pos)
        self._slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_in.start()

    def show_success(self, message: str = "Nice! Keep it up 💪"):
        """Swap to a brief celebratory state after the user confirms they
        completed the reminder — replaces the prompt with an acknowledgment
        instead of just silently closing."""
        self.cat_badge.setText("✅  AWESOME")
        self.cat_badge.setStyleSheet("""
            background-color: rgba(34, 197, 94, 0.18);
            color: #4ade80;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(74, 222, 128, 0.3);
        """)
        self.title_lbl.setText("Awesome! 🎉")
        self.msg_lbl.setText(message)
        self.btn_row_widget.hide()
        self.close_btn.hide()

    def vanish(self, callback=None):
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out.setDuration(160)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(lambda: (self.close(), callback() if callback else None))
        self._fade_out.start()


class SmjrifleReminderPopup:
    """
    Coordinates the two independent windows that make up one reminder
    encounter: a WalkingCompanion sprite that walks onto the desktop on its
    own, and a SpeechBubble card that only appears once it arrives.
    """

    EDGE_MARGIN = 24
    GAP = 12

    def __init__(self, main_app, reminder_data: Dict[str, Any]):
        self.main_app = main_app
        self.reminder = reminder_data
        self.config = main_app.config

        char_id = self.config.active_character
        self.companion = WalkingCompanion(char_id, self.reminder.get("icon", "💧"))

        self.bubble = SpeechBubble(self.config, self.reminder)
        self.bubble.close_btn.clicked.connect(self.action_dismiss)
        self.bubble.done_btn.clicked.connect(self.action_completed)
        self.bubble.snooze_btn.clicked.connect(self.action_snooze)
        self.bubble.settings_btn.clicked.connect(self.action_settings)

        self.target_pos, self.edge, self.avail = self._resting_spot()

    def _resting_spot(self):
        """Where the companion settles, and which screen edge it walks in from."""
        screen = QApplication.primaryScreen()
        if not screen:
            fallback_avail = QRect(0, 0, 1280, 800)
            return QPoint(100, 100), "left", fallback_avail

        avail = screen.availableGeometry()
        mode = self.config.position_mode
        w, h = self.companion.width(), self.companion.height()
        m = self.EDGE_MARGIN

        if mode == "top-right":
            target = QPoint(avail.x() + avail.width() - w - m, avail.y() + m)
            edge = "right"
        elif mode in ("auto", "bottom-right"):
            target = QPoint(avail.x() + avail.width() - w - m, avail.y() + avail.height() - h - m)
            edge = "right"
        elif mode == "top-left":
            target = QPoint(avail.x() + m, avail.y() + m)
            edge = "left"
        elif mode == "bottom-left":
            target = QPoint(avail.x() + m, avail.y() + avail.height() - h - m)
            edge = "left"
        else:  # Center
            target = QPoint(avail.x() + (avail.width() - w) // 2, avail.y() + (avail.height() - h) // 2)
            edge = "bottom"

        return target, edge, avail

    def _offscreen_pos(self, target_pos: QPoint, edge: str, avail) -> QPoint:
        if edge == "right":
            return QPoint(avail.x() + avail.width(), target_pos.y())
        if edge == "left":
            return QPoint(avail.x() - self.companion.width(), target_pos.y())
        return QPoint(target_pos.x(), avail.y() + avail.height())

    def _bubble_pos(self, companion_pos: QPoint, edge: str, avail) -> QPoint:
        cw, ch = self.companion.width(), self.companion.height()
        bw, bh = self.bubble.width(), self.bubble.height()
        by = companion_pos.y() + (ch - bh) // 2

        if edge == "left":
            bx = companion_pos.x() + cw + self.GAP
        else:
            bx = companion_pos.x() - bw - self.GAP

        bx = max(avail.x() + 4, min(bx, avail.x() + avail.width() - bw - 4))
        by = max(avail.y() + 4, min(by, avail.y() + avail.height() - bh - 4))
        return QPoint(bx, by)

    def trigger_display(self):
        self.target_pos, self.edge, self.avail = self._resting_spot()
        start_pos = self._offscreen_pos(self.target_pos, self.edge, self.avail)
        self.companion.walk(start_pos, self.target_pos, duration=950, on_finished=self._on_arrived)

    def _on_arrived(self):
        bubble_pos = self._bubble_pos(self.target_pos, self.edge, self.avail)
        self.bubble.appear_at(bubble_pos)
        if self.config.sound_enabled:
            QApplication.beep()

    def close(self):
        """Abrupt teardown — used when a new reminder interrupts this one."""
        self.companion.stop_movie()
        self.companion.close()
        self.bubble.close()

    def close_with_animation(self, callback=None):
        self.companion.stop_movie()
        offscreen = self._offscreen_pos(self.target_pos, self.edge, self.avail)

        def walk_away():
            self.companion.walk(self.target_pos, offscreen, duration=700, on_finished=lambda: (
                self.companion.close(), callback() if callback else None
            ))

        self.bubble.vanish(walk_away)

    def action_completed(self):
        self.config.log_completed_break()
        self.main_app.update_stats_ui()
        self.bubble.show_success()
        QTimer.singleShot(1400, lambda: self.close_with_animation(self.main_app.restart_timer))

    def action_snooze(self):
        reminder_id = self.reminder.get("id")
        self.close_with_animation(lambda: self.main_app.trigger_snooze(reminder_id))

    def action_dismiss(self):
        self.close_with_animation(self.main_app.restart_timer)

    def action_settings(self):
        self.close_with_animation(self.main_app.show_and_activate)


class ReminderEditDialog(QDialog):
    """Modal dialog for creating and modifying custom reminders."""

    def __init__(self, parent=None, reminder: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.reminder = reminder
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Edit Reminder" if self.reminder else "New Custom Reminder")
        self.setFixedSize(440, 390)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #121214;
                color: #f4f4f5;
                font-family: {FONT_FAMILY};
            }}
            QLabel {{
                color: #e4e4e7;
                font-size: 13px;
                font-weight: 500;
            }}
            QLineEdit, QTextEdit {{
                background-color: #1c1c21;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 8px 12px;
                color: #fafafa;
                font-size: 13px;
                font-family: {FONT_FAMILY};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid #0ea5e9;
                background-color: #22222a;
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#saveBtn {{
                background-color: #0284c7;
                color: #ffffff;
                border: none;
            }}
            QPushButton#saveBtn:hover {{
                background-color: #0369a1;
            }}
            QPushButton#cancelBtn {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #d4d4d8;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QPushButton#cancelBtn:hover {{
                background-color: rgba(255, 255, 255, 0.14);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        dialog_title = QLabel("Edit Reminder" if self.reminder else "Create Custom Reminder")
        dialog_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        layout.addWidget(dialog_title)

        row = QHBoxLayout()
        row.setSpacing(10)

        icon_layout = QVBoxLayout()
        icon_lbl = QLabel("Emoji / Icon")
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("💧")
        self.icon_input.setText(self.reminder.get("icon", "💧") if self.reminder else "💧")
        self.icon_input.setFixedWidth(80)
        self.icon_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_input.setStyleSheet("font-size: 18px;")
        icon_layout.addWidget(icon_lbl)
        icon_layout.addWidget(self.icon_input)
        row.addLayout(icon_layout)

        title_layout = QVBoxLayout()
        title_lbl = QLabel("Reminder Title")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Drink Water, Stretch, Rest Eyes")
        if self.reminder:
            self.title_input.setText(self.reminder.get("title", ""))
        title_layout.addWidget(title_lbl)
        title_layout.addWidget(self.title_input)
        row.addLayout(title_layout)

        layout.addLayout(row)

        cat_row = QHBoxLayout()
        cat_row.setSpacing(10)

        cat_layout = QVBoxLayout()
        cat_lbl = QLabel("Category / Tag")
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("e.g. Hydration, Posture, Eye Health, Focus")
        if self.reminder:
            self.cat_input.setText(self.reminder.get("category", "Wellness"))
        else:
            self.cat_input.setText("Wellness")
        cat_layout.addWidget(cat_lbl)
        cat_layout.addWidget(self.cat_input)
        cat_row.addLayout(cat_layout, stretch=1)

        interval_layout = QVBoxLayout()
        interval_lbl = QLabel("Repeat Every (minutes)")
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 480)
        self.interval_input.setValue(int(self.reminder.get("interval_minutes", 30)) if self.reminder else 30)
        self.interval_input.setFixedWidth(100)
        interval_layout.addWidget(interval_lbl)
        interval_layout.addWidget(self.interval_input)
        cat_row.addLayout(interval_layout)

        layout.addLayout(cat_row)

        msg_lbl = QLabel("Reminder Message Details")
        layout.addWidget(msg_lbl)
        self.msg_input = QTextEdit()
        self.msg_input.setPlaceholderText("Enter the gentle message you want to see...")
        if self.reminder:
            self.msg_input.setPlainText(self.reminder.get("message", ""))
        self.msg_input.setFixedHeight(80)
        layout.addWidget(self.msg_input)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)
        btn_bar.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Reminder")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.validate_and_save)

        btn_bar.addWidget(cancel_btn)
        btn_bar.addWidget(save_btn)
        layout.addLayout(btn_bar)

    def validate_and_save(self):
        title = self.title_input.text().strip()
        msg = self.msg_input.toPlainText().strip()
        icon = self.icon_input.text().strip() or "💧"
        category = self.cat_input.text().strip() or "Wellness"

        if not title:
            QMessageBox.warning(self, "Missing Title", "Please specify a title for this reminder.")
            return

        if not msg:
            QMessageBox.warning(self, "Missing Message", "Please enter a message description.")
            return

        self.result_data = {
            "title": title,
            "message": msg,
            "icon": icon,
            "category": category,
            "interval_minutes": self.interval_input.value(),
        }
        self.accept()


class ReminderItemWidget(QWidget):
    """Custom row widget for listing reminders in the Smjrifle Dashboard."""

    toggled = pyqtSignal(str, bool)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, reminder: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.reminder = reminder
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.reminder.get("enabled", True))
        self.checkbox.toggled.connect(lambda checked: self.toggled.emit(self.reminder["id"], checked))
        layout.addWidget(self.checkbox)

        icon_lbl = QLabel(self.reminder.get("icon", "💧"))
        icon_lbl.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            font-size: 16px;
            padding: 3px 6px;
        """)
        layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        title_lbl = QLabel(self.reminder.get("title", "Reminder"))
        title_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #f4f4f5;")
        header_row.addWidget(title_lbl)

        cat_tag = QLabel(self.reminder.get("category", "Wellness").upper())
        cat_tag.setStyleSheet("""
            background-color: rgba(14, 165, 233, 0.15);
            color: #38bdf8;
            font-size: 9px;
            font-weight: 700;
            padding: 2px 5px;
            border-radius: 4px;
        """)
        header_row.addWidget(cat_tag)

        interval_min = self.reminder.get("interval_minutes", 30)
        interval_tag = QLabel(f"⏱ {interval_min}m")
        interval_tag.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.06);
            color: #a1a1aa;
            font-size: 9px;
            font-weight: 600;
            padding: 2px 5px;
            border-radius: 4px;
        """)
        header_row.addWidget(interval_tag)
        header_row.addStretch()
        text_layout.addLayout(header_row)

        msg_preview = self.reminder.get("message", "")
        if len(msg_preview) > 38:
            msg_preview = msg_preview[:36] + "..."
        desc_lbl = QLabel(msg_preview)
        desc_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        desc_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text_layout.addWidget(desc_lbl)

        layout.addLayout(text_layout, stretch=1)

        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(48, 26)
        edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        edit_btn.setToolTip("Edit Reminder Settings")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #f4f4f5;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
                color: #ffffff;
                border-color: rgba(255, 255, 255, 0.28);
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.reminder["id"]))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("Delete")
        del_btn.setFixedSize(54, 26)
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.setToolTip("Delete Reminder")
        del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.12);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.25);
                color: #ffffff;
                border-color: rgba(239, 68, 68, 0.45);
            }
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.reminder["id"]))
        layout.addWidget(del_btn)


class CharacterCardWidget(QFrame):
    """Interactive visual card for selecting active buddy companion."""

    selected = pyqtSignal(str)

    def __init__(self, char_info: Dict[str, Any], is_active: bool, parent=None):
        super().__init__(parent)
        self.char_info = char_info
        self.is_active = is_active
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            CharacterCardWidget {{
                background-color: {"#0f2b48" if self.is_active else "#16161a"};
                border: 2px solid {"#0284c7" if self.is_active else "rgba(255, 255, 255, 0.08)"};
                border-radius: 12px;
            }}
            CharacterCardWidget:hover {{
                border-color: #38bdf8;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        name_lbl = QLabel(self.char_info["name"])
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        top_row.addWidget(name_lbl)
        top_row.addStretch()

        tag_lbl = QLabel(self.char_info.get("tag", "Buddy"))
        tag_lbl.setStyleSheet("""
            background: rgba(14, 165, 233, 0.2);
            color: #38bdf8;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        top_row.addWidget(tag_lbl)
        layout.addLayout(top_row)

        preview_box = QFrame()
        preview_box.setFixedSize(110, 140)
        preview_box.setStyleSheet("""
            background-color: rgba(10, 10, 14, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
        """)
        p_layout = QVBoxLayout(preview_box)
        p_layout.setContentsMargins(4, 4, 4, 4)

        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        preview_path = get_character_asset_path(self.char_info["id"], "preview.png")
        if os.path.exists(preview_path):
            pix = QPixmap(preview_path).scaled(90, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_lbl.setPixmap(pix)
        else:
            img_lbl.setText("🏃")
            img_lbl.setStyleSheet("font-size: 36px;")

        p_layout.addWidget(img_lbl)
        layout.addWidget(preview_box, alignment=Qt.AlignmentFlag.AlignCenter)

        desc_lbl = QLabel(self.char_info["description"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_lbl)

        select_btn = QPushButton("✓ Active Companion" if self.is_active else "Select Companion")
        select_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if self.is_active:
            select_btn.setStyleSheet("""
                background-color: #0284c7; color: #ffffff; border-radius: 6px;
                padding: 6px 12px; font-size: 12px; font-weight: 700; border: none;
            """)
        else:
            select_btn.setStyleSheet("""
                background-color: rgba(255, 255, 255, 0.08); color: #d4d4d8; border-radius: 6px;
                padding: 6px 12px; font-size: 12px; font-weight: 600; border: 1px solid rgba(255, 255, 255, 0.12);
            """)
        select_btn.clicked.connect(lambda: self.selected.emit(self.char_info["id"]))
        layout.addWidget(select_btn)


class SmjrifleReminderApp(QMainWindow):
    """
    Main Application Dashboard & Background Control Deck.
    """

    def __init__(self):
        super().__init__()
        self.config = SmjrifleConfig()
        self.active_popup: Optional[SmjrifleReminderPopup] = None
        self.is_paused = False
        self.next_trigger_time: Optional[float] = None
        # Each reminder runs on its own cadence: reminder id -> unix
        # timestamp it's next due. A single shared timer can't express that,
        # so scheduling is now polled once a second (see _tick) instead of
        # one QTimer firing "the next reminder" via rotation.
        self.next_due: Dict[str, float] = {}

        self.init_ui()
        self.init_system_tray()
        self.init_timer()

        if sys.platform == "darwin" and not self.config.show_in_dock:
            autostart.set_dock_icon_visible(False)

    def init_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(620, 660)
        self.resize(640, 680)

        icon_path = get_asset_path("icon.png")
        if os.path.exists(icon_path):
            self.app_icon = QIcon(icon_path)
            self.setWindowIcon(self.app_icon)
        else:
            self.app_icon = QIcon()

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #09090b;
                font-family: {FONT_FAMILY};
            }}
            QWidget {{
                color: #f4f4f5;
                font-family: {FONT_FAMILY};
            }}
            QTabWidget::pane {{
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                background-color: #121215;
                top: -1px;
            }}
            QTabBar::tab {{
                background: #18181b;
                color: #a1a1aa;
                padding: 9px 18px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background: #0284c7;
                color: #ffffff;
            }}
            QTabBar::tab:hover:!selected {{
                background: #27272a;
                color: #e4e4e7;
            }}
            QComboBox, QSpinBox {{
                background-color: #18181b;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 12px;
                color: #fafafa;
                font-size: 13px;
                min-height: 20px;
            }}
            QComboBox:focus, QSpinBox:focus {{
                border: 1px solid #0ea5e9;
            }}
            QCheckBox {{
                font-size: 13px;
                color: #e4e4e7;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background: #18181b;
            }}
            QCheckBox::indicator:checked {{
                background-color: #0284c7;
                border: 1px solid #38bdf8;
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#primaryBtn {{
                background-color: #0284c7;
                color: #ffffff;
                border: none;
            }}
            QPushButton#primaryBtn:hover {{
                background-color: #0369a1;
            }}
            QPushButton#secondaryBtn {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #f4f4f5;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }}
            QPushButton#secondaryBtn:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Header Hero Card
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #0369a1);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(18, 14, 18, 14)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        app_title = QLabel("Smjrifle Desktop Reminder ✨")
        app_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff; background: transparent;")
        app_subtitle = QLabel("Cross-Platform Floating Desktop Companion & Productivity Assistant")
        app_subtitle.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent;")
        title_col.addWidget(app_title)
        title_col.addWidget(app_subtitle)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        self.status_badge = QLabel("● Active")
        self.status_badge.setStyleSheet("""
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.4);
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
        """)
        header_layout.addWidget(self.status_badge)
        main_layout.addWidget(header_card)

        # Daily Wellness Stats Strip
        self.stats_bar = QFrame()
        self.stats_bar.setStyleSheet("""
            QFrame {
                background-color: #141418;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px 12px;
            }
        """)
        sb_layout = QHBoxLayout(self.stats_bar)
        sb_layout.setContentsMargins(10, 6, 10, 6)

        self.stat_breaks_lbl = QLabel("🏆 Today's Completed: 0 breaks")
        self.stat_breaks_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")
        sb_layout.addWidget(self.stat_breaks_lbl)
        sb_layout.addStretch()

        self.stat_streak_lbl = QLabel("🔥 Streak: 1 Day")
        self.stat_streak_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #facc15;")
        sb_layout.addWidget(self.stat_streak_lbl)
        sb_layout.addStretch()

        self.stat_timer_lbl = QLabel("⏱ Next in: --:--")
        self.stat_timer_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #a1a1aa;")
        sb_layout.addWidget(self.stat_timer_lbl)

        main_layout.addWidget(self.stats_bar)
        self.update_stats_ui()

        # Tabs for Reminders, Characters, Schedule, and Appearance
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_reminders_tab(), "📝 Reminders")
        self.tabs.addTab(self.create_characters_tab(), "👥 Characters")
        self.tabs.addTab(self.create_schedule_tab(), "⏱ Schedule")
        self.tabs.addTab(self.create_appearance_tab(), "🎨 Preferences")
        main_layout.addWidget(self.tabs, stretch=1)

        # Bottom Controls
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.preview_btn = QPushButton("⚡ Test Notification")
        self.preview_btn.setObjectName("secondaryBtn")
        self.preview_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.preview_btn.clicked.connect(self.show_notification)
        bottom_bar.addWidget(self.preview_btn)

        bottom_bar.addStretch()

        self.start_btn = QPushButton("✓ Start & Run in Background")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.start_btn.clicked.connect(self.start_and_minimize)
        bottom_bar.addWidget(self.start_btn)

        main_layout.addLayout(bottom_bar)

    def update_stats_ui(self):
        stats = self.config.stats
        today_cnt = stats.get("breaks_completed_today", 0)
        streak = stats.get("streak_days", 1)
        self.stat_breaks_lbl.setText(f"🏆 Today's Completed: {today_cnt} breaks")
        self.stat_streak_lbl.setText(f"🔥 Streak: {streak} Day{'s' if streak > 1 else ''}")

    def create_characters_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        head_lbl = QLabel("Choose Your Floating Desktop Companion")
        head_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        layout.addWidget(head_lbl)

        sub_lbl = QLabel("Your chosen companion will walk directly onto your screen with a floating speech bubble:")
        sub_lbl.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        layout.addWidget(sub_lbl)

        self.cards_grid = QHBoxLayout()
        self.cards_grid.setSpacing(16)
        layout.addLayout(self.cards_grid)
        layout.addStretch()

        self.refresh_character_cards()
        return tab

    def refresh_character_cards(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active_id = self.config.active_character
        for char_info in AVAILABLE_CHARACTERS:
            is_active = (char_info["id"] == active_id)
            card = CharacterCardWidget(char_info, is_active, self)
            card.selected.connect(self.on_character_selected)
            self.cards_grid.addWidget(card)

    def on_character_selected(self, char_id: str):
        self.config.active_character = char_id
        self.refresh_character_cards()
        self.show_notification()

    def create_reminders_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        count_active = len(self.config.get_active_reminders())
        self.rem_count_lbl = QLabel(f"Active Reminders ({count_active}/{len(self.config.reminders)})")
        self.rem_count_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #e4e4e7;")
        toolbar.addWidget(self.rem_count_lbl)
        toolbar.addStretch()

        add_btn = QPushButton("+ Add Reminder")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(30)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #0284c7; color: white; border-radius: 6px; font-size: 12px; font-weight: 600; padding: 4px 12px;
            }
            QPushButton:hover { background: #0369a1; }
        """)
        add_btn.clicked.connect(self.open_add_reminder_dialog)
        toolbar.addWidget(add_btn)

        reset_btn = QPushButton("↺ Defaults")
        reset_btn.setFixedHeight(30)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08); color: #d4d4d8; border-radius: 6px; font-size: 12px; padding: 4px 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.15); }
        """)
        reset_btn.clicked.connect(self.reset_reminders)
        toolbar.addWidget(reset_btn)

        layout.addLayout(toolbar)

        self.reminders_list = QListWidget()
        self.reminders_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.reminders_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.reminders_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.reminders_list.setStyleSheet("""
            QListWidget {
                background-color: #16161a;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                background: transparent;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.03);
            }
        """)
        layout.addWidget(self.reminders_list)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)
        mode_lbl = QLabel("Delivery Mode:")
        mode_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #a1a1aa;")
        mode_row.addWidget(mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🔄 Cycle in Sequence", "cycle")
        self.mode_combo.addItem("🎲 Random Pick", "random")
        idx = 0 if self.config.rotation_mode == "cycle" else 1
        self.mode_combo.setCurrentIndex(idx)
        self.mode_combo.currentIndexChanged.connect(self.on_rotation_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()

        layout.addLayout(mode_row)
        self.refresh_reminders_list()
        return tab

    def create_schedule_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        interval_card = QFrame()
        interval_card.setStyleSheet("""
            QFrame {
                background-color: #16161a;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px;
            }
        """)
        ic_layout = QVBoxLayout(interval_card)
        ic_layout.setSpacing(12)

        lbl_head = QLabel("⏰ Default Reminder Interval")
        lbl_head.setStyleSheet("font-weight: 700; font-size: 14px; color: #ffffff;")
        ic_layout.addWidget(lbl_head)

        row1 = QHBoxLayout()
        lbl1 = QLabel("Starting interval for newly created reminders (each one can be changed individually via its own ✏️ Edit button):")
        lbl1.setWordWrap(True)
        lbl1.setStyleSheet("color: #d4d4d8; font-size: 13px;")
        row1.addWidget(lbl1)

        self.interval_dropdown = QComboBox()
        self.interval_dropdown.addItem("⚡ Every 10 Seconds (Testing)", 10)
        self.interval_dropdown.addItem("Every 15 Minutes", 15 * 60)
        self.interval_dropdown.addItem("Every 20 Minutes (20-20-20)", 20 * 60)
        self.interval_dropdown.addItem("Every 30 Minutes (Recommended)", 30 * 60)
        self.interval_dropdown.addItem("Every 45 Minutes", 45 * 60)
        self.interval_dropdown.addItem("Every 1 Hour", 60 * 60)
        self.interval_dropdown.addItem("Every 2 Hours", 120 * 60)
        self.interval_dropdown.addItem("Custom Interval...", -1)

        curr_secs = self.config.interval_seconds
        matched = False
        for i in range(self.interval_dropdown.count()):
            if self.interval_dropdown.itemData(i) == curr_secs:
                self.interval_dropdown.setCurrentIndex(i)
                matched = True
                break
        if not matched:
            self.interval_dropdown.setCurrentIndex(self.interval_dropdown.count() - 1)

        self.interval_dropdown.currentIndexChanged.connect(self.on_interval_changed)
        row1.addWidget(self.interval_dropdown)
        ic_layout.addLayout(row1)

        self.custom_row = QWidget()
        cr_layout = QHBoxLayout(self.custom_row)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.addWidget(QLabel("Custom Minutes:"))
        self.custom_spin = QSpinBox()
        self.custom_spin.setRange(1, 480)
        self.custom_spin.setValue(max(1, curr_secs // 60))
        self.custom_spin.valueChanged.connect(self.on_custom_minutes_changed)
        cr_layout.addWidget(self.custom_spin)
        cr_layout.addStretch()
        ic_layout.addWidget(self.custom_row)
        self.custom_row.setVisible(self.interval_dropdown.currentData() == -1)

        layout.addWidget(interval_card)

        snooze_card = QFrame()
        snooze_card.setStyleSheet("""
            QFrame {
                background-color: #16161a;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px;
            }
        """)
        sc_layout = QHBoxLayout(snooze_card)
        sc_layout.setSpacing(12)

        s_lbl = QLabel("Snooze Duration:")
        s_lbl.setStyleSheet("color: #d4d4d8; font-size: 13px; font-weight: 600;")
        sc_layout.addWidget(s_lbl)

        self.snooze_dropdown = QComboBox()
        self.snooze_dropdown.addItem("2 Minutes", 2 * 60)
        self.snooze_dropdown.addItem("5 Minutes", 5 * 60)
        self.snooze_dropdown.addItem("10 Minutes (Standard)", 10 * 60)
        self.snooze_dropdown.addItem("15 Minutes", 15 * 60)

        snooze_secs = self.config.snooze_seconds
        for i in range(self.snooze_dropdown.count()):
            if self.snooze_dropdown.itemData(i) == snooze_secs:
                self.snooze_dropdown.setCurrentIndex(i)
                break
        self.snooze_dropdown.currentIndexChanged.connect(self.on_snooze_changed)
        sc_layout.addWidget(self.snooze_dropdown)
        sc_layout.addStretch()

        layout.addWidget(snooze_card)
        layout.addStretch()
        return tab

    def create_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #16161a;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(14)

        pos_row = QHBoxLayout()
        pos_lbl = QLabel("Desktop Companion Position:")
        pos_lbl.setStyleSheet("color: #d4d4d8; font-size: 13px; font-weight: 600;")
        pos_row.addWidget(pos_lbl)

        self.pos_dropdown = QComboBox()
        self.pos_dropdown.addItem("Bottom-Right (Above Taskbar / Dock)", "bottom-right")
        self.pos_dropdown.addItem("Top-Right (macOS Menu Bar Corner)", "top-right")
        self.pos_dropdown.addItem("Bottom-Left", "bottom-left")
        self.pos_dropdown.addItem("Top-Left", "top-left")
        self.pos_dropdown.addItem("Center Screen", "center")

        pos_val = self.config.position_mode
        for i in range(self.pos_dropdown.count()):
            if self.pos_dropdown.itemData(i) == pos_val:
                self.pos_dropdown.setCurrentIndex(i)
                break
        self.pos_dropdown.currentIndexChanged.connect(self.on_position_changed)
        pos_row.addWidget(self.pos_dropdown)
        c_layout.addLayout(pos_row)

        self.sound_check = QCheckBox("Play gentle alert sound when reminder triggers")
        self.sound_check.setChecked(self.config.sound_enabled)
        self.sound_check.toggled.connect(self.on_sound_toggled)
        c_layout.addWidget(self.sound_check)

        self.autostart_check = QCheckBox("Start automatically when you log in")
        self.autostart_check.setChecked(autostart.is_autostart_enabled())
        self.autostart_check.toggled.connect(self.on_autostart_toggled)
        c_layout.addWidget(self.autostart_check)

        if sys.platform == "darwin":
            self.dock_check = QCheckBox("Show icon in macOS Dock (uncheck for Menu Bar only)")
            self.dock_check.setChecked(self.config.show_in_dock)
            self.dock_check.toggled.connect(self.on_dock_toggled)
            c_layout.addWidget(self.dock_check)

        layout.addWidget(card)

        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #16161a;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px;
            }
        """)
        ic_layout = QVBoxLayout(info_card)
        ic_layout.setSpacing(6)

        info_head = QLabel("🖥 Application & Environment")
        info_head.setStyleSheet("font-weight: 700; font-size: 13px; color: #a1a1aa;")
        ic_layout.addWidget(info_head)

        os_name = "macOS" if sys.platform == "darwin" else ("Windows" if sys.platform == "win32" else "Linux/Unix")
        ic_layout.addWidget(QLabel(f"• Application: {APP_NAME}"))
        ic_layout.addWidget(QLabel(f"• Platform: {os_name} ({sys.platform})"))
        ic_layout.addWidget(QLabel(f"• Config Path: {get_config_dir()}"))
        ic_layout.addWidget(QLabel(f"• Active Companion: {self.config.active_character}"))
        ic_layout.addWidget(QLabel("• License: MIT - Copyright (c) 2026 Smjrifle"))
        layout.addWidget(info_card)

        layout.addStretch()
        return tab

    # ---------------- Reminder Actions ----------------

    def refresh_reminders_list(self):
        self.reminders_list.clear()
        for reminder in self.config.reminders:
            item = QListWidgetItem(self.reminders_list)
            widget = ReminderItemWidget(reminder, self)
            widget.toggled.connect(self.on_reminder_toggled)
            widget.edit_requested.connect(self.on_edit_reminder)
            widget.delete_requested.connect(self.on_delete_reminder)

            item.setSizeHint(QSize(0, 52))
            self.reminders_list.setItemWidget(item, widget)

        active_count = len(self.config.get_active_reminders())
        self.rem_count_lbl.setText(f"Active Reminders ({active_count}/{len(self.config.reminders)})")

    def on_reminder_toggled(self, rem_id: str, checked: bool):
        for r in self.config.reminders:
            if r.get("id") == rem_id:
                r["enabled"] = checked
                break
        self.config.save()
        active_count = len(self.config.get_active_reminders())
        self.rem_count_lbl.setText(f"Active Reminders ({active_count}/{len(self.config.reminders)})")
        self._ensure_scheduled()

    def open_add_reminder_dialog(self):
        dlg = ReminderEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.result_data
            self.config.add_reminder(
                data["title"], data["message"], data["icon"], data["category"],
                enabled=True, interval_minutes=data["interval_minutes"],
            )
            self.refresh_reminders_list()
            self._ensure_scheduled()

    def on_edit_reminder(self, rem_id: str):
        target = next((r for r in self.config.reminders if r["id"] == rem_id), None)
        if not target:
            return
        dlg = ReminderEditDialog(self, reminder=target)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.result_data
            self.config.update_reminder(
                rem_id, data["title"], data["message"], data["icon"], data["category"],
                target.get("enabled", True), data["interval_minutes"],
            )
            # The interval may have just changed -- drop any stale
            # schedule for this reminder so it picks up the new cadence
            # immediately instead of waiting out the old one.
            self.next_due.pop(rem_id, None)
            self.refresh_reminders_list()
            self._ensure_scheduled()

    def on_delete_reminder(self, rem_id: str):
        if len(self.config.reminders) <= 1:
            QMessageBox.information(self, "Cannot Delete", "You must have at least one reminder in your list.")
            return

        reply = QMessageBox.question(
            self, "Delete Reminder",
            "Are you sure you want to delete this reminder?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.delete_reminder(rem_id)
            self.next_due.pop(rem_id, None)
            self.refresh_reminders_list()

    def reset_reminders(self):
        reply = QMessageBox.question(
            self, "Restore Defaults",
            "Reset all reminders to the default wellness list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.reset_reminders_to_default()
            self.next_due.clear()
            self.refresh_reminders_list()
            self._ensure_scheduled()

    def on_rotation_mode_changed(self, index: int):
        self.config.rotation_mode = self.mode_combo.currentData()
        self.config.save()

    def on_interval_changed(self, index: int):
        val = self.interval_dropdown.currentData()
        if val == -1:
            self.custom_row.setVisible(True)
            self.config.interval_seconds = self.custom_spin.value() * 60
        else:
            self.custom_row.setVisible(False)
            self.config.interval_seconds = val
        self.config.save()
        self.restart_timer()

    def on_custom_minutes_changed(self, value: int):
        if self.interval_dropdown.currentData() == -1:
            self.config.interval_seconds = value * 60
            self.config.save()
            self.restart_timer()

    def on_snooze_changed(self, index: int):
        self.config.snooze_seconds = self.snooze_dropdown.currentData()
        self.config.save()

    def on_position_changed(self, index: int):
        self.config.position_mode = self.pos_dropdown.currentData()
        self.config.save()

    def on_sound_toggled(self, checked: bool):
        self.config.sound_enabled = checked
        self.config.save()

    def on_autostart_toggled(self, checked: bool):
        ok = autostart.set_autostart_enabled(checked)
        if not ok:
            # Revert the checkbox without re-triggering this handler --
            # the OS-level toggle failed (e.g. no registry/launchctl access).
            self.autostart_check.blockSignals(True)
            self.autostart_check.setChecked(not checked)
            self.autostart_check.blockSignals(False)
            QMessageBox.warning(
                self,
                "Couldn't Update Autostart",
                "Smjrifle Reminder couldn't register with your system's login "
                "items. Check the console output for details.",
            )

    def on_dock_toggled(self, checked: bool):
        self.config.show_in_dock = checked
        autostart.set_dock_icon_visible(checked)

    # ---------------- Timer & Background System ----------------

    def init_timer(self):
        # One shared ticker drives both the countdown display and the
        # per-reminder due-time check -- there's no single "the interval"
        # anymore now that each reminder can run on its own cadence, so a
        # single QTimer-fires-in-N-seconds model can't express this.
        self.clock_ticker = QTimer(self)
        self.clock_ticker.timeout.connect(self._tick)
        self.clock_ticker.start(1000)

        self._reset_all_schedules()

    def _reset_all_schedules(self):
        """Fresh countdown for every active reminder, starting now. Used on
        app launch and when resuming from a pause (mirrors the old
        behavior: a pause doesn't leave a backlog of overdue reminders that
        all fire at once the moment you resume)."""
        now = time.time()
        self.next_due = {
            r["id"]: now + self.config.get_reminder_interval_seconds(r)
            for r in self.config.get_active_reminders()
        }
        self._update_next_trigger_summary()

    def _ensure_scheduled(self):
        """Fill in schedules for reminders that don't have one yet (newly
        added, just re-enabled, or just edited) and drop ones that are no
        longer active -- without disturbing any reminder that's already
        mid-countdown."""
        active_ids = {r["id"] for r in self.config.get_active_reminders()}
        self.next_due = {rid: t for rid, t in self.next_due.items() if rid in active_ids}
        now = time.time()
        for r in self.config.get_active_reminders():
            if r["id"] not in self.next_due:
                self.next_due[r["id"]] = now + self.config.get_reminder_interval_seconds(r)
        self._update_next_trigger_summary()

    def _update_next_trigger_summary(self):
        self.next_trigger_time = min(self.next_due.values()) if self.next_due else None

    def restart_timer(self):
        """Kept as the popup-close callback name other code already calls.
        Does NOT reset every reminder's countdown -- only backfills ones
        missing a schedule -- so finishing/dismissing one reminder never
        resets how soon a *different* reminder is due."""
        if self.is_paused:
            return
        self._ensure_scheduled()

    def trigger_snooze(self, reminder_id: Optional[str] = None):
        if self.is_paused:
            return
        if reminder_id:
            self.next_due[reminder_id] = time.time() + self.config.snooze_seconds
        self._update_next_trigger_summary()

    def _tick(self):
        self.update_countdown_display()
        if self.is_paused or self.active_popup:
            return

        now = time.time()
        # If several are due at once, the one that's been waiting longest
        # goes first -- not insertion order, which would be arbitrary.
        # Whichever isn't picked just stays "due" and fires immediately
        # after this popup closes (checked again next tick), so ties never
        # drop or overlap a reminder -- they queue up sequentially instead.
        due_ids = sorted(
            (rid for rid, due_at in self.next_due.items() if now >= due_at),
            key=lambda rid: self.next_due[rid],
        )
        if not due_ids:
            return

        reminder = self.config.get_reminder_by_id(due_ids[0])
        if not reminder:
            del self.next_due[due_ids[0]]
            return
        self.next_due[reminder["id"]] = now + self.config.get_reminder_interval_seconds(reminder)
        self._update_next_trigger_summary()
        self._fire_popup(reminder)

    def update_countdown_display(self):
        if self.is_paused:
            self.stat_timer_lbl.setText("⏱ Paused")
            if hasattr(self, "tray_status_action"):
                self.tray_status_action.setText("Smjrifle Reminder: Paused ⏸")
            return

        if self.next_trigger_time:
            remaining = max(0, int(self.next_trigger_time - time.time()))
            mins = remaining // 60
            secs = remaining % 60
            time_str = f"{mins:02d}:{secs:02d}"
            self.stat_timer_lbl.setText(f"⏱ Next in: {time_str}")
            if hasattr(self, "tray_status_action"):
                self.tray_status_action.setText(f"Next Reminder: {time_str}")

    def _fire_popup(self, reminder: Dict[str, Any]):
        if self.active_popup:
            try:
                self.active_popup.close()
            except Exception:
                pass
        self.active_popup = SmjrifleReminderPopup(self, reminder)
        self.active_popup.trigger_display()

    def show_notification(self):
        """Manual trigger (tray '⚡ Remind Now' / Settings 'Test
        Notification'). Picks one reminder via the existing cycle/random
        rotation and reschedules just that one -- every other reminder's
        independent countdown is left untouched."""
        reminder = self.config.get_next_reminder()
        self.next_due[reminder["id"]] = time.time() + self.config.get_reminder_interval_seconds(reminder)
        self._update_next_trigger_summary()
        self._fire_popup(reminder)

    def init_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        if not self.app_icon.isNull():
            self.tray_icon.setIcon(self.app_icon)
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(2, 132, 199))
            self.tray_icon.setIcon(QIcon(pixmap))

        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: #18181b;
                color: #f4f4f5;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px;
                font-family: {FONT_FAMILY};
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: #0284c7;
            }}
        """)

        self.tray_status_action = QAction("Smjrifle Reminder: Active", self)
        self.tray_status_action.setEnabled(False)
        self.tray_menu.addAction(self.tray_status_action)
        self.tray_menu.addSeparator()

        trigger_action = QAction("⚡ Remind Now", self)
        trigger_action.triggered.connect(self.show_notification)
        self.tray_menu.addAction(trigger_action)

        self.pause_action = QAction("⏸ Pause Reminders", self)
        self.pause_action.triggered.connect(self.toggle_pause)
        self.tray_menu.addAction(self.pause_action)

        settings_action = QAction("⚙ Preferences & Dashboard...", self)
        settings_action.triggered.connect(self.show_and_activate)
        self.tray_menu.addAction(settings_action)

        self.tray_menu.addSeparator()

        quit_action = QAction("✕ Quit Smjrifle Reminder", self)
        quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        # On macOS, clicking the menu bar icon natively opens the context menu.
        # Only trigger direct window activation on DoubleClick (or Trigger on Windows/Linux)
        # to prevent AppKit NSMenuTrackingSession event collisions and crashes.
        if sys.platform != "darwin" and reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_and_activate()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_and_activate()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            # _tick() already no-ops while paused; nothing to stop.
            if hasattr(self, "pause_action"):
                self.pause_action.setText("▶ Resume Reminders")
            self.status_badge.setText("⏸ Paused")
            self.status_badge.setStyleSheet("""
                background: rgba(234, 179, 8, 0.2);
                color: #facc15;
                border: 1px solid rgba(234, 179, 8, 0.4);
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
        else:
            if hasattr(self, "pause_action"):
                self.pause_action.setText("⏸ Pause Reminders")
            self.status_badge.setText("● Active")
            self.status_badge.setStyleSheet("""
                background: rgba(34, 197, 94, 0.2);
                color: #4ade80;
                border: 1px solid rgba(34, 197, 94, 0.4);
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
            # Fresh countdown for everything on resume, not a backlog of
            # reminders that all went overdue during the pause and now fire
            # back-to-back the instant you resume.
            self._reset_all_schedules()
        self.update_countdown_display()

    def show_and_activate(self):
        self.update_stats_ui()
        self.refresh_character_cards()
        self.show()
        self.raise_()
        self.activateWindow()

    def start_and_minimize(self):
        self.restart_timer()
        self.hide()
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Smjrifle Reminder Active",
                "Running quietly in your system tray. Click icon anytime to open settings.",
                QSystemTrayIcon.MessageIcon.Information,
                2500
            )

    def closeEvent(self, event):
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
        else:
            event.accept()

    def quit_app(self):
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Smjrifle Reminder")
    app.setApplicationDisplayName("Smjrifle Desktop Reminder")
    app.setQuitOnLastWindowClosed(False)

    # macOS: run as a menu-bar-only background app, no Dock icon. Windows and
    # Linux need no equivalent call -- not showing the main window (below)
    # already keeps them off the taskbar / out of a normal window list.
    autostart.hide_from_macos_dock()

    icon_path = get_asset_path("icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = SmjrifleReminderApp()
    if hasattr(window, "tray_icon") and window.tray_icon.isVisible():
        # Tray is available: start quietly in the background, exactly like a
        # normal login-item run -- the dashboard opens only when requested
        # from the tray icon.
        window.start_and_minimize()
    else:
        # No system tray on this desktop environment -- fall back to a
        # normal visible window so the app is still reachable at all.
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
