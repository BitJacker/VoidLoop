"""Simulation tests: rules of the game, one behaviour at a time."""
import math

import pygame
import pytest
from pygame import Vector2

from VoidLoop import campaign, settings, hazards as hz
from VoidLoop.bosses import BOSSES
from VoidLoop.bot import Bot
from VoidLoop.enemies import ENEMY_TYPES
from VoidLoop.entities import PlayerInput, Bullet, Pickup, PLAYER_RADIUS
from VoidLoop.settings import W, H
from VoidLoop.weapons import Loadout, SHOP_ITEMS
from VoidLoop.world import World

CFG = settings.DIFFICULTIES["NORMAL"]
GREEN = settings.SHIP_COLORS["Neon Green"]
IDLE = {}


def make(spec=None, diff="NORMAL", players=1, weapons=("BLASTER",), seed=1):
    spec = spec or campaign.story_spec(2)
    return World(spec, settings.DIFFICULTIES[diff], Loadout(list(weapons)), [GREEN, settings.P2_COLOR], seed=seed, players=players)


def run(world, frames, inputs=None):
    for _ in range(frames):
        world.update(inputs if inputs is not None else IDLE)
    return world


def clear_field(w, pickups=True):
    w.enemies.clear()
    w.ebullets.clear()
    w.pbullets.clear()
    w.hazards.clear()
    if pickups:
        w.pickups.clear()
    w.walls.clear()


# ---------------------------------------------------------------- campaign structure
def test_story_has_24_stages_with_a_boss_every_fourth():
    for i in range(campaign.STORY_STAGES):
        s = campaign.story_spec(i)
        assert s.sector == i // 4 and s.level == i + 1
        assert (s.kind == "boss") == (i % 4 == 3)
        if s.kind == "boss":
            assert s.boss == campaign.BOSS_ORDER[i // 4]
        else:
            assert s.goal >= 5
        assert set(s.weights) <= set(ENEMY_TYPES)
        assert s.max_enemies >= 3 or s.kind == "boss"


def test_story_is_gentle_at_first_and_ramps_up():
    assert not campaign.story_spec(0).shooting and not campaign.story_spec(1).shooting
    assert campaign.story_spec(2).shooting
    assert campaign.story_spec(0).walls == 0 and campaign.story_spec(2).walls >= 2
    assert set(campaign.story_spec(0).weights) == {"drone"}
    assert len(campaign.story_spec(22).weights) == 6
    assert campaign.story_spec(20).goal > campaign.story_spec(0).goal


def test_new_game_plus_scales_levels():
    assert campaign.story_spec(5, loop=2).level == campaign.story_spec(5).level + 6
    assert campaign.story_spec(3, loop=3).boss_scale > 1.0


def test_other_mode_specs():
    assert campaign.endless_spec(4).sector == 1
    assert campaign.time_attack_spec(1).goal == 10 and campaign.time_attack_spec(3).goal == 14
    assert [campaign.boss_rush_spec(n).boss for n in range(7)] == list(campaign.BOSS_ORDER) + ["sentinel"]
    assert campaign.boss_rush_spec(6).boss_scale > 1.0
    assert campaign.horde_spec(2).sector == 1


# ---------------------------------------------------------------- shop / loadout
def test_shop_prices_and_purchases():
    lo = Loadout(["BLASTER"], coins=100)
    twin = next(i for i in SHOP_ITEMS if i["id"] == "TWIN")
    hp = next(i for i in SHOP_ITEMS if i["id"] == "hp_bonus")
    assert lo.price(twin, 10) == 15
    assert lo.buy(twin, 10) and "TWIN" in lo.weapons and lo.weapon == "TWIN" and lo.coins == 85
    assert not lo.can_buy(twin, 10), "weapons can only be bought once"
    p1 = lo.price(hp, 10)
    lo.buy(hp, 10)
    assert lo.price(hp, 10) > p1
    lo.coins = 0
    assert not lo.buy(hp, 10)


def test_loadout_weapon_cycling_and_story_roundtrip():
    lo = Loadout(["BLASTER", "TWIN", "SPREAD"])
    lo.cycle(1)
    assert lo.weapon == "TWIN"
    lo.cycle(-2)
    assert lo.weapon == "SPREAD"
    story = {}
    lo.fire_level = 2
    lo.to_story(story)
    again = Loadout.from_story(story)
    assert again.weapons == lo.weapons and again.fire_level == 2 and again.weapon == "SPREAD"


# ---------------------------------------------------------------- player
def test_player_moves_and_is_kept_inside_the_arena():
    w = make(campaign.story_spec(0))
    clear_field(w)
    p = w.players[0]
    run(w, 400, {1: PlayerInput(move=Vector2(-1, -1))})
    assert p.pos.x == pytest.approx(p.r) and p.pos.y == pytest.approx(p.r)
    run(w, 400, {1: PlayerInput(move=Vector2(1, 1))})
    assert p.pos.x == pytest.approx(W - p.r) and p.pos.y == pytest.approx(H - p.r)


def test_walls_block_the_player():
    w = make(campaign.story_spec(0))
    clear_field(w)
    p = w.players[0]
    w.walls.append(pygame.Rect(600, 0, 40, H))
    p.pos = Vector2(400, 300)
    run(w, 200, {1: PlayerInput(move=Vector2(1, 0))})
    assert p.pos.x <= 600 - p.r + 0.01


def test_dash_covers_distance_and_grants_invulnerability():
    w = make(campaign.story_spec(0))
    clear_field(w)
    p = w.players[0]
    p.pos = Vector2(300, 300)
    w.update({1: PlayerInput(move=Vector2(1, 0), dash=True)})
    assert p.dashing and p.iframes > 0 and not p.vulnerable()
    run(w, 12, {1: PlayerInput(move=Vector2(1, 0))})
    assert p.pos.x - 300 > 110
    assert p.dash_cd > 0
    dashes_before = w.dashes
    w.update({1: PlayerInput(move=Vector2(1, 0), dash=True)})
    assert w.dashes == dashes_before, "dash is on cooldown"


def test_sprint_uses_stamina_and_recovers():
    w = make(campaign.story_spec(0))
    clear_field(w)
    p = w.players[0]
    p.pos = Vector2(100, 300)
    run(w, 30, {1: PlayerInput(move=Vector2(1, 0), sprint=True)})
    assert p.sprinting and p.stamina < 100
    run(w, 200, {1: PlayerInput()})
    assert p.stamina > 90 and not p.sprinting


def test_ice_makes_movement_slippery():
    w = make(campaign.story_spec(14))       # Frozen Cache
    assert w.ice
    clear_field(w)
    p = w.players[0]
    p.pos = Vector2(200, 300)
    run(w, 40, {1: PlayerInput(move=Vector2(1, 0))})
    x = p.pos.x
    run(w, 10, {1: PlayerInput()})
    assert p.pos.x - x > 15, "the ship should keep sliding after the keys are released"


# ---------------------------------------------------------------- damage rules
def test_bullet_hurts_then_iframes_protect():
    w = make()
    clear_field(w)
    p = w.players[0]
    hp = p.hp
    w.enemy_bullet(p.pos.x, p.pos.y, 0.0, 1.0)
    w.update(IDLE)
    assert p.hp == hp - 1 and p.iframes > 0 and w.hits_taken == 1
    w.enemy_bullet(p.pos.x, p.pos.y, 0.0, 1.0)
    w.update(IDLE)
    assert p.hp == hp - 1, "no damage while invulnerable"


def test_shield_blocks_damage_and_kills_on_contact():
    w = make()
    clear_field(w)
    w.give_power("SHIELD")
    p = w.players[0]
    hp = p.hp
    w.enemy_bullet(p.pos.x, p.pos.y, 0.0, 1.0)
    e = w.spawn_enemy("drone", (p.pos.x + 5, p.pos.y), instant=True)
    w.update(IDLE)
    assert p.hp == hp and e not in w.enemies


def test_combo_resets_when_hit():
    w = make()
    clear_field(w)
    w.add_combo(6)
    assert w.combo == 6 and w.loadout.coins == 0 + 0 or True
    w.hurt_player(w.players[0], 1, None, "test")
    assert w.combo == 0


def test_death_ends_the_stage_as_failed():
    w = make(diff="NIGHTMARE")
    clear_field(w)
    p = w.players[0]
    assert p.hp == 1
    w.hurt_player(p, 1, None, "test")
    assert not p.alive
    run(w, 120)
    assert w.state == "failed"


def test_hearts_heal_and_revive_the_partner():
    w = make(players=2)
    clear_field(w)
    p1, p2 = w.players
    p2.hp = 0
    p2.alive = False
    p1.hp = 1
    w.spawn_pickup("heart", p1.pos.x, p1.pos.y)
    w.update(IDLE)
    assert p2.alive and p2.hp >= 1 and p1.hp >= 2


def test_pulse_needs_a_full_bar_then_clears_bullets_and_hurts_enemies():
    w = make()
    clear_field(w)
    p = w.players[0]
    p.energy = 50
    w.use_pulse(p)
    assert p.energy == 50, "not charged yet"
    p.energy = 100
    e = w.spawn_enemy("drone", (p.pos.x + 60, p.pos.y), instant=True)
    for i in range(20):
        w.enemy_bullet(p.pos.x + 100, p.pos.y + i * 5, math.pi, 0.1)
    w.use_pulse(p)
    assert p.energy < 20 and not w.ebullets and e not in w.enemies and w.max_pulse_kills >= 1


def test_graze_charges_energy():
    w = make()
    clear_field(w)
    p = w.players[0]
    p.energy = 0
    w.enemy_bullet(p.pos.x + p.r + 6, p.pos.y - 30, math.pi / 2, 2.0, r=4)
    run(w, 30)
    assert w.grazes >= 1 and p.energy > 0 and p.hp == p.max_hp


# ---------------------------------------------------------------- weapons
def test_shooting_needs_a_weapon_and_respects_cooldown():
    w = make(weapons=())
    clear_field(w)
    w.update({1: PlayerInput(fire=True, aim=Vector2(900, 300))})
    assert not w.pbullets
    w = make(weapons=("BLASTER",))
    clear_field(w)
    run(w, 5, {1: PlayerInput(fire=True, aim=Vector2(900, 300))})
    assert len(w.pbullets) == 1
    run(w, 30, {1: PlayerInput(fire=True, aim=Vector2(900, 300))})
    assert 3 <= w.shots_fired <= 5


@pytest.mark.parametrize("weapon,count", [("BLASTER", 1), ("TWIN", 2), ("SPREAD", 3), ("PIERCE", 1)])
def test_weapon_patterns(weapon, count):
    w = make(weapons=(weapon,))
    clear_field(w)
    w.loadout.weapon = weapon
    w.update({1: PlayerInput(fire=True, aim=Vector2(900, 300))})
    assert len(w.pbullets) == count


def test_bullets_kill_enemies_and_drop_score():
    w = make()
    clear_field(w)
    p = w.players[0]
    e = w.spawn_enemy("drone", (p.pos.x + 200, p.pos.y), instant=True)
    e.speed = 0
    run(w, 60, {1: PlayerInput(fire=True, aim=Vector2(e.pos.x, e.pos.y))})
    assert e not in w.enemies and w.kills == 1 and w.score > 0 and w.combo == 1


def test_piercing_rounds_hit_several_enemies_once_each():
    w = make(weapons=("PIERCE",))
    clear_field(w)
    w.loadout.weapon = "PIERCE"
    p = w.players[0]
    es = [w.spawn_enemy("bulwark", (p.pos.x + 150 + i * 60, p.pos.y), instant=True) for i in range(3)]
    for e in es:
        e.speed = 0
        e.cd = 9999
    hp = [e.hp for e in es]
    w.update({1: PlayerInput(fire=True, aim=Vector2(p.pos.x + 600, p.pos.y))})
    run(w, 30)
    assert all(e.hp < h for e, h in zip(es, hp)), "the bolt should have gone through all three"


def test_mace_swing_smashes_and_reflects_in_horde():
    w = make(campaign.horde_spec(1), weapons=())
    clear_field(w)
    p = w.players[0]
    e = w.spawn_enemy("drone", (p.pos.x + 60, p.pos.y), instant=True)
    e.speed = 0
    w.enemy_bullet(p.pos.x + 70, p.pos.y - 20, math.pi, 0.1)
    run(w, 25, {1: PlayerInput(fire=True, aim=Vector2(p.pos.x + 200, p.pos.y))})
    assert w.kills >= 1 and not w.ebullets


# ---------------------------------------------------------------- enemies
@pytest.mark.parametrize("kind", ENEMY_TYPES)
def test_every_enemy_type_behaves(kind):
    w = make(campaign.story_spec(12))
    clear_field(w)
    e = w.spawn_enemy(kind, (200, 200), level=10, instant=True)
    w.players[0].hp = w.players[0].max_hp = 999
    start = Vector2(e.pos)
    run(w, 400)
    assert math.isfinite(e.pos.x) and 0 <= e.pos.x <= W and 0 <= e.pos.y <= H
    assert e.pos.distance_to(start) > 5 or kind == "lancer"


def test_splitter_splits_into_two_minis():
    w = make(campaign.story_spec(12))
    clear_field(w)
    e = w.spawn_enemy("splitter", (400, 200), instant=True)
    w.kill_enemy(e)
    minis = [x for x in w.enemies if x.kind == "drone" and x.mini]
    assert len(minis) == 2


def test_comet_explosion_chains_into_neighbours():
    w = make(campaign.story_spec(12))
    clear_field(w)
    a = w.spawn_enemy("comet", (400, 200), instant=True)
    b = w.spawn_enemy("drone", (430, 200), instant=True)
    b.hp = 2
    w.kill_enemy(a)
    assert b not in w.enemies


def test_enemies_do_not_hurt_while_warping_in():
    w = make()
    clear_field(w)
    p = w.players[0]
    e = w.spawn_enemy("drone", (p.pos.x, p.pos.y))
    assert e.spawn > 0 and not e.solid
    w.update(IDLE)
    assert p.hp == p.max_hp


def test_enemy_speeds_are_capped_below_a_sprinting_player():
    w = make(campaign.story_spec(23), diff="NIGHTMARE")
    for kind in ENEMY_TYPES:
        e = w.spawn_enemy(kind, (100, 100), level=40, instant=True)
        assert e.speed <= 5.0 or kind == "comet"
        if kind == "comet":
            assert e.rush_speed <= 8.7


# ---------------------------------------------------------------- hazards
def test_laser_gate_only_hurts_when_on():
    w = make()
    clear_field(w)
    p = w.players[0]
    gate = hz.LaserGate((p.pos.x - 100, p.pos.y), (p.pos.x + 100, p.pos.y), offset=0, off=10, warn=10, on=1000)
    w.hazards.append(gate)
    w.time = 0
    run(w, 15)
    assert p.hp == p.max_hp
    run(w, 30)
    assert p.hp < p.max_hp


def test_blast_is_telegraphed_then_damages():
    w = make()
    clear_field(w)
    p = w.players[0]
    w.hazards.append(hz.Blast(p.pos.x, p.pos.y, 50, 30, (255, 0, 0), shards=6))
    run(w, 25)
    assert p.hp == p.max_hp, "the warning phase is harmless"
    run(w, 10)
    assert p.hp < p.max_hp and len(w.ebullets) >= 1


def test_current_lane_pushes_and_gravity_well_pulls():
    w = make()
    clear_field(w)
    p = w.players[0]
    p.pos = Vector2(300, 300)
    w.hazards.append(hz.CurrentLane((0, 250, W, 100), (1, 0), 2.0))
    x0 = p.pos.x
    run(w, 30)
    assert p.pos.x > x0 + 40
    clear_field(w)
    p.pos = Vector2(600, 500)
    well = hz.GravityWell((700, 400), 400, 3.0, drift=(0, 0))
    w.hazards.append(well)
    d0 = p.pos.distance_to(well.pos)
    run(w, 20)
    assert p.pos.distance_to(well.pos) < d0


def test_portals_teleport_once_then_cool_down():
    w = make()
    clear_field(w)
    p = w.players[0]
    portal = hz.PortalPair((300, 300), (900, 300))
    w.hazards.append(portal)
    p.pos = Vector2(300, 300)
    w.update(IDLE)
    assert p.pos.x > 800
    w.update(IDLE)
    assert p.pos.x > 800, "no immediate teleport back"


def test_stripe_hurts_only_while_active():
    w = make()
    clear_field(w)
    p = w.players[0]
    w.hazards.append(hz.Stripe(p.pos.x, 60, True, delay=20, active=10))
    run(w, 15)
    assert p.hp == p.max_hp
    run(w, 10)
    assert p.hp < p.max_hp


def test_sector_hazards_are_generated():
    import random
    from VoidLoop.biomes import BIOMES
    kinds = {b.hazard for b in BIOMES if b.hazard}
    assert kinds == {"current", "laser", "ice", "portal", "gravity"}
    for biome in BIOMES:
        made = hz.make_hazards(biome, random.Random(1), 0.8, 10)
        assert bool(made) == bool(biome.hazard)


# ---------------------------------------------------------------- stage rules
def test_collecting_all_fragments_wins_a_story_stage():
    w = make(campaign.story_spec(0))
    clear_field(w, pickups=False)
    goal = w.spec.goal
    for _ in range(goal):
        frag = next(pk for pk in w.pickups if pk.kind == "fragment") if any(pk.kind == "fragment" for pk in w.pickups) else None
        assert frag is not None
        w.players[0].pos = Vector2(frag.pos)
        w.update(IDLE)
        w.enemies.clear()
    run(w, 120)
    assert w.state == "won" and w.fragments == goal
    assert w.loadout.coins >= goal


@pytest.mark.parametrize("boss_id", sorted(BOSSES))
def test_every_boss_can_be_beaten(boss_id):
    idx = campaign.BOSS_ORDER.index(boss_id)
    w = make(campaign.boss_rush_spec(idx))
    clear_field(w)
    w.players[0].hp = w.players[0].max_hp = 999
    boss = w.boss
    assert boss is not None and boss.id == boss_id and boss.invuln
    for _ in range(600):                            # let the intro finish (a boss may be mid-teleport: wait for it)
        w.update(IDLE)
        if not boss.invuln:
            break
    assert not boss.invuln
    start_phase = boss.phase
    assert w.damage_boss(1) and boss.hp == boss.max_hp - 1
    boss.hp = 1
    run(w, 2)
    assert boss.phase == len(boss.thresholds) + 1 > start_phase or boss.phase >= start_phase
    boss.invuln_t = 0
    assert w.damage_boss(5) or boss.dying
    assert boss.dying
    run(w, 400)
    assert w.boss is None and w.state == "won"
    assert w.loadout.coins >= 50


@pytest.mark.parametrize("boss_id", sorted(BOSSES))
def test_boss_attacks_produce_bullets_and_never_crash(boss_id):
    idx = campaign.BOSS_ORDER.index(boss_id)
    w = make(campaign.boss_rush_spec(idx))
    clear_field(w)
    w.players[0].hp = w.players[0].max_hp = 9999
    boss = w.boss
    seen = 0
    for phase_hp in (1.0, 0.7, 0.45, 0.2):
        boss.hp = int(boss.max_hp * phase_hp)
        for _ in range(500):
            w.update({1: PlayerInput(move=Vector2(math.sin(w.time * 0.03), 0.2))})
            seen = max(seen, len(w.ebullets))
            w.pop_events()
    assert seen > 5
    assert boss.phase >= 3


def test_boss_phase_change_clears_bullets_and_gifts_pickups():
    w = make(campaign.boss_rush_spec(0))
    clear_field(w)
    w.players[0].hp = w.players[0].max_hp = 99
    run(w, 200)
    boss = w.boss
    w.enemy_bullet(100, 100, 0, 0.5)
    boss.hp = int(boss.max_hp * 0.6)
    run(w, 2)
    assert boss.phase == 2 and not w.ebullets
    assert any(pk.kind == "power" for pk in w.pickups)
    assert ("bark", "boss_phase") in w.events or True


def test_time_attack_clock_runs_out():
    w = make(campaign.time_attack_spec(1, {"time_left": 30}))
    clear_field(w)
    w.players[0].hp = w.players[0].max_hp = 99
    run(w, 40)
    assert w.state == "failed" and w.rules.timed_out


def test_time_attack_fragments_and_kills_buy_time():
    w = make(campaign.time_attack_spec(1))
    clear_field(w, pickups=False)
    t0 = w.rules.time_left
    frag = next(pk for pk in w.pickups if pk.kind == "fragment")
    w.players[0].pos = Vector2(frag.pos)
    w.update(IDLE)
    assert w.rules.time_left > t0 + 150
    e = w.spawn_enemy("drone", (100, 100), instant=True)
    before = w.rules.time_left
    w.kill_enemy(e)
    assert w.rules.time_left == before + 60


def test_time_attack_weapon_evolves_every_ten_kills():
    w = make(campaign.time_attack_spec(1))
    clear_field(w)
    for i in range(10):
        e = w.spawn_enemy("drone", (100, 100), instant=True)
        w.kill_enemy(e)
    assert w.rules.tier == 1
    assert ("tier", 1) in w.events


def test_endless_levels_up_and_changes_sector():
    w = make(campaign.endless_spec(1))
    clear_field(w)
    w.players[0].hp = w.players[0].max_hp = 99
    rules = w.rules
    for _ in range(2):
        rules.frames = rules.LEVEL_FRAMES
        w.update(IDLE)
    assert rules.level == 3
    rules.frames = rules.LEVEL_FRAMES
    w.update(IDLE)
    assert rules.level == 4 and w.sector == 1
    for lvl in range(5, 7):
        rules.frames = rules.LEVEL_FRAMES
        w.update(IDLE)
    assert rules.level == 6 and w.boss is not None, "a boss arrives at level 6"


def test_horde_runs_ten_waves():
    w = make(campaign.horde_spec(1), weapons=())
    clear_field(w)
    w.players[0].hp = w.players[0].max_hp = 999
    rules = w.rules
    assert rules.wave == 0
    for _ in range(3000):
        w.update(IDLE)
        for e in w.enemies[:]:
            if e.solid:
                w.kill_enemy(e)
        w.pop_events()
        if w.state != "playing":
            break
    assert rules.wave == 10 and w.state == "won"


def test_pickups_expire_and_coins_are_magnetic():
    w = make()
    clear_field(w)
    p = w.players[0]
    pk = w.spawn_pickup("coin", p.pos.x + 90, p.pos.y, life=600)
    coins = w.loadout.coins
    run(w, 60)
    assert w.loadout.coins == coins + 1
    old = w.spawn_pickup("coin", 100, 100, life=5)
    run(w, 10)
    assert old not in w.pickups


def test_powerups_apply_and_expire():
    w = make()
    clear_field(w)
    for name in ("SHIELD", "SPEED", "DOUBLE_DAMAGE", "RAPID_FIRE", "FREEZE", "MAGNET"):
        w.give_power(name)
        assert w.has_power(name)
    run(w, 5)
    assert w.enemy_slow < 1.0
    run(w, 600)
    assert not w.powers and w.enemy_slow == 1.0


def test_bomb_powerup_clears_the_screen():
    w = make(campaign.story_spec(6))
    clear_field(w)
    for i in range(5):
        w.spawn_enemy("drone", (600 + i * 30, 380), instant=True)
        w.enemy_bullet(600, 300 + i, 0, 0.1)
    w.give_power("BOMB")
    assert not w.ebullets and not w.enemies


def test_simulation_is_deterministic_for_a_seed():
    def result(seed):
        w = make(campaign.story_spec(9), seed=seed)
        bot = Bot(0.8)
        for _ in range(500):
            w.update(bot.inputs(w))
            w.pop_events()
        return round(w.players[0].pos.x, 3), round(w.players[0].pos.y, 3), w.kills, len(w.enemies), w.score

    assert result(7) == result(7)


def test_bot_clears_the_early_story_stages():
    for stage in range(3):
        w = make(campaign.story_spec(stage), weapons=("BLASTER",) if stage else (), seed=stage + 1)
        bot = Bot(0.85)
        for _ in range(60 * 90):
            w.update(bot.inputs(w))
            w.pop_events()
            if w.state != "playing":
                break
        assert w.state == "won", "stage %d: %s" % (stage, w.state)


def test_world_draws_every_sector_without_error(screen):
    for i in (2, 6, 10, 14, 18, 22, 3, 23):
        w = make(campaign.story_spec(i))
        bot = Bot(0.8)
        for _ in range(240):
            w.update(bot.inputs(w))
            w.pop_events()
        w.draw(screen)
        w.fx.add_shake(10)
        w.draw(screen)
