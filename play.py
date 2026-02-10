import tkinter as tk
from tkinter import ttk, messagebox
import subprocess, os, json

class NeonButton(tk.Canvas):
    def __init__(self, parent, text, command, color="#00ff96", width=320, **kwargs):
        super().__init__(parent, width=width, height=50, bg="#0a0a0a", highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.color = color
        self.hover = False
        self.width = width
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.draw()
    
    def draw(self):
        self.delete("all")
        glow = 4 if self.hover else 2
        
        for i in range(glow, 0, -1):
            alpha = 40 - (i * 8)
            glow_color = self.color if self.hover else "#333333"
            self.create_rectangle(i, i, self.width-i, 50-i, outline=glow_color, width=1)
        
        self.create_rectangle(2, 2, self.width-2, 48, outline=self.color if self.hover else "#444444", width=2)
        
        self.create_text(self.width//2, 25, text=self.text, fill=self.color if self.hover else "#888888", 
                        font=("Courier New", 14, "bold"))
    
    def on_enter(self, e):
        self.hover = True
        self.draw()
    
    def on_leave(self, e):
        self.hover = False
        self.draw()
    
    def on_click(self, e):
        if self.command:
            self.command()

class VoidLoopLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("VoidLoop - Enhanced Edition")
        self.root.geometry("600x900")
        self.root.configure(bg="#0a0a0a")
        self.root.resizable(False, False)
        
        self.saves_dir = os.path.join("VoidLoop", "saves")
        self.save_path = os.path.join(self.saves_dir, "savegame.json")
        
        if not os.path.exists(self.saves_dir):
            try:
                os.makedirs(self.saves_dir)
            except:
                pass
        
        # Variabili
        self.lang_var = tk.StringVar(value="it")
        self.color_var = tk.StringVar(value="Neon Green")
        self.mode_var = tk.StringVar(value="1 PLAYER")
        self.screen_var = tk.StringVar(value="WINDOWED")
        self.diff_var = tk.StringVar(value="NORMAL")
        self.game_mode_var = tk.StringVar(value="STORY")
        
        self.save_exists, self.save_level, self.save_coins = self.load_save_info()
        
        self.create_ui()
    
    def load_save_info(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "r") as f:
                    data = json.load(f)
                    level = data.get("level", 1)
                    coins = data.get("coins", 0)
                    return True, level, coins
            except:
                return False, 1, 0
        return False, 1, 0
    
    def delete_save(self):
        if os.path.exists(self.save_path):
            try:
                os.remove(self.save_path)
                messagebox.showinfo("Save Deleted", "Save game deleted successfully!\nStarting new game...")
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete save: {e}")
                return False
        return True
    
    def create_ui(self):
        # === CONTAINER PRINCIPALE ===
        main_container = tk.Frame(self.root, bg="#0a0a0a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # === HEADER QUADRATO ===
        header_box = tk.Frame(main_container, bg="#0f0f0f", highlightbackground="#00ff96", 
                             highlightthickness=3)
        header_box.pack(fill=tk.X, pady=(0, 15))
        
        title = tk.Label(header_box, text="◢ VOID LOOP ◣", font=("Courier New", 36, "bold"),
                        fg="#00ff96", bg="#0f0f0f")
        title.pack(pady=(15, 5))
        
        subtitle = tk.Label(header_box, text="[ ENHANCED EDITION - v3.0 ]", 
                           font=("Courier New", 11), fg="#00ffff", bg="#0f0f0f")
        subtitle.pack(pady=(0, 15))
        
        # === SAVE GAME BOX ===
        if self.save_exists:
            save_container = tk.Frame(main_container, bg="#0f0f0f", highlightbackground="#00ff96", 
                                     highlightthickness=2)
            save_container.pack(fill=tk.X, pady=(0, 15))
            
            tk.Label(save_container, text="[ SAVE GAME FOUND ]", font=("Courier New", 11, "bold"),
                    fg="#00ff96", bg="#0f0f0f").pack(pady=(10, 5))
            
            tk.Label(save_container, text=f"Level: {self.save_level}  |  Coins: {self.save_coins}",
                    font=("Courier New", 10), fg="#ffffff", bg="#0f0f0f").pack(pady=(0, 10))
        
        # === CONFIGURAZIONE BOX ===
        config_container = tk.Frame(main_container, bg="#0f0f0f", highlightbackground="#666666", 
                                   highlightthickness=2)
        config_container.pack(fill=tk.X, pady=(0, 15))
        
        config_title = tk.Label(config_container, text="[ CONFIGURATION ]", 
                               font=("Courier New", 12, "bold"), fg="#00ffff", bg="#0f0f0f")
        config_title.pack(pady=(10, 10))
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Neon.TCombobox",
                       fieldbackground="#1a1a1a",
                       background="#1a1a1a",
                       foreground="#00ff96",
                       arrowcolor="#00ff96",
                       bordercolor="#00ff96",
                       lightcolor="#1a1a1a",
                       darkcolor="#1a1a1a")
        style.map('Neon.TCombobox',
                 fieldbackground=[('readonly', '#1a1a1a')],
                 selectbackground=[('readonly', '#00ff96')],
                 selectforeground=[('readonly', '#000000')])
        
        settings = [
            ("LANGUAGE", self.lang_var, ["it", "en", "es", "fr"], "#00ff96"),
            ("SHIP COLOR", self.color_var, ["Neon Green", "Cyber Blue", "Void Purple"], "#00ffff"),
            ("MODE", self.mode_var, ["1 PLAYER", "2 PLAYERS"], "#b400ff"),
            ("SCREEN", self.screen_var, ["WINDOWED", "FULLSCREEN"], "#00ff96"),
            ("DIFFICULTY", self.diff_var, ["EASY", "NORMAL", "HARD", "NIGHTMARE"], "#ff0066")
        ]
        
        for label_text, var, options, color in settings:
            option_frame = tk.Frame(config_container, bg="#0f0f0f")
            option_frame.pack(pady=5, padx=20, fill=tk.X)
            
            label = tk.Label(option_frame, text=label_text, font=("Courier New", 10, "bold"),
                           fg=color, bg="#0f0f0f", width=14, anchor="w")
            label.pack(side=tk.LEFT, padx=(0, 15))
            
            combo = ttk.Combobox(option_frame, textvariable=var, values=options, 
                               state="readonly", width=20, font=("Courier New", 9),
                               style="Neon.TCombobox")
            combo.pack(side=tk.LEFT)
        
        # Spazio finale
        tk.Label(config_container, text="", bg="#0f0f0f").pack(pady=5)
        
        # === GAME MODE BOX ===
        mode_container = tk.Frame(main_container, bg="#0f0f0f", highlightbackground="#ff0066", 
                                 highlightthickness=2)
        mode_container.pack(fill=tk.X, pady=(0, 15))
        
        mode_title = tk.Label(mode_container, text="[ SELECT GAME MODE ]", 
                             font=("Courier New", 12, "bold"), fg="#ff0066", bg="#0f0f0f")
        mode_title.pack(pady=(10, 10))
        
        game_modes = [
            ("STORY", "#00ff96"),
            ("ENDLESS", "#ffaa00"),
            ("TIME ATTACK", "#00ffff"),
            ("BOSS RUSH", "#b400ff"),
            ("HORDE", "#ff0066")
        ]
        
        # Griglia di bottoni quadrati
        grid_frame = tk.Frame(mode_container, bg="#0f0f0f")
        grid_frame.pack(pady=(0, 15))
        
        self.mode_buttons = []
        for i, (mode_name, color) in enumerate(game_modes):
            row = i // 3
            col = i % 3
            
            btn = tk.Button(grid_frame, text=mode_name, 
                          command=lambda m=mode_name.replace(" ", "_"): self.select_game_mode(m),
                          font=("Courier New", 9, "bold"),
                          bg="#1a1a1a", fg=color,
                          activebackground="#2a2a2a", activeforeground=color,
                          relief=tk.FLAT, width=12, height=2,
                          highlightthickness=2, highlightbackground="#333333")
            btn.grid(row=row, column=col, padx=5, pady=5)
            
            self.mode_buttons.append((btn, mode_name.replace(" ", "_"), color))
        
        # Seleziona STORY di default
        self.select_game_mode("STORY")
        
        # === INFO BOX ===
        info_container = tk.Frame(main_container, bg="#0f0f0f", highlightbackground="#666666", 
                                 highlightthickness=2)
        info_container.pack(fill=tk.X, pady=(0, 15))
        
        diff_info = {
            "EASY": "Cost: 5P | Speed: 70% | More forgiving",
            "NORMAL": "Cost: 10P | Speed: 100% | Balanced",
            "HARD": "Cost: 20P | Speed: 140% | Challenging",
            "NIGHTMARE": "Cost: 30P | Speed: 190% | Extreme"
        }
        
        self.info_label = tk.Label(info_container, text=diff_info["NORMAL"],
                                  font=("Courier New", 9), fg="#888888", bg="#0f0f0f")
        self.info_label.pack(pady=12)
        
        def update_info(*args):
            self.info_label.config(text=diff_info.get(self.diff_var.get(), ""))
        self.diff_var.trace('w', update_info)
        
        # === PULSANTI AZIONE ===
        button_container = tk.Frame(main_container, bg="#0a0a0a")
        button_container.pack(fill=tk.X, pady=(0, 10))
        
        if self.save_exists:
            continue_btn = NeonButton(button_container, "▶ CONTINUE GAME", 
                                     lambda: self.start_game(continue_save=True), 
                                     color="#00ff96", width=560)
            continue_btn.pack(pady=5)
            
            new_game_btn = NeonButton(button_container, "◉ NEW GAME", 
                                      lambda: self.start_game(continue_save=False), 
                                      color="#ffaa00", width=560)
            new_game_btn.pack(pady=5)
        else:
            start_btn = NeonButton(button_container, "▶ START GAME", 
                                  lambda: self.start_game(continue_save=False), 
                                  color="#00ff96", width=560)
            start_btn.pack(pady=5)
        
        exit_btn = NeonButton(button_container, "✕ EXIT", 
                             self.root.quit, color="#ff0066", width=560)
        exit_btn.pack(pady=5)
        
        # === FOOTER ===
        footer = tk.Label(self.root, text="v3.0 | Enhanced Edition | 2026",
                         font=("Courier New", 8), fg="#333333", bg="#0a0a0a")
        footer.pack(side=tk.BOTTOM, pady=10)
    
    def select_game_mode(self, mode):
        """Evidenzia il game mode selezionato"""
        self.game_mode_var.set(mode)
        
        for btn, btn_mode, color in self.mode_buttons:
            if btn_mode == mode:
                btn.config(highlightbackground=color, highlightthickness=3, 
                          bg="#2a2a2a", relief=tk.SOLID)
            else:
                btn.config(highlightbackground="#333333", highlightthickness=2, 
                          bg="#1a1a1a", relief=tk.FLAT)
    
    def start_game(self, continue_save=True):
        if not continue_save and self.save_exists:
            response = messagebox.askyesno(
                "New Game",
                f"This will delete your current save:\n\nLevel: {self.save_level}\nCoins: {self.save_coins}\n\nAre you sure?",
                icon='warning'
            )
            if not response:
                return
            
            if not self.delete_save():
                return
        
        # Raccogli parametri
        lang = self.lang_var.get()
        color = self.color_var.get()
        mode = self.mode_var.get()
        screen_mode = self.screen_var.get()
        diff = self.diff_var.get()
        game_mode = self.game_mode_var.get()
        
        self.root.destroy()
        
        # Avvia il gioco con il nome file corretto
        script_path = os.path.join("VoidLoop", "voidloopgame.py")
        
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Game file not found at:\n{script_path}\n\nPlease check the file structure.")
            return
        
        try:
            subprocess.run(["python3", script_path, lang, color, mode, screen_mode, diff, game_mode])
        except FileNotFoundError:
            try:
                subprocess.run(["python", script_path, lang, color, mode, screen_mode, diff, game_mode])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch game:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VoidLoopLauncher(root)
    root.mainloop()
