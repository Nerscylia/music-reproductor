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

        #Progreso de reproducción
        self.elapsed_ms = 0 
        self._last_tick = None

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

        # variables para controlar el fin de pista
        self.endcheck_job = None
        self._advancing = False

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

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_scale = tk.Scale(
            self.progress_frame,
            variable=self.progress_var,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            showvalue=0,
            length=400,
            troughcolor="#444",
            bg="#222",
            highlightthickness=0,
            sliderrelief="flat",
            state="disabled",   # sin seek por ahora
        )
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

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
        #self.add_log(f"Volumen: {int(self.volume * 100)}%") No quiero que sature el log con tanta mierda lol

    def scan_wallpapers(self):
        #escaneamos los wallpapers que hay
        img_folder = "img"

        #extensiones validas.
        valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

        #por si acaso creo la carpeta si no existe.

        if not os.path.exists(img_folder):
            os.makedirs(img_folder)

            self.add_log("Carpeta 'img' creada (vacía por ahora).")
            return
        
        images = [f for f in os.listdir(img_folder) if f.lower().endswith(valid_exts)]

        if not images:
            self.add_log("No se encontraron imágenes en la carpeta 'img'.")
            return
        
        self.add_log(f"{len(images)} imagen(es) encontradas:")

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
                self.add_log("No se seleccionó ninguna imagen.")
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
            self.add_log(f"Fondo aplicado: {os.path.basename(image_path)}")

            #guardo en la config el ultimo background usado.
            self.config.set("background_image", image_path)
            self.config.save_config()


        except Exception as e:
            self.add_log(f"Error al aplicar fondo: {e}")


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
            text="Seleccionar carpeta",
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
        self.add_log(f"{len(songs)} canciones cargadas desde: {os.path.basename(folder)}")

    def play_selected_song(self, event):
        selection = self.song_listbox.curselection()
        if selection:
            index = selection[0]
            filename = self.song_listbox.get(index)
            filepath = os.path.join(self.song_folder, filename)
            self.play_music(filepath)
            self.add_log(f"Reproduciendo: {filename}")

    def toggle_shuffle(self):
        self.shuffle_enabled = not self.shuffle_enabled
        if self.shuffle_enabled:
            self.shuffle_button.config(text="🔀 Shuffle ON", bg="#555")
            self.add_log("Modo aleatorio activado.")
        else:
            self.shuffle_button.config(text="🔀 Shuffle OFF", bg="#333")
            self.add_log("Modo aleatorio desactivado.")
        # guardar en config
        self.config.set("shuffle_enabled", self.shuffle_enabled)
        self.config.save_config()
        



    def play_music(self, file_path=None):

        #reproduce una pista de prueba

        try:

            if pygame.mixer.music.get_busy() and not self.is_paused:
                if file_path and file_path != self.current_track:
                    self.add_log(f"Deteniendo: {os.path.basename(self.current_track)}")
                    pygame.mixer.music.stop()
                else:
                    self.add_log("Ya hay una canción reproduciéndose.")
                    return
            
            if self.is_paused and (not file_path or file_path == self.current_track):
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.add_log("Reanudado.")
                return
            
            if not file_path:
                if hasattr(self, "current_track") and self.current_track:
                    file_path = self.current_track
                else:
                    self.add_log("No hay pista seleccionada para reproducir.")
                    return
            
            #Verificar que existe
            if not os.path.exists(file_path):
                self.add_log(f"No se encontró el archivo: {file_path}")
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

            try:
                audio = MP3(file_path)
                self.track_length = float(audio.info.length)
            except Exception:
                self.track_length = pygame.mixer.Sound(file_path).get_length()

            self.total_time_label.config(text=self.format_time(self.track_length))
            self.progress_var.set(0)

            #INICIO PROGRESO
            self.elapsed_ms = 0
            self._start_progress_loop()
            #FIN PROGRESO

            # ---- inicio el seguimiento de la pista. ----
            self._start_endcheck_loop()
            # ---- Finalizo el seguimiento de la pista. ----

        except Exception as e:
            self.add_log(f"❌ Error al reproducir: {e}")

        
    def _start_endcheck_loop(self):
            # cancela uno previo si lo hubiera y reninicia.
            if self.endcheck_job:
                self.root.after_cancel(self.endcheck_job)
                self.endcheck_job = None
            self._advancing = False
            #Aqui se hace la primera comprobacion.
            self.endcheck_job = self.root.after(500, self._endcheck_tick)

    def _endcheck_tick(self):
        try:
            #solo si tenemos duracion conocida
            if hasattr(self, "track_length") and self.track_length > 0:
                total_ms = int(self.track_length * 1000)
                # Lo pongo "casi al final"
                near_end = self.elapsed_ms >= max(0, total_ms - 250)
                finished = (not self.is_paused) and (not pygame.mixer.music.get_busy()) and near_end

                if finished and not self._advancing:
                    self._advancing = True
                    if self.endcheck_job:
                        self.root.after_cancel(self.endcheck_job)
                        self.endcheck_job = None
                    self.play_next_song()
                    return
                
        finally:
            #Re-programa la comproacion.
            self.endcheck_job = self.root.after(500, self._endcheck_tick)

    def _start_progress_loop(self):
        #inicio bucle de actaulizacion de progreso.
        #primero cancela uno previo si ya existe.

        if self.update_progress_job:
            self.root.after_cancel(self.update_progress_job)
            self.update_progress_job = None
        
        # Marca de tiempo para acumular desde ahora.
        self._last_tick = time.monotonic()
        self.progress_tick() #primera iteracion


    def progress_tick(self):

        #esto actualiza el elapsed_ms y refresca UI; basicamente se auto-programa
        try:
            #si en tal caso no hay pista.
            if not hasattr(self, "track_length") or self.track_length <= 0:
                #si no hay nada hace un reintento suave.
                self.update_progress_job = self.root.after(250, self.progress_tick)
                return
            
            # Si esta pausado, solo reprograma sin acumular.
            if self.is_paused or not pygame.mixer.music.get_busy():
                #mantenemos last tick actualizado, asi el delta no salta al reanudar
                self._last_tick = time.monotonic()
                self._refresh_progress_ui()
                self.update_progress_job = self.root.after(250, self.progress_tick)
                return
            
            #al reproducir: acumula delta desde el ultimo uso de tick
            now = time.monotonic()
            delta = max(0.0, (now - (self._last_tick or now)) * 1000.0)
            self._last_tick = now
            self.elapsed_ms += delta

            #clamp para una capita de seguridad

            total_ms = int(self.track_length * 1000)
            if self.elapsed_ms > total_ms:
                self.elapsed_ms = total_ms

            self._refresh_progress_ui()
        finally:
            # repograma la siguiente iteracion en caso de fallo.
            self.update_progress_job = self.root.after(250, self.progress_tick)

    
    def _refresh_progress_ui(self):
        #Refresca labels y slider del progreso
        elapsed_s = max(0, int(self.elapsed_ms / 1000))
        total_s = int(self.track_length) if self.track_length > 0 else 0

        #esto son etiquetas de tiempo
        self.current_time_label.config(text=self.format_time(elapsed_s))
        self.total_time_label.config(text=self.format_time(total_s))

        #aqui el slider

        progress = 0
        if total_s > 0:
            progress = min(100, (elapsed_s / total_s) * 100.0)
        self.progress_var.set(progress)

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
            #como ya se que funciona lo comento.
            #self.add_log("Transición suave a la siguiente canción...")
            pygame.mixer.music.fadeout(2000)

            self.root.after(2000, self.play_next_song)

        except Exception as e:
            self.add_log(f"Error en transición: {e}")

    def play_next_song(self):

        if not hasattr(self, "song_folder"):
            return
        
        try:
            if getattr(self, "shuffle_enabled", False):
                #inicia la lista de canciones si no existe.

                if not hasattr(self, "remaining_shuffle_songs") or not self.remaining_shuffle_songs:
                    self.remaining_shuffle_songs = list(range(self.song_listbox.size()))
                    random.shuffle(self.remaining_shuffle_songs)
                    self.add_log("Reiniciando lista aleatoria.")
                next_index = self.remaining_shuffle_songs.pop(0)

            else:
                current_index = self.song_listbox.curselection()
                if not current_index:
                    #intenta encontrar el indice de la pista actual.
                    if hasattr(self, "current_track") and self.current_track:
                        base = os.path.basename(self.current_track)
                        #busca coincidencia
                        for i in range(self.song_listbox.size()):
                            if self.song_listbox.get(i) == base:
                                current_index = (i,)
                                break
                    if not current_index:
                        return

                next_index = current_index[0]+1
                if next_index >= self.song_listbox.size():
                    if self.update_progress_job:
                        self.root.after_cancel(self.update_progress_job)
                        self.update_progress_job = None
                    if self.endcheck_job:
                        self.root.after_cancel(self.endcheck_job)
                        self.endcheck_job = None
                    self._advancing = False
                    self.add_log(("Playlist terminada."))
                    return
            
            self.song_listbox.selection_clear(0, END)
            self.song_listbox.selection_set(next_index)
            self.song_listbox.activate(next_index)

            next_song = self.song_listbox.get(next_index)
            filepath = os.path.join(self.song_folder, next_song)
            self.play_music(filepath)

        except Exception as e:
            self.add_log(f"Error al reproducir siguiente canción: {e}")        

    def pause_music(self):
        #detener musica
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            self.add_log("No hay música en reproducción.")
            return
        
        if self.is_paused:
            #reanudar
            pygame.mixer.music.unpause()
            self.is_paused = False
            # Re-sincroniza el tick de referencia
            self._last_tick = time.monotonic()
            self.add_log("Reanudado.")

        else:
            now = time.monotonic()
            if self._last_tick is not None:
                self.elapsed_ms += max(0.0, (now - self._last_tick) * 1000.0)
            pygame.mixer.music.pause()
            self.is_paused = True
            self.add_log("Pausado.")



    def stop_music(self):
            #stops the music
            pygame.mixer.music.stop()
            self.add_log("Musica detenida.")
            #cancela progreso
            if self.update_progress_job:
                self.root.after_cancel(self.update_progress_job)
                self.update_progress_job = None
            if self.endcheck_job:
                self.root.after_cancel(self.endcheck_job)
                self.endcheck_job = None


    def on_close(self):
        # guardar tamaño actual antes de cerrar
        self.config.set("maximized", self.root.state() == "zoomed")
        self.config.save_config()
        # Cancela progreso
        if self.update_progress_job:
            self.root.after_cancel(self.update_progress_job)
            self.update_progress_job = None
        if self.endcheck_job:
                self.root.after_cancel(self.endcheck_job)
                self.endcheck_job = None
        self.root.destroy()

    def run(self):
        self.root.mainloop()