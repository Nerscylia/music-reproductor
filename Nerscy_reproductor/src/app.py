import tkinter as tk
from tkinter import scrolledtext, Toplevel, filedialog, Scrollbar, Listbox, RIGHT, Y, END
from src.config_manager import ConfigManager
import pygame
import random
import time
import os
from mutagen.mp3 import MP3
from PIL import Image, ImageTk



class MusicPlayerApp:
    def __init__(self):
        #Cargar configuracion
        self.config = ConfigManager()
        self.config.load_config()

        img_folder = "img"
    
        #iniciar pygame mixer

        pygame.mixer.init()

        #Crear ventana principal
        self.root = tk.Tk()
        self.root.title("Nerscy Music Reproductor")
        self.root.minsize(800, 800)
        self.root.geometry(self.config.get("window_size", "800x800"))

        # Creo un label vacio, esto me permite guardar el fondo.
        
        self.bg_label = tk.Label(self.root)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # creo la log area

        self.create_log_area()

        # Si hay fondo lo guarda.

        saved_bg = self.config.get("background_image", None)
        if saved_bg and os.path.exists(saved_bg):
            #esto espera 100 ms a que la ventana se muestre antes de aplicarse.
            self.root.after(100, lambda:self.set_background(saved_bg))
                
        # variables musica

        self.current_track = None
        self.is_paused = False
        self.shuffle_enabled = False

        # Leo en la config si la ventana estaba maximizada o no.
        maximized = self.config.get("maximized", True)
        if maximized:
            self.root.state("zoomed")

        #Eventos

        self.TRACK_EMD_EVENT = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.TRACK_EMD_EVENT)
        self.fade_timer_id = None
        
        # aqui va la parte que hace el progreso de la cancion.

        self.progress_frame = tk.Frame(self.root, bg="#222")
        self.progress_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.current_time_label = tk.Label(self.progress_frame, text="00:00", fg="white", bg="#222")
        self.current_time_label.pack(side=tk.LEFT, padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_var = tk.Scale(
            self.progress_frame,
            variable= self.progress_var,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            showvalue=0,
            length=400,
            troughcolor="#444",
            bg="#222",
            highlightthickness=0,
            sliderrelief="flat"
            #command=self.on_seek
        )

        self.progress_var.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.total_time_label = tk.Label(self.progress_frame, text="00:00", fg="white", bg="#222")
        self.total_time_label.pack(side=tk.RIGHT, padx=5)

        self.current_length = 0
        self.update_progress_job = None

        #Si hay volumen lo guarda.

        saved_volume = self.config.get("volume", 0.5)
        self.volume = saved_volume
        pygame.mixer.music.set_volume(saved_volume)
        if hasattr(self, "volume_slider"):
            self.volume_slider.set(saved_volume * 100)

        #creamos la lista de canciones

        self.create_song_list_area()

        # crear barra ahora si 
        
        self.create_bottom_bar()

        #Vincular evento para guardar el tamano al cerrar
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

 
    def create_log_area(self):

        #parte para los logs
        frame_logs = tk.Frame(self.root, bg="#1e1e1e")
        frame_logs.pack(side=tk.BOTTOM, fill=tk.X)

        self.log_box = scrolledtext.ScrolledText(
            frame_logs,
            height=8,
            bg="#111111",
            fg="#00ff66",
            font=("Consolas", 10),
            state="disabled"
        )
        self.log_box.pack(fill=tk.BOTH, padx=5, pady=5)

        self.add_log("System working.")

    def add_log(self, message):
        #añadir linea a los logs
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, f"{message}\n")
        self.log_box.config(state="disabled")
        self.log_box.see(tk.END)


    def create_bottom_bar(self):
        #Crea la barra inferior de controles básicos
        bottom_bar = tk.Frame(self.root, height=100, bg="#292929")
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)



        # Botones de control
        btn_play = tk.Button(bottom_bar, text="▶ Play", command=self.play_music, width=10)
        btn_pause = tk.Button(bottom_bar, text="⏸ Pause", command=self.pause_music, width=10)
        btn_stop = tk.Button(bottom_bar, text="⏹ Stop", command=self.stop_music, width=10)
        # Botón Shuffle
        self.shuffle_enabled = self.config.get("shuffle_enabled", False)
        shuffle_text = "🔀 Shuffle ON" if self.shuffle_enabled else "🔀 Shuffle OFF"
        shuffle_color = "#555" if self.shuffle_enabled else "#333"
        self.shuffle_button = tk.Button(bottom_bar, text=shuffle_text, bg=shuffle_color, fg="white", command=self.toggle_shuffle)

        #creo la parte de la barra de la musica
        self.time_label = tk.Label(bottom_bar, text="00:00 / 00:00", bg="#222", fg="white")
        

        #posicionarlos

        btn_play.pack(side=tk.LEFT, padx=10, pady=10)
        btn_pause.pack(side=tk.LEFT, padx=10, pady=10)
        btn_stop.pack(side=tk.LEFT, padx=10, pady=10)
        self.shuffle_button.pack(side=tk.LEFT, padx=5)
        self.time_label.pack(side="left", padx=10)

        tk.Label(bottom_bar, text="Volume", bg="#222222", fg="white").pack(side=tk.RIGHT, padx=(0,5))
        self.volume_slider = tk.Scale(
            bottom_bar,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.set_volume,
            bg="#222222",
            fg="white",
            troughcolor="#444444",
            highlightthickness=0,
            length=150
        )

        self.volume_slider.set(self.volume * 100)
        self.volume_slider.pack(side=tk.RIGHT, padx=(0,15))

        btn_wallpaper = tk.Button(bottom_bar, text="🖼 Wallpaper", command=self.scan_wallpapers, width=12)
        btn_wallpaper.pack(side=tk.LEFT, padx=10, pady=10)

    def set_volume(self, value):
        #ajusta volumen
        self.volume = float(value) / 100.0
        pygame.mixer.music.set_volume(self.volume)
        #self.add_log(f"🔊 Volumen: {int(self.volume * 100)}%") No quiero que sature el log con tanta mierda lol

    def scan_wallpapers(self):
        #escaneamos los wallpapers que hay
        img_folder = "img"

        #extensiones validas.
        valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

        #por si acaso creo la carpeta si no existe.

        if not os.path.exists(img_folder):
            os.makedirs(img_folder)

            self.add_log("🖼 Carpeta 'img' creada (vacía por ahora).")
            return
        
        images = [f for f in os.listdir(img_folder) if f.lower().endswith(valid_exts)]

        if not images:
            self.add_log("⚠ No se encontraron imágenes en la carpeta 'img'.")
            return
        
        self.add_log(f"📸 {len(images)} imagen(es) encontradas:")

        win = Toplevel(self.root)
        win.title("Seleccionar fondo")
        win.geometry("300x250")
        win.configure(bg="#222222")

        tk.Label(win, bg="#111111", fg="white").pack(pady=10)
        listbox = Listbox(win, bg="#222222", fg="white", selectbackground="#00aa66")
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        for img in images:
            listbox.insert(END, img)

        def apply_selected():
            selection =listbox.curselection()
            if not selection:
                self.add_log("⚠ No se seleccionó ninguna imagen.")
            selected_img = images[selection[0]]
            self.set_background(os.path.join(img_folder, selected_img))
            self.add_log(os.path.join(img_folder, selected_img))
            print(os.path.join(img_folder, selected_img))
            win.destroy()
        
        tk.Button(win, text="Aplicar Fondo", command=apply_selected).pack(pady=5)
            

    def set_background(self, image_path, resize_only=False):
        #Aplica la imagen de fondo.
        try:
            self.current_background_path = image_path
            image = Image.open(image_path)
            # como recordatorio, esto hace que se cree pero no espera a que este renderizado y falla el fondo.
            #image = image.resize((self.root.winfo_width(), self.root.winfo_height()))

            self.bg_image = ImageTk.PhotoImage(image)

            if hasattr(self, "bg_label"):
                self.bg_label.config(image=self.bg_image)
            else:
                self.bg_label = tk.Label(self.root, image=self.bg_image)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            #movemos el fondo (de forma visual)

            self.bg_label.lower()
            self.root.configure(bg="#000000")
            self.add_log(f"🖼 Fondo aplicado: {os.path.basename(image_path)}")

            #guardo en la config el ultimo background usado.
            self.config.set("background_image", image_path)
            self.config.save_config()


        except Exception as e:
            self.add_log(f"❌ Error al aplicar fondo: {e}")


#lagea mucho, por ahora no.
    """def on_resize(self, event):
        if hasattr(self, "current_background_path") and self.current_background_path:
            self.set_background(self.current_background_path, resize_only=True)"""
        

    def create_song_list_area(self):
        #lo encajamos en la parte derecha
        self.song_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.song_frame.pack(side="right", fill=Y)

        #boton para seleccionar carpeta.
        self.folder_button = tk.Button(
            self.song_frame,
            text="📂 Seleccionar carpeta",
            command= self.select_music_folder,
            bg="#2e2e2e",
            fg ="white"
        )

        self.folder_button.pack(fill="x", pady=5)

        #lista con scroll

        self.scrollbar = Scrollbar(self.song_frame)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        self.song_listbox = Listbox(
            self.song_frame,
            bg="#202020",
            fg="white",
            selectbackground="#404040",
            yscrollcommand=self.scrollbar.set
        )

        self.song_listbox.pack(side=RIGHT, fill=Y)
        self.song_listbox.config(width=50)
        
        self.scrollbar.config(command=self.song_listbox.yview)

        #para reproducir con dobleclick.

        self.song_listbox.bind("<Double-Button-1>", self.play_selected_song)

        #si hay una carpeta guardada, cargarla

        last_folder = self.config.get("last_music_folder", None)
        if last_folder and os.path.exists(last_folder):
            self.load_songs_from_folder(last_folder)

    
    def select_music_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de musica.")
        if folder:
            self.config.set("last_music_folder", folder)
            self.config.save_config()
            self.load_songs_from_folder(folder)

    def load_songs_from_folder(self, folder):
        supported = (".mp3", ".wav", ".ogg", ".flac")
        songs = [f for f in os.listdir(folder) if f.lower().endswith(supported)]
        self.song_listbox.delete(0, END)
        for song in songs:
            self.song_listbox.insert(END, song)
        self.song_folder = folder
        self.add_log(f"🎵 {len(songs)} canciones cargadas desde: {os.path.basename(folder)}")

    def play_selected_song(self, event):
        selection = self.song_listbox.curselection()
        if selection:
            index = selection[0]
            filename = self.song_listbox.get(index)
            filepath = os.path.join(self.song_folder, filename)
            self.play_music(filepath)
            self.add_log(f"▶ Reproduciendo: {filename}")

    def toggle_shuffle(self):
        self.shuffle_enabled = not self.shuffle_enabled
        if self.shuffle_enabled:
            self.shuffle_button.config(text="🔀 Shuffle ON", bg="#555")
            self.add_log("🔀 Modo aleatorio activado.")
        else:
            self.shuffle_button.config(text="🔀 Shuffle OFF", bg="#333")
            self.add_log("🔁 Modo aleatorio desactivado.")
        # guardar en config
        self.config.set("shuffle_enabled", self.shuffle_enabled)
        self.config.save_config()
        



    def play_music(self, file_path=None):

        #reproduce una pista de prueba

        try:

            if pygame.mixer.music.get_busy() and not self.is_paused:
                if file_path and file_path != self.current_track:
                    self.add_log(f"⏹ Deteniendo: {os.path.basename(self.current_track)}")
                    pygame.mixer.music.stop()
                else:
                    self.add_log("⚠ Ya hay una canción reproduciéndose.")
                    return
            
            if self.is_paused and (not file_path or file_path == self.current_track):
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.add_log("▶ Reanudado.")
                return
            
            if not file_path:
                if hasattr(self, "current_track") and self.current_track:
                    file_path = self.current_track
                else:
                    self.add_log("⚠ No hay pista seleccionada para reproducir.")
                    return
            
            #Verificar que existe
            if not os.path.exists(file_path):
                self.add_log(f"⚠ No se encontró el archivo: {file_path}")
                return
            #Se buggea, comentado por ahora
            """if self.update_progress_job:
                self.root.after_cancel(self.update_progress_job)"""

            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            self.start_time = time.time()
            self.current_track = file_path
            self.is_paused = False
            self.track_length = pygame.mixer.Sound(file_path).get_length()
            self.total_time_label.config(text=self.format_time(self.track_length))
            self.progress_var.set(0)


            #comentado por bugs, esto es la barra de abajo para que trackee la musica
            #self.update_progress()

            try:
                audio = MP3(file_path)
                self.song_length = audio.info.length
            except Exception:
                self.song_length = 0

            #para hacer el fadein fadeout

            sound = pygame.mixer.Sound(file_path)
            length_ms = int(sound.get_length() * 1000)
            fade_start = max(0, length_ms - 3000)

            #cancela temporizadores previos

            if self.fade_timer_id:
                self.root.after_cancel(self.fade_timer_id)

            self.fade_timer_id = self.root.after(fade_start, self.fade_and_next)


            self.current_track = file_path
            self.is_paused = False
            self.add_log(f"▶ Reproduciendo: {os.path.basename(file_path)}")

        except Exception as e:
            self.add_log(f"❌ Error al reproducir: {e}")


    """def on_seek(self, value):
        if not pygame.mixer.music.get_busy() or self.track_length <= 0:
            return
        
        try:

            # calcular el nuevo tiempo a partir del porcentaje
            seek_time = (float(value) / 100) * self.track_length
            self.start_time = time.time() - seek_time # esto es para corregir el contador manual
            pygame.mixer.music.play(start=seek_time) # Salta al nuevo tiempo
            self.add_log(f"⏩ Saltado a {self.format_time(seek_time)}")

        except Exception as e:
            self.add_log(f"❌ Error al saltar: {e}")"""


# FUNCION PARA ACTUALIZAR EL TIEMPO DE REPRODUCCION.
# Se buggea mucho, por el momento se queda desactivada hasta que vea como arreglarla o hacerla mejor.
    """
    def update_progress(self):
        try:
            #Si no hay cancion no hacemos nada.

            if not pygame.mixer.music.get_busy() or not hasattr(self, "start_time"):
                self.update_progress_job = self.root.after(500, self.update_progress)
                return
            
            #saco el tiempo actual en segundos

            elapsed_time = time.time() - self.start_time

            # duracion total (menciono tambien a "track_length" por si no hay "song_length")

            total_length = getattr(self, "song_length", getattr(self, "track_length", 0))

            if total_length > 0:
                progress = min((elapsed_time / total_length) * 100, 100)
            else:
                progress = 0

            self.progress_var.set(progress)
            self.current_time_label.config(text=self.format_time(elapsed_time))
            self.total_time_label.config(text=self.format_time(total_length))

        except Exception as e:
            self.add_log(f"⚠ Error al actualizar progreso: {e}")

        #self.update_progress_job = self.root.after(500, self.update_progress)


            """



# FUNCION PARA CONVERTIR LAS UNIDADES DEL TIEMPO

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def set_volume(self, value):
        vol = float(value) / 100
        pygame.mixer.music.set_volume(vol)
        self.config.set("volume", vol)
        self.config.save_config()
        
    def fade_and_next(self):

        try:
            self.add_log("🔄 Transición suave a la siguiente canción...")
            pygame.mixer.music.fadeout(2000)

            self.root.after(2000, self.play_next_song)

        except Exception as e:
            self.add_log(f"❌ Error en transición: {e}")

    def play_next_song(self):

        if not hasattr(self, "song_folder"):
            return
        
        try:
            if getattr(self, "shuffle_enabled", False):
                #inicia la lista de canciones si no existe.

                if not hasattr(self, "remaining_shuffle_songs") or not self.remaining_shuffle_song:
                    self.remaining_shuffle_songs = list(range(self.song_listbox.size()))
                    random.shuffle(self.remaining_shuffle_songs)
                    self.add_log("🔀 Reiniciando lista aleatoria.")
            
                next_index = self.remaining_shuffle_songs.pop(0)


            
            else:
                current_index = self.song_listbox.curselection()
                if not current_index:
                    return
            
                next_index = current_index[0]+1
                if next_index >= self.song_listbox.size():
                    self.add_log(("🏁 Playlist terminada."))
                    return
            
            self.song_listbox.selection_clear(0, END)
            self.song_listbox.selection_set(next_index)
            self.song_listbox.activate(next_index)

            next_song = self.song_listbox.get(next_index)
            filepath = os.path.join(self.song_folder, next_song)
            self.play_music(filepath)

        except Exception as e:
            self.add_log(f"❌ Error al reproducir siguiente canción: {e}")        

    def pause_music(self):
        #detener musica
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            self.add_log("⚠ No hay música en reproducción.")
            return
        
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.add_log("▶ Reanudado.")

        else:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.add_log("⏸ Pausado.")

    def stop_music(self):
            #stops the music
            pygame.mixer.music.stop()
            self.add_log("⏹ Música detenida.")


    def on_close(self):
        # guardar tamaño actual antes de cerrar
        self.config.set("maximized", self.root.state() == "zoomed")
        self.config.save_config()
        self.root.destroy()

    def run(self):
        self.root.mainloop()