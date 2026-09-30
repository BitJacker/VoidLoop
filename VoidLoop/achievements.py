"""Achievements: definitions and the checks that unlock them."""

# id, icon
ACHIEVEMENTS = (
    ("first_blood", "star"),
    ("combo_master", "star"),
    ("combo_legend", "star"),
    ("boss_slayer", "skull"),
    ("untouchable", "shield"),
    ("dasher", "dash"),
    ("collector", "fragment"),
    ("graze_king", "pulse"),
    ("pulse_master", "pulse"),
    ("rich", "coin"),
    ("sector_3", "skull"),
    ("loop_breaker", "star"),
    ("loop_keeper", "star"),
    ("nightmare", "skull"),
    ("marathon", "star"),
    ("time_lord", "star"),
    ("horde_master", "mace"),
    ("rush_master", "skull"),
    ("coop", "heart"),
)
ACHIEVEMENT_IDS = tuple(a for a, _ in ACHIEVEMENTS)
ICONS = dict(ACHIEVEMENTS)


def live_check(app, run, world):
    """Cheap checks made while playing (so toasts pop up at the right moment)."""
    st = app.save.stats
    unlock = app.unlock
    if st["kills"] + world.kills >= 1:
        unlock("first_blood")
    if world.best_combo >= 10:
        unlock("combo_master")
    if world.best_combo >= 30:
        unlock("combo_legend")
    if st["dashes"] + world.dashes >= 100:
        unlock("dasher")
    if st["grazes"] + world.grazes >= 250:
        unlock("graze_king")
    if world.max_pulse_kills >= 5:
        unlock("pulse_master")
    if run.loadout.coins >= 200:
        unlock("rich")
    if run.mode == "ENDLESS" and world.rules.total_frames >= 5 * 60 * 60:
        unlock("marathon")
    if st["fragments"] + world.fragments >= 100:
        unlock("collector")


def stage_check(app, run, world, cleared):
    """Checks made when a stage ends."""
    live_check(app, run, world)
    unlock = app.unlock
    if cleared:
        if world.hits_taken == 0 and world.spec.kind != "endless":
            unlock("untouchable")
        if world.spec.mode == "STORY" and run.difficulty == "NIGHTMARE":
            unlock("nightmare")
        if run.players == 2 and world.spec.mode == "STORY":
            unlock("coop")
        if world.spec.kind == "boss":
            unlock("boss_slayer")
            if world.spec.mode == "STORY" and world.spec.sector >= 2:
                unlock("sector_3")
        if world.spec.mode == "HORDE":
            unlock("horde_master")
    if run.mode == "TIME_ATTACK" and run.ta_level >= 5:
        unlock("time_lord")
    if run.mode == "BOSS_RUSH" and run.index >= 6:
        unlock("rush_master")
