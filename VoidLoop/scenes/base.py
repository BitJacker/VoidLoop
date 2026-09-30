"""Scene base class and small helpers shared by all screens."""
import pygame

from .. import gfx


class Scene:
    music = None                 # music track to play while this scene is active
    captures_text = False        # True if the scene wants raw key presses (disables the global M shortcut)

    def __init__(self, app):
        self.app = app
        self.t = 0

    def enter(self):
        if self.music:
            self.app.audio.play_music(self.music)

    def leave(self):
        pass

    def event(self, e):
        pass

    def update(self):
        self.t += 1

    def draw(self, surf):
        surf.fill((0, 0, 0))


def is_back(e):
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)


def is_confirm(e):
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


def is_click(e):
    return e.type == pygame.MOUSEBUTTONDOWN and e.button == 1


def sequence(app, factories):
    """Run scenes one after another. Each factory receives a ``done`` callback."""
    it = iter(factories)

    def advance():
        try:
            factory = next(it)
        except StopIteration:
            return
        app.go(factory(advance))

    advance()
