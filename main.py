import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTabWidget, 
                            QLineEdit, QGroupBox, QFormLayout, QSpinBox, 
                            QDoubleSpinBox, QCheckBox, QComboBox, QTextEdit,
                            QFileDialog, QMessageBox, QSystemTrayIcon, QMenu,
                            QAction, QListWidget, QListWidgetItem, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QColor, QImage
import pyautogui
import time
import keyboard
import sqlite3
import hashlib
import uuid
import cv2
import numpy as np
from datetime import datetime

# Disable PyAutoGUI fail-safe temporarily (we'll implement our own)
pyautogui.FAILSAFE = False

class PixelDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.setMaximumSize(150, 150)
        self.pixmap = QPixmap(150, 150)
        self.pixmap.fill(Qt.white)
        self.current_pos = QPoint(0, 0)
        self.zoom_factor = 10  # Each pixel becomes 10x10
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_pixel_display)
        self.update_timer.start(100)  # Update every 100ms
        
    def update_pixel_display(self):
        try:
            x, y = pyautogui.position()
            self.current_pos = QPoint(x, y)
            
            # Capture screen area around cursor
            screenshot = pyautogui.screenshot(region=(x-7, y-7, 15, 15))
            img = screenshot.convert('RGB')
            
            # Create a new pixmap
            self.pixmap = QPixmap(150, 150)
            self.pixmap.fill(Qt.white)
            
            # Draw the zoomed pixels
            qp = QPainter(self.pixmap)
            for i in range(15):
                for j in range(15):
                    try:
                        r, g, b = img.getpixel((i, j))
                        qp.fillRect(i*self.zoom_factor, j*self.zoom_factor, 
                                   self.zoom_factor, self.zoom_factor, 
                                   QColor(r, g, b))
                    except:
                        pass
            
            # Draw crosshair at center
            qp.setPen(QPen(Qt.red, 1))
            center = 7 * self.zoom_factor + self.zoom_factor // 2
            qp.drawLine(center, 0, center, 150)
            qp.drawLine(0, center, 150, center)
            qp.end()
            
            self.update()
        except:
            pass
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

class RecordingThread(QThread):
    action_recorded = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.actions = []
        self.start_time = 0
        self.last_position = None
        self.record_movement = True
        self.movement_threshold = 5  # pixels
        self.movement_interval = 0.1  # seconds
        self.last_movement_time = 0
    
    def run(self):
        self.running = True
        self.start_time = time.time()
        self.last_position = pyautogui.position()
        self.last_movement_time = time.time()
        
        while self.running:
            # Record mouse position changes
            current_pos = pyautogui.position()
            current_time = time.time()
            
            # Record significant mouse movements
            if self.record_movement and (current_time - self.last_movement_time) >= self.movement_interval:
                x_diff = abs(current_pos[0] - self.last_position[0])
                y_diff = abs(current_pos[1] - self.last_position[1])
                
                if x_diff > self.movement_threshold or y_diff > self.movement_threshold:
                    action = {
                        'type': 'move',
                        'x': current_pos[0],
                        'y': current_pos[1],
                        'time': current_time - self.start_time
                    }
                    self.action_recorded.emit(action)
                    self.actions.append(action)
                    self.last_position = current_pos
                    self.last_movement_time = current_time
            
            # Small sleep to prevent high CPU usage
            time.sleep(0.01)
    
    def stop(self):
        self.running = False
    
    def add_action(self, action_type, **kwargs):
        action = {
            'type': action_type,
            'time': time.time() - self.start_time,
            **kwargs
        }
        self.actions.append(action)
        self.action_recorded.emit(action)

class PlaybackThread(QThread):
    playback_finished = pyqtSignal()
    action_played = pyqtSignal(int)
    
    def __init__(self, actions, speed_factor=1.0, repeat_count=1, randomize=False, randomize_factor=0.1):
        super().__init__()
        self.actions = actions
        self.speed_factor = speed_factor
        self.repeat_count = repeat_count
        self.running = False
        self.randomize = randomize
        self.randomize_factor = randomize_factor
    
    def run(self):
        self.running = True
        
        for _ in range(self.repeat_count):
            if not self.running:
                break
                
            last_time = 0
            for i, action in enumerate(self.actions):
                if not self.running:
                    break
                
                # Calculate delay
                if i > 0:
                    delay = (action['time'] - last_time) / self.speed_factor
                    
                    # Add randomization if enabled
                    if self.randomize:
                        random_factor = 1.0 + (np.random.random() * 2 - 1) * self.randomize_factor
                        delay *= random_factor
                    
                    time.sleep(max(0, delay))
                
                # Execute action
                self._execute_action(action)
                last_time = action['time']
                
                # Emit signal for UI update
                self.action_played.emit(i)
        
        self.running = False
        self.playback_finished.emit()
    
    def _execute_action(self, action):
        try:
            if action['type'] == 'click':
                if self.randomize:
                    # Add slight randomization to click position
                    rand_x = action['x'] + int((np.random.random() * 2 - 1) * 3)
                    rand_y = action['y'] + int((np.random.random() * 2 - 1) * 3)
                    pyautogui.click(rand_x, rand_y, button=action.get('button', 'left'))
                else:
                    pyautogui.click(action['x'], action['y'], button=action.get('button', 'left'))
                    
            elif action['type'] == 'move':
                pyautogui.moveTo(action['x'], action['y'])
                
            elif action['type'] == 'keypress':
                pyautogui.press(action['key'])
                
            elif action['type'] == 'keydown':
                pyautogui.keyDown(action['key'])
                
            elif action['type'] == 'keyup':
                pyautogui.keyUp(action['key'])
                
            elif action['type'] == 'scroll':
                pyautogui.scroll(action['amount'])
        except Exception as e:
            print(f"Error executing action: {e}")
    
    def stop(self):
        self.running = False

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        try:
            self.conn = sqlite3.connect('autoclick.db')
            cursor = self.conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create scripts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scripts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                description TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create profiles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                hotkey TEXT,
                script_id TEXT,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (script_id) REFERENCES scripts (id)
            )
            ''')
            
            self.conn.commit()
        except Exception as e:
            print(f"Database setup error: {e}")
    
    def create_user(self, username, password):
        try:
            cursor = self.conn.cursor()
            user_id = str(uuid.uuid4())
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                (user_id, username, password_hash)
            )
            self.conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None  # Username already exists
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def authenticate_user(self, username, password):
        try:
            cursor = self.conn.cursor()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                "SELECT id FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def save_script(self, user_id, name, description, content):
        try:
            cursor = self.conn.cursor()
            script_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO scripts (id, user_id, name, description, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (script_id, user_id, name, description, json.dumps(content), now, now)
            )
            self.conn.commit()
            return script_id
        except Exception as e:
            print(f"Error saving script: {e}")
            return None
    
    def update_script(self, script_id, name, description, content):
        try:
            cursor = self.conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "UPDATE scripts SET name = ?, description = ?, content = ?, updated_at = ? WHERE id = ?",
                (name, description, json.dumps(content), now, script_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating script: {e}")
            return False
    
    def get_user_scripts(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, description, created_at FROM scripts WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting scripts: {e}")
            return []
    
    def get_script(self, script_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name, description, content FROM scripts WHERE id = ?",
                (script_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'description': result[1],
                    'content': json.loads(result[2])
                }
            return None
        except Exception as e:
            print(f"Error getting script: {e}")
            return None
    
    def save_profile(self, user_id, name, hotkey, script_id, settings):
        try:
            cursor = self.conn.cursor()
            profile_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO profiles (id, user_id, name, hotkey, script_id, settings, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (profile_id, user_id, name, hotkey, script_id, json.dumps(settings), now, now)
            )
            self.conn.commit()
            return profile_id
        except Exception as e:
            print(f"Error saving profile: {e}")
            return None
    
    def get_user_profiles(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.id, p.name, p.hotkey, s.name 
                FROM profiles p
                JOIN scripts s ON p.script_id = s.id
                WHERE p.user_id = ?
                ORDER BY p.updated_at DESC
                """,
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting profiles: {e}")
            return []
    
    def get_profile(self, profile_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.name, p.hotkey, p.script_id, p.settings, s.content
                FROM profiles p
                JOIN scripts s ON p.script_id = s.id
                WHERE p.id = ?
                """,
                (profile_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'hotkey': result[1],
                    'script_id': result[2],
                    'settings': json.loads(result[3]),
                    'script_content': json.loads(result[4])
                }
            return None
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def close(self):
        if self.conn:
            self.conn.close()

class LoginDialog(QWidget):
    login_successful = pyqtSignal(str, str)  # user_id, username
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Auto Click - Login')
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Logo or title
        title_label = QLabel("Auto Click")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title_label)
        
        # Login form
        form_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        
        form_container = QWidget()
        form_container.setLayout(form_layout)
        layout.addWidget(form_container)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.clicked.connect(self.register)
        
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.register_btn)
        
        button_container = QWidget()
        button_container.setLayout(button_layout)
        layout.addWidget(button_container)
        
        # Status message
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        user_id = self.db_manager.authenticate_user(username, password)
        if user_id:
            self.login_successful.emit(user_id, username)
            self.close()
        else:
            self.status_label.setText("Invalid username or password")
    
    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        if len(password) < 6:
            self.status_label.setText("Password must be at least 6 characters")
            return
        
        user_id = self.db_manager.create_user(username, password)
        if user_id:
            self.status_label.setText("Registration successful! You can now login.")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("Username already exists")

class ImageRecognitionTool:
    def __init__(self):
        self.templates = {}  # Store loaded templates
    
    def load_template(self, name, image_path):
        try:
            template = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if template is None:
                return False
            self.templates[name] = template
            return True
        except Exception as e:
            print(f"Error loading template: {e}")
            return False
    
    def find_on_screen(self, template_name, confidence=0.8):
        if template_name not in self.templates:
            return None
        
        template = self.templates[template_name]
        screenshot = pyautogui.screenshot()
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            # Get the dimensions of the template
            h, w = template.shape[:2]
            # Calculate the center point of the match
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y, max_val)
        
        return None

class AutoClickApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.image_recognition = ImageRecognitionTool()
        self.user_id = None
        self.username = None
        self.recording_thread = None
        self.playback_thread = None
        self.current_actions = []
        self.current_script_id = None
        self.current_script_name = ""
        self.current_script_description = ""
        self.active_profiles = {}  # Store active profiles with their hotkeys
        
        # Show login dialog first
        self.show_login_dialog()
    
    def show_login_dialog(self):
        self.login_dialog = LoginDialog(self.db_manager)
        self.login_dialog.login_successful.connect(self.on_login_successful)
        self.login_dialog.show()
    
    def on_login_successful(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.initUI()
        self.show()
    
    def initUI(self):
        self.setWindowTitle(f'Auto Click - {self.username}')
        self.setGeometry(100, 100, 1000, 700)
        
        # Create main tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.recorder_tab = QWidget()
        self.scripts_tab = QWidget()
        self.profiles_tab = QWidget()
        self.settings_tab = QWidget()
        
        self.setup_recorder_tab()
        self.setup_scripts_tab()
        self.setup_profiles_tab()
        self.setup_settings_tab()
        
        self.tabs.addTab(self.recorder_tab, "Recorder")
        self.tabs.addTab(self.scripts_tab, "Scripts")
        self.tabs.addTab(self.profiles_tab, "Profiles")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        self.setCentralWidget(self.tabs)
        
        # Setup system tray
        self.setup_system_tray()
        
        # Load settings
        self.load_settings()
    
    def setup_recorder_tab(self):
        layout = QVBoxLayout()
        
        # Top section with coordinate display and pixel viewer
        top_layout = QHBoxLayout()
        
        # Coordinate display
        coord_group = QGroupBox("Cursor Position")
        coord_layout = QVBoxLayout()
        
        self.coord_label = QLabel("X: 0, Y: 0")
        self.coord_label.setAlignment(Qt.AlignCenter)
        self.coord_label.setStyleSheet("font-size: 16px;")
        coord_layout.addWidget(self.coord_label)
        
        # Color display
        self.color_label = QLabel("RGB: 0, 0, 0")
        self.color_label.setAlignment(Qt.AlignCenter)
        coord_layout.addWidget(self.color_label)
        
        coord_group.setLayout(coord_layout)
        top_layout.addWidget(coord_group)
        
        # Pixel display
        pixel_group = QGroupBox("Pixel View")
        pixel_layout = QVBoxLayout()
        self.pixel_display = PixelDisplayWidget()
        pixel_layout.addWidget(self.pixel_display)
        pixel_group.setLayout(pixel_layout)
        top_layout.addWidget(pixel_group)
        
        # Recording controls
        controls_group = QGroupBox("Recording Controls")
        controls_layout = QVBoxLayout()
        
        # Script info
        script_info_layout = QFormLayout()
        self.script_name_input = QLineEdit()
        self.script_desc_input = QTextEdit()
        self.script_desc_input.setMaximumHeight(60)
        
        script_info_layout.addRow("Name:", self.script_name_input)
        script_info_layout.addRow("Description:", self.script_desc_input)
        controls_layout.addLayout(script_info_layout)
        
        # Record/Stop buttons
        button_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_recording)
        self.play_btn.setEnabled(False)
        
        button_layout.addWidget(self.record_btn)
        button_layout.addWidget(self.play_btn)
        
        controls_layout.addLayout(button_layout)
        
        # Playback settings
        playback_layout = QFormLayout()
        
        self.speed_input = QDoubleSpinBox()
        self.speed_input.setRange(0.1, 10.0)
        self.speed_input.setValue(1.0)
        self.speed_input.setSingleStep(0.1)
        
        self.repeat_input = QSpinBox()
        self.repeat_input.setRange(1, 9999)
        self.repeat_input.setValue(1)
        
        self.randomize_cb = QCheckBox("Add randomization")
        
        playback_layout.addRow("Speed:", self.speed_input)
        playback_layout.addRow("Repeat:", self.repeat_input)
        playback_layout.addRow("", self.randomize_cb)
        
        controls_layout.addLayout(playback_layout)
        
        # Save/Load buttons
        save_load_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Script")
        self.save_btn.clicked.connect(self.save_script)
        self.save_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_recording)
        
        save_load_layout.addWidget(self.save_btn)
        save_load_layout.addWidget(self.clear_btn)
        
        controls_layout.addLayout(save_load_layout)
        
        controls_group.setLayout(controls_layout)
        top_layout.addWidget(controls_group)
        
        layout.addLayout(top_layout)
        
        # Actions list
        actions_group = QGroupBox("Recorded Actions")
        actions_layout = QVBoxLayout()
        
        self.actions_list = QListWidget()
        actions_layout.addWidget(self.actions_list)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        self.recorder_tab.setLayout(layout)
        
        # Setup timer to update coordinates
        self.coord_timer = QTimer(self)
        self.coord_timer.timeout.connect(self.update_coordinates)
        self.coord_timer.start(100)  # Update every 100ms
        
        # Setup global hotkeys
        keyboard.on_press(self.on_key_press)
    
    def setup_scripts_tab(self):
        layout = QVBoxLayout()
        
        # Scripts list
        self.scripts_list = QListWidget()
        self.scripts_list.itemDoubleClicked.connect(self.load_script)
        layout.addWidget(self.scripts_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_scripts_btn = QPushButton("Refresh")
        self.refresh_scripts_btn.clicked.connect(self.load_user_scripts)
        
        self.delete_script_btn = QPushButton("Delete")
        self.delete_script_btn.clicked.connect(self.delete_script)
        
        self.export_script_btn = QPushButton("Export")
        self.export_script_btn.clicked.connect(self.export_script)
        
        self.import_script_btn = QPushButton("Import")
        self.import_script_btn.clicked.connect(self.import_script)
        
        button_layout.addWidget(self.refresh_scripts_btn)
        button_layout.addWidget(self.delete_script_btn)
        button_layout.addWidget(self.export_script_btn)
        button_layout.addWidget(self.import_script_btn)
        
        layout.addLayout(button_layout)
        
        self.scripts_tab.setLayout(layout)
        
        # Load user scripts
        self.load_user_scripts()
    
    def setup_profiles_tab(self):
        layout = QVBoxLayout()
        
        # Profiles list
        self.profiles_list = QListWidget()
        self.profiles_list.itemDoubleClicked.connect(self.edit_profile)
        layout.addWidget(self.profiles_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.new_profile_btn = QPushButton("New Profile")
        self.new_profile_btn.clicked.connect(self.create_profile)
        
        self.refresh_profiles_btn = QPushButton("Refresh")
        self.refresh_profiles_btn.clicked.connect(self.load_user_profiles)
        
        self.delete_profile_btn = QPushButton("Delete")
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        
        button_layout.addWidget(self.new_profile_btn)
        button_layout.addWidget(self.refresh_profiles_btn)
        button_layout.addWidget(self.delete_profile_btn)
        
        layout.addLayout(button_layout)
        
        self.profiles_tab.setLayout(layout)
        
        # Load user profiles
        self.load_user_profiles()
    
    def setup_settings_tab(self):
        layout = QVBoxLayout()
        
        # General settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()
        
        self.start_with_windows_cb = QCheckBox()
        self.minimize_to_tray_cb = QCheckBox()
        
        general_layout.addRow("Start with Windows:", self.start_with_windows_cb)
        general_layout.addRow("Minimize to tray:", self.minimize_to_tray_cb)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Recording settings
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()
        
        self.record_mouse_movement_cb = QCheckBox()
        Let me continue implementing the Auto Click program with PyQt:

{% code path="main.py" type="update" %}
import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTabWidget, 
                            QLineEdit, QGroupBox, QFormLayout, QSpinBox, 
                            QDoubleSpinBox, QCheckBox, QComboBox, QTextEdit,
                            QFileDialog, QMessageBox, QSystemTrayIcon, QMenu,
                            QAction, QListWidget, QListWidgetItem, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QColor, QImage, QPainter, QPen
import pyautogui
import time
import keyboard
import sqlite3
import hashlib
import uuid
import cv2
import numpy as np
from datetime import datetime

# Disable PyAutoGUI fail-safe temporarily (we'll implement our own)
pyautogui.FAILSAFE = False

class PixelDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.setMaximumSize(150, 150)
        self.pixmap = QPixmap(150, 150)
        self.pixmap.fill(Qt.white)
        self.current_pos = QPoint(0, 0)
        self.zoom_factor = 10  # Each pixel becomes 10x10
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_pixel_display)
        self.update_timer.start(100)  # Update every 100ms
        
    def update_pixel_display(self):
        try:
            x, y = pyautogui.position()
            self.current_pos = QPoint(x, y)
            
            # Capture screen area around cursor
            screenshot = pyautogui.screenshot(region=(x-7, y-7, 15, 15))
            img = screenshot.convert('RGB')
            
            # Create a new pixmap
            self.pixmap = QPixmap(150, 150)
            self.pixmap.fill(Qt.white)
            
            # Draw the zoomed pixels
            qp = QPainter(self.pixmap)
            for i in range(15):
                for j in range(15):
                    try:
                        r, g, b = img.getpixel((i, j))
                        qp.fillRect(i*self.zoom_factor, j*self.zoom_factor, 
                                   self.zoom_factor, self.zoom_factor, 
                                   QColor(r, g, b))
                    except:
                        pass
            
            # Draw crosshair at center
            qp.setPen(QPen(Qt.red, 1))
            center = 7 * self.zoom_factor + self.zoom_factor // 2
            qp.drawLine(center, 0, center, 150)
            qp.drawLine(0, center, 150, center)
            qp.end()
            
            self.update()
        except:
            pass
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

class RecordingThread(QThread):
    action_recorded = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.actions = []
        self.start_time = 0
        self.last_position = None
        self.record_movement = True
        self.movement_threshold = 5  # pixels
        self.movement_interval = 0.1  # seconds
        self.last_movement_time = 0
    
    def run(self):
        self.running = True
        self.start_time = time.time()
        self.last_position = pyautogui.position()
        self.last_movement_time = time.time()
        
        while self.running:
            # Record mouse position changes
            current_pos = pyautogui.position()
            current_time = time.time()
            
            # Record significant mouse movements
            if self.record_movement and (current_time - self.last_movement_time) >= self.movement_interval:
                x_diff = abs(current_pos[0] - self.last_position[0])
                y_diff = abs(current_pos[1] - self.last_position[1])
                
                if x_diff > self.movement_threshold or y_diff > self.movement_threshold:
                    action = {
                        'type': 'move',
                        'x': current_pos[0],
                        'y': current_pos[1],
                        'time': current_time - self.start_time
                    }
                    self.action_recorded.emit(action)
                    self.actions.append(action)
                    self.last_position = current_pos
                    self.last_movement_time = current_time
            
            # Small sleep to prevent high CPU usage
            time.sleep(0.01)
    
    def stop(self):
        self.running = False
    
    def add_action(self, action_type, **kwargs):
        action = {
            'type': action_type,
            'time': time.time() - self.start_time,
            **kwargs
        }
        self.actions.append(action)
        self.action_recorded.emit(action)

class PlaybackThread(QThread):
    playback_finished = pyqtSignal()
    action_played = pyqtSignal(int)
    
    def __init__(self, actions, speed_factor=1.0, repeat_count=1, randomize=False, randomize_factor=0.1):
        super().__init__()
        self.actions = actions
        self.speed_factor = speed_factor
        self.repeat_count = repeat_count
        self.running = False
        self.randomize = randomize
        self.randomize_factor = randomize_factor
    
    def run(self):
        self.running = True
        
        for _ in range(self.repeat_count):
            if not self.running:
                break
                
            last_time = 0
            for i, action in enumerate(self.actions):
                if not self.running:
                    break
                
                # Calculate delay
                if i > 0:
                    delay = (action['time'] - last_time) / self.speed_factor
                    
                    # Add randomization if enabled
                    if self.randomize:
                        random_factor = 1.0 + (np.random.random() * 2 - 1) * self.randomize_factor
                        delay *= random_factor
                    
                    time.sleep(max(0, delay))
                
                # Execute action
                self._execute_action(action)
                last_time = action['time']
                
                # Emit signal for UI update
                self.action_played.emit(i)
        
        self.running = False
        self.playback_finished.emit()
    
    def _execute_action(self, action):
        try:
            if action['type'] == 'click':
                if self.randomize:
                    # Add slight randomization to click position
                    rand_x = action['x'] + int((np.random.random() * 2 - 1) * 3)
                    rand_y = action['y'] + int((np.random.random() * 2 - 1) * 3)
                    pyautogui.click(rand_x, rand_y, button=action.get('button', 'left'))
                else:
                    pyautogui.click(action['x'], action['y'], button=action.get('button', 'left'))
                    
            elif action['type'] == 'move':
                pyautogui.moveTo(action['x'], action['y'])
                
            elif action['type'] == 'keypress':
                pyautogui.press(action['key'])
                
            elif action['type'] == 'keydown':
                pyautogui.keyDown(action['key'])
                
            elif action['type'] == 'keyup':
                pyautogui.keyUp(action['key'])
                
            elif action['type'] == 'scroll':
                pyautogui.scroll(action['amount'])
        except Exception as e:
            print(f"Error executing action: {e}")
    
    def stop(self):
        self.running = False

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        try:
            self.conn = sqlite3.connect('autoclick.db')
            cursor = self.conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create scripts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scripts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                description TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create profiles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                hotkey TEXT,
                script_id TEXT,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (script_id) REFERENCES scripts (id)
            )
            ''')
            
            self.conn.commit()
        except Exception as e:
            print(f"Database setup error: {e}")
    
    def create_user(self, username, password):
        try:
            cursor = self.conn.cursor()
            user_id = str(uuid.uuid4())
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                (user_id, username, password_hash)
            )
            self.conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None  # Username already exists
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def authenticate_user(self, username, password):
        try:
            cursor = self.conn.cursor()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                "SELECT id FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def save_script(self, user_id, name, description, content):
        try:
            cursor = self.conn.cursor()
            script_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO scripts (id, user_id, name, description, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (script_id, user_id, name, description, json.dumps(content), now, now)
            )
            self.conn.commit()
            return script_id
        except Exception as e:
            print(f"Error saving script: {e}")
            return None
    
    def update_script(self, script_id, name, description, content):
        try:
            cursor = self.conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "UPDATE scripts SET name = ?, description = ?, content = ?, updated_at = ? WHERE id = ?",
                (name, description, json.dumps(content), now, script_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating script: {e}")
            return False
    
    def get_user_scripts(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, description, created_at FROM scripts WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting scripts: {e}")
            return []
    
    def get_script(self, script_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name, description, content FROM scripts WHERE id = ?",
                (script_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'description': result[1],
                    'content': json.loads(result[2])
                }
            return None
        except Exception as e:
            print(f"Error getting script: {e}")
            return None
    
    def save_profile(self, user_id, name, hotkey, script_id, settings):
        try:
            cursor = self.conn.cursor()
            profile_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO profiles (id, user_id, name, hotkey, script_id, settings, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (profile_id, user_id, name, hotkey, script_id, json.dumps(settings), now, now)
            )
            self.conn.commit()
            return profile_id
        except Exception as e:
            print(f"Error saving profile: {e}")
            return None
    
    def get_user_profiles(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.id, p.name, p.hotkey, s.name 
                FROM profiles p
                JOIN scripts s ON p.script_id = s.id
                WHERE p.user_id = ?
                ORDER BY p.updated_at DESC
                """,
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting profiles: {e}")
            return []
    
    def get_profile(self, profile_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.name, p.hotkey, p.script_id, p.settings, s.content
                FROM profiles p
                JOIN scripts s ON p.script_id = s.id
                WHERE p.id = ?
                """,
                (profile_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'hotkey': result[1],
                    'script_id': result[2],
                    'settings': json.loads(result[3]),
                    'script_content': json.loads(result[4])
                }
            return None
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def close(self):
        if self.conn:
            self.conn.close()

class LoginDialog(QWidget):
    login_successful = pyqtSignal(str, str)  # user_id, username
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Auto Click - Login')
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Logo or title
        title_label = QLabel("Auto Click")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title_label)
        
        # Login form
        form_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        
        form_container = QWidget()
        form_container.setLayout(form_layout)
        layout.addWidget(form_container)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.clicked.connect(self.register)
        
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.register_btn)
        
        button_container = QWidget()
        button_container.setLayout(button_layout)
        layout.addWidget(button_container)
        
        # Status message
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        user_id = self.db_manager.authenticate_user(username, password)
        if user_id:
            self.login_successful.emit(user_id, username)
            self.close()
        else:
            self.status_label.setText("Invalid username or password")
    
    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        if len(password) < 6:
            self.status_label.setText("Password must be at least 6 characters")
            return
        
        user_id = self.db_manager.create_user(username, password)
        if user_id:
            self.status_label.setText("Registration successful! You can now login.")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("Username already exists")

class ImageRecognitionTool:
    def __init__(self):
        self.templates = {}  # Store loaded templates
    
    def load_template(self, name, image_path):
        try:
            template = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if template is None:
                return False
            self.templates[name] = template
            return True
        except Exception as e:
            print(f"Error loading template: {e}")
            return False
    
    def find_on_screen(self, template_name, confidence=0.8):
        if template_name not in self.templates:
            return None
        
        template = self.templates[template_name]
        screenshot = pyautogui.screenshot()
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            # Get the dimensions of the template
            h, w = template.shape[:2]
            # Calculate the center point of the match
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y, max_val)
        
        return None

class AutoClickApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.image_recognition = ImageRecognitionTool()
        self.user_id = None
        self.username = None
        self.recording_thread = None
        self.playback_thread = None
        self.current_actions = []
        self.current_script_id = None
        self.current_script_name = ""
        self.current_script_description = ""
        self.active_profiles = {}  # Store active profiles with their hotkeys
        
        # Show login dialog first
        self.show_login_dialog()
    
    def show_login_dialog(self):
        self.login_dialog = LoginDialog(self.db_manager)
        self.login_dialog.login_successful.connect(self.on_login_successful)
        self.login_dialog.show()
    
    def on_login_successful(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.initUI()
        self.show()
    
    def initUI(self):
        self.setWindowTitle(f'Auto Click - {self.username}')
        self.setGeometry(100, 100, 1000, 700)
        
        # Create main tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.recorder_tab = QWidget()
        self.scripts_tab = QWidget()
        self.profiles_tab = QWidget()
        self.settings_tab = QWidget()
        
        self.setup_recorder_tab()
        self.setup_scripts_tab()
        self.setup_profiles_tab()
        self.setup_settings_tab()
        
        self.tabs.addTab(self.recorder_tab, "Recorder")
        self.tabs.addTab(self.scripts_tab, "Scripts")
        self.tabs.addTab(self.profiles_tab, "Profiles")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        self.setCentralWidget(self.tabs)
        
        # Setup system tray
        self.setup_system_tray()
        
        # Load settings
        self.load_settings()
    
    def setup_recorder_tab(self):
        layout = QVBoxLayout()
        
        # Top section with coordinate display and pixel viewer
        top_layout = QHBoxLayout()
        
        # Coordinate display
        coord_group = QGroupBox("Cursor Position")
        coord_layout = QVBoxLayout()
        
        self.coord_label = QLabel("X: 0, Y: 0")
        self.coord_label.setAlignment(Qt.AlignCenter)
        self.coord_label.setStyleSheet("font-size: 16px;")
        coord_layout.addWidget(self.coord_label)
        
        # Color display
        self.color_label = QLabel("RGB: 0, 0, 0")
        self.color_label.setAlignment(Qt.AlignCenter)
        coord_layout.addWidget(self.color_label)
        
        coord_group.setLayout(coord_layout)
        top_layout.addWidget(coord_group)
        
        # Pixel display
        pixel_group = QGroupBox("Pixel View")
        pixel_layout = QVBoxLayout()
        self.pixel_display = PixelDisplayWidget()
        pixel_layout.addWidget(self.pixel_display)
        pixel_group.setLayout(pixel_layout)
        top_layout.addWidget(pixel_group)
        
        # Recording controls
        controls_group = QGroupBox("Recording Controls")
        controls_layout = QVBoxLayout()
        
        # Script info
        script_info_layout = QFormLayout()
        self.script_name_input = QLineEdit()
        self.script_desc_input = QTextEdit()
        self.script_desc_input.setMaximumHeight(60)
        
        script_info_layout.addRow("Name:", self.script_name_input)
        script_info_layout.addRow("Description:", self.script_desc_input)
        controls_layout.addLayout(script_info_layout)
        
        # Record/Stop buttons
        button_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_recording)
        self.play_btn.setEnabled(False)
        
        button_layout.addWidget(self.record_btn)
        button_layout.addWidget(self.play_btn)
        
        controls_layout.addLayout(button_layout)
        
        # Playback settings
        playback_layout = QFormLayout()
        
        self.speed_input = QDoubleSpinBox()
        self.speed_input.setRange(0.1, 10.0)
        self.speed_input.setValue(1.0)
        self.speed_input.setSingleStep(0.1)
        
        self.repeat_input = QSpinBox()
        self.repeat_input.setRange(1, 9999)
        self.repeat_input.setValue(1)
        
        self.randomize_cb = QCheckBox("Add randomization")
        
        playback_layout.addRow("Speed:", self.speed_input)
        playback_layout.addRow("Repeat:", self.repeat_input)
        playback_layout.addRow("", self.randomize_cb)
        
        controls_layout.addLayout(playback_layout)
        
        # Save/Load buttons
        save_load_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Script")
        self.save_btn.clicked.connect(self.save_script)
        self.save_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_recording)
        
        save_load_layout.addWidget(self.save_btn)
        save_load_layout.addWidget(self.clear_btn)
        
        controls_layout.addLayout(save_load_layout)
        
        controls_group.setLayout(controls_layout)
        top_layout.addWidget(controls_group)
        
        layout.addLayout(top_layout)
        
        # Actions list
        actions_group = QGroupBox("Recorded Actions")
        actions_layout = QVBoxLayout()
        
        self.actions_list = QListWidget()
        actions_layout.addWidget(self.actions_list)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        self.recorder_tab.setLayout(layout)
        
        # Setup timer to update coordinates
        self.coord_timer = QTimer(self)
        self.coord_timer.timeout.connect(self.update_coordinates)
        self.coord_timer.start(100)  # Update every 100ms
        
        # Setup global hotkeys
        keyboard.on_press(self.on_key_press)
    
    def setup_scripts_tab(self):
        layout = QVBoxLayout()
        
        # Scripts list
        self.scripts_list = QListWidget()
        self.scripts_list.itemDoubleClicked.connect(self.load_script)
        layout.addWidget(self.scripts_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_scripts_btn = QPushButton("Refresh")
        self.refresh_scripts_btn.clicked.connect(self.load_user_scripts)
        
        self.delete_script_btn = QPushButton("Delete")
        self.delete_script_btn.clicked.connect(self.delete_script)
        
        self.export_script_btn = QPushButton("Export")
        self.export_script_btn.clicked.connect(self.export_script)
        
        self.import_script_btn = QPushButton("Import")
        self.import_script_btn.clicked.connect(self.import_script)
        
        button_layout.addWidget(self.refresh_scripts_btn)
        button_layout.addWidget(self.delete_script_btn)
        button_layout.addWidget(self.export_script_btn)
        button_layout.addWidget(self.import_script_btn)
        
        layout.addLayout(button_layout)
        
        self.scripts_tab.setLayout(layout)
        
        # Load user scripts
        self.load_user_scripts()
    
    def setup_profiles_tab(self):
        layout = QVBoxLayout()
        
        # Profiles list
        self.profiles_list = QListWidget()
        self.profiles_list.itemDoubleClicked.connect(self.edit_profile)
        layout.addWidget(self.profiles_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.new_profile_btn = QPushButton("New Profile")
        self.new_profile_btn.clicked.connect(self.create_profile)
        
        self.refresh_profiles_btn = QPushButton("Refresh")
        self.refresh_profiles_btn.clicked.connect(self.load_user_profiles)
        
        self.delete_profile_btn = QPushButton("Delete")
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        
        button_layout.addWidget(self.new_profile_btn)
        button_layout.addWidget(self.refresh_profiles_btn)
        button_layout.addWidget(self.delete_profile_btn)
        
        layout.addLayout(button_layout)
        
        self.profiles_tab.setLayout(layout)
        
        # Load user profiles
        self.load_user_profiles()
    
    def setup_settings_tab(self):
        layout = QVBoxLayout()
        
        # General settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()
        
        self.start_with_windows_cb = QCheckBox()
        self.minimize_to_tray_cb = QCheckBox()
        
        general_layout.addRow("Start with Windows:", self.start_with_windows_cb)
        general_layout.addRow("Minimize to tray:", self.minimize_to_tray_cb)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Recording settings
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()
        
        self.record_mouse_movement_cb = QCheckBox()
        self.record_mouse_movement_cb.setChecked(True)
        
        self.movement_threshold_input = QSpinBox()
        self.movement_threshold_input.setRange(1, 50)
        self.movement_threshold_input.setValue(5)
        
        self.movement_interval_input = QDoubleSpinBox()
        self.movement_interval_input.setRange(0.01, 1.0)
        self.movement_interval_input.setValue(0.1)
        self.movement_interval_input.setSingleStep(0.01)
        
        recording_layout.addRow("Record mouse movement:", self.record_mouse_movement_cb)
        recording_```python
        recording_layout.addRow("Movement threshold (px):", self.movement_threshold_input)
        recording_layout.addRow("Movement interval (s):", self.movement_interval_input)
        
        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)
        
        # Hotkeys settings
        hotkeys_group = QGroupBox("Hotkeys")
        hotkeys_layout = QFormLayout()
        
        self.stop_hotkey_input = QLineEdit()
        self.stop_hotkey_input.setText("esc")
        self.stop_hotkey_input.setReadOnly(True)
        
        hotkeys_layout.addRow("Stop playback:", self.stop_hotkey_input)
        
        hotkeys_group.setLayout(hotkeys_layout)
        layout.addWidget(hotkeys_group)
        
        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout()
        
        self.randomize_factor_input = QDoubleSpinBox()
        self.randomize_factor_input.setRange(0.01, 0.5)
        self.randomize_factor_input.setValue(0.1)
        self.randomize_factor_input.setSingleStep(0.01)
        
        advanced_layout.addRow("Randomization factor:", self.randomize_factor_input)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # Save button
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_btn)
        
        self.settings_tab.setLayout(layout)
    
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("input-mouse"))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
    
    def update_coordinates(self):
        try:
            x, y = pyautogui.position()
            self.coord_label.setText(f"X: {x}, Y: {y}")
            
            # Get pixel color
            pixel_color = pyautogui.screenshot().getpixel((x, y))
            self.color_label.setText(f"RGB: {pixel_color[0]}, {pixel_color[1]}, {pixel_color[2]}")
        except:
            pass
    
    def on_key_press(self, event):
        # Check if we're recording
        if self.recording_thread and self.recording_thread.running:
            # Record key press
            key_name = event.name
            if len(key_name) == 1 or key_name in ['space', 'enter', 'tab', 'backspace', 'esc']:
                self.recording_thread.add_action('keypress', key=key_name)
        
        # Check for stop hotkey (ESC)
        if event.name == 'esc' and self.playback_thread and self.playback_thread.running:
            self.stop_playback()
        
        # Check for profile hotkeys
        for profile_id, profile_data in self.active_profiles.items():
            if event.name == profile_data['hotkey']:
                self.run_profile(profile_id)
    
    def toggle_recording(self):
        if self.recording_thread and self.recording_thread.running:
            # Stop recording
            self.recording_thread.stop()
            self.recording_thread.wait()
            self.record_btn.setText("Start Recording")
            self.play_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
        else:
            # Start recording
            self.recording_thread = RecordingThread()
            self.recording_thread.action_recorded.connect(self.on_action_recorded)
            
            # Apply settings
            self.recording_thread.record_movement = self.record_mouse_movement_cb.isChecked()
            self.recording_thread.movement_threshold = self.movement_threshold_input.value()
            self.recording_thread.movement_interval = self.movement_interval_input.value()
            
            # Clear previous recording
            self.current_actions = []
            self.actions_list.clear()
            
            # Start the thread
            self.recording_thread.start()
            self.record_btn.setText("Stop Recording")
            self.play_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            
            # Setup mouse listener
            self.setup_mouse_listener()
    
    def setup_mouse_listener(self):
        # Use PyAutoGUI's mouseDown and mouseUp events
        def on_mouse_click(x, y, button, pressed):
            if not self.recording_thread or not self.recording_thread.running:
                return
            
            if pressed:
                self.recording_thread.add_action('click', x=x, y=y, button=button)
        
        # Use pynput for mouse events
        from pynput import mouse
        self.mouse_listener = mouse.Listener(on_click=on_mouse_click)
        self.mouse_listener.start()
    
    def on_action_recorded(self, action):
        # Add action to the list widget
        action_str = self.format_action(action)
        self.actions_list.addItem(action_str)
        self.actions_list.scrollToBottom()
        
        # Add to current actions
        self.current_actions.append(action)
    
    def format_action(self, action):
        if action['type'] == 'click':
            return f"[{action['time']:.2f}s] Click at ({action['x']}, {action['y']})"
        elif action['type'] == 'move':
            return f"[{action['time']:.2f}s] Move to ({action['x']}, {action['y']})"
        elif action['type'] == 'keypress':
            return f"[{action['time']:.2f}s] Press key '{action['key']}'"
        elif action['type'] == 'scroll':
            return f"[{action['time']:.2f}s] Scroll {action['amount']}"
        return f"[{action['time']:.2f}s] {action['type']}"
    
    def play_recording(self):
        if not self.current_actions:
            QMessageBox.warning(self, "Warning", "No actions to play.")
            return
        
        # Disable UI elements
        self.record_btn.setEnabled(False)
        self.play_btn.setText("Stop")
        self.play_btn.clicked.disconnect()
        self.play_btn.clicked.connect(self.stop_playback)
        
        # Create and start playback thread
        self.playback_thread = PlaybackThread(
            self.current_actions,
            self.speed_input.value(),
            self.repeat_input.value(),
            self.randomize_cb.isChecked(),
            self.randomize_factor_input.value()
        )
        self.playback_thread.playback_finished.connect(self.on_playback_finished)
        self.playback_thread.action_played.connect(self.on_action_played)
        self.playback_thread.start()
    
    def stop_playback(self):
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
            self.on_playback_finished()
    
    def on_playback_finished(self):
        # Re-enable UI elements
        self.record_btn.setEnabled(True)
        self.play_btn.setText("Play")
        self.play_btn.clicked.disconnect()
        self.play_btn.clicked.connect(self.play_recording)
        
        # Clear selection in actions list
        self.actions_list.clearSelection()
    
    def on_action_played(self, index):
        # Highlight the current action in the list
        self.actions_list.setCurrentRow(index)
    
    def clear_recording(self):
        self.current_actions = []
        self.actions_list.clear()
        self.current_script_id = None
        self.current_script_name = ""
        self.current_script_description = ""
        self.script_name_input.clear()
        self.script_desc_input.clear()
        self.play_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
    
    def save_script(self):
        name = self.script_name_input.text().strip()
        description = self.script_desc_input.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the script.")
            return
        
        if not self.current_actions:
            QMessageBox.warning(self, "Warning", "No actions to save.")
            return
        
        if self.current_script_id:
            # Update existing script
            success = self.db_manager.update_script(
                self.current_script_id,
                name,
                description,
                self.current_actions
            )
            if success:
                QMessageBox.information(self, "Success", "Script updated successfully.")
                self.load_user_scripts()
            else:
                QMessageBox.critical(self, "Error", "Failed to update script.")
        else:
            # Create new script
            script_id = self.db_manager.save_script(
                self.user_id,
                name,
                description,
                self.current_actions
            )
            if script_id:
                self.current_script_id = script_id
                QMessageBox.information(self, "Success", "Script saved successfully.")
                self.load_user_scripts()
            else:
                QMessageBox.critical(self, "Error", "Failed to save script.")
    
    def load_user_scripts(self):
        self.scripts_list.clear()
        scripts = self.db_manager.get_user_scripts(self.user_id)
        
        for script_id, name, description, created_at in scripts:
            item = QListWidgetItem(f"{name}")
            item.setData(Qt.UserRole, script_id)
            item.setToolTip(description)
            self.scripts_list.addItem(item)
    
    def load_script(self, item):
        script_id = item.data(Qt.UserRole)
        script = self.db_manager.get_script(script_id)
        
        if script:
            self.current_script_id = script_id
            self.current_script_name = script['name']
            self.current_script_description = script['description']
            self.current_actions = script['content']
            
            # Update UI
            self.script_name_input.setText(self.current_script_name)
            self.script_desc_input.setText(self.current_script_description)
            
            # Update actions list
            self.actions_list.clear()
            for action in self.current_actions:
                action_str = self.format_action(action)
                self.actions_list.addItem(action_str)
            
            # Enable play button
            self.play_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            
            # Switch to recorder tab
            self.tabs.setCurrentWidget(self.recorder_tab)
    
    def delete_script(self):
        selected_items = self.scripts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a script to delete.")
            return
        
        script_id = selected_items[0].data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            "Are you sure you want to delete this script?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Delete script from database
            cursor = self.db_manager.conn.cursor()
            cursor.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
            self.db_manager.conn.commit()
            
            # Refresh list
            self.load_user_scripts()
            
            # Clear current script if it was the deleted one
            if self.current_script_id == script_id:
                self.clear_recording()
    
    def export_script(self):
        selected_items = self.scripts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a script to export.")
            return
        
        script_id = selected_items[0].data(Qt.UserRole)
        script = self.db_manager.get_script(script_id)
        
        if script:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Script",
                f"{script['name']}.json",
                "JSON Files (*.json)"
            )
            
            if file_path:
                try:
                    with open(file_path, 'w') as f:
                        json.dump({
                            'name': script['name'],
                            'description': script['description'],
                            'actions': script['content'],
                            'version': '1.0'
                        }, f, indent=2)
                    
                    QMessageBox.information(self, "Success", "Script exported successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to export script: {e}")
    
    def import_script(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Script",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Validate script format
                if not all(key in data for key in ['name', 'actions']):
                    raise ValueError("Invalid script format")
                
                # Save imported script
                script_id = self.db_manager.save_script(
                    self.user_id,
                    data['name'],
                    data.get('description', ''),
                    data['actions']
                )
                
                if script_id:
                    QMessageBox.information(self, "Success", "Script imported successfully.")
                    self.load_user_scripts()
                else:
                    QMessageBox.critical(self, "Error", "Failed to import script.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import script: {e}")
    
    def load_user_profiles(self):
        self.profiles_list.clear()
        profiles = self.db_manager.get_user_profiles(self.user_id)
        
        for profile_id, name, hotkey, script_name in profiles:
            item = QListWidgetItem(f"{name} ({hotkey}) - {script_name}")
            item.setData(Qt.UserRole, profile_id)
            self.profiles_list.addItem(item)
    
    def create_profile(self):
        # Get scripts for selection
        scripts = self.db_manager.get_user_scripts(self.user_id)
        if not scripts:
            QMessageBox.warning(self, "Warning", "You need to create scripts first.")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Profile")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        name_input = QLineEdit()
        
        hotkey_input = QLineEdit()
        hotkey_input.setPlaceholderText("Press a key...")
        hotkey_input.setReadOnly(True)
        
        # Capture key press for hotkey
        def on_key_press_event(event):
            key = event.text()
            if key and key.isalnum():
                hotkey_input.setText(key.lower())
            elif event.key() == Qt.Key_F1:
                hotkey_input.setText("f1")
            elif event.key() == Qt.Key_F2:
                hotkey_input.setText("f2")
            # Add more function keys as needed
        
        hotkey_input.keyPressEvent = on_key_press_event
        
        script_combo = QComboBox()
        for script_id, script_name, _, _ in scripts:
            script_combo.addItem(script_name, script_id)
        
        form_layout.addRow("Name:", name_input)
        form_layout.addRow("Hotkey:", hotkey_input)
        form_layout.addRow("Script:", script_combo)
        
        layout.addLayout(form_layout)
        
        # Settings
        settings_group = QGroupBox("Playback Settings")
        settings_layout = QFormLayout()
        
        speed_input = QDoubleSpinBox()
        speed_input.setRange(0.1, 10.0)
        speed_input.setValue(1.0)
        speed_input.setSingleStep(0.1)
        
        repeat_input = QSpinBox()
        repeat_input.setRange(1, 9999)
        repeat_input.setValue(1)
        
        randomize_cb = QCheckBox()
        
        settings_layout.addRow("Speed:", speed_input)
        settings_layout.addRow("Repeat:", repeat_input)
        settings_layout.addRow("Randomize:", randomize_cb)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            profile_name = name_input.text().strip()
            hotkey = hotkey_input.text().strip()
            script_id = script_combo.currentData()
            
            if not profile_name or not hotkey:
                QMessageBox.warning(self, "Warning", "Please enter both name and hotkey.")
                return
            
            # Save settings
            settings = {
                'speed': speed_input.value(),
                'repeat': repeat_input.value(),
                'randomize': randomize_cb.isChecked()
            }
            
            # Save profile
            profile_id = self.db_manager.save_profile(
                self.user_id,
                profile_name,
                hotkey,
                script_id,
                settings
            )
            
            if profile_id:
                QMessageBox.information(self, "Success", "Profile created successfully.")
                self.load_user_profiles()
                
                # Add to active profiles
                self.active_profiles[profile_id] = {
                    'hotkey': hotkey,
                    'script_id': script_id,
                    'settings': settings
                }
            else:
                QMessageBox.critical(self, "Error", "Failed to create profile.")
    
    def edit_profile(self, item):
        profile_id = item.data(Qt.UserRole)
        profile = self.db_manager.get_profile(profile_id)
        
        if profile:
            # Load the script
            self.current_script_id = profile['script_id']
            script = self.db_manager.get_script(profile['script_id'])
            
            if script:
                self.current_script_name = script['name']
                self.current_script_description = script['description']
                self.current_actions = script['content']
                
                # Update UI
                self.script_name_input.setText(self.current_script_name)
                self.script_desc_input.setText(self.current_script_description)
                
                # Update actions list
                self.actions_list.clear()
                for action in self.current_actions:
                    action_str = self.format_action(action)
                    self.actions_list.addItem(action_str)
                
                # Set playback settings
                self.speed_input.setValue(profile['settings'].get('speed', 1.0))
                self.repeat_input.setValue(profile['settings'].get('repeat', 1))
                self.randomize_cb.setChecked(profile['settings'].get('randomize', False))
                
                # Enable play button
                self.play_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
                
                # Switch to recorder tab
                self.tabs.setCurrentWidget(self.recorder_tab)
    
    def delete_profile(self):
        selected_items = self.profiles_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a profile to delete.")
            return
        
        profile_id = selected_items[0].data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            "Are you sure you want to delete this profile?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Delete profile from database
            cursor = self.db_manager.conn.cursor()
            cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            self.db_manager.conn.commit()
            
            # Remove from active profiles
            if profile_id in self.active_profiles:
                del self.active_profiles[profile_id]
            
            # Refresh list
            self.load_user_profiles()
    
    def run_profile(self, profile_id):
        profile = self.db_manager.get_profile(profile_id)
        
        if profile and 'script_content' in profile:
            # Create and start playback thread
            self.playback_thread = PlaybackThread(
                profile['script_content'],
                profile['settings'].get('speed', 1.0),
                profile['settings'].get('repeat', 1),
                profile['settings'].get('randomize', False),
                self.randomize_factor_input.value()
            )
            self.playback_thread.start()
    
    def load_settings(self):
        settings = QSettings("AutoClick", "AutoClickApp")
        
        # General settings
        self.start_with_windows_cb.setChecked(settings.value("start_with_windows", False, type=bool))
        self.minimize_to_tray_cb.setChecked(settings.value("minimize_to_tray", True, type=bool))
        
        # Recording settings
        self.record_mouse_movement_cb.setChecked(settings.value("record_mouse_movement", True, type=bool))
        self.movement_threshold_input.setValue(settings.value("movement_threshold", 5, type=int))
        self.movement_interval_input.setValue(settings.value("movement_interval", 0.1, type=float))
        
        # Advanced settings
        self.randomize_factor_input.setValue(settings.value("randomize_factor", 0.1, type=float))
        
        # Load active profiles
        profiles = self.db_manager.get_user_profiles(self.user_id)
        for profile_id, _, hotkey, _ in profiles:
            profile = self.db_manager.get_profile(profile_id)
            if profile:
                self.active_profiles[profile_id] = {
                    'hotkey': hotkey,
                    'script_id': profile['script_id'],
                    'settings': profile['settings']
                }
    
    def save_settings(self):
        settings = QSettings("AutoClick", "AutoClickApp")
        
        # General settings
        settings.setValue("start_with_windows", self.start_with_windows_cb.isChecked())
        settings.setValue("minimize_to_tray", self.minimize_to_tray_cb.isChecked())
        
        # Recording settings
        settings.setValue("record_mouse_movement", self.record_mouse_movement_cb.isChecked())
        settings.setValue("movement_threshold", self.movement_threshold_input.value())
        settings.setValue("movement_interval", self.movement_interval_input.value())
        
        # Advanced settings
        settings.setValue("randomize_factor", self.randomize_factor_input.value())
        
        # Apply startup settings
        if self.start_with_windows_cb.isChecked():
            self.set_autostart(True)
        else:
            self.set_autostart(False)
        
        QMessageBox.information(self, "Success", "Settings saved successfully.")
    
    def set_autostart(self, enable):
        if sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            
            if enable:
                winreg.SetValueEx(
                    key,
                    "AutoClick",
                    0,
                    winreg.REG_SZ,
                    sys.argv[0]
                )
            else:
                try:
                    winreg.DeleteValue(key, "AutoClick")
                except:
                    pass
    
    def closeEvent(self, event):
        if self.minimize_to_tray_cb.isChecked():
            event.ignore()
            self.hide()
        else:
            self.quit_application()
    
    def quit_application(self):
        # Stop any running threads
        if self.recording_thread and self.recording_thread.running:
            self.recording_thread.stop()
            self.recording_thread.wait()
        
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
        
        # Close database connection
        self.db_manager.close()
        
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for consistent look
    
    # Set application icon
    app_icon = QIcon.fromTheme("input-mouse")
    app.setWindowIcon(app_icon)
    
    window = AutoClickApp()
    sys.exit(app.exec_())