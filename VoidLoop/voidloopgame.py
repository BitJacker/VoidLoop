import pygame, sys, json, random, os, math, time

# --- LOGICA SALVATAGGI ---
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
SAVE_FILE = os.path.join(SAVE_DIR, "savegame.json")

if not os.path.exists(SAVE_DIR):
    try:
        os.makedirs(SAVE_DIR)
    except:
        pass

def save_progress(lvl, coins, achievements=None):
    try:
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        data = {"level": lvl, "coins": coins}
        if achievements:
            data["achievements"] = achievements
        with open(SAVE_FILE, "w") as f: 
            json.dump(data, f)
    except: 
        pass

def load_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                return data.get("level", 1), data.get("coins", 0), data.get("achievements", [])
        except: 
            return 1, 0, []
    return 1, 0, []

# --- CONFIGURAZIONE ARGOMENTI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
lang = sys.argv[1] if len(sys.argv) > 1 else "en"
ship_color = sys.argv[2] if len(sys.argv) > 2 else "Neon Green"
is_2p = sys.argv[3] == "2 PLAYERS" if len(sys.argv) > 3 else False
is_full = sys.argv[4] == "FULLSCREEN" if len(sys.argv) > 4 else False
difficulty = sys.argv[5] if len(sys.argv) > 5 else "NORMAL"
game_mode = sys.argv[6] if len(sys.argv) > 6 else "STORY"

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
    WIDTH, HEIGHT = 1200, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

COLOR_MAP = {"Neon Green": (0, 255, 150), "Cyber Blue": (0, 150, 255), "Void Purple": (180, 0, 255)}
P1_COL = COLOR_MAP.get(ship_color, (0, 255, 150))
P2_COL, WHITE, RED, GOLD, GRAY, CYAN = (255, 100, 0), (255, 255, 255), (255, 50, 50), (255, 215, 0), (60, 60, 60), (0, 255, 255)
ORANGE, PINK, PURPLE = (255, 150, 0), (255, 100, 200), (180, 0, 255)

clock = pygame.time.Clock()
font_hud = pygame.font.SysFont("Courier New", 22, bold=True)
font_small = pygame.font.SysFont("Courier New", 16, bold=True)
font_big = pygame.font.SysFont("Courier New", 48, bold=True)
font_medium = pygame.font.SysFont("Courier New", 32, bold=True)

# --- TRADUZIONI MENU PAUSA ---
PAUSE_TEXTS = {
    "it": {"title": "GIOCO IN PAUSA", "continue": "CONTINUA", "save": "SALVA PARTITA", "exit": "ESCI AL MENU", "saved": "Partita salvata!"},
    "en": {"title": "GAME PAUSED", "continue": "CONTINUE", "save": "SAVE GAME", "exit": "EXIT TO MENU", "saved": "Game saved!"},
    "es": {"title": "JUEGO PAUSADO", "continue": "CONTINUAR", "save": "GUARDAR PARTIDA", "exit": "SALIR AL MENÚ", "saved": "¡Partida guardada!"},
    "fr": {"title": "JEU EN PAUSE", "continue": "CONTINUER", "save": "SAUVEGARDER", "exit": "QUITTER AU MENU", "saved": "Partie sauvegardée!"}
}

# --- PARTICELLE ---
class Particle:
    def __init__(self, x, y, color, speed=3):
        self.x, self.y = x, y
        self.color = color
        self.vx = random.uniform(-speed, speed)
        self.vy = random.uniform(-speed, speed)
        self.life = random.randint(20, 40)
        self.size = random.randint(2, 5)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(1, self.size - 0.1)
        return self.life > 0
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

# --- SPINE (Boss Level 4) ---
class Spike:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.size = 5
        self.max_size = 40
        self.growing = True
        self.lifetime = 180  # 3 secondi
        
    def update(self):
        if self.growing:
            self.size += 2
            if self.size >= self.max_size:
                self.growing = False
        else:
            self.lifetime -= 1
        return self.lifetime > 0
    
    def draw(self, screen):
        # Disegna spike triangolare
        points = [
            (self.x, self.y - self.size),
            (self.x - self.size//2, self.y + self.size//2),
            (self.x + self.size//2, self.y + self.size//2)
        ]
        pygame.draw.polygon(screen, RED, points)
        pygame.draw.polygon(screen, (255, 100, 100), points, 2)
    
    def get_rect(self):
        return pygame.Rect(self.x - self.size//2, self.y - self.size, self.size, self.size * 1.5)

# --- POWER-UPS ---
class PowerUp:
    TYPES = {
        "SHIELD": {"color": CYAN, "duration": 300, "icon": "S"},
        "SPEED": {"color": (255, 255, 0), "duration": 240, "icon": "⚡"},
        "DOUBLE_DAMAGE": {"color": RED, "duration": 180, "icon": "2X"},
        "RAPID_FIRE": {"color": ORANGE, "duration": 200, "icon": "R"}
    }
    
    def __init__(self, x, y, power_type=None):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.type = power_type or random.choice(list(PowerUp.TYPES.keys()))
        self.data = PowerUp.TYPES[self.type]
        self.pulse = 0
    
    def draw(self, screen):
        self.pulse = (self.pulse + 0.1) % (2 * math.pi)
        size_offset = int(math.sin(self.pulse) * 3)
        rect = self.rect.inflate(size_offset, size_offset)
        
        pygame.draw.rect(screen, self.data["color"], rect)
        pygame.draw.rect(screen, WHITE, rect, 2)
        
        icon = font_small.render(self.data["icon"], True, WHITE)
        screen.blit(icon, (rect.x + 5, rect.y + 5))

# --- BULLET ---
class Bullet:
    def __init__(self, x, y, target_pos, color, speed=12, damage=1):
        self.rect = pygame.Rect(x, y, 8, 8)
        self.color = color
        self.damage = damage
        angle = math.atan2(target_pos[1] - y, target_pos[0] - x)
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
    
    def update(self, walls):
        self.rect.x += self.vx
        self.rect.y += self.vy
        
        for wall in walls:
            if self.rect.colliderect(wall):
                return False
        
        return 0 <= self.rect.x <= WIDTH and 0 <= self.rect.y <= HEIGHT

# --- ENEMY ---
class Enemy:
    def __init__(self, level, enemy_type="NORMAL"):
        self.type = enemy_type
        self.level = level
        
        if enemy_type == "TANK":
            self.rect = pygame.Rect(random.choice([-50, WIDTH+50]), random.randint(0, HEIGHT), 40, 40)
            self.speed = (0.8 + (level * 0.05)) * cfg["speed_mult"]
            self.hp = 3 + level // 2
            self.color = (150, 50, 50)
            self.shoot_cooldown = random.randint(150, 250)
        elif enemy_type == "SNIPER":
            self.rect = pygame.Rect(random.choice([-50, WIDTH+50]), random.randint(0, HEIGHT), 20, 20)
            self.speed = (0.5 + (level * 0.03)) * cfg["speed_mult"]
            self.hp = 1
            self.color = (255, 150, 0)
            self.shoot_cooldown = random.randint(80, 120)
        elif enemy_type == "KAMIKAZE":
            self.rect = pygame.Rect(random.choice([-50, WIDTH+50]), random.randint(0, HEIGHT), 18, 18)
            self.speed = (2.5 + (level * 0.15)) * cfg["speed_mult"]
            self.hp = 1
            self.color = (255, 0, 255)
            self.shoot_cooldown = 9999
        else:
            self.rect = pygame.Rect(random.choice([-50, WIDTH+50]), random.randint(0, HEIGHT), 25, 25)
            self.hp = 1
            self.color = RED
            
            if level <= 2:
                self.speed = (1.0 + (level * 0.1)) * cfg["speed_mult"]
            elif level <= 4:
                self.speed = (1.3 + ((level - 2) * 0.15)) * cfg["speed_mult"]
            else:
                self.speed = (1.8 + ((level - 4) * 0.25)) * cfg["speed_mult"]
            
            self.shoot_cooldown = random.randint(120, 220) if level <= 4 else random.randint(35, 70)
        
        self.max_hp = self.hp

    def move(self, targets):
        target = min(targets, key=lambda t: math.hypot(t.centerx-self.rect.centerx, t.centery-self.rect.centery))
        dx, dy = target.centerx - self.rect.centerx, target.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        
        if self.type == "SNIPER" and dist < 200:
            self.rect.x -= (dx/dist) * self.speed
            self.rect.y -= (dy/dist) * self.speed
        else:
            if dist > 0:
                self.rect.x += (dx/dist) * self.speed
                self.rect.y += (dy/dist) * self.speed
        
        return target
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        
        if self.type == "TANK":
            pygame.draw.rect(screen, WHITE, self.rect, 3)
        elif self.type == "SNIPER":
            pygame.draw.circle(screen, self.color, self.rect.center, self.rect.width//2 + 3, 1)
        elif self.type == "KAMIKAZE":
            for i in range(3):
                pygame.draw.rect(screen, (255, 0, 255, 100), self.rect.inflate(3 + i*2, 3 + i*2), 1)
        
        if self.type == "TANK" and self.hp < self.max_hp:
            hp_width = int((self.hp / self.max_hp) * self.rect.width)
            pygame.draw.rect(screen, RED, (self.rect.x, self.rect.y - 8, self.rect.width, 4))
            pygame.draw.rect(screen, (0, 255, 0), (self.rect.x, self.rect.y - 8, hp_width, 4))

# --- BOSS MIGLIORATO ---
class Boss:
    def __init__(self, level):
        self.rect = pygame.Rect(WIDTH//2 - 60, 50, 120, 120)
        self.level = level
        self.hp = 50 + (level * 20)
        self.max_hp = self.hp
        self.speed = 2.0 * cfg["speed_mult"]
        self.shoot_cooldown = 0
        self.phase = 1
        self.pattern = 0
        self.pattern_timer = 0
        self.dash_cooldown = 0
        self.teleport_cooldown = 0
        self.spike_cooldown = 0
        
    def update(self, targets):
        self.pattern_timer += 1
        
        # LEVEL 2+: DASH
        if self.level >= 2 and self.dash_cooldown <= 0 and random.random() < 0.01:
            target = random.choice(targets)
            dx = target.centerx - self.rect.centerx
            dy = target.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.rect.x += (dx/dist) * 100
                self.rect.y += (dy/dist) * 100
                self.dash_cooldown = 120
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        
        # LEVEL 3+: TELEPORT
        if self.level >= 3 and self.teleport_cooldown <= 0 and random.random() < 0.005:
            self.rect.x = random.randint(100, WIDTH-100)
            self.rect.y = random.randint(100, 300)
            self.teleport_cooldown = 180
        
        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= 1
        
        # MOVIMENTO NORMALE
        if self.pattern == 0:
            center_x, center_y = WIDTH//2, HEIGHT//3
            angle = self.pattern_timer * 0.03
            radius = 150
            target_x = center_x + math.cos(angle) * radius
            target_y = center_y + math.sin(angle) * radius
        elif self.pattern == 1:
            target_x = WIDTH//2 + math.sin(self.pattern_timer * 0.02) * 300
            target_y = HEIGHT//3
        else:
            target = random.choice(targets)
            target_x = target.centerx
            target_y = max(100, target.centery - 150)
        
        dx = target_x - self.rect.centerx
        dy = target_y - self.rect.centery
        dist = math.hypot(dx, dy)
        
        if dist > 5:
            self.rect.x += (dx/dist) * self.speed
            self.rect.y += (dy/dist) * self.speed
        
        if self.pattern_timer > 300:
            self.pattern = (self.pattern + 1) % 3
            self.pattern_timer = 0
        
        if self.hp < self.max_hp * 0.3:
            self.phase = 3
        elif self.hp < self.max_hp * 0.6:
            self.phase = 2
    
    def draw(self, screen):
        # Teleport warning
        if self.teleport_cooldown > 0 and self.teleport_cooldown < 30:
            alpha = int((self.teleport_cooldown / 30) * 255)
            for i in range(10, 0, -1):
                glow_rect = self.rect.inflate(i*8, i*8)
                pygame.draw.rect(screen, (0, 255, 255, alpha//i), glow_rect, 2)
        
        for i in range(5, 0, -1):
            glow_rect = self.rect.inflate(i*4, i*4)
            color = (100 + i*20, 0, 100 + i*20)
            pygame.draw.rect(screen, color, glow_rect, 2)
        
        pygame.draw.rect(screen, PURPLE, self.rect)
        pygame.draw.rect(screen, PINK, self.rect, 4)
        
        eye_y = self.rect.y + 40
        pygame.draw.circle(screen, RED, (self.rect.x + 30, eye_y), 10)
        pygame.draw.circle(screen, RED, (self.rect.x + 90, eye_y), 10)
        
        # HP Bar
        hp_bar_width = WIDTH - 200
        hp_bar_x = 100
        hp_bar_y = 20
        
        pygame.draw.rect(screen, GRAY, (hp_bar_x, hp_bar_y, hp_bar_width, 25))
        hp_width = int((self.hp / self.max_hp) * hp_bar_width)
        
        hp_color = RED if self.phase == 3 else ORANGE if self.phase == 2 else PURPLE
        
        pygame.draw.rect(screen, hp_color, (hp_bar_x, hp_bar_y, hp_width, 25))
        pygame.draw.rect(screen, WHITE, (hp_bar_x, hp_bar_y, hp_bar_width, 25), 3)
        
        hp_text = font_small.render(f"BOSS LV{self.level}: {self.hp}/{self.max_hp} | PHASE {self.phase}", True, WHITE)
        screen.blit(hp_text, (hp_bar_x + hp_bar_width//2 - hp_text.get_width()//2, hp_bar_y + 5))

# --- MELEE WEAPON (Horde) ---
class MeleeWeapon:
    def __init__(self, owner):
        self.owner = owner
        self.swinging = False
        self.swing_timer = 0
        self.swing_duration = 15
        self.cooldown = 0
        self.angle = 0
        self.damage = 2
        
    def swing(self, mouse_pos):
        if self.cooldown <= 0:
            self.swinging = True
            self.swing_timer = self.swing_duration
            self.cooldown = 30
            # Calcola angolo verso mouse
            dx = mouse_pos[0] - self.owner.centerx
            dy = mouse_pos[1] - self.owner.centery
            self.angle = math.atan2(dy, dx)
    
    def update(self):
        if self.swing_timer > 0:
            self.swing_timer -= 1
            if self.swing_timer == 0:
                self.swinging = False
        if self.cooldown > 0:
            self.cooldown -= 1
    
    def draw(self, screen):
        if self.swinging:
            # Disegna mazza che ruota
            progress = 1 - (self.swing_timer / self.swing_duration)
            current_angle = self.angle + (progress * math.pi)
            
            end_x = self.owner.centerx + math.cos(current_angle) * 50
            end_y = self.owner.centery + math.sin(current_angle) * 50
            
            pygame.draw.line(screen, GRAY, self.owner.center, (end_x, end_y), 8)
            pygame.draw.circle(screen, RED, (int(end_x), int(end_y)), 12)
    
    def get_hit_rect(self):
        if self.swinging:
            progress = 1 - (self.swing_timer / self.swing_duration)
            current_angle = self.angle + (progress * math.pi)
            
            end_x = self.owner.centerx + math.cos(current_angle) * 50
            end_y = self.owner.centery + math.sin(current_angle) * 50
            
            return pygame.Rect(end_x - 12, end_y - 12, 24, 24)
        return None

# --- FUNZIONI ---
def move_player(player_rect, dx, dy, walls):
    player_rect.x += dx
    for wall in walls:
        if player_rect.colliderect(wall):
            if dx > 0:
                player_rect.right = wall.left
            elif dx < 0:
                player_rect.left = wall.right
    
    player_rect.y += dy
    for wall in walls:
        if player_rect.colliderect(wall):
            if dy > 0:
                player_rect.bottom = wall.top
            elif dy < 0:
                player_rect.top = wall.bottom
    
    player_rect.x = max(0, min(WIDTH - player_rect.width, player_rect.x))
    player_rect.y = max(0, min(HEIGHT - player_rect.height, player_rect.y))

def draw_pause_menu(screen, lang):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    menu_width, menu_height = 500, 400
    menu_x, menu_y = WIDTH//2 - menu_width//2, HEIGHT//2 - menu_height//2
    
    for i in range(5, 0, -1):
        glow_rect = pygame.Rect(menu_x - i*2, menu_y - i*2, menu_width + i*4, menu_height + i*4)
        pygame.draw.rect(screen, (0, 255, 150, 50), glow_rect, 2)
    
    pygame.draw.rect(screen, (10, 10, 20), (menu_x, menu_y, menu_width, menu_height))
    pygame.draw.rect(screen, (0, 255, 150), (menu_x, menu_y, menu_width, menu_height), 3)
    
    texts = PAUSE_TEXTS.get(lang, PAUSE_TEXTS["en"])
    title = font_big.render(texts["title"], True, (0, 255, 150))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, menu_y + 40))
    
    buttons = []
    button_y = menu_y + 140
    
    for text_key in ["continue", "save", "exit"]:
        btn_rect = pygame.Rect(menu_x + 50, button_y, menu_width - 100, 60)
        buttons.append((btn_rect, text_key))
        button_y += 80
    
    return buttons

def draw_pause_button(screen, rect, text, color, hover, lang):
    texts = PAUSE_TEXTS.get(lang, PAUSE_TEXTS["en"])
    
    if hover:
        for i in range(3, 0, -1):
            glow_rect = rect.inflate(i*2, i*2)
            pygame.draw.rect(screen, color, glow_rect, 2)
        pygame.draw.rect(screen, (30, 30, 40), rect)
    else:
        pygame.draw.rect(screen, (20, 20, 30), rect)
    
    pygame.draw.rect(screen, color, rect, 3)
    
    button_text = font_medium.render(texts[text], True, color if hover else (150, 150, 150))
    text_x = rect.x + rect.width//2 - button_text.get_width()//2
    text_y = rect.y + rect.height//2 - button_text.get_height()//2
    screen.blit(button_text, (text_x, text_y))

# --- GAME VARIABLES ---
level, coins, achievements = load_progress()
score, p_bullets, e_bullets, enemies, walls, particles, power_ups = 0, [], [], [], [], [], []
active_powerups = {}
combo_counter, combo_timer, total_kills = 0, 0, 0

p1 = pygame.Rect(WIDTH//2-50, HEIGHT//2, 30, 30)
p2 = pygame.Rect(WIDTH//2+50, HEIGHT//2, 30, 30)

game_state, current_chapter = "STORY", "prologue"
paused, save_notification = False, 0
weapon_unlocked = False
fire_cooldown = 0
line_idx, char_idx = 0, 0

boss = None
boss_defeated = False
spikes = []

wave_number, enemies_this_wave = 1, 0
weapon_level = 1  # TIME_ATTACK weapon upgrade
melee_weapon = None  # HORDE melee weapon

dash_cooldown_p1, dash_cooldown_p2 = 0, 0
sprint_active_p1, sprint_active_p2 = False, False
DASH_DISTANCE, DASH_COOLDOWN, SPRINT_MULTIPLIER = 60, 45, 1.8

level_start_time, level_completion_time = 0, 0

json_path = os.path.join(BASE_DIR, "lang", f"dialogues_{lang}.json")
try:
    with open(json_path, "r", encoding="utf-8") as f: 
        story_data = json.load(f)
except: 
    story_data = {"prologue":["LOOP START..."], "game_over":["CONNECTION LOST. REBOOT?"]}

def spawn_powerup():
    if random.random() < 0.15:
        power_ups.append(PowerUp(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100)))

def setup_level(lvl):
    global walls, enemies, p_bullets, e_bullets, score, fragments_needed, line_idx, char_idx
    global level_start_time, boss, boss_defeated, wave_number, enemies_this_wave, particles, power_ups
    global combo_counter, combo_timer, weapon_unlocked, weapon_level, melee_weapon, spikes
    
    enemies.clear()
    p_bullets.clear()
    e_bullets.clear()
    walls.clear()
    particles.clear()
    power_ups.clear()
    spikes.clear()
    
    score, line_idx, char_idx = 0, 0, 0
    boss, boss_defeated = None, False
    combo_counter, combo_timer = 0, 0
    level_start_time = time.time()
    
    # MODE-SPECIFIC SETUP
    if game_mode == "BOSS_RUSH":
        fragments_needed = 0  # No fragments needed
        weapon_unlocked = True  # Start with weapon
        boss = Boss(lvl)
        
    elif game_mode == "HORDE":
        fragments_needed = 0  # No fragments
        wave_number = 1
        enemies_this_wave = 5 + lvl * 2
        melee_weapon = MeleeWeapon(p1)  # Give melee weapon
        
    elif game_mode == "TIME_ATTACK":
        fragments_needed = 0  # No fragments, just kill enemies
        weapon_unlocked = True  # Start with weapon
        weapon_level = 1
        
    elif game_mode == "ENDLESS":
        fragments_needed = 0  # No fragments in endless
        weapon_unlocked = True  # Start with weapon
        
    else:  # STORY mode
        fragments_needed = 4 + lvl
        if lvl % 5 == 0:
            boss = Boss(lvl)
        
        # WALLS only in STORY
        if lvl >= 3:
            num_walls = min(3 + lvl * 2, 25)
            for _ in range(num_walls):
                w, h = random.randint(80, 200), random.randint(15, 35)
                x = random.randint(150, WIDTH - 150 - w)
                y = random.randint(80, HEIGHT - 80 - h)
                walls.append(pygame.Rect(x, y, w, h))

setup_level(level)
fragment = pygame.Rect(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100), 20, 20)

# MAIN LOOP
while True:
    screen.fill((5, 5, 15))
    m_pos = pygame.mouse.get_pos()
    m_click = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN: 
            m_click = True
            
            # HORDE: Melee attack
            if game_mode == "HORDE" and melee_weapon and not paused:
                melee_weapon.swing(m_pos)
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and game_state == "PLAYING":
                paused = not paused
            
            if event.key == pygame.K_LSHIFT and dash_cooldown_p1 <= 0 and not paused:
                keys = pygame.key.get_pressed()
                dx = (keys[pygame.K_d] - keys[pygame.K_a]) * DASH_DISTANCE
                dy = (keys[pygame.K_s] - keys[pygame.K_w]) * DASH_DISTANCE
                if dx != 0 or dy != 0:
                    move_player(p1, dx, dy, walls)
                    dash_cooldown_p1 = DASH_COOLDOWN
                    for _ in range(15):
                        particles.append(Particle(p1.centerx, p1.centery, P1_COL, speed=5))
            
            if is_2p and event.key == pygame.K_RSHIFT and dash_cooldown_p2 <= 0 and not paused:
                keys = pygame.key.get_pressed()
                dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * DASH_DISTANCE
                dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * DASH_DISTANCE
                if dx != 0 or dy != 0:
                    move_player(p2, dx, dy, walls)
                    dash_cooldown_p2 = DASH_COOLDOWN
                    for _ in range(15):
                        particles.append(Particle(p2.centerx, p2.centery, P2_COL, speed=5))
            
            if event.key == pygame.K_SPACE and not paused:
                if game_state == "STORY":
                    if current_chapter in story_data and line_idx < len(story_data[current_chapter]):
                        txt = story_data[current_chapter][line_idx]
                        if char_idx < len(txt): 
                            char_idx = len(txt)
                        else:
                            line_idx += 1
                            char_idx = 0
                            if line_idx >= len(story_data[current_chapter]):
                                if current_chapter == "game_over":
                                    setup_level(level)
                                    current_chapter = "prologue"
                                game_state = "PLAYING"
                    else: 
                        game_state = "PLAYING"

    if game_state == "SHOP":
        screen.blit(font_big.render(f"LEVEL {level-1} COMPLETE", True, GOLD), (WIDTH//2-250, 80))
        
        minutes, seconds = int(level_completion_time // 60), int(level_completion_time % 60)
        
        y_offset = 180
        stats = [
            f"TIME: {minutes:02d}:{seconds:02d}",
            f"KILLS: {total_kills}",
            f"COINS EARNED: +{score}",
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
        
        btn = pygame.Rect(WIDTH//2-150, 450, 300, 60)
        can_buy = coins >= cfg["cost"]
        btn_color = CYAN if (btn.collidepoint(m_pos) and can_buy) else (GRAY if not can_buy else (100, 100, 100))
        pygame.draw.rect(screen, btn_color, btn, 3)
        
        btn_txt = f"BUY WEAPON ({cfg['cost']} P.)" if not weapon_unlocked else "WEAPON OWNED"
        screen.blit(font_hud.render(btn_txt, True, WHITE if can_buy else GRAY), (btn.x+20, btn.y+18))
        
        if m_click and btn.collidepoint(m_pos) and can_buy and not weapon_unlocked:
            coins -= cfg["cost"]
            weapon_unlocked = True
            save_progress(level, coins, achievements)
        
        continue_btn = pygame.Rect(WIDTH//2-150, 540, 300, 60)
        pygame.draw.rect(screen, GOLD if continue_btn.collidepoint(m_pos) else GRAY, continue_btn, 3)
        screen.blit(font_hud.render("CONTINUE", True, WHITE), (continue_btn.x+75, continue_btn.y+18))
        
        if m_click and continue_btn.collidepoint(m_pos) or pygame.key.get_pressed()[pygame.K_SPACE]:
            game_state, current_chapter = "STORY", "prologue"
            setup_level(level)

    elif game_state == "STORY":
        box = pygame.Rect(WIDTH*0.1, HEIGHT*0.7, WIDTH*0.8, HEIGHT*0.2)
        pygame.draw.rect(screen, (0, 15, 30), box)
        pygame.draw.rect(screen, P1_COL, box, 2)
        
        if current_chapter in story_data and line_idx < len(story_data[current_chapter]):
            txt = story_data[current_chapter][line_idx]
            if char_idx < len(txt): 
                char_idx += 1
            screen.blit(font_hud.render(txt[:char_idx], True, P1_COL), (box.x + 20, box.y + 20))

    elif game_state == "PLAYING" and not paused:
        keys = pygame.key.get_pressed()
        
        for ptype in list(active_powerups.keys()):
            active_powerups[ptype] -= 1
            if active_powerups[ptype] <= 0:
                del active_powerups[ptype]
        
        sprint_active_p1 = keys[pygame.K_LCTRL]
        speed_mult = SPRINT_MULTIPLIER if sprint_active_p1 else 1.0
        if "SPEED" in active_powerups:
            speed_mult *= 1.5
        
        speed_p1 = 6 * speed_mult
        dx = (keys[pygame.K_d] - keys[pygame.K_a]) * speed_p1
        dy = (keys[pygame.K_s] - keys[pygame.K_w]) * speed_p1
        move_player(p1, dx, dy, walls)
        
        targets = [p1]
        if is_2p:
            targets.append(p2)
            sprint_active_p2 = keys[pygame.K_RCTRL]
            speed_mult2 = SPRINT_MULTIPLIER if sprint_active_p2 else 1.0
            if "SPEED" in active_powerups:
                speed_mult2 *= 1.5
            
            speed_p2 = 6 * speed_mult2
            dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * speed_p2
            dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * speed_p2
            move_player(p2, dx, dy, walls)

        if dash_cooldown_p1 > 0: dash_cooldown_p1 -= 1
        if dash_cooldown_p2 > 0: dash_cooldown_p2 -= 1
        
        if combo_timer > 0:
            combo_timer -= 1
        else:
            combo_counter = 0

        # WEAPON SYSTEM
        if weapon_unlocked:
            if fire_cooldown > 0: 
                fire_cooldown -= 1
            
            fire_rate = 12
            if "RAPID_FIRE" in active_powerups:
                fire_rate = 4
            
            if pygame.mouse.get_pressed()[0] and fire_cooldown <= 0:
                base_damage = weapon_level if game_mode == "TIME_ATTACK" else 1
                damage = (base_damage * 2) if "DOUBLE_DAMAGE" in active_powerups else base_damage
                p_bullets.append(Bullet(p1.centerx, p1.centery, m_pos, P1_COL, damage=damage))
                fire_cooldown = fire_rate
                
                for _ in range(5):
                    particles.append(Particle(p1.centerx, p1.centery, P1_COL, speed=2))
            
            pygame.draw.circle(screen, P1_COL, m_pos, 8, 1)
        
        # MELEE WEAPON (HORDE)
        if melee_weapon:
            melee_weapon.update()
            melee_weapon.draw(screen)

        # SPAWN ENEMIES
        if not boss:
            if game_mode == "HORDE":
                if len(enemies) == 0 and enemies_this_wave > 0:
                    for _ in range(min(enemies_this_wave, 10)):
                        e_type = random.choices(["NORMAL", "TANK", "SNIPER", "KAMIKAZE"], weights=[50, 20, 15, 15])[0]
                        enemies.append(Enemy(level, e_type))
                    enemies_this_wave = 0
            elif game_mode in ["ENDLESS", "TIME_ATTACK"]:
                spawn_chance = cfg["spawn_rate"] + (level * 0.002)
                if level >= 5: 
                    spawn_chance += 0.005
                
                if random.random() < spawn_chance:
                    e_type = random.choices(["NORMAL", "TANK", "SNIPER", "KAMIKAZE"], weights=[60, 15, 15, 10])[0] if level >= 3 else "NORMAL"
                    enemies.append(Enemy(level, e_type))
            else:  # STORY
                spawn_chance = cfg["spawn_rate"] + (level * 0.002)
                if level >= 5: 
                    spawn_chance += 0.005
                
                if random.random() < spawn_chance:
                    e_type = random.choices(["NORMAL", "TANK", "SNIPER", "KAMIKAZE"], weights=[60, 15, 15, 10])[0] if level >= 3 else "NORMAL"
                    enemies.append(Enemy(level, e_type))
        
        # POWER-UPS (only STORY and ENDLESS)
        if game_mode in ["STORY", "ENDLESS"] and random.random() < 0.001 and len(power_ups) < 2:
            spawn_powerup()
        
        # BOSS LOGIC
        if boss:
            boss.update(targets)
            boss.draw(screen)
            
            # LEVEL 4+: SPAWN SPIKES
            if boss.level >= 4 and boss.spike_cooldown <= 0:
                for _ in range(3):
                    x, y = random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100)
                    spikes.append(Spike(x, y))
                boss.spike_cooldown = 180
            
            if boss.spike_cooldown > 0:
                boss.spike_cooldown -= 1
            
            # Boss shooting
            boss.shoot_cooldown -= 1
            if boss.shoot_cooldown <= 0:
                if boss.phase == 1:
                    target = random.choice(targets)
                    e_bullets.append(Bullet(boss.rect.centerx, boss.rect.centery, target.center, PURPLE, speed=8))
                    boss.shoot_cooldown = 40
                elif boss.phase == 2:
                    for t in targets:
                        e_bullets.append(Bullet(boss.rect.centerx, boss.rect.centery, t.center, PURPLE, speed=9))
                    boss.shoot_cooldown = 35
                else:
                    for angle in range(0, 360, 30):
                        rad = math.radians(angle)
                        target_x = boss.rect.centerx + math.cos(rad) * 500
                        target_y = boss.rect.centery + math.sin(rad) * 500
                        e_bullets.append(Bullet(boss.rect.centerx, boss.rect.centery, (target_x, target_y), PURPLE, speed=10))
                    boss.shoot_cooldown = 60
            
            for b in p_bullets[:]:
                if boss.rect.colliderect(b.rect):
                    boss.hp -= b.damage
                    p_bullets.remove(b)
                    
                    for _ in range(10):
                        particles.append(Particle(b.rect.centerx, b.rect.centery, PINK, speed=4))
                    
                    if boss.hp <= 0:
                        boss_defeated = True
                        coins += 50
                        total_kills += 1
                        
                        for _ in range(100):
                            particles.append(Particle(boss.rect.centerx, boss.rect.centery, random.choice([PURPLE, PINK, RED]), speed=8))
                        
                        if game_mode == "BOSS_RUSH":
                            level += 1
                            save_progress(level, coins, achievements)
                            game_state = "SHOP"
                        else:
                            boss = None
        
        # SPIKES
        for spike in spikes[:]:
            if not spike.update():
                spikes.remove(spike)
            else:
                spike.draw(screen)
                # Check collision with player
                for t in targets:
                    if spike.get_rect().colliderect(t) and not "SHIELD" in active_powerups:
                        game_state, current_chapter, line_idx, char_idx = "STORY", "game_over", 0, 0
        
        # PLAYER BULLETS
        for b in p_bullets[:]:
            if not b.update(walls): 
                p_bullets.remove(b)
            else:
                pygame.draw.rect(screen, b.color, b.rect)
                
                for e in enemies[:]:
                    if b.rect.colliderect(e.rect):
                        e.hp -= b.damage
                        
                        if e.hp <= 0:
                            enemies.remove(e)
                            total_kills += 1
                            combo_counter += 1
                            combo_timer = 120
                            
                            # TIME_ATTACK: Upgrade weapon
                            if game_mode == "TIME_ATTACK" and total_kills % 10 == 0:
                                weapon_level += 1
                            
                            if combo_counter >= 5:
                                coins += combo_counter // 5
                            
                            for _ in range(15):
                                particles.append(Particle(e.rect.centerx, e.rect.centery, e.color, speed=4))
                        
                        try:
                            p_bullets.remove(b)
                        except:
                            pass
                        break

        # MELEE WEAPON HITS
        if melee_weapon and melee_weapon.swinging:
            hit_rect = melee_weapon.get_hit_rect()
            if hit_rect:
                for e in enemies[:]:
                    if hit_rect.colliderect(e.rect):
                        e.hp -= melee_weapon.damage
                        
                        if e.hp <= 0:
                            enemies.remove(e)
                            total_kills += 1
                            combo_counter += 1
                            combo_timer = 120
                            
                            for _ in range(15):
                                particles.append(Particle(e.rect.centerx, e.rect.centery, e.color, speed=4))

        # ENEMY BULLETS
        for eb in e_bullets[:]:
            if not eb.update(walls): 
                e_bullets.remove(eb)
            else:
                pygame.draw.circle(screen, eb.color, eb.rect.center, 5)
                
                for t in targets:
                    if eb.rect.colliderect(t):
                        if "SHIELD" in active_powerups:
                            try:
                                e_bullets.remove(eb)
                            except:
                                pass
                            for _ in range(10):
                                particles.append(Particle(t.centerx, t.centery, CYAN, speed=3))
                        else:
                            game_state, current_chapter, line_idx, char_idx = "STORY", "game_over", 0, 0

        # ENEMIES
        for e in enemies[:]:
            target = e.move(targets)
            e.draw(screen)
            
            if level >= 3 and e.type != "KAMIKAZE":
                e.shoot_cooldown -= 1
                if e.shoot_cooldown <= 0:
                    if e.type == "SNIPER":
                        e_bullets.append(Bullet(e.rect.centerx, e.rect.centery, target.center, e.color, speed=14))
                        e.shoot_cooldown = random.randint(80, 120)
                    elif e.type == "TANK":
                        for offset in [-20, 0, 20]:
                            e_bullets.append(Bullet(e.rect.centerx, e.rect.centery, (target.centerx + offset, target.centery), e.color, speed=6))
                        e.shoot_cooldown = random.randint(150, 250)
                    else:
                        e_bullets.append(Bullet(e.rect.centerx, e.rect.centery, target.center, RED, speed=6 if level <= 4 else 11))
                        e.shoot_cooldown = random.randint(120, 220) if level <= 4 else random.randint(35, 70)

            for t in targets:
                if t.colliderect(e.rect):
                    if "SHIELD" in active_powerups:
                        try:
                            enemies.remove(e)
                        except:
                            pass
                        for _ in range(15):
                            particles.append(Particle(t.centerx, t.centery, CYAN, speed=4))
                    else:
                        game_state, current_chapter, line_idx, char_idx = "STORY", "game_over", 0, 0

        # POWER-UPS
        for pu in power_ups[:]:
            pu.draw(screen)
            
            for t in targets:
                if t.colliderect(pu.rect):
                    active_powerups[pu.type] = pu.data["duration"]
                    power_ups.remove(pu)
                    
                    for _ in range(20):
                        particles.append(Particle(pu.rect.centerx, pu.rect.centery, pu.data["color"], speed=5))
                    break

        # WALLS (STORY only)
        for w in walls:
            pygame.draw.rect(screen, GRAY, w)
            pygame.draw.rect(screen, (100, 100, 100), w, 2)
        
        # FRAGMENT (STORY only)
        if game_mode == "STORY" and (not boss or boss_defeated):
            pygame.draw.circle(screen, GOLD, fragment.center, 12)
            pulse = int(abs(math.sin(time.time() * 3)) * 5)
            pygame.draw.circle(screen, GOLD, fragment.center, 12 + pulse, 1)
            
            for t in targets:
                if t.colliderect(fragment):
                    score += 1
                    coins += 1
                    combo_counter += 1
                    combo_timer = 120
                    
                    for _ in range(20):
                        particles.append(Particle(fragment.centerx, fragment.centery, GOLD, speed=4))
                    
                    fragment.topleft = (random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100))
                    
                    if score >= fragments_needed:
                        level_completion_time = time.time() - level_start_time
                        level += 1
                        save_progress(level, coins, achievements)
                        game_state = "SHOP"
        
        # LEVEL COMPLETION (other modes)
        if game_mode == "ENDLESS":
            # Endless never ends, just gets harder
            if len(enemies) == 0:
                level += 1
                setup_level(level)
        
        elif game_mode == "HORDE":
            if len(enemies) == 0 and enemies_this_wave == 0:
                wave_number += 1
                enemies_this_wave = 5 + level * 2 + wave_number * 3
                
                if wave_number > 10:
                    level_completion_time = time.time() - level_start_time
                    level += 1
                    save_progress(level, coins, achievements)
                    game_state = "SHOP"

        # PARTICLES
        for p in particles[:]:
            if p.update():
                p.draw(screen)
            else:
                particles.remove(p)

        # PLAYER
        pygame.draw.rect(screen, P1_COL, p1)
        
        if sprint_active_p1:
            pygame.draw.rect(screen, (255, 255, 0), p1, 2)
        if "SHIELD" in active_powerups:
            shield_pulse = int(abs(math.sin(time.time() * 5)) * 3)
            pygame.draw.rect(screen, CYAN, p1.inflate(10 + shield_pulse, 10 + shield_pulse), 2)
        if "SPEED" in active_powerups:
            for _ in range(2):
                if random.random() < 0.3:
                    particles.append(Particle(p1.centerx, p1.centery, (255, 255, 0), speed=1))
        
        if is_2p:
            pygame.draw.rect(screen, P2_COL, p2)
            if sprint_active_p2:
                pygame.draw.rect(screen, (255, 255, 0), p2, 2)
            if "SHIELD" in active_powerups:
                shield_pulse = int(abs(math.sin(time.time() * 5)) * 3)
                pygame.draw.rect(screen, CYAN, p2.inflate(10 + shield_pulse, 10 + shield_pulse), 2)

        # HUD
        if game_mode == "STORY":
            perc = int((score/fragments_needed)*100)
            bar_width = 400
            bar_x = WIDTH//2 - bar_width//2
            pygame.draw.rect(screen, (40, 40, 40), (bar_x, 20, bar_width, 25))
            pygame.draw.rect(screen, P1_COL, (bar_x, 20, bar_width*(score/fragments_needed), 25))
            pygame.draw.rect(screen, WHITE, (bar_x, 20, bar_width, 25), 2)
            hud_txt = font_hud.render(f"SYNC: {perc}% | {difficulty} | LVL {level}", True, WHITE)
        elif game_mode == "HORDE":
            hud_txt = font_hud.render(f"WAVE {wave_number}/10 | LVL {level}", True, WHITE)
        elif game_mode == "BOSS_RUSH":
            hud_txt = font_hud.render(f"BOSS LEVEL {level}", True, WHITE)
        elif game_mode == "TIME_ATTACK":
            hud_txt = font_hud.render(f"WEAPON LV{weapon_level} | KILLS: {total_kills}", True, WHITE)
        else:  # ENDLESS
            hud_txt = font_hud.render(f"LEVEL {level} | KILLS: {total_kills}", True, WHITE)
        
        screen.blit(hud_txt, (WIDTH//2 - hud_txt.get_width()//2, 20))
        
        elapsed = int(time.time() - level_start_time)
        timer_txt = font_small.render(f"TIME: {elapsed//60:02d}:{elapsed%60:02d}", True, WHITE)
        screen.blit(timer_txt, (10, 10))
        
        kills_txt = font_small.render(f"KILLS: {total_kills}", True, RED)
        screen.blit(kills_txt, (10, 35))
        
        if combo_counter > 0:
            combo_color = GOLD if combo_counter >= 10 else ORANGE if combo_counter >= 5 else WHITE
            combo_txt = font_hud.render(f"COMBO x{combo_counter}", True, combo_color)
            screen.blit(combo_txt, (10, 65))
        
        if dash_cooldown_p1 > 0:
            dash_txt = font_small.render(f"DASH: {dash_cooldown_p1//10}", True, CYAN)
            screen.blit(dash_txt, (10, 95))
        else:
            screen.blit(font_small.render("DASH: READY", True, GOLD), (10, 95))
        
        coins_txt = font_small.render(f"COINS: {coins}", True, GOLD)
        screen.blit(coins_txt, (WIDTH - 150, 10))
        
        y_offset = 35
        for ptype, frames_left in active_powerups.items():
            seconds = frames_left // 60
            pu_data = PowerUp.TYPES[ptype]
            pu_txt = font_small.render(f"{pu_data['icon']} {ptype}: {seconds}s", True, pu_data["color"])
            screen.blit(pu_txt, (WIDTH - 200, y_offset))
            y_offset += 25
        
        mode_txt = font_small.render(f"MODE: {game_mode}", True, CYAN)
        screen.blit(mode_txt, (WIDTH//2 - mode_txt.get_width()//2, HEIGHT - 30))
        
        if save_notification > 0:
            save_notification -= 1
            texts = PAUSE_TEXTS.get(lang, PAUSE_TEXTS["en"])
            notif = font_hud.render(texts["saved"], True, (0, 255, 150))
            screen.blit(notif, (WIDTH//2 - notif.get_width()//2, HEIGHT - 80))

    # PAUSE MENU
    if paused and game_state == "PLAYING":
        pause_buttons = draw_pause_menu(screen, lang)
        
        for btn_rect, btn_key in pause_buttons:
            hover = btn_rect.collidepoint(m_pos)
            color = (0, 255, 150) if btn_key == "continue" else (0, 150, 255) if btn_key == "save" else (255, 50, 50)
            
            draw_pause_button(screen, btn_rect, btn_key, color, hover, lang)
            
            if m_click and hover:
                if btn_key == "continue":
                    paused = False
                elif btn_key == "save":
                    save_progress(level, coins, achievements)
                    save_notification = 120
                    paused = False
                elif btn_key == "exit":
                    pygame.quit()
                    sys.exit()

    pygame.display.flip()
    clock.tick(60)
