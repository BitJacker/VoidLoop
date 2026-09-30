"""Draw the VoidLoop emblem and export the application icons (needs Pillow).

    python tools/make_icons.py

Writes VoidLoop/assets/icons/voidloop.png, packaging/linux/voidloop.png and packaging/windows/voidloop.ico
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

from VoidLoop import gfx  # noqa: E402


def render(size=1024):
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((64, 64))
    surf = pygame.Surface((size, size)).convert()
    surf.fill((5, 8, 18))
    gfx.draw_glow(surf, (size // 2, size // 2), int(size * 0.62), (0, 110, 90), 0.9)
    gfx.draw_glow(surf, (size // 2, size // 2), int(size * 0.40), (0, 160, 190), 0.55)
    # faint grid, like the boot sector
    for i in range(0, size, size // 8):
        pygame.draw.line(surf, (8, 34, 34), (i, 0), (i, size))
        pygame.draw.line(surf, (8, 34, 34), (0, i), (size, i))
    gfx.draw_logo(surf, size // 2, size // 2, size * 0.36, 0.0, gfx.GREEN, gfx.CYAN)
    gfx.draw_glow(surf, (size // 2, size // 2), int(size * 0.34), (0, 255, 150), 0.30)
    gfx.draw_logo(surf, size // 2, size // 2, size * 0.36, 0.0, gfx.GREEN, gfx.CYAN)
    # rounded square mask
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, size, size), border_radius=int(size * 0.2))
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    out.blit(surf, (0, 0))
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(out, (0, 255, 150, 255), (size * 0.012, size * 0.012, size * 0.976, size * 0.976), max(3, size // 96), border_radius=int(size * 0.19))
    return Image.frombytes("RGBA", (size, size), pygame.image.tostring(out, "RGBA"))


def main():
    big = render(1024)
    targets = {
        "VoidLoop/assets/icons/voidloop.png": 256,
        "packaging/linux/voidloop.png": 512,
    }
    for rel, px in targets.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        big.resize((px, px), Image.LANCZOS).save(path, optimize=True)
        print("wrote", rel)
    ico = os.path.join(ROOT, "packaging", "windows", "voidloop.ico")
    os.makedirs(os.path.dirname(ico), exist_ok=True)
    big.resize((256, 256), Image.LANCZOS).save(ico, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote packaging/windows/voidloop.ico")


if __name__ == "__main__":
    main()
