"""
Advanced Media Player - Python 3.12+ with Tkinter
Complete video player with modern interface and extensive features
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import time
import os
import json
from pathlib import Path
import queue
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Video information data class"""
    path: str
    name: str
    duration: float
    fps: float
    width: int
    height: int
    current_position: float = 0.0
    is_playing: bool = False


class Settings:
    """Application settings manager"""

    DEFAULT_SETTINGS = {
        "last_folder": "",
        "volume": 0.7,
        "window_size": [1200, 800],
        "theme": "dark",
        "last_playlist": [],
        "muted": False,
        "last_position": 0
    }

    def __init__(self, settings_file: str = "player_settings.json"):
        """Initialize settings manager"""
        self.settings_file = settings_file
        self.settings = self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with default settings to ensure all keys exist
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(loaded_settings)
                    logger.info("Settings loaded successfully")
                    return settings
            else:
                logger.info("No settings file found, using defaults")
                return self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self) -> None:
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self.settings[key] = value
        self.save_settings()


class ThemeManager:
    """Theme management for the application"""

    THEMES = {
        "dark": {
            "bg": "#1a1a2e",
            "fg": "#e0e0e0",
            "accent": "#16213e",
            "button_bg": "#0f3460",
            "button_fg": "#ffffff",
            "progress_bg": "#0f3460",
            "progress_fg": "#e94560",
            "listbox_bg": "#16213e",
            "listbox_fg": "#e0e0e0",
            "slider_bg": "#0f3460",
            "slider_fg": "#e94560",
            "entry_bg": "#16213e",
            "entry_fg": "#e0e0e0",
            "frame_bg": "#1a1a2e",
            "canvas_bg": "#000000"
        },
        "light": {
            "bg": "#f0f0f0",
            "fg": "#333333",
            "accent": "#e0e0e0",
            "button_bg": "#4a90e2",
            "button_fg": "#ffffff",
            "progress_bg": "#d0d0d0",
            "progress_fg": "#4a90e2",
            "listbox_bg": "#ffffff",
            "listbox_fg": "#333333",
            "slider_bg": "#d0d0d0",
            "slider_fg": "#4a90e2",
            "entry_bg": "#ffffff",
            "entry_fg": "#333333",
            "frame_bg": "#f0f0f0",
            "canvas_bg": "#000000"
        },
        "midnight": {
            "bg": "#0a0a1a",
            "fg": "#c0c0c0",
            "accent": "#1a1a3a",
            "button_bg": "#2a2a4a",
            "button_fg": "#ffffff",
            "progress_bg": "#2a2a4a",
            "progress_fg": "#6a6aff",
            "listbox_bg": "#1a1a3a",
            "listbox_fg": "#c0c0c0",
            "slider_bg": "#2a2a4a",
            "slider_fg": "#6a6aff",
            "entry_bg": "#1a1a3a",
            "entry_fg": "#c0c0c0",
            "frame_bg": "#0a0a1a",
            "canvas_bg": "#000000"
        }
    }

    def __init__(self):
        """Initialize theme manager"""
        self.current_theme = "dark"

    def get_theme(self, theme_name: str = None) -> Dict[str, str]:
        """Get theme colors"""
        if theme_name is None:
            theme_name = self.current_theme
        return self.THEMES.get(theme_name, self.THEMES["dark"])

    def apply_theme(self, widget: tk.Widget, theme_name: str = None) -> None:
        """Apply theme to a widget recursively"""
        theme = self.get_theme(theme_name)

        if isinstance(widget, (tk.Tk, tk.Toplevel)):
            widget.configure(bg=theme["bg"])

        for child in widget.winfo_children():
            self._apply_theme_to_widget(child, theme)

    def _apply_theme_to_widget(self, widget: tk.Widget, theme: Dict[str, str]) -> None:
        """Apply theme to individual widget"""
        try:
            if isinstance(widget, tk.Frame):
                widget.configure(bg=theme["frame_bg"])
            elif isinstance(widget, tk.Label):
                widget.configure(
                    bg=theme["bg"],
                    fg=theme["fg"]
                )
            elif isinstance(widget, tk.Button):
                widget.configure(
                    bg=theme["button_bg"],
                    fg=theme["button_fg"],
                    activebackground=theme["button_bg"],
                    activeforeground=theme["button_fg"]
                )
            elif isinstance(widget, tk.Entry):
                widget.configure(
                    bg=theme["entry_bg"],
                    fg=theme["entry_fg"],
                    insertbackground=theme["fg"]
                )
            elif isinstance(widget, tk.Listbox):
                widget.configure(
                    bg=theme["listbox_bg"],
                    fg=theme["listbox_fg"],
                    selectbackground=theme["button_bg"]
                )
            elif isinstance(widget, tk.Scrollbar):
                widget.configure(
                    bg=theme["accent"],
                    troughcolor=theme["bg"]
                )
            elif isinstance(widget, tk.Canvas):
                widget.configure(bg=theme["canvas_bg"])

            # Recursively apply to children
            for child in widget.winfo_children():
                self._apply_theme_to_widget(child, theme)

        except tk.TclError as e:
            logger.warning(f"Could not apply theme to widget: {e}")


class PlaylistManager:
    """Manages playlist operations"""

    def __init__(self):
        """Initialize playlist manager"""
        self.current_index = -1
        self.playlist: List[str] = []
        self.current_video: Optional[str] = None

    def add_videos(self, video_paths: List[str]) -> None:
        """Add videos to playlist"""
        for path in video_paths:
            if os.path.exists(path) and path not in self.playlist:
                self.playlist.append(path)
        logger.info(f"Added {len(video_paths)} videos to playlist")

    def remove_video(self, index: int) -> None:
        """Remove video from playlist"""
        if 0 <= index < len(self.playlist):
            removed = self.playlist.pop(index)
            logger.info(f"Removed video: {removed}")
            if index <= self.current_index:
                self.current_index = max(-1, self.current_index - 1)

    def clear(self) -> None:
        """Clear the playlist"""
        self.playlist.clear()
        self.current_index = -1
        self.current_video = None
        logger.info("Playlist cleared")

    def get_next(self) -> Optional[str]:
        """Get next video in playlist"""
        if not self.playlist:
            return None

        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.current_video = self.playlist[self.current_index]
        return self.current_video

    def get_previous(self) -> Optional[str]:
        """Get previous video in playlist"""
        if not self.playlist:
            return None

        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.current_video = self.playlist[self.current_index]
        return self.current_video

    def set_current(self, index: int) -> Optional[str]:
        """Set current video by index"""
        if 0 <= index < len(self.playlist):
            self.current_index = index
            self.current_video = self.playlist[index]
            return self.current_video
        return None

    def is_empty(self) -> bool:
        """Check if playlist is empty"""
        return len(self.playlist) == 0


class VideoProcessor:
    """Handles video processing using OpenCV"""

    def __init__(self):
        """Initialize video processor"""
        self.cap: Optional[cv2.VideoCapture] = None
        self.current_frame: Optional[Any] = None
        self.is_playing = False
        self.video_path: Optional[str] = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.audio_queue = queue.Queue()

    def load_video(self, video_path: str) -> bool:
        """Load a video file"""
        try:
            if self.cap:
                self.release()

            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return False

            self.video_path = video_path
            self.is_playing = False
            logger.info(f"Video loaded: {video_path}")
            return True

        except Exception as e:
            logger.error(f"Error loading video: {e}")
            return False

    def get_video_info(self) -> Optional[VideoInfo]:
        """Get information about the current video"""
        if not self.cap or not self.cap.isOpened():
            return None

        try:
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            video_name = os.path.basename(self.video_path) if self.video_path else "Unknown"

            return VideoInfo(
                path=self.video_path or "",
                name=video_name,
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                current_position=0.0,
                is_playing=False
            )
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None

    def read_frame(self) -> Optional[Any]:
        """Read the next frame from video"""
        if not self.cap or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if ret:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame_rgb
        return None

    def seek(self, position_seconds: float) -> bool:
        """Seek to a specific position in the video"""
        if not self.cap or not self.cap.isOpened():
            return False

        try:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, position_seconds * 1000)
            return True
        except Exception as e:
            logger.error(f"Error seeking: {e}")
            return False

    def get_current_position(self) -> float:
        """Get current video position in seconds"""
        if not self.cap or not self.cap.isOpened():
            return 0.0

        return self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

    def get_duration(self) -> float:
        """Get video duration in seconds"""
        if not self.cap or not self.cap.isOpened():
            return 0.0

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frame_count = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        return frame_count / fps if fps > 0 else 0.0

    def release(self) -> None:
        """Release video resources"""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_path = None
        self.is_playing = False
        logger.info("Video resources released")


class VideoPlayer:
    """Main Video Player class"""

    def __init__(self, root: tk.Tk):
        """Initialize the video player"""
        self.root = root
        self.root.title("Advanced Media Player")
        self.root.geometry("1200x800")

        # Initialize components
        self.settings = Settings()
        self.theme_manager = ThemeManager()
        self.playlist_manager = PlaylistManager()
        self.video_processor = VideoProcessor()

        # Player state
        self.is_playing = False
        self.is_fullscreen = False
        self.volume = self.settings.get("volume", 0.7)
        self.is_muted = self.settings.get("muted", False)
        self.current_video_info: Optional[VideoInfo] = None
        self.play_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Apply saved window size
        window_size = self.settings.get("window_size", [1200, 800])
        self.root.geometry(f"{window_size[0]}x{window_size[1]}")

        # Apply theme
        theme_name = self.settings.get("theme", "dark")
        self.theme_manager.current_theme = theme_name

        # Setup UI
        self.setup_ui()
        self.setup_bindings()

        # Apply theme to all widgets
        self.theme_manager.apply_theme(self.root, theme_name)

        # Load last playlist if exists
        last_playlist = self.settings.get("last_playlist", [])
        if last_playlist:
            self.playlist_manager.add_videos(last_playlist)
            self.update_playlist_display()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("Video Player initialized")

    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Menu bar
        self.create_menu()

        # Main content area
        self.content_frame = tk.Frame(self.main_container)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel (playlist)
        self.create_playlist_panel()

        # Right panel (video)
        self.create_video_panel()

        # Bottom control bar
        self.create_control_bar()

        # Status bar
        self.create_status_bar()

    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Open Folder", command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Playback menu
        playback_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Playback", menu=playback_menu)
        playback_menu.add_command(label="Play/Pause", command=self.toggle_play_pause, accelerator="Space")
        playback_menu.add_command(label="Stop", command=self.stop_video)
        playback_menu.add_command(label="Next", command=self.play_next)
        playback_menu.add_command(label="Previous", command=self.play_previous)
        playback_menu.add_separator()
        playback_menu.add_command(label="Forward 10s", command=self.forward_10_seconds, accelerator="Right")
        playback_menu.add_command(label="Backward 10s", command=self.backward_10_seconds, accelerator="Left")

        # Audio menu
        audio_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Audio", menu=audio_menu)
        audio_menu.add_command(label="Mute/Unmute", command=self.toggle_mute, accelerator="M")
        audio_menu.add_separator()
        audio_menu.add_command(label="Volume Up", command=self.volume_up)
        audio_menu.add_command(label="Volume Down", command=self.volume_down)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Fullscreen", command=self.toggle_fullscreen, accelerator="F11")
        view_menu.add_separator()

        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Dark", command=lambda: self.change_theme("dark"))
        theme_menu.add_command(label="Light", command=lambda: self.change_theme("light"))
        theme_menu.add_command(label="Midnight", command=lambda: self.change_theme("midnight"))

        view_menu.add_command(label="Toggle Playlist", command=self.toggle_playlist_visibility)

    def create_playlist_panel(self):
        """Create playlist panel on the left side"""
        self.playlist_frame = tk.Frame(self.content_frame, width=300)
        self.playlist_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.playlist_frame.pack_propagate(False)

        # Playlist header
        playlist_header = tk.Label(
            self.playlist_frame,
            text="Playlist",
            font=("Arial", 12, "bold")
        )
        playlist_header.pack(pady=5)

        # Playlist controls
        playlist_controls = tk.Frame(self.playlist_frame)
        playlist_controls.pack(fill=tk.X, padx=5, pady=2)

        tk.Button(
            playlist_controls,
            text="Add",
            command=self.add_to_playlist
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            playlist_controls,
            text="Remove",
            command=self.remove_from_playlist
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            playlist_controls,
            text="Clear",
            command=self.clear_playlist
        ).pack(side=tk.LEFT, padx=2)

        # Playlist listbox with scrollbar
        playlist_list_frame = tk.Frame(self.playlist_frame)
        playlist_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(playlist_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.playlist_listbox = tk.Listbox(
            playlist_list_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        self.playlist_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.playlist_listbox.yview)

        # Bind double-click on playlist
        self.playlist_listbox.bind("<Double-Button-1>", self.playlist_double_click)

    def create_video_panel(self):
        """Create video display panel"""
        self.video_frame = tk.Frame(self.content_frame)
        self.video_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Video title
        self.video_title = tk.Label(
            self.video_frame,
            text="No video loaded",
            font=("Arial", 10)
        )
        self.video_title.pack(pady=2)

        # Video display canvas
        self.canvas = tk.Canvas(
            self.video_frame,
            bg="black"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def create_control_bar(self):
        """Create bottom control bar"""
        self.control_frame = tk.Frame(self.main_container)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Row 1: Progress bar
        progress_frame = tk.Frame(self.control_frame)
        progress_frame.pack(fill=tk.X, pady=2)

        self.time_label = tk.Label(progress_frame, text="00:00:00")
        self.time_label.pack(side=tk.LEFT, padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(
            progress_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.progress_var,
            command=self.on_progress_change
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.duration_label = tk.Label(progress_frame, text="00:00:00")
        self.duration_label.pack(side=tk.RIGHT, padx=5)

        # Row 2: Control buttons
        buttons_frame = tk.Frame(self.control_frame)
        buttons_frame.pack(fill=tk.X, pady=2)

        # Left side buttons
        left_buttons = tk.Frame(buttons_frame)
        left_buttons.pack(side=tk.LEFT)

        buttons = [
            ("⏮", self.play_previous, "Previous"),
            ("⏪", self.backward_10_seconds, "-10s"),
            ("⏯", self.toggle_play_pause, "Play/Pause"),
            ("⏩", self.forward_10_seconds, "+10s"),
            ("⏭", self.play_next, "Next"),
            ("⏹", self.stop_video, "Stop")
        ]

        for text, command, tooltip in buttons:
            btn = tk.Button(
                left_buttons,
                text=text,
                command=command,
                font=("Arial", 14),
                width=4
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.create_tooltip(btn, tooltip)

        # Right side buttons
        right_buttons = tk.Frame(buttons_frame)
        right_buttons.pack(side=tk.RIGHT)

        # Volume controls
        self.mute_button = tk.Button(
            right_buttons,
            text="🔊",
            command=self.toggle_mute,
            font=("Arial", 10),
            width=3
        )
        self.mute_button.pack(side=tk.LEFT, padx=2)

        self.volume_var = tk.DoubleVar(value=self.volume * 100)
        self.volume_slider = ttk.Scale(
            right_buttons,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self.on_volume_change,
            length=100
        )
        self.volume_slider.pack(side=tk.LEFT, padx=5)

        self.volume_label = tk.Label(right_buttons, text="70%")
        self.volume_label.pack(side=tk.LEFT, padx=2)

        # Fullscreen button
        self.fullscreen_button = tk.Button(
            right_buttons,
            text="⛶",
            command=self.toggle_fullscreen,
            font=("Arial", 12),
            width=3
        )
        self.fullscreen_button.pack(side=tk.LEFT, padx=5)

    def create_status_bar(self):
        """Create status bar"""
        self.status_frame = tk.Frame(self.main_container)
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)

        self.status_label = tk.Label(
            self.status_frame,
            text="Ready",
            font=("Arial", 8),
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.fps_label = tk.Label(
            self.status_frame,
            text="0 FPS",
            font=("Arial", 8)
        )
        self.fps_label.pack(side=tk.RIGHT, padx=5)

    def setup_bindings(self):
        """Setup keyboard bindings"""
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.root.bind("<space>", lambda e: self.toggle_play_pause())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<m>", lambda e: self.toggle_mute())
        self.root.bind("<M>", lambda e: self.toggle_mute())
        self.root.bind("<Left>", lambda e: self.backward_10_seconds())
        self.root.bind("<Right>", lambda e: self.forward_10_seconds())

        # Drag and drop support
        try:
            self.root.drop_target_register("DND_Files")
            self.root.dnd_bind("<<Drop>>", self.on_drop)
            logger.info("Drag and drop enabled")
        except Exception as e:
            logger.warning(f"Drag and drop not available: {e}")

    def create_tooltip(self, widget, text):
        """Create tooltip for widget"""

        def enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

            label = tk.Label(
                tooltip,
                text=text,
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
                font=("Arial", 8)
            )
            label.pack()

            def leave(event):
                tooltip.destroy()

            widget.tooltip = tooltip
            widget.bind("<Leave>", leave)

        widget.bind("<Enter>", enter)

    def open_file(self):
        """Open video file dialog"""
        file_path = filedialog.askopenfilename(
            title="Open Video File",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mkv *.wmv *.webm"),
                ("All Files", "*.*")
            ],
            initialdir=self.settings.get("last_folder", "")
        )

        if file_path:
            # Save last folder
            self.settings.set("last_folder", os.path.dirname(file_path))

            # Add to playlist and play
            self.playlist_manager.add_videos([file_path])
            self.update_playlist_display()
            self.play_video(file_path)

    def open_folder(self):
        """Open folder with videos"""
        folder_path = filedialog.askdirectory(
            title="Select Folder with Videos",
            initialdir=self.settings.get("last_folder", "")
        )

        if folder_path:
            self.settings.set("last_folder", folder_path)

            # Find video files in folder
            video_extensions = {'.mp4', '.avi', '.mkv', '.wmv', '.webm'}
            video_files = []

            for file in os.listdir(folder_path):
                if os.path.splitext(file)[1].lower() in video_extensions:
                    video_files.append(os.path.join(folder_path, file))

            if video_files:
                self.playlist_manager.add_videos(video_files)
                self.update_playlist_display()

                # Play first video
                first_video = self.playlist_manager.get_next()
                if first_video:
                    self.play_video(first_video)
            else:
                messagebox.showinfo("No Videos", "No video files found in selected folder")

    def add_to_playlist(self):
        """Add videos to playlist"""
        file_paths = filedialog.askopenfilenames(
            title="Add Videos to Playlist",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mkv *.wmv *.webm"),
                ("All Files", "*.*")
            ],
            initialdir=self.settings.get("last_folder", "")
        )

        if file_paths:
            self.playlist_manager.add_videos(list(file_paths))
            self.update_playlist_display()

            # If nothing is playing, play the first added video
            if not self.is_playing and not self.playlist_manager.is_empty():
                first_video = self.playlist_manager.get_next()
                if first_video:
                    self.play_video(first_video)

    def remove_from_playlist(self):
        """Remove selected video from playlist"""
        selection = self.playlist_listbox.curselection()
        if selection:
            index = selection[0]
            self.playlist_manager.remove_video(index)
            self.update_playlist_display()

    def clear_playlist(self):
        """Clear the entire playlist"""
        if messagebox.askyesno("Clear Playlist", "Are you sure you want to clear the playlist?"):
            self.stop_video()
            self.playlist_manager.clear()
            self.update_playlist_display()
            self.canvas.delete("all")
            self.video_title.config(text="No video loaded")

    def update_playlist_display(self):
        """Update the playlist listbox"""
        self.playlist_listbox.delete(0, tk.END)

        for video_path in self.playlist_manager.playlist:
            video_name = os.path.basename(video_path)
            self.playlist_listbox.insert(tk.END, video_name)

        # Save playlist to settings
        self.settings.set("last_playlist", self.playlist_manager.playlist)

    def playlist_double_click(self, event):
        """Handle double-click on playlist item"""
        selection = self.playlist_listbox.curselection()
        if selection:
            index = selection[0]
            video_path = self.playlist_manager.set_current(index)
            if video_path:
                self.play_video(video_path)

    def play_video(self, video_path: str):
        """Play a video file"""
        try:
            # Stop current playback
            self.stop_video()

            # Load video
            if not self.video_processor.load_video(video_path):
                messagebox.showerror("Error", f"Could not load video: {video_path}")
                return

            # Get video info
            self.current_video_info = self.video_processor.get_video_info()

            if self.current_video_info:
                # Update UI
                self.video_title.config(text=self.current_video_info.name)
                self.duration_label.config(
                    text=self.format_time(self.current_video_info.duration)
                )
                self.progress_bar.config(to=self.current_video_info.duration)
                self.update_status(f"Playing: {self.current_video_info.name}")

                # Set playlist index
                if video_path in self.playlist_manager.playlist:
                    self.playlist_manager.current_index = self.playlist_manager.playlist.index(video_path)

                # Start playback
                self.is_playing = True
                self.stop_event.clear()
                self.play_thread = threading.Thread(target=self.playback_loop)
                self.play_thread.daemon = True
                self.play_thread.start()

        except Exception as e:
            logger.error(f"Error playing video: {e}")
            messagebox.showerror("Error", f"Error playing video: {str(e)}")

    def playback_loop(self):
        """Main playback loop running in separate thread"""
        frame_count = 0
        fps_timer = time.time()

        try:
            while not self.stop_event.is_set() and self.is_playing:
                frame = self.video_processor.read_frame()

                if frame is None:
                    # Video ended, play next
                    self.stop_event.set()
                    self.root.after(0, self.on_video_ended)
                    break

                # Update frame on canvas
                self.display_frame(frame)

                # Update progress
                current_time = self.video_processor.get_current_position()
                self.root.after(0, self.update_progress, current_time)

                # Calculate FPS
                frame_count += 1
                if time.time() - fps_timer >= 1:
                    fps = frame_count / (time.time() - fps_timer)
                    self.root.after(0, self.update_fps, fps)
                    frame_count = 0
                    fps_timer = time.time()

                # Control playback speed
                time.sleep(0.01)  # Small delay to prevent CPU overload

        except Exception as e:
            logger.error(f"Playback error: {e}")
            self.root.after(0, self.on_playback_error, str(e))

    def display_frame(self, frame):
        """Display video frame on canvas"""
        try:
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 800
                canvas_height = 600

            # Resize frame to fit canvas
            frame_height, frame_width = frame.shape[:2]

            # Calculate scaling
            scale_w = canvas_width / frame_width
            scale_h = canvas_height / frame_height
            scale = min(scale_w, scale_h)

            new_width = int(frame_width * scale)
            new_height = int(frame_height * scale)

            # Resize frame
            resized_frame = cv2.resize(frame, (new_width, new_height))

            # Convert to PhotoImage
            image = Image.fromarray(resized_frame)
            photo = ImageTk.PhotoImage(image=image)

            # Update canvas
            self.root.after(0, self.update_canvas, photo)

        except Exception as e:
            logger.error(f"Error displaying frame: {e}")

    def update_canvas(self, photo):
        """Update canvas with new frame"""
        try:
            self.canvas.delete("all")

            # Center the frame
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            x = (canvas_width - photo.width()) // 2
            y = (canvas_height - photo.height()) // 2

            self.canvas.create_image(x, y, anchor=tk.NW, image=photo)
            self.canvas.image = photo  # Keep reference
        except Exception as e:
            logger.error(f"Error updating canvas: {e}")

    def update_progress(self, current_time: float):
        """Update progress bar and time display"""
        try:
            if self.current_video_info:
                self.progress_var.set(current_time)
                self.time_label.config(text=self.format_time(current_time))
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def update_fps(self, fps: float):
        """Update FPS display"""
        self.fps_label.config(text=f"{fps:.1f} FPS")

    def on_progress_change(self, value):
        """Handle progress bar change"""
        if self.current_video_info and self.video_processor.cap:
            try:
                position = float(value)
                self.video_processor.seek(position)
                self.time_label.config(text=self.format_time(position))
            except Exception as e:
                logger.error(f"Error changing progress: {e}")

    def on_volume_change(self, value):
        """Handle volume change"""
        try:
            self.volume = float(value) / 100
            self.volume_label.config(text=f"{int(self.volume * 100)}%")
            self.settings.set("volume", self.volume)

            # Update mute button
            if self.volume == 0:
                self.mute_button.config(text="🔇")
                self.is_muted = True
            else:
                self.mute_button.config(text="🔊")
                self.is_muted = False

            self.settings.set("muted", self.is_muted)

        except Exception as e:
            logger.error(f"Error changing volume: {e}")

    def toggle_play_pause(self):
        """Toggle play/pause"""
        if not self.current_video_info:
            return

        if self.is_playing:
            self.pause_video()
        else:
            self.resume_video()

    def pause_video(self):
        """Pause video playback"""
        self.is_playing = False
        self.stop_event.set()
        self.update_status("Paused")
        logger.info("Video paused")

    def resume_video(self):
        """Resume video playback"""
        if self.current_video_info:
            self.is_playing = True
            self.stop_event.clear()
            self.play_thread = threading.Thread(target=self.playback_loop)
            self.play_thread.daemon = True
            self.play_thread.start()
            self.update_status(f"Playing: {self.current_video_info.name}")
            logger.info("Video resumed")

    def stop_video(self):
        """Stop video playback"""
        self.is_playing = False
        self.stop_event.set()

        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)

        self.canvas.delete("all")
        self.time_label.config(text="00:00:00")
        self.progress_var.set(0)
        self.fps_label.config(text="0 FPS")
        self.update_status("Stopped")
        logger.info("Video stopped")

    def play_next(self):
        """Play next video in playlist"""
        if not self.playlist_manager.is_empty():
            next_video = self.playlist_manager.get_next()
            if next_video:
                self.play_video(next_video)

    def play_previous(self):
        """Play previous video in playlist"""
        if not self.playlist_manager.is_empty():
            prev_video = self.playlist_manager.get_previous()
            if prev_video:
                self.play_video(prev_video)

    def forward_10_seconds(self):
        """Jump forward 10 seconds"""
        if self.current_video_info and self.video_processor.cap:
            current_time = self.video_processor.get_current_position()
            new_time = min(current_time + 10, self.current_video_info.duration)
            self.video_processor.seek(new_time)
            self.progress_var.set(new_time)
            self.update_status(f"Forward 10s to {self.format_time(new_time)}")

    def backward_10_seconds(self):
        """Jump backward 10 seconds"""
        if self.current_video_info and self.video_processor.cap:
            current_time = self.video_processor.get_current_position()
            new_time = max(current_time - 10, 0)
            self.video_processor.seek(new_time)
            self.progress_var.set(new_time)
            self.update_status(f"Backward 10s to {self.format_time(new_time)}")

    def toggle_mute(self):
        """Toggle mute/unmute"""
        self.is_muted = not self.is_muted

        if self.is_muted:
            self.mute_button.config(text="🔇")
            self.volume_var.set(0)
            self.volume_label.config(text="0%")
        else:
            self.mute_button.config(text="🔊")
            self.volume_var.set(self.volume * 100)
            self.volume_label.config(text=f"{int(self.volume * 100)}%")

        self.settings.set("muted", self.is_muted)
        self.update_status("Muted" if self.is_muted else "Unmuted")

    def volume_up(self):
        """Increase volume"""
        new_volume = min(self.volume + 0.1, 1.0)
        self.volume = new_volume
        self.volume_var.set(new_volume * 100)
        self.volume_label.config(text=f"{int(new_volume * 100)}%")
        self.settings.set("volume", new_volume)

    def volume_down(self):
        """Decrease volume"""
        new_volume = max(self.volume - 0.1, 0.0)
        self.volume = new_volume
        self.volume_var.set(new_volume * 100)
        self.volume_label.config(text=f"{int(new_volume * 100)}%")
        self.settings.set("volume", new_volume)

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

        if self.is_fullscreen:
            self.fullscreen_button.config(text="⛶")
            self.update_status("Fullscreen mode")
        else:
            self.fullscreen_button.config(text="⛶")
            self.update_status("Windowed mode")

    def exit_fullscreen(self):
        """Exit fullscreen mode"""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.fullscreen_button.config(text="⛶")
            self.update_status("Windowed mode")

    def change_theme(self, theme_name: str):
        """Change application theme"""
        self.theme_manager.current_theme = theme_name
        self.theme_manager.apply_theme(self.root, theme_name)
        self.settings.set("theme", theme_name)
        self.update_status(f"Theme changed to {theme_name}")
        logger.info(f"Theme changed to {theme_name}")

    def toggle_playlist_visibility(self):
        """Toggle playlist panel visibility"""
        if self.playlist_frame.winfo_viewable():
            self.playlist_frame.pack_forget()
            self.update_status("Playlist hidden")
        else:
            self.playlist_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), before=self.video_frame)
            self.update_status("Playlist visible")

    def on_drop(self, event):
        """Handle drag and drop events"""
        try:
            files = event.data
            if files:
                # Parse dropped files
                video_extensions = {'.mp4', '.avi', '.mkv', '.wmv', '.webm'}
                video_files = []

                for file_path in files.split():
                    file_path = file_path.strip('{}')
                    if os.path.exists(file_path) and os.path.splitext(file_path)[1].lower() in video_extensions:
                        video_files.append(file_path)

                if video_files:
                    self.playlist_manager.add_videos(video_files)
                    self.update_playlist_display()

                    # Play the first dropped video
                    if not self.is_playing:
                        first_video = video_files[0]
                        self.playlist_manager.current_index = self.playlist_manager.playlist.index(first_video)
                        self.play_video(first_video)

                    self.update_status(f"Added {len(video_files)} video(s)")
        except Exception as e:
            logger.error(f"Error handling drop: {e}")

    def on_video_ended(self):
        """Handle video end event"""
        logger.info("Video ended")

        # Auto-play next video
        if not self.playlist_manager.is_empty():
            next_video = self.playlist_manager.get_next()
            if next_video:
                self.play_video(next_video)
            else:
                self.stop_video()
                self.update_status("Playlist finished")

    def on_playback_error(self, error_msg: str):
        """Handle playback errors"""
        messagebox.showerror("Playback Error", f"An error occurred during playback: {error_msg}")
        self.stop_video()
        self.update_status("Playback error")

    def update_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)

    def format_time(self, seconds: float) -> str:
        """Format time as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def on_closing(self):
        """Handle application closing"""
        # Save settings
        self.settings.set("window_size", [self.root.winfo_width(), self.root.winfo_height()])
        self.settings.set("volume", self.volume)
        self.settings.set("muted", self.is_muted)
        self.settings.set("last_playlist", self.playlist_manager.playlist)

        # Stop playback
        self.stop_video()

        # Release resources
        self.video_processor.release()

        # Close application
        self.root.destroy()
        logger.info("Application closed")


def main():
    """Main entry point"""
    try:
        # Create and run the application
        root = tk.Tk()
        app = VideoPlayer(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        messagebox.showerror("Fatal Error", f"Application failed to start: {str(e)}")


if __name__ == "__main__":
    main()