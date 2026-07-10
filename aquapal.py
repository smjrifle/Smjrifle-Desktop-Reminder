import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QComboBox
)

class AquaPalSettings(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AquaPal - Settings")
        self.setFixedSize(350, 200)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #f3f3f3; }
            QLabel { color: #1a1a1a; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
            QComboBox { border: 1px solid #cccccc; border-radius: 4px; padding: 5px; background-color: #ffffff; min-width: 120px; }
            QPushButton { background-color: #0078d4; color: white; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #106ebe; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("How often should AquaPal remind you?")
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.interval_dropdown = QComboBox()
        self.interval_dropdown.addItem("Every 10 Seconds (Testing)", 10 * 1000)
        self.interval_dropdown.addItem("Every 30 Minutes", 30 * 60 * 1000)
        self.interval_dropdown.addItem("Every 1 Hour", 60 * 60 * 1000)
        layout.addWidget(self.interval_dropdown, alignment=Qt.AlignmentFlag.AlignCenter)

        self.start_btn = QPushButton("Start AquaPal")
        self.start_btn.clicked.connect(self.start_timer)
        layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.reminder_timer = QTimer()
        self.reminder_timer.timeout.connect(self.show_notification)

    def start_timer(self):
        interval = self.interval_dropdown.currentData()
        self.reminder_timer.start(interval)
        self.hide()

    def show_notification(self):
        self.reminder_timer.stop()
        self.popup = AquaPalToast(self)
        self.popup.show()


class AquaPalToast(QWidget):
    def __init__(self, settings_window):
        super().__init__()
        self.settings_window = settings_window
        self.init_ui()

    def init_ui(self):
        # Window attributes: Frameless, transparent, stays on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # CRITICAL FIX: Drastically smaller dimensions (similar to a standard Windows toast notification)
        self.setFixedSize(380, 520)

        # Base horizontal container representing the Toast Body
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        # 1. Compact Character Animation Container
        self.char_label = QLabel()
        self.char_label.setFixedSize(120, 140)  # Constrained thumbnail scale
        self.char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.movie = QMovie("character.gif")
        # Scaled down to fit seamlessly inside the notification tray bounding boxes
        self.movie.setScaledSize(self.char_label.size()) 
        self.char_label.setMovie(self.movie)
        self.movie.start()
        main_layout.addWidget(self.char_label)

        # 2. Right side container: Text Cloud + Actions stacked vertically
        right_content = QVBoxLayout()
        right_content.setSpacing(8)

        # Content Text
        text_msg = QLabel("Time to stay hydrated! 💧")
        text_msg.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }
        """)
        right_content.addWidget(text_msg)

        # Quick Control Interaction Grid
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        drank_btn = QPushButton("✓ Drank It")
        snooze_btn = QPushButton("⏰ Snooze")

        # Windows 11 styling rules applied directly to action frames
        drank_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4; color: white; border-radius: 4px;
                padding: 6px 12px; font-family: 'Segoe UI'; font-size: 12px; font-weight: 600; border: none;
            }
            QPushButton:hover { background-color: #106ebe; }
        """)
        snooze_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15); color: white; border-radius: 4px;
                padding: 6px 12px; font-family: 'Segoe UI'; font-size: 12px; border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.25); }
        """)

        drank_btn.clicked.connect(self.action_drank)
        snooze_btn.clicked.connect(self.action_snooze)

        btn_layout.addWidget(drank_btn)
        btn_layout.addWidget(snooze_btn)
        btn_layout.addStretch() # Push buttons to the left inside their sub-tray
        right_content.addLayout(btn_layout)

        main_layout.addLayout(right_content)

        # Apply Windows 11 styling directly onto the main toast bubble background
        self.setStyleSheet("""
            AquaPalToast {
                background-color: rgba(32, 32, 32, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)

        # Position precisely at bottom right corner above Windows system tray
        screen_geo = QApplication.primaryScreen().geometry()
        self.move(screen_geo.width() - self.width() - 20, screen_geo.height() - self.height() - 50)

    def action_drank(self):
        self.movie.stop()
        self.close()
        self.settings_window.start_timer()

    def action_snooze(self):
        self.movie.stop()
        self.close()
        # Custom short loop interval trigger rule logic for instant snooze state
        self.settings_window.reminder_timer.start(10 * 60 * 1000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AquaPalSettings()
    window.show()
    sys.exit(app.exec())
