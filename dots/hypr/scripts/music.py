#!/usr/bin/env python3
import gi, subprocess, threading, time, urllib.request, os, hashlib, socket, sys
from pathlib import Path

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango

# ================= IPC =================
SOCKET_PATH = "/tmp/now_playing_widget.sock"

def send_toggle():
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SOCKET_PATH)
        s.sendall(b"toggle")
        s.close()
        return True
    except:
        return False

# ================= CONSTANTS =================
CACHE_DIR = Path.home() / ".cache" / "now_playing"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Custom icons using Unicode
PLAY_ICON = "▶"
PAUSE_ICON = "⏸"
PREV_ICON = "⏮"
NEXT_ICON = "⏭"
REPEAT_ICON = "∞"
SHUFFLE_ICON = "⤮"

# Color scheme - SOLID GLOSSY BLACK
COLORS = {
    "primary": "#8a2be2",  # Purple accent
    "secondary": "#00ced1",  # Turquoise
    "bg_glossy": "#000000",  # SOLID GLOSSY BLACK (no transparency)
    "bg_darker": "#05050a",  # Even darker for gradient
    "border": "#1a1a1f",
    "text": "#ffffff",  # WHITE text
    "text_secondary": "#cccccc",  # Light gray
    "progress_fill": "#8a2be2",
    "progress_bg": "rgba(255, 255, 255, 0.1)",
    "shadow": "rgba(0, 0, 0, 0.8)",
    "gloss": "rgba(255, 255, 255, 0.08)",  # Glossy highlight
}

# ================= MAIN =================
class NowPlaying(Gtk.Window):
    def __init__(self):
        super().__init__(title="Now Playing")
        self.set_default_size(420, 480)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)

        # Make entire window draggable
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.visible_state = True
        self.last_track = None
        self.current_duration = 0.0
        self.is_playing = False

        # Main container - simple vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)

        # Connect drag events to main box
        main_box.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        main_box.connect("button-press-event", self.on_window_press)
        main_box.connect("button-release-event", self.on_window_release)
        main_box.connect("motion-notify-event", self.on_window_motion)

        self.add(main_box)

        # ===== ALBUM ART WITH GLOSSY BLACK FRAME =====
        self.art_frame = Gtk.EventBox()
        self.art_frame.set_name("art-frame")
        self.art_frame.set_size_request(320, 280)
        self.art_frame.set_valign(Gtk.Align.CENTER)
        self.art_frame.set_halign(Gtk.Align.CENTER)

        self.art_image = Gtk.Image()
        self.art_frame.add(self.art_image)
        main_box.pack_start(self.art_frame, True, True, 0)

        # ===== TRACK INFO =====
        track_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        track_box.set_margin_top(15)
        track_box.set_margin_bottom(10)

        # Title - WHITE TEXT
        self.title_label = Gtk.Label(label="No track playing")
        self.title_label.set_name("track-title")
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_max_width_chars(30)
        track_box.pack_start(self.title_label, False, False, 0)

        # Artist - LIGHT GRAY TEXT
        self.artist_label = Gtk.Label(label="Unknown artist")
        self.artist_label.set_name("track-artist")
        self.artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        track_box.pack_start(self.artist_label, False, False, 0)

        main_box.pack_start(track_box, False, False, 0)

        # ===== PROGRESS BAR =====
        progress_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        progress_container.set_margin_top(10)
        progress_container.set_margin_bottom(10)

        # Time labels - LIGHT GRAY
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.time_label = Gtk.Label(label="0:00")
        self.time_label.set_name("time-label")
        self.duration_label = Gtk.Label(label="0:00")
        self.duration_label.set_name("time-label")

        time_box.pack_start(self.time_label, False, False, 0)
        time_box.pack_end(self.duration_label, False, False, 0)
        progress_container.pack_start(time_box, False, False, 0)

        # PROPER ProgressBar widget
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_name("progress-bar")
        self.progress_bar.set_hexpand(True)
        self.progress_bar.set_size_request(380, 8)

        # Connect click event for seeking
        progress_event = Gtk.EventBox()
        progress_event.add(self.progress_bar)
        progress_event.connect("button-press-event", self.on_progress_click)
        progress_event.set_name("progress-container")

        progress_container.pack_start(progress_event, False, False, 0)
        main_box.pack_start(progress_container, False, False, 0)

        # ===== CONTROLS =====
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        controls_box.set_halign(Gtk.Align.CENTER)
        controls_box.set_margin_top(15)
        controls_box.set_margin_bottom(15)

        # Shuffle button
        self.shuffle_btn = Gtk.Button(label=SHUFFLE_ICON)
        self.shuffle_btn.set_name("control-btn")
        self.shuffle_btn.connect("clicked", lambda w: subprocess.Popen(["playerctl", "shuffle", "on"]))

        # Previous button
        self.prev_btn = Gtk.Button(label=PREV_ICON)
        self.prev_btn.set_name("control-btn")
        self.prev_btn.set_size_request(48, 48)
        self.prev_btn.connect("clicked", lambda *_: subprocess.Popen(["playerctl", "previous"]))

        # Play/Pause button (larger)
        self.play_btn = Gtk.Button(label=PLAY_ICON)
        self.play_btn.set_name("play-btn")
        self.play_btn.set_size_request(64, 64)
        self.play_btn.connect("clicked", lambda *_: subprocess.Popen(["playerctl", "play-pause"]))

        # Next button
        self.next_btn = Gtk.Button(label=NEXT_ICON)
        self.next_btn.set_name("control-btn")
        self.next_btn.set_size_request(48, 48)
        self.next_btn.connect("clicked", lambda *_: subprocess.Popen(["playerctl", "next"]))

        # Repeat button
        self.repeat_btn = Gtk.Button(label=REPEAT_ICON)
        self.repeat_btn.set_name("control-btn")
        self.repeat_btn.connect("clicked", lambda w: subprocess.Popen(["playerctl", "loop", "Playlist"]))

        controls_box.pack_start(self.shuffle_btn, False, False, 0)
        controls_box.pack_start(self.prev_btn, False, False, 0)
        controls_box.pack_start(self.play_btn, False, False, 0)
        controls_box.pack_start(self.next_btn, False, False, 0)
        controls_box.pack_start(self.repeat_btn, False, False, 0)

        main_box.pack_start(controls_box, False, False, 0)

        # Apply CSS styling
        self.apply_styles()

        self.show_all()

        # Start background threads
        threading.Thread(target=self.metadata_loop, daemon=True).start()
        threading.Thread(target=self.progress_loop, daemon=True).start()
        threading.Thread(target=self.socket_listener, daemon=True).start()

    # ================= STYLING =================
    def apply_styles(self):
        css = f"""
        * {{
            font-family: 'Segoe UI', 'Ubuntu', sans-serif;
        }}

        /* Main window - SOLID GLOSSY BLACK BACKGROUND */


        /* Album art frame - ALSO SOLID GLOSSY BLACK */
        #art-frame {{
            background: linear-gradient(
                135deg,
                #08080c,
                #040408
            );

            border-radius: 20px;
            border: 2px solid {COLORS['border']};
        }}

        /* Track title - BRIGHT WHITE */
        #track-title {{
            color: {COLORS['text']};
            font-size: 20px;
            font-weight: 600;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
        }}

        /* Artist name - LIGHT GRAY */
        #track-artist {{
            color: {COLORS['text_secondary']};
            font-size: 14px;
            margin: 0;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
        }}

        /* Time labels - LIGHT GRAY */
        #time-label {{
            color: {COLORS['text_secondary']};
            font-size: 12px;
            font-weight: 500;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
        }}


        /* Control buttons - SEMI-TRANSPARENT ON BLACK */
        #control-btn {{
            color: {COLORS['text']};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            font-size: 20px;
            padding: 8px;
            min-width: 40px;
            min-height: 40px;
        }}

        #control-btn:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(138, 43, 226, 0.3);
            color: {COLORS['primary']}
        }}

        /* Play button - COLORFUL GRADIENT */
        #play-btn {{
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 24px;
            padding: 0;
        }}

        #play-btn:hover {{
            background: rgba(255, 255, 255, 0.08);
        }}

        """

        self.set_app_paintable(False)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)


        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # ================= DRAG HANDLING =================
    def on_window_press(self, widget, event):
        if event.button == 1:
            self.drag_start_x = event.x_root - self.get_position().x
            self.drag_start_y = event.y_root - self.get_position().y
            return True
        return False

    def on_window_release(self, widget, event):
        self.drag_start_x = 0
        self.drag_start_y = 0
        return True

    def on_window_motion(self, widget, event):
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.move(x, y)
            return True
        return False

    # ================= SEEK =================
    def on_progress_click(self, widget, event):
        if self.current_duration <= 0:
            return

        width = widget.get_allocated_width()
        click_x = max(0, min(event.x, width))
        fraction = click_x / width
        new_pos = self.current_duration * fraction

        subprocess.Popen(["playerctl", "position", str(new_pos)])

    # ================= METADATA =================
    def metadata_loop(self):
        while True:
            try:
                r = subprocess.run(
                    ["playerctl", "metadata", "--format",
                     "{{title}}|{{artist}}|{{mpris:artUrl}}|{{status}}"],
                    capture_output=True, text=True
                )
                if r.returncode == 0:
                    parts = r.stdout.strip().split("|")
                    if len(parts) == 4:
                        title, artist, art, status = parts

                        # Update play/pause button
                        is_now_playing = status.lower() == "playing"
                        if is_now_playing != self.is_playing:
                            self.is_playing = is_now_playing
                            GLib.idle_add(self.play_btn.set_label,
                                         PAUSE_ICON if is_now_playing else PLAY_ICON)

                        track = title + artist
                        if track != self.last_track:
                            self.last_track = track
                            pix = self.load_art(art)
                            GLib.idle_add(self.update_track, pix, title, artist)
            except Exception as e:
                print(f"Metadata error: {e}")
            time.sleep(0.5)

    def update_track(self, pix, title, artist):
        if pix:
            self.art_image.set_from_pixbuf(pix)

        self.title_label.set_text(title if title else "No title")
        self.artist_label.set_text(artist if artist else "Unknown artist")

    # ================= PROGRESS =================
    def progress_loop(self):
        while True:
            try:
                r = subprocess.run(
                    ["playerctl", "metadata", "--format",
                     "{{position}}|{{mpris:length}}"],
                    capture_output=True, text=True
                )
                if r.returncode == 0:
                    parts = r.stdout.strip().split("|")
                    if len(parts) == 2 and all(parts):
                        pos, dur = parts
                        if pos and dur:
                            pos = int(pos) / 1e6
                            dur = int(dur) / 1e6
                            self.current_duration = dur

                            # Update PROPER progress bar fraction
                            fraction = pos / dur if dur > 0 else 0
                            GLib.idle_add(self.progress_bar.set_fraction, fraction)

                            # Update time labels
                            pos_str = f"{int(pos//60)}:{int(pos%60):02d}"
                            dur_str = f"{int(dur//60)}:{int(dur%60):02d}"
                            GLib.idle_add(self.time_label.set_text, pos_str)
                            GLib.idle_add(self.duration_label.set_text, dur_str)
            except Exception as e:
                print(f"Progress error: {e}")
            time.sleep(0.1)

    # ================= ART =================
    def load_art(self, url):
        try:
            if url.startswith("file://"):
                path = url[7:]
            else:
                path = CACHE_DIR / (hashlib.md5(url.encode()).hexdigest() + ".png")
                if not path.exists() and url and url.startswith("http"):
                    urllib.request.urlretrieve(url, path)

            if Path(path).exists():
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), 380, 380, True)
        except Exception as e:
            print(f"Art load error: {e}")

        # Return glossy black default art
        return self.create_default_art()

    def create_default_art(self):
        """Create a glossy black default art"""
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 380, 380)

        # Solid glossy black with subtle gradient
        for x in range(380):
            for y in range(380):
                # Very dark base
                r_base, g_base, b_base = 8, 8, 12

                # Subtle glossy highlight (stronger at top)
                highlight = int(max(0, 1 - (y / 380) * 1.2) * 10)

                r = r_base + highlight
                g = g_base + highlight
                b = b_base + highlight

                # Set pixel
                pixbuf.fill_pixel(x, y, (r << 24) | (g << 16) | (b << 8) | 255)

        return pixbuf

    # ================= TOGGLE =================
    def toggle(self):
        if self.visible_state:
            self.hide()
        else:
            self.show_all()
        self.visible_state = not self.visible_state

    def socket_listener(self):
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(SOCKET_PATH)
        s.listen(1)

        while True:
            c, _ = s.accept()
            if c.recv(16) == b"toggle":
                GLib.idle_add(self.toggle)
            c.close()

# ================= ENTRY =================
if __name__ == "__main__":
    if "--toggle" in sys.argv:
        if send_toggle():
            sys.exit(0)

    win = NowPlaying()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
