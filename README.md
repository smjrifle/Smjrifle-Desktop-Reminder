# 💧 Smjrifle Desktop Reminder

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()
[![Release](https://img.shields.io/badge/Release-v1.0.0-orange.svg)]()

> **Smjrifle Desktop Reminder** is a cross-platform desktop pet companion and wellness assistant. A hand-drawn animated pixel mascot walks directly onto your desktop screen and prompts you with a floating speech bubble to drink water, fix your posture, or take wellness breaks.

---

## ✨ Features

- 🚶 **True Floating Desktop Companion**:
  - The pixel character glides directly onto your screen with smooth easing curves (`OutCubic`).
  - 100% transparent background with zero rigid box enclosures or borders.
- 💬 **Acrylic Glassmorphism Speech Bubble**:
  - Displays context-aware action buttons: **`✓ I Drank Water!`** (for hydration) or **`✓ Completed`** (for wellness).
  - Quick **`⏰ Snooze (10m)`** and direct settings shortcut.
- 👥 **Companion Mascots**:
  - 🎾 **Aqua Athlete (Tennis)**: Hand-drawn 8-frame walking & drinking cycle with animated water droplets (`💧✨`) and celebration star (`⭐`).
  - ⚽ **Striker #7 (CR7 Tribute)**: Athletic soccer striker companion in the red #7 kit.
- 🔥 **Daily Streak Tracker & Productivity Stats**:
  - Tracks consecutive daily streaks and total logged breaks.
- 📝 **Multi-Reminder Management (CRUD)**:
  - Create and customize reminders (Hydration, 20-20-20 Eye Rest, Posture Check, Stretch).
  - Delivery modes: Sequential cycle or randomized picks.
- 🖥 **Cross-Platform Native System Tray**:
  - Runs unobtrusively in the macOS Menu Bar, Windows System Tray, or Linux notification area with live countdown timers.

---

## 🚀 Quick Start

### 1. Clone the Repository

**From GitHub:**
```bash
git clone https://github.com/smjrifle/Smjrifle-Desktop-Reminder.git
cd Smjrifle-Desktop-Reminder
```

**From GitLab:**
```bash
git clone https://gitlab.com/smjrifle/smjrifle-desktop-reminder.git
cd smjrifle-desktop-reminder
```

### 2. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run the App

```bash
python main.py
```

---

## 📦 Standalone macOS App

You can run or install the pre-built standalone macOS application directly without needing Python:

1. Download or locate `dist/SmjrifleReminder-macOS.zip` (or `dist/SmjrifleReminder.app`).
2. Unzip and drag `SmjrifleReminder.app` into your **`/Applications`** folder.
3. Double-click to launch!

### Building from Source with PyInstaller:

#### 🍎 macOS
```bash
pyinstaller --noconsole --windowed \
  --name "SmjrifleReminder" \
  --icon "icon.icns" \
  --add-data "character.gif:." \
  --add-data "icon.png:." \
  --add-data "icon.icns:." \
  --add-data "assets:assets" \
  -y --clean \
  main.py
```

#### 🪟 Windows
```cmd
pyinstaller --noconsole --onefile ^
  --name "SmjrifleReminder" ^
  --icon "icon.ico" ^
  --add-data "character.gif;." ^
  --add-data "icon.png;." ^
  --add-data "assets;assets" ^
  -y --clean ^
  main.py
```

#### 🐧 Linux
```bash
pyinstaller --noconsole --onefile \
  --name "smjrifle-reminder" \
  --icon "icon.png" \
  --add-data "character.gif:." \
  --add-data "icon.png:." \
  --add-data "assets:assets" \
  -y --clean \
  main.py
```

---

## 🌐 Dual Public Release (GitHub & GitLab)

To sync and push your repository to both **GitHub** and **GitLab**:

```bash
# 1. Stage and commit your changes
git add .
git commit -m "feat: release Smjrifle Desktop Reminder v1.0.0"

# 2. Configure GitHub remote
git remote add github https://github.com/smjrifle/Smjrifle-Desktop-Reminder.git

# 3. Configure GitLab remote
git remote add gitlab git@gitlab.com:smjrifle/smjrifle-desktop-reminder.git

# 4. Push to both platforms
git push -u github main
git push -u gitlab main
```

---

## 🛡️ License & Originality

- **License**: [MIT License](LICENSE) — Copyright (c) 2026 Smjrifle.
- **Originality**: All source code, application architecture, UI components, and pixel sprite sequences were crafted specifically for this project with zero proprietary or third-party copyrighted assets.
