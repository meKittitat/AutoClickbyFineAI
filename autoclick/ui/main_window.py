"""
Main window for the Auto Click application.
"""
import keyboard
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QSystemTrayIcon, 
                            QMenu, QAction, QMessageBox, QWidget, QVBoxLayout,
                            QLabel, QPushButton, QApplication)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSettings

from autoclick.config import USER_ROLES, APP_NAME, APP_ICON
from autoclick.ui.login_dialog import LoginDialog
from autoclick.ui.user_management import UserManagementDialog
from autoclick.ui.recorder_tab import RecorderTab
from autoclick.ui.scripts_tab import ScriptsTab
from autoclick.ui.profiles_tab import ProfilesTab
from autoclick.ui.settings_tab import SettingsTab
from autoclick.core.playback import PlaybackThread

class MainWindow(QMainWindow):
    def __init__(self, db_manager, image_recognition):
        super().__init__()
        self.db_manager = db_manager
        self.image_recognition = image_recognition
        self.user_id = None
        self.username = None
        self.role = None
        self.permissions = []
        self.playback_thread = None
        
        # Show login dialog first
        self.show_login_dialog()
    
    def show_login_dialog(self):
        self.login_dialog = LoginDialog(self.db_manager)
        self.login_dialog.login_successful.connect(self.on_login_successful)
        self.login_dialog.show()
    
    def on_login_successful(self, user_id, username, role, permissions):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions
        self.initUI()
        self.show()
    
    def initUI(self):
        self.setWindowTitle(f'{APP_NAME} - {self.username} ({USER_ROLES.get(self.role, self.role)})')
        self.setGeometry(100, 100, 1000, 700)
        
        # Create main tab widget
        self.tabs = QTabWidget()
        
        # Create recorder tab first (needed by other tabs)
        self.recorder_tab = RecorderTab(self.db_manager, self.user_id, self.permissions)
        
        # Create other tabs
        self.scripts_tab = ScriptsTab(self.db_manager, self.user_id, self.permissions, self.recorder_tab)
        self.profiles_tab = ProfilesTab(self.db_manager, self.user_id, self.permissions, self.recorder_tab)
        self.settings_tab = SettingsTab(self.permissions)
        
        # Add tabs to widget
        self.tabs.addTab(self.recorder_tab, "Recorder")
        self.tabs.addTab(self.scripts_tab, "Scripts")
        self.tabs.addTab(self.profiles_tab, "Profiles")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Add user management tab for admins
        if 'manage_users' in self.permissions:
            self.users_tab = QWidget()
            self.setup_users_tab()
            self.tabs.addTab(self.users_tab, "User Management")
        
        self.setCentralWidget(self.tabs)
        
        # Setup system tray
        self.setup_system_tray()
        
        # Setup global hotkeys
        keyboard.on_press(self.on_key_press)
        
        # Load settings
        self.load_settings()
    
    def setup_users_tab(self):
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Manage users and their permissions. Click 'Manage Users' to open the user management dialog.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Open user management button
        manage_users_btn = QPushButton("Manage Users")
        manage_users_btn.clicked.connect(self.open_user_management)
        layout.addWidget(manage_users_btn)
        
        # Add spacer
        layout.addStretch()
        
        self.users_tab.setLayout(layout)
    
    def open_user_management(self):
        dialog = UserManagementDialog(self.db_manager, self)
        dialog.exec_()
    
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme(APP_ICON))
        
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
    
    def load_settings(self):
        # Load hotkeys
        settings = QSettings("AutoClick", "AutoClickApp")
        self.start_record_hotkey = settings.value("start_record_hotkey", "f9")
        self.stop_record_hotkey = settings.value("stop_record_hotkey", "f10")
        self.stop_playback_hotkey = settings.value("stop_playback_hotkey", "esc")
    
    def on_key_press(self, event):
        # Check for recording hotkeys
        if event.name == self.start_record_hotkey and 'record_macros' in self.permissions:
            # Switch to recorder tab and start recording
            self.tabs.setCurrentWidget(self.recorder_tab)
            if not self.recorder_tab.recording_thread or not self.recorder_tab.recording_thread.running:
                self.recorder_tab.toggle_recording()
        
        elif event.name == self.stop_record_hotkey and 'record_macros' in self.permissions:
            # Stop recording if active
            if self.recorder_tab.recording_thread and self.recorder_tab.recording_thread.running:
                self.recorder_tab.toggle_recording()
        
        # Check for stop playback hotkey
        elif event.name == self.stop_playback_hotkey:
            if self.playback_thread and self.playback_thread.running:
                self.stop_playback()
            elif self.recorder_tab.playback_thread and self.recorder_tab.playback_thread.running:
                self.recorder_tab.stop_playback()
        
        # Check for profile hotkeys
        active_profiles = self.profiles_tab.get_active_profiles()
        for profile_id, profile_data in active_profiles.items():
            if event.name == profile_data['hotkey']:
                self.run_profile(profile_id)
    
    def run_profile(self, profile_id):
        # Check permission
        if 'play_macros' not in self.permissions:
            return  # Silently fail when triggered by hotkey
            
        profile = self.db_manager.get_profile(profile_id)
        
        if profile and 'script_content' in profile:
            # Create and start playback thread
            self.playback_thread = PlaybackThread(
                profile['script_content'],
                profile['settings'].get('speed', 1.0),
                profile['settings'].get('repeat', 1),
                profile['settings'].get('randomize', False),
                self.settings_tab.get_randomize_factor()
            )
            self.playback_thread.start()
    
    def stop_playback(self):
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
    
    def closeEvent(self, event):
        settings = QSettings("AutoClick", "AutoClickApp")
        if settings.value("minimize_to_tray", True, type=bool):
            event.ignore()
            self.hide()
        else:
            self.quit_application()
    
    def quit_application(self):
        # Stop any running threads
        if self.recorder_tab.recording_thread and self.recorder_tab.recording_thread.running:
            self.recorder_tab.recording_thread.stop()
            self.recorder_tab.recording_thread.wait()
        
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
        
        # Close database connection
        self.db_manager.close()
        
        QApplication.quit()