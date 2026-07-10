# 💧 AquaPal - Desktop Water Reminder

**AquaPal** is a lightweight, modern Windows 11 desktop assistant designed to help you stay properly hydrated throughout your busy workday. Built completely in Python, AquaPal runs unobtrusively in the background and surfaces as a beautiful, compact toast notification featuring a custom-animated character to remind you when it's time to take a drink.

---

## ✨ Features

* **Windows 11 Native Aesthetic:** Features a beautifully styled, compact dark acrylic notification tray theme (`380x120px`) that aligns seamlessly with modern operating system notifications.
* **Animated Hydration Buddy:** Displays a seamless, loopable animated character to bring visual charm to your daily wellness routine.
* **Flexible Timing Configurations:** Pick your preferred custom tracking intervals (e.g., Every 30 Minutes or Every 1 Hour) right from an intuitive startup configuration deck.
* **Interactive Control Blocks:** Includes quick-action mechanics allowing you to log your drink instantly or trigger a **10-minute snooze extension** loop if you are away from your desk.
* **Zero Distraction Mode:** Keeps your terminal and command screens hidden, running quietly in your device background environments.

---

## 🛠️ Technology Stack

* **Language:** Python 
* **UI Framework:** PyQt6 (for modern UI component structures and layouts)
* **Deployment Pipeline:** PyInstaller (compiled down to a standalone Windows `.exe`)

---

## 🚀 Getting Started (For Users)

If you just want to run the application on your computer:

1. Download the executable file from the latest release bundle.
2. Ensure that your custom `character.gif` animation file rests directly in the **same directory folder** right next to `aquapal.exe`.
3. Double-click `aquapal.exe`, select your timing window interval rule from the options menu dropdown, and press **Start AquaPal**.

---

## 💻 Development & Building from Source

If you want to tweak the code or build the project directly from your terminal:

### 1. Requirements Installation
```bash
pip install PyQt6 pyinstaller

### 2. Running Locally
 
python aquapal.py
### 3. Compiling Down to a Standalone Executable
To convert the script into a single, clean .exe application without exposing a background terminal prompt shell:
 
pyinstaller --noconsole --onefile aquapal.py
⚠️ Important Deployment Note: Once PyInstaller compiles the code framework down into your root directory build maps, look inside the newly generated dist/ project folder and manually copy/paste your character.gif file right beside the executable.
