"""The arsenal: spend coins on weapons and permanent upgrades between stages."""
import math

import pygame

from .. import biomes, gfx
from ..i18n import T
from ..settings import W, H
from ..ui import Menu, Item, draw_header
from ..weapons import SHOP_ITEMS, WEAPONS
from .base import Scene, is_back


class ShopMenu(Menu):
    """Menu whose rows are shop cards."""

    def __init__(self, app, run, items):
        super().__init__(app, items, 400, 176, 560, 58, 8, 20, gfx.CYAN)
        self.run = run

    def draw_item(self, surf, it, selected):
        r = it.rect
        base = self.color
        if it.key == "continue":
            col = gfx.GREEN
            if selected:
                gfx.panel(surf, r.inflate(8, 4), col, fill=(*gfx.scale_color(col, 0.18), 230), border=2)
            else:
                gfx.panel(surf, r, gfx.scale_color(col, 0.5), fill=(6, 10, 20, 190), border=1, halo=False)
            gfx.draw_text(surf, T("shop.continue"), r.center, "display", 22, gfx.WHITE if selected else col, "center")
            return
        item = it.item
        lo = self.run.loadout
        cost = self.run.cfg["cost"]
        maxed = lo.is_maxed(item)
        price = lo.price(item, cost)
        afford = lo.coins >= price
        col = gfx.GOLD if (afford and not maxed) else gfx.scale_color(base, 0.6)
        if selected:
            gfx.panel(surf, r.inflate(8, 4), col, fill=(*gfx.scale_color(col, 0.14), 230), border=2)
        else:
            gfx.panel(surf, r, gfx.scale_color(col, 0.45), fill=(6, 10, 20, 190), border=1, halo=False)
        gfx.draw_icon(surf, item["icon"], r.x + 34, r.centery, 13, gfx.WHITE if selected else col)
        gfx.draw_text(surf, T("shop.%s.name" % item["id"]), (r.x + 66, r.centery - 12), "display", 18, gfx.WHITE if selected else col, "midleft")
        if item["kind"] == "upgrade":
            level = getattr(lo, item["id"])
            for i in range(item["max"]):
                pygame.draw.rect(surf, col if i < level else (40, 50, 70), (r.x + 66 + i * 18, r.centery + 8, 14, 7))
        else:
            owned = item["id"] in lo.weapons
            gfx.draw_text(surf, T("shop.owned") if owned else T("shop.weapon"), (r.x + 66, r.centery + 12), "mono", 15, gfx.LIME if owned else (130, 145, 170), "midleft")
        if maxed:
            gfx.draw_text(surf, T("shop.max"), (r.right - 22, r.centery), "display", 18, gfx.LIME, "midright")
        else:
            gfx.draw_icon(surf, "coin", r.right - 96, r.centery, 7, gfx.GOLD if afford else gfx.RED)
            gfx.draw_text(surf, str(price), (r.right - 22, r.centery), "display", 20, gfx.GOLD if afford else gfx.RED, "midright")


class ShopScene(Scene):
    music = None

    def __init__(self, app, run, done):
        super().__init__(app)
        self.run = run
        self.done = done
        self.sector = min(run.spec().sector, 5) if run.mode != "STORY" or run.index < 24 else 5
        self.bg = biomes.make_background(self.sector)
        items = []
        for item in SHOP_ITEMS:
            if run.mode == "HORDE" and item["kind"] == "weapon":
                continue
            if run.mode == "HORDE" and item["id"] == "fire_level":
                continue
            it = Item(item["id"], item["id"])
            it.item = item
            items.append(it)
        cont = Item("continue", "continue")
        items.append(cont)
        self.menu = ShopMenu(app, run, items)
        self._finished = False
        self.flash = 0
        self.message = None

    def finish(self):
        if not self._finished:
            self._finished = True
            self.run.save_story()
            self.done()

    def event(self, e):
        key = self.menu.event(e)
        if is_back(e):
            self.finish()
            return
        if key == "continue":
            self.finish()
        elif key:
            item = next(i for i in SHOP_ITEMS if i["id"] == key)
            lo = self.run.loadout
            if lo.buy(item, self.run.cfg["cost"]):
                self.app.audio.play("buy")
                self.flash = 20
                self.message = (T("shop.bought", name=T("shop.%s.name" % key)), gfx.LIME)
                self.run.save_story()
            else:
                self.app.audio.play("ui_error")
                self.message = (T("shop.maxed") if lo.is_maxed(item) else T("shop.no_coins"), gfx.RED)

    def update(self):
        super().update()
        self.bg.update()
        self.menu.update()
        if self.flash:
            self.flash -= 1

    def description(self, item):
        lo = self.run.loadout
        key = "shop.%s.desc" % item["id"]
        text = T(key)
        if item["id"] == "hp_bonus":
            text += "  " + T("shop.now", n=self.run.cfg["hp"] + lo.hp_bonus)
        elif item["id"] == "fire_level":
            text += "  " + T("shop.now", n=lo.fire_cooldown(lo.weapon if lo.weapon in WEAPONS else "BLASTER"))
        elif item["id"] == "dash_level":
            text += "  " + T("shop.now", n=lo.dash_cooldown())
        return text

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 8), 150), (0, 0))
        draw_header(surf, T("shop.title"), T("shop.subtitle", cost=self.run.cfg["cost"]), gfx.CYAN, 50)
        lo = self.run.loadout
        # coins
        gfx.draw_icon(surf, "coin", W - 190, 46, 12, gfx.GOLD)
        gfx.draw_text(surf, str(lo.coins), (W - 160, 46), "title", 34, gfx.GOLD, "midleft")
        self.menu.draw(surf)
        # detail panel
        sel = self.menu.items[self.menu.sel]
        panel = pygame.Rect(720, 176, 460, 420)
        gfx.panel(surf, panel, gfx.CYAN, fill=(4, 8, 18, 222), border=2, cut=16)
        if sel.key != "continue":
            item = sel.item
            gfx.draw_glow(surf, (panel.centerx, panel.y + 92), 90, gfx.CYAN, 0.35)
            gfx.draw_icon(surf, item["icon"], panel.centerx, panel.y + 92, 40, gfx.WHITE)
            gfx.draw_text(surf, T("shop.%s.name" % item["id"]).upper(), (panel.centerx, panel.y + 162), "display", 24, gfx.CYAN, "center")
            y = panel.y + 204
            for ln in gfx.wrap_text(self.description(item), "mono", 20, panel.w - 56):
                gfx.draw_text(surf, ln, (panel.x + 28, y), "mono", 20, gfx.WHITE)
                y += 27
            if item["kind"] == "weapon":
                w = WEAPONS[item["id"]]
                stats = [T("shop.stat_dmg", n=w["dmg"]), T("shop.stat_rate", n=round(60 / lo.fire_cooldown(item["id"]), 1)), T("shop.stat_shots", n=len(w["shots"]))]
                gfx.draw_text(surf, "   ".join(stats), (panel.centerx, panel.bottom - 36), "mono", 17, (150, 175, 200), "center")
        else:
            gfx.draw_text(surf, T("shop.loadout"), (panel.centerx, panel.y + 40), "display", 22, gfx.CYAN, "center")
            rows = [("HP", str(self.run.cfg["hp"] + lo.hp_bonus)), (T("shop.stat_rate_label"), str(round(60 / lo.fire_cooldown(lo.weapon if lo.weapon in WEAPONS else "BLASTER"), 1))),
                    (T("shop.dash_label"), "%.2fs" % (lo.dash_cooldown() / 60)), (T("shop.weapons_label"), str(len(lo.weapons)))]
            y = panel.y + 100
            for label, value in rows:
                gfx.draw_text(surf, label, (panel.x + 40, y), "mono", 22, gfx.WHITE)
                gfx.draw_text(surf, value, (panel.right - 40, y), "display", 20, gfx.GOLD, "topright")
                y += 46
        if self.message:
            text, col = self.message
            gfx.draw_text(surf, text, (W // 2, H - 44), "mono", 22, col, "center")
        if self.flash:
            surf.blit(gfx.tint_overlay((255, 215, 60), self.flash * 4), (0, 0))
