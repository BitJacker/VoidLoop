import pygame, sys, json, random, os, math, time

# --- LOGICA SALVATAGGI ---
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
SAVE_FILE = os.path.join(SAVE_DIR, "savegame.json")

# Crea la cartella saves se non esiste
if not os.path.exists(SAVE_DIR):
    try:
        os.makedirs(SAVE_DIR)
    except:
        pass

def save_progress(lvl, coins):
    try:
        # Assicurati che la cartella esista
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
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

# --- CONFIGURAZIONE ARGOMENTI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
lang = sys.argv[1] if len(sys.argv) > 1 else "en"
ship_color = sys.argv[2] if len(sys.argv) > 2 else "Neon Green"
is_2p = sys.argv[3] == "2 PLAYERS" if len(sys.argv) > 3 else False
is_full = sys.argv[4] == "FULLSCREEN" if len(sys.argv) > 4 else False
difficulty = sys.argv[5] if len(sys.argv) > 5 else "NORMAL"

DIFF_SETTINGS = {
    "EASY": {"speed_mult": 0.7, "spawn_rate": 0.005, "cost": 5},
    "NORMAL": {"speed_mult": 1.0, "spawn_rate": 0.009, "cost": 10},
    "HARD": {"speed_mult": 1.4, "spawn_rate": 0.015, "cost": 20},
    "NIGHTMARE": {"speed_mult": 1.9, "spawn_rate": 0.025, "cost": 30}
}
cfg = DIFF_SETTINGS.get(difficulty, DIFF_SETTINGS["NORMAL"])

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
P2_COL, WHITE, RED, GOLD, GRAY, CYAN = (255, 100, 0), (255, 255, 255), (255, 50, 50), (255, 215, 0), (60, 60, 60), (0, 255, 255)

clock = pygame.time.Clock()
font_hud = pygame.font.SysFont("Courier New", 22, bold=True)
font_small = pygame.font.SysFont("Courier New", 16, bold=True)

# --- CLASSI ---
class Bullet:
    def __init__(self, x, y, target_pos, color, speed=12):
        self.rect = pygame.Rect(x, y, 8, 8)
        self.color = color
        angle = math.atan2(target_pos[1] - y, target_pos[0] - x)
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
    
    def update(self, walls):
        self.rect.x += self.vx
        self.rect.y += self.vy
        
        # Collisione con muri
        for wall in walls:
            if self.rect.colliderect(wall):
                return False
        
        return 0 <= self.rect.x <= WIDTH and 0 <= self.rect.y <= HEIGHT

class Enemy:
    def __init__(self, level):
        self.rect = pygame.Rect(random.choice([-50, WIDTH+50]), random.randint(0, HEIGHT), 25, 25)
        self.level = level
        
        # PROGRESSIONE VELOCITÀ BASATA SUL LIVELLO
        if level <= 2:
            self.speed = (1.0 + (level * 0.1)) * cfg["speed_mult"]
        elif level <= 4:
            self.speed = (1.3 + ((level - 2) * 0.15)) * cfg["speed_mult"]
        else:
            self.speed = (1.8 + ((level - 4) * 0.25)) * cfg["speed_mult"]
        
        # COOLDOWN SPARO
        if level <= 4:
            self.shoot_cooldown = random.randint(120, 220)
        else:
            self.shoot_cooldown = random.randint(35, 70)

    def move(self, targets):
        target = min(targets, key=lambda t: math.hypot(t.centerx-self.rect.centerx, t.centery-self.rect.centery))
        dx, dy = target.centerx - self.rect.centerx, target.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.rect.x += (dx/dist) * self.speed
            self.rect.y += (dy/dist) * self.speed
        return target

# --- FUNZIONI MOVIMENTO CON COLLISIONI ---
def move_player(player_rect, dx, dy, walls):
    """Muove il player e controlla collisioni con muri"""
    # Movimento orizzontale
    player_rect.x += dx
    for wall in walls:
        if player_rect.colliderect(wall):
            if dx > 0:  # Movimento a destra
                player_rect.right = wall.left
            elif dx < 0:  # Movimento a sinistra
                player_rect.left = wall.right
    
    # Movimento verticale
    player_rect.y += dy
    for wall in walls:
        if player_rect.colliderect(wall):
            if dy > 0:  # Movimento in basso
                player_rect.bottom = wall.top
            elif dy < 0:  # Movimento in alto
                player_rect.top = wall.bottom
    
    # Limiti schermo
    player_rect.x = max(0, min(WIDTH - player_rect.width, player_rect.x))
    player_rect.y = max(0, min(HEIGHT - player_rect.height, player_rect.y))

# --- LOGICA DI GIOCO ---
level, coins = load_progress()
score, p_bullets, e_bullets, enemies, walls = 0, [], [], [], []
p1 = pygame.Rect(WIDTH//2-50, HEIGHT//2, 30, 30)
p2 = pygame.Rect(WIDTH//2+50, HEIGHT//2, 30, 30)
fragment = pygame.Rect(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100), 20, 20)

game_state, current_chapter = "STORY", "prologue"
weapon_unlocked = False
fire_cooldown = 0
line_idx, char_idx = 0, 0

# DASH E SPRINT
dash_cooldown_p1 = 0
dash_cooldown_p2 = 0
sprint_active_p1 = False
sprint_active_p2 = False
DASH_DISTANCE = 60
DASH_COOLDOWN = 45  # Frames
SPRINT_MULTIPLIER = 1.8

# TIMER LIVELLO
level_start_time = 0
level_completion_time = 0

# Dialoghi
json_path = os.path.join(BASE_DIR, "lang", f"dialogues_{lang}.json")
try:
    with open(json_path, "r", encoding="utf-8") as f: story_data = json.load(f)
except: story_data = {"prologue":["LOOP START..."], "game_over":["CONNECTION LOST. REBOOT?"]}

def setup_level(lvl):
    global walls, enemies, p_bullets, e_bullets, score, fragments_needed, line_idx, char_idx, level_start_time
    enemies.clear(); p_bullets.clear(); e_bullets.clear(); walls.clear()
    score, line_idx, char_idx = 0, 0, 0
    fragments_needed = 4 + lvl
    level_start_time = time.time()
    
    # MOLTI PIÙ MURI dal livello 3+
    if lvl >= 3:
        num_walls = min(3 + lvl * 2, 20)  # Aumenta drasticamente con il livello
        for _ in range(num_walls):
            # Muri più grandi e posizionati strategicamente
            w = random.randint(80, 180)
            h = random.randint(15, 30)
            x = random.randint(150, WIDTH - 150 - w)
            y = random.randint(80, HEIGHT - 80 - h)
            walls.append(pygame.Rect(x, y, w, h))

setup_level(level)

while True:
    screen.fill((5, 5, 15))
    m_pos = pygame.mouse.get_pos()
    m_click = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN: m_click = True
        
        # DASH Player 1 (Shift sinistro)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LSHIFT and dash_cooldown_p1 <= 0:
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_d] - keys[pygame.K_a]) * DASH_DISTANCE
            dy = (keys[pygame.K_s] - keys[pygame.K_w]) * DASH_DISTANCE
            if dx != 0 or dy != 0:
                move_player(p1, dx, dy, walls)
                dash_cooldown_p1 = DASH_COOLDOWN
        
        # DASH Player 2 (Shift destro)
        if is_2p and event.type == pygame.KEYDOWN and event.key == pygame.K_RSHIFT and dash_cooldown_p2 <= 0:
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * DASH_DISTANCE
            dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * DASH_DISTANCE
            if dx != 0 or dy != 0:
                move_player(p2, dx, dy, walls)
                dash_cooldown_p2 = DASH_COOLDOWN
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if game_state == "STORY":
                if current_chapter in story_data and line_idx < len(story_data[current_chapter]):
                    txt = story_data[current_chapter][line_idx]
                    if char_idx < len(txt): char_idx = len(txt)
                    else:
                        line_idx += 1; char_idx = 0
                        if line_idx >= len(story_data[current_chapter]):
                            if current_chapter == "game_over":
                                setup_level(level)
                                current_chapter = "prologue"
                            game_state = "PLAYING"
                else: game_state = "PLAYING"

    if game_state == "SHOP":
        # SCHERMATA SHOP MIGLIORATA
        screen.blit(font_hud.render(f"=== LEVEL {level-1} COMPLETE ===", True, GOLD), (WIDTH//2-180, 80))
        
        # Statistiche completamento
        minutes = int(level_completion_time // 60)
        seconds = int(level_completion_time % 60)
        
        y_offset = 150
        stats = [
            f"TIME: {minutes:02d}:{seconds:02d}",
            f"COINS EARNED: +1 per fragment",
            f"TOTAL COINS: {coins}",
            "",
            f"--- ARSENAL ({difficulty}) ---",
            f"WEAPON COST: {cfg['cost']} coins"
        ]
        
        for stat in stats:
            if stat:
                txt = font_small.render(stat, True, CYAN if "ARSENAL" in stat else WHITE)
                screen.blit(txt, (WIDTH//2 - txt.get_width()//2, y_offset))
            y_offset += 30
        
        # Bottone acquisto
        btn = pygame.Rect(WIDTH//2-150, 400, 300, 60)
        can_buy = coins >= cfg["cost"]
        btn_color = CYAN if (btn.collidepoint(m_pos) and can_buy) else (GRAY if not can_buy else (100, 100, 100))
        pygame.draw.rect(screen, btn_color, btn, 3)
        
        btn_txt = f"BUY WEAPON ({cfg['cost']} P.)" if not weapon_unlocked else "WEAPON OWNED"
        screen.blit(font_hud.render(btn_txt, True, WHITE if can_buy else GRAY), (btn.x+20, btn.y+18))
        
        if m_click and btn.collidepoint(m_pos) and can_buy and not weapon_unlocked:
            coins -= cfg["cost"]; weapon_unlocked = True
            save_progress(level, coins)
        
        # Bottone continua
        continue_btn = pygame.Rect(WIDTH//2-150, 490, 300, 60)
        pygame.draw.rect(screen, GOLD if continue_btn.collidepoint(m_pos) else GRAY, continue_btn, 3)
        screen.blit(font_hud.render("CONTINUE", True, WHITE), (continue_btn.x+75, continue_btn.y+18))
        
        if m_click and continue_btn.collidepoint(m_pos):
            game_state, current_chapter = "STORY", "prologue"
            setup_level(level)
        
        if pygame.key.get_pressed()[pygame.K_SPACE]:
            game_state, current_chapter = "STORY", "prologue"
            setup_level(level)

    elif game_state == "STORY":
        box = pygame.Rect(WIDTH*0.1, HEIGHT*0.7, WIDTH*0.8, HEIGHT*0.2)
        pygame.draw.rect(screen, (0, 15, 30), box); pygame.draw.rect(screen, P1_COL, box, 2)
        if current_chapter in story_data and line_idx < len(story_data[current_chapter]):
            txt = story_data[current_chapter][line_idx]
            if char_idx < len(txt): char_idx += 1
            screen.blit(font_hud.render(txt[:char_idx], True, P1_COL), (box.x + 20, box.y + 20))

    elif game_state == "PLAYING":
        keys = pygame.key.get_pressed()
        
        # SPRINT Player 1 (Ctrl sinistro)
        sprint_active_p1 = keys[pygame.K_LCTRL]
        speed_p1 = 6 * (SPRINT_MULTIPLIER if sprint_active_p1 else 1.0)
        
        dx = (keys[pygame.K_d] - keys[pygame.K_a]) * speed_p1
        dy = (keys[pygame.K_s] - keys[pygame.K_w]) * speed_p1
        move_player(p1, dx, dy, walls)
        
        targets = [p1]
        if is_2p:
            targets.append(p2)
            # SPRINT Player 2 (Ctrl destro)
            sprint_active_p2 = keys[pygame.K_RCTRL]
            speed_p2 = 6 * (SPRINT_MULTIPLIER if sprint_active_p2 else 1.0)
            
            dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * speed_p2
            dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * speed_p2
            move_player(p2, dx, dy, walls)
            pygame.draw.rect(screen, P2_COL, p2)

        # Cooldown dash
        if dash_cooldown_p1 > 0: dash_cooldown_p1 -= 1
        if dash_cooldown_p2 > 0: dash_cooldown_p2 -= 1

        # Arma
        if weapon_unlocked:
            if fire_cooldown > 0: fire_cooldown -= 1
            if pygame.mouse.get_pressed()[0] and fire_cooldown <= 0:
                p_bullets.append(Bullet(p1.centerx, p1.centery, m_pos, P1_COL))
                fire_cooldown = 12
            pygame.draw.circle(screen, P1_COL, m_pos, 8, 1)

        # Spawn nemici
        spawn_chance = cfg["spawn_rate"] + (level * 0.002)
        if level >= 5: spawn_chance += 0.005
        if random.random() < spawn_chance: enemies.append(Enemy(level))
        
        # Proiettili Player
        for b in p_bullets[:]:
            if not b.update(walls): p_bullets.remove(b)
            else:
                pygame.draw.rect(screen, b.color, b.rect)
                for e in enemies[:]:
                    if b.rect.colliderect(e.rect):
                        enemies.remove(e); p_bullets.remove(b); break

        # Proiettili Nemici
        for eb in e_bullets[:]:
            if not eb.update(walls): e_bullets.remove(eb)
            else:
                pygame.draw.circle(screen, RED, eb.rect.center, 5)
                for t in targets:
                    if eb.rect.colliderect(t): 
                        game_state, current_chapter, line_idx, char_idx = "STORY", "game_over", 0, 0

        # Nemici
        for e in enemies[:]:
            target = e.move(targets)
            pygame.draw.rect(screen, RED, e.rect)
            
            if level >= 3:
                e.shoot_cooldown -= 1
                if e.shoot_cooldown <= 0:
                    bullet_speed = 6 if level <= 4 else 11
                    e_bullets.append(Bullet(e.rect.centerx, e.rect.centery, target.center, RED, speed=bullet_speed))
                    if level <= 4:
                        e.shoot_cooldown = random.randint(120, 220)
                    else:
                        e.shoot_cooldown = random.randint(35, 70)

            for t in targets:
                if t.colliderect(e.rect): 
                    game_state, current_chapter, line_idx, char_idx = "STORY", "game_over", 0, 0

        # Muri
        for w in walls: 
            pygame.draw.rect(screen, GRAY, w)
            pygame.draw.rect(screen, (100, 100, 100), w, 2)  # Bordo
        
        # Frammento
        pygame.draw.circle(screen, GOLD, fragment.center, 12)
        for t in targets:
            if t.colliderect(fragment):
                score += 1; coins += 1
                fragment.topleft = (random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100))
                if score >= fragments_needed:
                    level_completion_time = time.time() - level_start_time
                    level += 1
                    save_progress(level, coins)
                    game_state = "SHOP"

        # Player
        pygame.draw.rect(screen, P1_COL, p1)
        # Indicatore sprint
        if sprint_active_p1:
            pygame.draw.rect(screen, (255, 255, 0), p1, 2)
        
        # HUD
        perc = int((score/fragments_needed)*100)
        pygame.draw.rect(screen, (40, 40, 40), (WIDTH//2-150, 20, 300, 20))
        pygame.draw.rect(screen, P1_COL, (WIDTH//2-150, 20, 300*(score/fragments_needed), 20))
        hud_txt = font_hud.render(f"SYNC: {perc}% | {difficulty} | LVL: {level}", True, WHITE)
        screen.blit(hud_txt, (WIDTH//2 - hud_txt.get_width()//2, 45))
        
        # Timer
        elapsed = int(time.time() - level_start_time)
        timer_txt = font_small.render(f"TIME: {elapsed//60:02d}:{elapsed%60:02d}", True, WHITE)
        screen.blit(timer_txt, (10, 10))
        
        # Dash cooldown
        if dash_cooldown_p1 > 0:
            dash_txt = font_small.render(f"DASH: {dash_cooldown_p1//10}", True, CYAN)
            screen.blit(dash_txt, (10, 35))
        else:
            screen.blit(font_small.render("DASH: READY", True, GOLD), (10, 35))
        
        # Coins
        coins_txt = font_small.render(f"COINS: {coins}", True, GOLD)
        screen.blit(coins_txt, (WIDTH - 120, 10))

    pygame.display.flip()
    clock.tick(60)
