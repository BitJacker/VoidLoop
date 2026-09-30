"""Campaign structure and the stage specification of every game mode.

Story mode is 6 sectors x 4 stages (three fragment runs, then a boss).
"""
from dataclasses import dataclass, field

SECTORS = 6
STAGES_PER_SECTOR = 4
STORY_STAGES = SECTORS * STAGES_PER_SECTOR
BOSS_ORDER = ("sentinel", "weaver", "inferno", "cryo", "glitch", "origin")

SECTOR_WEIGHTS = (
    {"drone": 100},
    {"drone": 58, "lancer": 24, "comet": 18},
    {"drone": 38, "bulwark": 16, "lancer": 14, "comet": 16, "splitter": 16},
    {"drone": 28, "bulwark": 14, "lancer": 12, "comet": 12, "splitter": 14, "orbiter": 20},
    {"drone": 24, "bulwark": 15, "lancer": 14, "comet": 12, "splitter": 14, "orbiter": 21},
    {"drone": 20, "bulwark": 16, "lancer": 14, "comet": 12, "splitter": 16, "orbiter": 22},
)


@dataclass
class StageSpec:
    mode: str                     # STORY / ENDLESS / TIME_ATTACK / BOSS_RUSH / HORDE
    kind: str                     # fragments | boss | endless | timeattack | horde
    level: int                    # 1-based difficulty level (scales enemy stats)
    sector: int                   # 0..5 (biome)
    index: int = 0                # story stage index / boss-rush number / horde round
    goal: int = 0                 # fragments to collect
    boss: str = ""
    boss_scale: float = 1.0
    weights: dict = field(default_factory=lambda: {"drone": 1})
    max_enemies: int = 6
    walls: int = 0
    hazards: bool = True
    intensity: float = 0.5
    shooting: bool = True         # do enemies fire bullets?
    elite_chance: float = 0.0
    carry: dict = field(default_factory=dict)      # values carried between stages (time attack)


def weights_for_level(level):
    """Which enemy types exist at a given level (Endless / Time Attack / Horde)."""
    w = {"drone": 100}
    if level >= 2:
        w["comet"] = 14
    if level >= 3:
        w["lancer"] = 18
    if level >= 5:
        w["bulwark"] = 16
    if level >= 7:
        w["splitter"] = 14
    if level >= 9:
        w["orbiter"] = 18
    return w


def story_spec(index, loop=1):
    index = max(0, min(index, STORY_STAGES - 1))
    sector, k = divmod(index, STAGES_PER_SECTOR)
    level = index + 1 + 6 * (loop - 1)
    is_boss = k == STAGES_PER_SECTOR - 1
    weights = dict(SECTOR_WEIGHTS[sector])
    if sector == 0 and k >= 2:
        weights = {"drone": 85, "comet": 15}
    elite = 0.0 if sector < 3 else 0.06 + 0.02 * (sector - 3)
    return StageSpec(
        mode="STORY", kind="boss" if is_boss else "fragments", level=level, sector=sector, index=index,
        goal=0 if is_boss else 5 + 2 * k + sector,
        boss=BOSS_ORDER[sector] if is_boss else "",
        boss_scale=1.0 + 0.25 * (loop - 1),
        weights=weights,
        max_enemies=4 if is_boss else min(3 + level // 2, 13),
        walls=0 if (index < 2 or is_boss) else min(2 + index // 3, 8),
        hazards=sector > 0 and (not is_boss or sector in (1, 5)),
        intensity=0.45 + 0.2 * k + 0.03 * sector,
        shooting=index >= 2,
        elite_chance=elite,
    )


def endless_spec(level=1):
    sector = ((level - 1) // 3) % SECTORS
    return StageSpec(
        mode="ENDLESS", kind="endless", level=level, sector=sector, index=level,
        weights=weights_for_level(level), max_enemies=min(4 + level, 16), walls=0,
        hazards=sector > 0, intensity=min(1.3, 0.45 + 0.06 * level), shooting=level >= 2,
        elite_chance=0.0 if level < 8 else 0.06,
    )


def time_attack_spec(level=1, carry=None):
    sector = ((level - 1) // 2) % SECTORS
    return StageSpec(
        mode="TIME_ATTACK", kind="timeattack", level=level, sector=sector, index=level,
        goal=8 + 2 * level, weights=weights_for_level(level + 1), max_enemies=min(5 + level, 15),
        walls=0 if level < 3 else min(level, 6), hazards=sector > 0, intensity=min(1.3, 0.45 + 0.08 * level),
        shooting=level >= 2, elite_chance=0.0 if level < 6 else 0.05, carry=dict(carry or {}),
    )


def boss_rush_spec(n=0):
    """The n-th boss of a Boss Rush (0-based). Bosses repeat, stronger, after the sixth."""
    sector = n % SECTORS
    cycle = n // SECTORS
    return StageSpec(
        mode="BOSS_RUSH", kind="boss", level=4 * (sector + 1) + 12 * cycle, sector=sector, index=n,
        boss=BOSS_ORDER[sector], boss_scale=1.0 + 0.4 * cycle, max_enemies=0, walls=0,
        hazards=sector in (1, 5), intensity=0.6, shooting=True,
    )


def horde_spec(round_no=1):
    sector = (round_no - 1) % SECTORS
    level = 2 + 3 * round_no
    return StageSpec(
        mode="HORDE", kind="horde", level=level, sector=sector, index=round_no,
        weights=weights_for_level(level), max_enemies=min(9 + round_no * 2, 16), walls=0 if round_no == 1 else min(round_no + 1, 5),
        hazards=sector > 0, intensity=min(1.3, 0.45 + 0.1 * round_no), shooting=round_no >= 2,
        elite_chance=0.0 if round_no < 3 else 0.08,
    )
