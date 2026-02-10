# 🌀 VoidLoop: Enhanced Edition

<div align="center">

![Version](https://img.shields.io/badge/Version-3.0%20Enhanced-00ff96?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.5+-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red?style=for-the-badge)

### *An intense top-down shooter in an endless digital void*

**Survive • Evolve • Conquer**

[🎮 Quick Start](#-quick-start) • [🕹️ Game Modes](#️-game-modes) • [⌨️ Controls](#️-controls) • [📖 How to Play](#-how-to-play)

---

</div>

## 📖 About

**VoidLoop** is a fast-paced **top-down arcade shooter** where you're trapped in a hostile digital simulation. Each game mode offers a unique challenge:

- **STORY**: Campaign with fragments and epic boss fights
- **ENDLESS**: Infinite survival with escalating difficulty  
- **TIME ATTACK**: Fast-paced combat with evolving weapons
- **BOSS RUSH**: Face increasingly powerful bosses with unique abilities
- **HORDE**: Survive waves using only melee combat

---

## ✨ Key Features

### 🎯 Five Unique Game Modes

Each mode has distinct mechanics, objectives, and strategies:

| Mode | Weapon | Walls | Fragments | Objective |
|------|--------|-------|-----------|-----------|
| 🎬 **STORY** | Buy | ✓ | ✓ | Collect fragments, fight bosses every 5 levels |
| ♾️ **ENDLESS** | Start | ✗ | ✗ | Survive infinite waves, level up continuously |
| ⏱️ **TIME ATTACK** | Start | ✗ | ✗ | Kill enemies to upgrade weapon, maximize kills |
| 🦸 **BOSS RUSH** | Start | ✗ | ✗ | Defeat 5 progressive boss levels |
| 🌊 **HORDE** | Melee | ✗ | ✗ | Survive 10 waves per level with melee weapon |

### 👾 Enemy Types

- 🔴 **Normal**: Standard chase and shoot (1 HP)
- 🟤 **Tank**: Slow, triple-shot spread attack (3+ HP)
- 🟠 **Sniper**: Long-range fast bullets, keeps distance (1 HP)
- 🟣 **Kamikaze**: Lightning-fast suicide attacker (1 HP)

### 🦸 Boss Evolution (Boss Rush)

Bosses gain new abilities each level:

1. **Level 1**: Basic shooting attacks
2. **Level 2**: Dash attacks toward player
3. **Level 3**: Teleportation with warning flashes
4. **Level 4**: Spike traps that grow from the ground
5. **Level 5**: All abilities combined - ultimate challenge

### ⚡ Core Mechanics

- **Dash System**: Quick teleport on cooldown (45 frames)
- **Sprint**: 1.8x speed boost while held
- **Power-ups** (Story/Endless only):
  - 🛡️ **Shield**: 5s invincibility
  - ⚡ **Speed**: 4s +50% movement
  - 💥 **Double Damage**: 3s 2x damage
  - 🔫 **Rapid Fire**: 3.3s triple fire rate

- **Combo System**: Chain kills for bonus coins (2-second window)
- **Weapon Evolution** (Time Attack): +1 damage every 10 kills
- **Melee Combat** (Horde): Swing mace with mouse click

### 🎨 Visual Effects

- Dynamic particle systems
- Glow effects and visual polish
- Smooth animations
- Real-time HUD with live stats

---

## 🎮 Game Modes (Detailed)

### 🎬 STORY Mode

**Classic campaign experience**

- Collect **4 + level** gold fragments to progress
- **Boss fights every 5 levels** with multi-phase combat
- **Wall obstacles** from level 3+ (use as cover)
- **Buy weapons** at shop between levels
- **Power-ups** spawn randomly
- Save progress between sessions

**Strategy**: Use walls for cover, save coins for weapon early, maintain combos for bonus income.

---

### ♾️ ENDLESS Mode

**Infinite survival challenge**

- No fragments to collect
- **Start with weapon unlocked**
- **No walls** - pure combat skill
- Levels increase automatically when enemies cleared
- Difficulty scales infinitely
- **Power-ups** available
- Perfect for high-score runs

**Strategy**: Focus on movement and positioning, use dash aggressively, prioritize Sniper enemies.

---

### ⏱️ TIME ATTACK Mode

**Kill-based weapon progression**

- No fragments or walls
- **Start with basic weapon**
- **Weapon upgrades every 10 kills** (+1 damage)
- No power-ups (weapon IS the progression)
- **Goal**: Maximize kills in shortest time
- Enemy spawn rate increases with level

**Strategy**: Aggressive playstyle, prioritize weak enemies for fast upgrades, don't miss shots.

---

### 🦸 BOSS RUSH Mode

**Progressive boss gauntlet**

- No fragments, no enemies, no walls
- **Start with weapon unlocked**
- **5 boss levels** with unique abilities:
  
  **Boss Level 1** - Basic Shooter
  - Circular movement pattern
  - Single-target shots
  
  **Boss Level 2** - Dasher
  - Adds dash attacks
  - More aggressive movement
  
  **Boss Level 3** - Teleporter
  - Can teleport with cyan warning
  - Unpredictable positioning
  
  **Boss Level 4** - Spike Master
  - Summons spike traps
  - Requires constant movement
  
  **Boss Level 5** - Ultimate Form
  - **ALL ABILITIES COMBINED**
  - Shoots + Dashes + Teleports + Spikes
  - Maximum difficulty

- HP scales: 50 + (level × 20)
- 3-phase combat (100-60-30% HP breakpoints)

**Strategy**: Learn patterns, dodge telegraphed attacks, save dash for emergencies.

---

### 🌊 HORDE Mode

**Melee survival**

- **Melee weapon only** (no shooting)
- **Wave-based**: 10 waves per level
- Wave difficulty: 5 + level×2 + wave×3 enemies
- **No walls, no fragments, no power-ups**
- All 4 enemy types spawn
- **Left-click** to swing mace

**Melee weapon stats**:
- Damage: 2 per hit
- Swing duration: 15 frames
- Cooldown: 30 frames
- Range: 50 pixels

**Strategy**: Time swings carefully, kite enemies into groups, use dash to reposition.

---

## ⌨️ Controls

### 🎮 Player 1

| Action | Key |
|--------|-----|
| **Movement** | `W` `A` `S` `D` |
| **Sprint** | `Left Ctrl` (hold) |
| **Dash** | `Left Shift` |
| **Shoot** | `Left Mouse` (aim with cursor) |
| **Melee** | `Left Mouse` (Horde mode only) |
| **Pause** | `ESC` |

### 👥 Player 2 (Co-op)

| Action | Key |
|--------|-----|
| **Movement** | `↑` `↓` `←` `→` |
| **Sprint** | `Right Ctrl` |
| **Dash** | `Right Shift` |

### 💡 Advanced Techniques

```
DASH + SPRINT = Maximum mobility
DASH through bullet patterns in emergencies
Use walls (Story) to block enemy fire
Maintain 2s combo window for bonus coins
Power-up combos: SHIELD + RAPID_FIRE = invincible DPS
Time Attack: Don't miss shots - accuracy > fire rate
Boss Rush: Learn boss tells before attacks
Horde: Swing timing is everything
```

---

## 🚀 Quick Start

### 📋 Requirements

- **Python 3.8+**
- **Pygame 2.5+**
- ~50 MB disk space

### 🐧 Linux / macOS

```bash
# Clone repository
git clone https://github.com/YourUsername/VoidLoop.git
cd VoidLoop

# Install dependencies
pip install -r requirements.txt

# Launch game
python3 play.py
```

### 🪟 Windows

```powershell
# Install dependencies
pip install -r requirements.txt

# Launch game
python play.py
```

---

## 📂 Project Structure

```
VoidLoop/
├── play.py                    # Launcher with game mode selection
├── VoidLoop/
│   ├── voidloopgame.py        # Main game engine
│   ├── lang/                  # Localization files
│   │   ├── dialogues_it.json  # Italian
│   │   ├── dialogues_en.json  # English
│   │   ├── dialogues_es.json  # Spanish
│   │   └── dialogues_fr.json  # French
│   └── saves/
│       └── savegame.json      # Progress save
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🎯 Difficulty Levels

| Difficulty | Speed Mult. | Spawn Rate | Weapon Cost | Recommended For |
|------------|-------------|------------|-------------|-----------------|
| 🟢 **Easy** | 0.7x | 0.5% | 5 coins | Beginners |
| 🟡 **Normal** | 1.0x | 0.9% | 10 coins | Balanced play |
| 🔴 **Hard** | 1.4x | 1.5% | 20 coins | Veterans |
| 💀 **Nightmare** | 1.9x | 2.5% | 30 coins | Masochists |

---

## 💾 Save System

### Auto-saves:
- ✅ Level completion
- ✅ Weapon purchase
- ✅ Shop entry

### Manual save:
- Press `ESC` → **SAVE GAME**

**Save location**: `VoidLoop/saves/savegame.json`

**Save data includes**:
```json
{
  "level": 12,
  "coins": 187,
  "achievements": []
}
```

---

## 🎨 Customization

### Ship Colors

Edit `voidloopgame.py`:

```python
COLOR_MAP = {
    "Neon Green": (0, 255, 150),
    "Cyber Blue": (0, 150, 255),
    "Void Purple": (180, 0, 255),
    "Your Color": (R, G, B)  # Add custom color
}
```

### Difficulty Tweaking

```python
DIFF_SETTINGS = {
    "CUSTOM": {
        "speed_mult": 1.2,    # Enemy speed
        "spawn_rate": 0.012,  # Spawn frequency
        "cost": 15            # Weapon price
    }
}
```

---

## 🌍 Languages

Fully localized in 4 languages:
- 🇮🇹 **Italian** (Italiano)
- 🇬🇧 **English**
- 🇪🇸 **Spanish** (Español)
- 🇫🇷 **French** (Français)

All UI, dialogues, and pause menu translated.

---

## 🛠️ Troubleshooting

<details>
<summary><b>Game file not found error</b></summary>

**Solution**: Ensure file structure matches:
```
VoidLoop/
├── play.py
└── VoidLoop/
    └── voidloopgame.py
```
</details>

<details>
<summary><b>No module named 'pygame'</b></summary>

**Solution**:
```bash
pip install pygame --upgrade
```
</details>

<details>
<summary><b>Low framerate / lag</b></summary>

**Solutions**:
- Use windowed mode
- Close background apps
- Update graphics drivers
</details>

<details>
<summary><b>Save file corruption</b></summary>

**Solution**:
```bash
rm VoidLoop/saves/savegame.json
# Start new game
```
</details>

---

## 🗺️ Roadmap

### ✅ Version 3.0 (Current)
- [x] 5 unique game modes
- [x] Enhanced boss mechanics (5 levels)
- [x] Melee combat system
- [x] Weapon evolution (Time Attack)
- [x] Pause menu with save
- [x] Multi-language support

### 🔜 Version 3.1 (Planned)
- [ ] Achievements system
- [ ] Statistics tracking
- [ ] Sound effects
- [ ] Background music
- [ ] More power-ups

### 🔮 Version 3.2+ (Future)
- [ ] Online leaderboards
- [ ] Gamepad support
- [ ] Level editor
- [ ] Daily challenges
- [ ] Multiplayer

---

## 📜 License

**VoidLoop Enhanced Edition** - Copyright © 2026  
**All Rights Reserved**

### ✅ Permitted:
- ✔️ Personal use and gameplay
- ✔️ Educational study of source code
- ✔️ Sharing via GitHub link

### ❌ Prohibited:
- ❌ Commercial use
- ❌ Code redistribution
- ❌ Asset reuse in other projects
- ❌ Modified versions

---

## 👤 Credits

**Created by**: BitJacker  
**Engine**: Pygame 2.5+  
**Language**: Python 3.8+  
**Version**: 3.0 Enhanced Edition

### Special Thanks
- Pygame Community
- Python Software Foundation
- All beta testers
- **You** for playing!

---

## 🎮 Pro Tips

```
🎯 GENERAL
- Dash cooldown is 45 frames (~0.75s) - use wisely
- Combo window is 120 frames (2s) - chain kills fast
- Sprint drains no resource - use liberally

📖 STORY MODE
- Buy weapon ASAP (levels 1-3 are tutorial)
- Walls block enemy bullets - use as cover
- Save SHIELD power-up for boss Phase 3
- Boss every 5 levels - prepare with coins

♾️ ENDLESS
- No walls = pure movement skill
- Prioritize Sniper enemies (long range)
- Level difficulty never caps - survive as long as possible

⏱️ TIME ATTACK
- Every 10 kills = +1 damage
- Speed > accuracy until weapon maxed
- Kamikaze enemies = easy kills for upgrades

🦸 BOSS RUSH
- Boss Level 1-2: Learn basic patterns
- Boss Level 3: Watch for teleport flashes
- Boss Level 4: Keep moving to avoid spikes
- Boss Level 5: Requires mastery of all mechanics

🌊 HORDE
- Melee timing >>> button mashing
- Swing cooldown is 30 frames - count it
- Kite enemies into tight groups
- Tank enemies take 2 swings - prioritize them last
```

---

<div align="center">

## 💖 Enjoy VoidLoop Enhanced Edition!

**Made with ❤️ and ☕ by BitJacker**

[![Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Powered%20by-Pygame-green?style=for-the-badge)](https://www.pygame.org/)

[🔝 Back to Top](#-voidloop-enhanced-edition)

---

**Version 3.0 Enhanced Edition** | **2026**

</div>
