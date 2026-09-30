"""Weapon definitions, Time Attack tiers and the shop catalogue."""

# shots: (angle offset in radians, sideways offset in pixels) for every bullet fired
WEAPONS = {
    "BLASTER": dict(cd=12, dmg=1, speed=14.0, shots=((0.0, 0.0),), pierce=0, size=4, icon="blaster"),
    "TWIN":    dict(cd=11, dmg=1, speed=14.0, shots=((0.0, -7.0), (0.0, 7.0)), pierce=0, size=4, icon="twin"),
    "SPREAD":  dict(cd=16, dmg=1, speed=13.0, shots=((-0.22, 0.0), (0.0, 0.0), (0.22, 0.0)), pierce=0, size=4, icon="spread"),
    "PIERCE":  dict(cd=22, dmg=3, speed=19.0, shots=((0.0, 0.0),), pierce=3, size=6, icon="pierce"),
    # Time Attack tiers (the weapon evolves every 10 kills)
    "TIER4":   dict(cd=13, dmg=2, speed=15.0, shots=((-0.2, 0.0), (0.0, 0.0), (0.2, 0.0)), pierce=0, size=5, icon="spread"),
    "TIER5":   dict(cd=9, dmg=2, speed=16.0, shots=((-0.36, 0.0), (-0.18, 0.0), (0.0, 0.0), (0.18, 0.0), (0.36, 0.0)), pierce=1, size=5, icon="spread"),
}
TIME_ATTACK_TIERS = ("BLASTER", "TWIN", "SPREAD", "TIER4", "TIER5")

SHOP_WEAPONS = ("TWIN", "SPREAD", "PIERCE")

# Shop catalogue. Price = difficulty base cost x mult x (1 + 0.5 x current level)
SHOP_ITEMS = (
    {"id": "TWIN", "kind": "weapon", "mult": 1.5, "icon": "twin"},
    {"id": "SPREAD", "kind": "weapon", "mult": 2.0, "icon": "spread"},
    {"id": "PIERCE", "kind": "weapon", "mult": 2.5, "icon": "pierce"},
    {"id": "hp_bonus", "kind": "upgrade", "mult": 2.0, "max": 3, "icon": "heart"},
    {"id": "fire_level", "kind": "upgrade", "mult": 1.5, "max": 3, "icon": "rapid"},
    {"id": "dash_level", "kind": "upgrade", "mult": 1.0, "max": 3, "icon": "dash"},
    {"id": "shield_cell", "kind": "upgrade", "mult": 2.5, "max": 1, "icon": "shield"},
)

BLASTER_PRICE_MULT = 1.0     # used by the (optional) first purchase in non-story modes


class Loadout:
    """What the player owns: weapons and permanent upgrades. Shared by both players."""

    def __init__(self, weapons=None, weapon="BLASTER", hp_bonus=0, fire_level=0, dash_level=0, shield_cell=0, coins=0):
        self.weapons = list(weapons) if weapons else []
        self.weapon = weapon
        self.hp_bonus = hp_bonus
        self.fire_level = fire_level
        self.dash_level = dash_level
        self.shield_cell = shield_cell
        self.coins = coins

    # ---- persistence with the story save ------------------------------
    @classmethod
    def from_story(cls, story):
        return cls(story.get("weapons"), story.get("weapon", "BLASTER"), story.get("hp_bonus", 0), story.get("fire_level", 0),
                   story.get("dash_level", 0), story.get("shield_cell", 0), story.get("coins", 0))

    def to_story(self, story):
        story.update(weapons=list(self.weapons), weapon=self.weapon, hp_bonus=self.hp_bonus, fire_level=self.fire_level,
                     dash_level=self.dash_level, shield_cell=self.shield_cell, coins=self.coins)

    # ---- weapons ---------------------------------------------------------
    @property
    def can_shoot(self):
        return bool(self.weapons)

    def grant(self, weapon):
        if weapon not in self.weapons:
            self.weapons.append(weapon)
        if self.weapon not in self.weapons:
            self.weapon = weapon

    def cycle(self, step):
        if not self.weapons:
            return
        i = self.weapons.index(self.weapon) if self.weapon in self.weapons else 0
        self.weapon = self.weapons[(i + step) % len(self.weapons)]

    def select_index(self, index):
        if 0 <= index < len(self.weapons):
            self.weapon = self.weapons[index]

    # ---- shop ----------------------------------------------------------------
    def level_of(self, item_id):
        return getattr(self, item_id, 0) if item_id not in WEAPONS else (1 if item_id in self.weapons else 0)

    def price(self, item, base_cost):
        level = 0 if item["kind"] == "weapon" else getattr(self, item["id"])
        return int(round(base_cost * item["mult"] * (1 + 0.5 * level)))

    def is_maxed(self, item):
        if item["kind"] == "weapon":
            return item["id"] in self.weapons
        return getattr(self, item["id"]) >= item["max"]

    def can_buy(self, item, base_cost):
        return (not self.is_maxed(item)) and self.coins >= self.price(item, base_cost)

    def buy(self, item, base_cost):
        if not self.can_buy(item, base_cost):
            return False
        self.coins -= self.price(item, base_cost)
        if item["kind"] == "weapon":
            self.grant(item["id"])
            self.weapon = item["id"]
        else:
            setattr(self, item["id"], getattr(self, item["id"]) + 1)
        return True

    # ---- derived stats -------------------------------------------------------------
    def fire_cooldown(self, weapon_id):
        return max(4, WEAPONS[weapon_id]["cd"] - 2 * self.fire_level)

    def dash_cooldown(self):
        return max(20, 45 - 8 * self.dash_level)
