import pygame, sys, subprocess, os

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("VoidLoop - Terminal Interface")
clock = pygame.time.Clock()

GREEN, CYAN, WHITE = (0, 255, 150), (0, 255, 255), (255, 255, 255)
font_main = pygame.font.SysFont("Courier New", 22, bold=True)
font_title = pygame.font.SysFont("Courier New", 50, bold=True)

# Opzioni
options = {
    "lang": ["en", "it", "es", "fr"],
    "color": ["Neon Green", "Cyber Blue", "Void Purple"],
    "mode": ["1 PLAYER", "2 PLAYERS"],
    "screen": ["WINDOWED", "FULLSCREEN"]
}
idx = {"lang": 0, "color": 0, "mode": 0, "screen": 0}

def draw_grid():
    screen.fill((5, 5, 15))
    for i in range(0, WIDTH, 40): pygame.draw.line(screen, (10, 30, 40), (i, 0), (i, HEIGHT))
    for i in range(0, HEIGHT, 40): pygame.draw.line(screen, (10, 30, 40), (0, i), (WIDTH, i))

while True:
    draw_grid()
    m_pos = pygame.mouse.get_pos()
    m_click = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN: m_click = True

    # Titolo
    title_surf = font_title.render("VOID_LOOP", True, GREEN)
    screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 80))

    # Rendering Opzioni Cliccabili
    y = 200
    current_opts = []
    for key in options:
        txt = f"{key.upper()}: < {options[key][idx[key]]} >"
        surf = font_main.render(txt, True, WHITE)
        rect = surf.get_rect(center=(WIDTH//2, y))
        if rect.collidepoint(m_pos):
            surf = font_main.render(txt, True, CYAN)
            if m_click: idx[key] = (idx[key] + 1) % len(options[key])
        screen.blit(surf, rect)
        y += 50

    # Start
    btn_txt = font_main.render(":: INITIALIZE MISSION ::", True, GREEN)
    btn_rect = btn_txt.get_rect(center=(WIDTH//2, 500))
    if btn_rect.collidepoint(m_pos):
        btn_txt = font_main.render(":: INITIALIZE MISSION ::", True, WHITE)
        if m_click:
            script = os.path.join(os.getcwd(), "VoidLoop", "voidloopgame.py")
            # Passiamo i nuovi argomenti: lang, color, mode, screen
            subprocess.Popen([sys.executable, script, options["lang"][idx["lang"]], options["color"][idx["color"]], options["mode"][idx["mode"]], options["screen"][idx["screen"]]])
            pygame.quit(); sys.exit()
    screen.blit(btn_txt, btn_rect)

    pygame.display.flip()
    clock.tick(60)