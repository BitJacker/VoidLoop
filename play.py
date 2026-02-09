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
        
        # Effetto glow
        for i in range(glow, 0, -1):
            alpha = 40 - (i * 8)
            glow_color = self.color if self.hover else "#333333"
            self.create_rectangle(i, i, self.width-i, 50-i, outline=glow_color, width=1)
        
        # Bordo principale
        self.create_rectangle(2, 2, self.width-2, 48, outline=self.color if self.hover else "#444444", width=2)
        
        # Testo
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
        self.root.title("VoidLoop - BitJacker Edition")
        self.root.geometry("500x850")
        self.root.configure(bg="#0a0a0a")
        self.root.resizable(False, False)
        
        # Percorso salvataggio in VoidLoop/saves/
        self.saves_dir = os.path.join("VoidLoop", "saves")
        self.save_path = os.path.join(self.saves_dir, "savegame.json")
        
        # Crea cartella saves se non esiste
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
        
        # Carica info save
        self.save_exists, self.save_level, self.save_coins = self.load_save_info()
        
        self.create_ui()
    
    def load_save_info(self):
        """Carica informazioni sul salvataggio esistente"""
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
        """Elimina il salvataggio esistente"""
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
        # === HEADER ===
        header = tk.Frame(self.root, bg="#0a0a0a")
        header.pack(pady=30)
        
        # Titolo con effetto glitch
        title = tk.Label(header, text="◢ VOID LOOP ◣", font=("Courier New", 32, "bold"),
                        fg="#00ff96", bg="#0a0a0a")
        title.pack()
        
        subtitle = tk.Label(header, text="[ NEURAL SYNCHRONIZATION TERMINAL ]", 
                           font=("Courier New", 10), fg="#00ffff", bg="#0a0a0a")
        subtitle.pack(pady=5)
        
        # Linea separatrice
        separator = tk.Canvas(self.root, width=400, height=2, bg="#0a0a0a", highlightthickness=0)
        separator.pack()
        separator.create_line(0, 1, 400, 1, fill="#00ff96", width=2)
        
        # === SAVE GAME INFO ===
        if self.save_exists:
            save_frame = tk.Frame(self.root, bg="#0a0a0a")
            save_frame.pack(pady=15)
            
            # Box save
            save_box = tk.Frame(save_frame, bg="#1a1a1a", highlightbackground="#00ff96", 
                               highlightthickness=2, padx=15, pady=10)
            save_box.pack()
            
            tk.Label(save_box, text="[ SAVE GAME FOUND ]", font=("Courier New", 10, "bold"),
                    fg="#00ff96", bg="#1a1a1a").pack()
            
            tk.Label(save_box, text=f"Level: {self.save_level}  |  Coins: {self.save_coins}",
                    font=("Courier New", 9), fg="#ffffff", bg="#1a1a1a").pack(pady=5)
        
        # === CONFIGURAZIONE ===
        config_frame = tk.Frame(self.root, bg="#0a0a0a")
        config_frame.pack(pady=15)
        
        # Stile personalizzato per combobox
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
            ("◆ LANGUAGE", self.lang_var, ["it", "en", "es", "fr"], "#00ff96"),
            ("◆ SHIP COLOR", self.color_var, ["Neon Green", "Cyber Blue", "Void Purple"], "#00ffff"),
            ("◆ MODE", self.mode_var, ["1 PLAYER", "2 PLAYERS"], "#b400ff"),
            ("◆ SCREEN", self.screen_var, ["WINDOWED", "FULLSCREEN"], "#00ff96"),
            ("◆ DIFFICULTY", self.diff_var, ["EASY", "NORMAL", "HARD", "NIGHTMARE"], "#ff0066")
        ]
        
        for label_text, var, options, color in settings:
            # Frame per ogni opzione
            option_frame = tk.Frame(config_frame, bg="#0a0a0a")
            option_frame.pack(pady=8)
            
            # Label
            label = tk.Label(option_frame, text=label_text, font=("Courier New", 11, "bold"),
                           fg=color, bg="#0a0a0a", width=18, anchor="w")
            label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Combobox
            combo = ttk.Combobox(option_frame, textvariable=var, values=options, 
                               state="readonly", width=18, font=("Courier New", 10),
                               style="Neon.TCombobox")
            combo.pack(side=tk.LEFT)
        
        # === INFO DIFFICOLTÀ ===
        info_frame = tk.Frame(self.root, bg="#0a0a0a")
        info_frame.pack(pady=15)
        
        info_title = tk.Label(info_frame, text="[ DIFFICULTY INFO ]", 
                             font=("Courier New", 9, "bold"), fg="#666666", bg="#0a0a0a")
        info_title.pack()
        
        diff_info = {
            "EASY": "Cost: 5P | Speed: 70%",
            "NORMAL": "Cost: 10P | Speed: 100%",
            "HARD": "Cost: 20P | Speed: 140%",
            "NIGHTMARE": "Cost: 30P | Speed: 190%"
        }
        
        self.info_label = tk.Label(info_frame, text=diff_info["NORMAL"],
                                  font=("Courier New", 9), fg="#888888", bg="#0a0a0a")
        self.info_label.pack(pady=5)
        
        # Update info quando cambia difficoltà
        def update_info(*args):
            self.info_label.config(text=diff_info.get(self.diff_var.get(), ""))
        self.diff_var.trace('w', update_info)
        
        # === PULSANTI ===
        button_frame = tk.Frame(self.root, bg="#0a0a0a")
        button_frame.pack(pady=20)
        
        if self.save_exists:
            # Bottone CONTINUE (se c'è un save)
            continue_btn = NeonButton(button_frame, "▶ CONTINUE GAME", 
                                     lambda: self.start_game(continue_save=True), 
                                     color="#00ff96", width=320)
            continue_btn.pack(pady=8)
            
            # Bottone NEW GAME
            new_game_btn = NeonButton(button_frame, "◉ NEW GAME", 
                                      lambda: self.start_game(continue_save=False), 
                                      color="#ffaa00", width=320)
            new_game_btn.pack(pady=8)
        else:
            # Bottone START (se non c'è un save)
            start_btn = NeonButton(button_frame, "▶ START GAME", 
                                  lambda: self.start_game(continue_save=False), 
                                  color="#00ff96", width=320)
            start_btn.pack(pady=8)
        
        # Bottone EXIT
        exit_btn = NeonButton(button_frame, "✕ EXIT TERMINAL", 
                             self.root.quit, color="#ff0066", width=320)
        exit_btn.pack(pady=8)
        
        # === FOOTER ===
        footer = tk.Label(self.root, text="v2.0 | BitJacker Edition | 2026",
                         font=("Courier New", 8), fg="#333333", bg="#0a0a0a")
        footer.pack(side=tk.BOTTOM, pady=10)
    
    def start_game(self, continue_save=True):
        """Avvia il gioco con o senza il save esistente"""
        # Se NEW GAME e c'è un save, chiedi conferma ed elimina
        if not continue_save and self.save_exists:
            response = messagebox.askyesno(
                "New Game",
                f"This will delete your current save:\n\nLevel: {self.save_level}\nCoins: {self.save_coins}\n\nAre you sure?",
                icon='warning'
            )
            if not response:
                return  # Annulla
            
            if not self.delete_save():
                return  # Errore nell'eliminazione
        
        # Raccogli parametri
        lang = self.lang_var.get()
        color = self.color_var.get()
        mode = self.mode_var.get()
        screen_mode = self.screen_var.get()
        diff = self.diff_var.get()
        
        self.root.destroy()
        
        # Avvia il gioco
        script_path = os.path.join("VoidLoop", "voidloopgame.py")
        
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Game file not found at:\n{script_path}\n\nPlease check the file structure.")
            return
        
        try:
            subprocess.run(["python3", script_path, lang, color, mode, screen_mode, diff])
        except FileNotFoundError:
            try:
                subprocess.run(["python", script_path, lang, color, mode, screen_mode, diff])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch game:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VoidLoopLauncher(root)
    root.mainloop()
