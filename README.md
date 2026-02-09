<div align="center">

# 🌀 VoidLoop: Cyber-Survival

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Pygame](https://img.shields.io/badge/pygame-2.5+-green.svg)](https://www.pygame.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

**A frenetic arcade shooter with minimalist aesthetics set in an infinite digital simulation**

[🎮 Features](#-main-features) • [🕹️ Controls](#️-game-controls) • [🛠️ Installation](#️-installation) • [📖 Guide](#-how-to-play)

![Game Screenshot](https://via.placeholder.com/800x400/0a0e27/00ff41?text=VoidLoop+Screenshot)

</div>

---

## 📖 Description

**VoidLoop** throws you into a hostile digital dimension where you must:
- 🎯 Collect **data fragments** to unlock new weapons
- 🛡️ Survive **progressive waves** of defense systems
- ⚡ Upgrade your ship in the **Arsenal Shop**
- 🔄 Break the infinite loop by conquering increasingly complex levels

Each match is unique thanks to the dynamic progression system and automatic progress saving.

---

## 🌟 Main Features

### 🎮 Gameplay
- **Progressive Level System**: Increasing difficulty with new enemies (Bullets, Walls, Armored Helicopters)
- **Integrated Arsenal Shop**: Spend collected credits to unlock devastating weapons
- **Precision Aiming**: Mouse-lock system for surgical accuracy
- **Smart Auto-Save**: Your progress is automatically saved

### 👥 Multiplayer Mode
- **Local Co-op (2 Players)**: Play with a friend on the same keyboard
- **Independent Controls**: Each player has their own control scheme

### 🌍 Localization
- 🇮🇹 Italian
- 🇬🇧 English
- 🇪🇸 Spanish
- 🇫🇷 French

### 🖥️ Graphics
- **Fullscreen HD**: Native support for high-resolution monitors
- **Adaptive Scaling**: Scalable graphics without quality loss
- **Minimalist Cyberpunk Aesthetic**: Clean and modern design

---

## 🕹️ Game Controls

<div align="center">

| Action | Player 1 | Player 2 |
|:---:|:---:|:---:|
| **Movement** | <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> | <kbd>↑</kbd> <kbd>←</kbd> <kbd>↓</kbd> <kbd>→</kbd> |
| **Aim & Shoot** | <kbd>Mouse</kbd> + <kbd>Left Click</kbd> | Shared with P1 |
| **Continue/Dialogues** | <kbd>Space</kbd> | <kbd>Space</kbd> |
| **Menu/Pause** | <kbd>ESC</kbd> | <kbd>ESC</kbd> |

</div>

---

## 🛠️ Installation

### 📋 System Requirements
- **Python**: 3.8 or higher
- **Pip**: Python package installer
- **RAM**: Minimum 512 MB
- **Disk Space**: ~50 MB

### 🐧 Linux (Ubuntu/Debian/Kali/Arch)
```bash
# 1. Clone the repository
git clone https://github.com/BitJacker/VoidLoop.git
cd VoidLoop

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip3 install -r requirements.txt

# 4. Launch the game
python3 play.py
```

### 🪟 Windows 10/11

#### Method 1: Manual Installation
1. Download and install [Python 3.8+](https://www.python.org/downloads/)
   - ⚠️ **Important**: Check "Add Python to PATH" during installation
2. Download this repository as [ZIP](https://github.com/BitJacker/VoidLoop/archive/refs/heads/main.zip)
3. Extract the contents to a folder
4. Open **PowerShell** or **CMD** in the game folder
5. Run the following commands:
```powershell
# Install dependencies
pip install -r requirements.txt

# Launch the game
python play.py
```

#### Method 2: Git Bash
```bash
git clone https://github.com/BitJacker/VoidLoop.git
cd VoidLoop
pip install -r requirements.txt
python play.py
```

### 🍎 macOS
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python3

# Clone and install
git clone https://github.com/BitJacker/VoidLoop.git
cd VoidLoop
pip3 install -r requirements.txt
python3 play.py
```

---

## 📖 How to Play

### 🎯 Objective
Survive as long as possible by collecting **data fragments** (green objects) and avoiding or destroying enemies.

### 💰 Progression System
1. **Collect Fragments**: Each green fragment gives you credits
2. **Complete Levels**: Overcome enemy waves to advance
3. **Visit the Shop**: Between levels, invest your credits in weapons
4. **Unlock Weapons**: After your first purchase, you can use the mouse to shoot

### 🎮 Survival Strategies
- **Constant Movement**: Never stay still
- **Strategic Collection**: Assess risk/benefit before taking a fragment
- **Use Walls**: Enemies can be blocked by obstacles
- **Manage Resources**: Don't waste credits, plan your purchases

---

## 📂 Project Structure
```
VoidLoop/
├── 📄 play.py                    # Main launcher with config menu
├── 📄 voidloopgame.py           # Game core engine
├── 📄 requirements.txt           # Python dependencies
├── 📄 README.md                  # This guide
├── 📄 LICENSE                    # Usage license
├── 📄 .gitignore                # Files to ignore in Git
├── 💾 savegame.json             # Save file (auto-generated)
├── 🌍 lang/                     # Localization
│   ├── dialogues_it.json        # Italian texts
│   ├── dialogues_en.json        # English texts
│   ├── dialogues_es.json        # Spanish texts
│   └── dialogues_fr.json        # French texts
└── 🐍 venv/                     # Python virtual environment (optional)
```

---

## 🔧 Troubleshooting

### ❌ Problem: `pygame not found`
**Solution**:
```bash
pip install pygame --upgrade
```

### ❌ Problem: Game is too slow
**Solutions**:
- Close heavy background applications
- Reduce screen resolution
- Update graphics card drivers

### ❌ Problem: `Permission Denied` error on Linux
**Solution**:
```bash
chmod +x play.py
```

### ❌ Problem: Save not working
**Solution**:
- Check folder permissions
- Make sure `savegame.json` is not read-only

---

## 🗺️ Roadmap

- [ ] **v1.1**: Endless mode with global leaderboard
- [ ] **v1.2**: New weapons and temporary power-ups
- [ ] **v1.3**: Boss fights at end of level
- [ ] **v2.0**: Online multiplayer
- [ ] **v2.1**: Integrated level editor
- [ ] **v2.2**: Gamepad/controller support

---

## 📜 License

**VoidLoop** - Copyright © 2026 BitJacker

### ✅ Permitted Usage:
- Download, run, and play the game for personal use
- Study the source code for educational purposes

### ❌ Prohibited Usage:
- Modify the source code and redistribute it
- Sell this software or use it for commercial purposes
- Use assets (images, dialogues, code) in other projects without permission

**All rights reserved.**

See the [LICENSE](LICENSE) file for full details.

---

## 👤 Author

Created with ❤️ by **BitJacker**

---

<div align="center">

**If you like VoidLoop, leave a ⭐ on GitHub!**

[🔝 Back to top](#-voidloop-cyber-survival)

</div>
```

---

## 📄 LICENSE (English Version)
```
VoidLoop - Copyright (c) 2026 BitJacker

PERMITTED USAGE:
- You are free to download, run, and play the game for personal use.
- You are free to study the source code for educational purposes.

PROHIBITED USAGE:
- You are NOT allowed to modify the source code and redistribute it.
- You are NOT allowed to sell this software or use it for any commercial purpose.
- You are NOT allowed to use assets (images, dialogue, code) in other projects without permission.

All rights reserved.
