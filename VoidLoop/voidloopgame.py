import pygame, sys, json, random, os, math
from enum import Enum, auto

# --- GESTIONE SALVATAGGI ---
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "savegame.json")

def save_progress(lvl, coins):
    try:
        with open(SAVE_FILE, "w") as f: json.dump({"level": lvl, "coins": coins}, f)
    except: pass

def load_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                return data.get("level", 1), data.get("coins", 0)
        except: return 1, 0
    return 1, 0

# --- CONFIGURAZIONE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
lang = sys.argv[1] if len(sys.argv) > 1 else "en"
ship_color = sys.argv[2] if len(sys.argv) > 2 else "Neon Green"
is_2p = sys.argv[3] == "2 PLAYERS" if len(sys.argv) > 3 else False
is_full = sys.argv[4] == "FULLSCREEN" if len(sys.argv) > 4 else False

pygame.init()
if is_full:
    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
else:
    WIDTH, HEIGHT = 1000, 700
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

COLOR_MAP = {"Neon Green": (0, 255, 150), "Cyber Blue": (0, 150, 255), "Void Purple": (180, 0, 255)}
P1_COL = COLOR_MAP.get(ship_color, (0, 255, 150))
P2_COL, WHITE, RED, GOLD, GRAY, CYAN = (255, 100, 0), (255, 255, 255), (255, 50, 50), (255, 215, 0), (80, 80, 80), (0, 255, 255)

clock = pygame.time.Clock()
font_hud = pygame.font.SysFont("Courier New", 22, bold=True)

# --- CLASSI ---
class PlayerBullet:
    def __init__(self, x, y, angle, color):
        self.rect = pygame.Rect(x, y, 8, 8)
        self.vx, self.vy = math.cos(angle) * 10, math.sin(angle) * 10
        self.color = color
    def update(self):
        self.rect.x += self.vx; self.rect.y += self.vy
        return 0 <= self.rect.x <= WIDTH and 0 <= self.rect.y <= HEIGHT

class Enemy:
    def __init__(self, level):
        self.rect = pygame.Rect(random.choice([-50, WIDTH+50]), random.randint(0, HEIGHT), 25, 25)
        self.speed = 1.2 + (level * 0.15)
    def move(self, targets):
        target = min(targets, key=lambda t: math.hypot(t.centerx - self.rect.centerx, t.centery - self.rect.centery))
        dx, dy = target.centerx - self.rect.centerx, target.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.rect.x += (dx/dist) * self.speed
            self.rect.y += (dy/dist) * self.speed

# --- LOGICA ---
level, coins = load_progress()
score = 0
fragments_needed = 4 + level
walls, enemies, p_bullets = [], [], []
p1 = pygame.Rect(WIDTH//2-50, HEIGHT//2, 30, 30)
p2 = pygame.Rect(WIDTH//2+50, HEIGHT//2, 30, 30)
fragment = pygame.Rect(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100), 20, 20)

game_state = "STORY"
current_chapter = "prologue"
weapon_p1 = "None"
weapon_p2 = "None"

# Caricamento Dialoghi
json_path = os.path.join(BASE_DIR, "lang", f"dialogues_{lang}.json")
try:
    with open(json_path, "r", encoding="utf-8") as f: story_data = json.load(f)
except: story_data = {"prologue":["INIZIO..."], "game_over":["ONLINE."]}

line_idx, char_idx = 0, 0

def setup_level(lvl):
    global walls, enemies, p_bullets, score, fragments_needed
    enemies.clear(); p_bullets.clear(); walls.clear(); score = 0
    fragments_needed = 4 + lvl
    if lvl >= 3:
        for _ in range(min(lvl // 2, 5)):
            walls.append(pygame.Rect(random.randint(200, WIDTH-200), random.randint(100, HEIGHT-100), 120, 15))

setup_level(level)

while True:
    screen.fill((5, 5, 15))
    m_pos = pygame.mouse.get_pos()
    m_click = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN: m_click = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if game_state == "STORY":
                txt = story_data[current_chapter][line_idx]
                if char_idx < len(txt): char_idx = len(txt)
                else:
                    line_idx += 1; char_idx = 0
                    if line_idx >= len(story_data[current_chapter]):
                        if current_chapter == "game_over":
                            setup_level(level); current_chapter = "prologue"; line_idx = 0
                        game_state = "PLAYING"

    if game_state == "SHOP":
        title = font_hud.render("--- ARSENAL ---", True, CYAN)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        f_txt = font_hud.render(f"FRAMMENTI: {coins}", True, GOLD)
        screen.blit(f_txt, (WIDTH//2 - f_txt.get_width()//2, 150))
        
        # Bottoni Shop
        options = [("BLASTER", 5), ("NOVA", 10)]
        for i, (name, price) in enumerate(options):
            rect = pygame.Rect(WIDTH//2-150, 250 + i*80, 300, 50)
            pygame.draw.rect(screen, CYAN if rect.collidepoint(m_pos) else GRAY, rect, 2)
            txt = font_hud.render(f"{name}: {price} F.", True, WHITE)
            screen.blit(txt, (rect.x + 20, rect.y + 12))
            if m_click and rect.collidepoint(m_pos) and coins >= price:
                coins -= price; weapon_p1 = name; weapon_p2 = name
                game_state = "STORY"; setup_level(level)

        skip = font_hud.render("PREMI SPAZIO PER SALTARE", True, GRAY)
        screen.blit(skip, (WIDTH//2 - skip.get_width()//2, 500))
        if pygame.key.get_pressed()[pygame.K_SPACE]: game_state = "STORY"; setup_level(level)

    elif game_state == "STORY":
        box = pygame.Rect(WIDTH*0.1, HEIGHT*0.7, WIDTH*0.8, HEIGHT*0.2)
        pygame.draw.rect(screen, (0, 15, 30), box); pygame.draw.rect(screen, P1_COL, box, 2)
        txt = story_data[current_chapter][line_idx]
        if char_idx < len(txt): char_idx += 1
        screen.blit(font_hud.render(txt[:char_idx], True, P1_COL), (box.x + 20, box.y + 20))

    elif game_state == "PLAYING":
        keys = pygame.key.get_pressed()
        
        # --- P1 (WASD) ---
        p1_move = (keys[pygame.K_d]-keys[pygame.K_a], keys[pygame.K_s]-keys[pygame.K_w])
        old_p1 = p1.copy()
        p1.x = max(0, min(WIDTH-30, p1.x + p1_move[0]*6))
        p1.y = max(0, min(HEIGHT-30, p1.y + p1_move[1]*6))
        for w in walls: 
            if p1.colliderect(w): p1 = old_p1
        
        targets = [p1]

        # --- P2 (FRECCE) ---
        if is_2p:
            targets.append(p2)
            p2_move = (keys[pygame.K_RIGHT]-keys[pygame.K_LEFT], keys[pygame.K_DOWN]-keys[pygame.K_UP])
            old_p2 = p2.copy()
            p2.x = max(0, min(WIDTH-30, p2.x + p2_move[0]*6))
            p2.y = max(0, min(HEIGHT-30, p2.y + p2_move[1]*6))
            for w in walls: 
                if p2.colliderect(w): p2 = old_p2
            pygame.draw.rect(screen, P2_COL, p2)

        # Attacco Armi
        if weapon_p1 != "None" and random.random() < 0.05:
            if weapon_p1 == "BLASTER": p_bullets.append(PlayerBullet(p1.centerx, p1.centery, 0, P1_COL))
            if weapon_p1 == "NOVA":
                for a in [0, 1.57, 3.14, 4.71]: p_bullets.append(PlayerBullet(p1.centerx, p1.centery, a, P1_COL))

        # Disegno Muri e Nemici
        for w in walls: pygame.draw.rect(screen, GRAY, w)
        if random.random() < 0.01 + (level * 0.003): enemies.append(Enemy(level))
        
        for b in p_bullets[:]:
            if not b.update(): p_bullets.remove(b)
            else:
                pygame.draw.rect(screen, b.color, b.rect)
                for e in enemies[:]:
                    if b.rect.colliderect(e.rect):
                        enemies.remove(e); p_bullets.remove(b); break

        for e in enemies[:]:
            e.move(targets)
            pygame.draw.rect(screen, RED, e.rect)
            for t in targets:
                if t.colliderect(e.rect):
                    game_state, current_chapter, line_idx, char_idx = "STORY", "game_over", 0, 0

        # Frammento
        pygame.draw.circle(screen, GOLD, fragment.center, 12)
        for t in targets:
            if t.colliderect(fragment):
                score += 1; coins += 1
                fragment.topleft = (random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100))
                if score >= fragments_needed:
                    level += 1; save_progress(level, coins); game_state = "SHOP"

        pygame.draw.rect(screen, P1_COL, p1)
        
        # HUD: Percentuale e Sync
        bar_w = 300
        perc = int((score/fragments_needed)*100)
        pygame.draw.rect(screen, (40, 40, 40), (WIDTH//2 - bar_w//2, 20, bar_w, 20))
        pygame.draw.rect(screen, P1_COL, (WIDTH//2 - bar_w//2, 20, bar_w * (score/fragments_needed), 20))
        hud_txt = font_hud.render(f"SYNC: {perc}% | LVL: {level} | MONETE: {coins}", True, WHITE)
        screen.blit(hud_txt, (WIDTH//2 - hud_txt.get_width()//2, 45))

    pygame.display.flip()
    clock.tick(60)