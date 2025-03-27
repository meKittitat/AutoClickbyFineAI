"""
Main window for the Auto Click application.
"""
import keyboard
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QSystemTrayIcon, 
                            QMenu, QAction, QMessageBox, QWidget, QVBoxLayout,
                            QLabel, QPushButton, QApplication, QToolBar, QStatusBar)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSettings, QTimer, QTime

from autoclick.config import USER_ROLES, APP_NAME, APP_ICON, APP_VERSION, DEFAULT_ROLE_PERMISSIONS
from autoclick.ui.login_dialog import LoginDialog
from autoclick.ui.user_management import UserManagementDialog, RoleManagementDialog
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
        self.time_remaining = 0  # Time remaining in minutes
        self.lifetime_pass = False
        self.is_admin = False
        self.preview_mode = False
        self.preview_user_id = None
        
        # Show login dialog first
        self.show_login_dialog()
    
    def show_login_dialog(self):
        self.login_dialog = LoginDialog(self.db_manager)
        self.login_dialog.login_successful.connect(self.on_login_successful)
        self.login_dialog.show()
    
    def on_login_successful(self, user_id, username, role, permissions, time_remaining, lifetime_pass):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions
        self.time_remaining = time_remaining
        self.lifetime_pass = lifetime_pass
        self.is_admin = 'manage_users' in permissions
        
        self.initUI()
        self.show()
        
        # Start time tracking if not admin and not lifetime pass
        if not self.is_admin and not self.lifetime_pass:
            self.start_time_tracking()
    
    def initUI(self):
        self.setWindowTitle(f'{APP_NAME} v{APP_VERSION} - {self.username} ({USER_ROLES.get(self.role, self.role)})')
        self.setGeometry(100, 100, 1000, 700)
        
        # Create toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # Add logout button
        self.logout_action = QAction(QIcon.fromTheme("system-log-out"), "Logout", self)
        self.logout_action.triggered.connect(self.logout)
        self.toolbar.addAction(self.logout_action)
        
        # Add exit preview button (hidden by default)
        self.exit_preview_action = QAction(QIcon.fromTheme("view-restore"), "Exit Preview", self)
        self.exit_preview_action.triggered.connect(self.exit_preview_mode)
        self.exit_preview_action.setVisible(False)
        self.toolbar.addAction(self.exit_preview_action)
        
        # Add time remaining label if not admin
        if not self.is_admin:
            self.toolbar.addSeparator()
            self.time_label = QLabel()
            self.update_time_display()
            self.toolbar.addWidget(self.time_label)
        
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
        
        # Add role management tab for admins with role management permission
        if 'manage_roles' in self.permissions:
            self.roles_tab = QWidget()
            self.setup_roles_tab()
            self.tabs.addTab(self.roles_tab, "Role Management")
        
        self.setCentralWidget(self.tabs)
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
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
    
    def setup_roles_tab(self):
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Manage roles and their permissions. Click 'Manage Roles' to open the role management dialog.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Open role management button
        manage_roles_btn = QPushButton("Manage Roles")
        manage_roles_btn.clicked.connect(self.open_role_management)
        layout.addWidget(manage_roles_btn)
        
        # Add spacer
        layout.addStretch()
        
        self.roles_tab.setLayout(layout)
    
    def open_user_management(self):
        dialog = UserManagementDialog(self.db_manager, self)
        dialog.preview_user.connect(self.preview_user_role)
        dialog.exec_()
    
    def open_role_management(self):
        dialog = RoleManagementDialog(self.db_manager, self)
        dialog.exec_()
    
    def preview_user_role(self, user_id, username, role, permissions, time_remaining, lifetime_pass):
        """Enter preview mode to see the application as another user"""
        if self.preview_mode:
            return  # Already in preview mode
        
        # Save current user info
        self.preview_mode = True
        self.preview_user_id = self.user_id
        self.preview_username = self.username
        self.preview_role = self.role
        self.preview_permissions = self.permissions
        self.preview_time_remaining = self.time_remaining
        self.preview_lifetime_pass = self.lifetime_pass
        
        # Switch to previewed user
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions
        self.time_remaining = time_remaining
        self.lifetime_pass = lifetime_pass
        self.is_admin = 'manage_users' in permissions
        
        # Update UI
        self.setWindowTitle(f'{APP_NAME} v{APP_VERSION} - PREVIEW MODE: {username} ({USER_ROLES.get(role, role)})')
        
        # Show exit preview button
        self.exit_preview_action.setVisible(True)
        
        # Recreate tabs with new permissions
        self.recreate_tabs()
        
        # Show time remaining if not admin
        if not self.is_admin:
            if not hasattr(self, 'time_label'):
                self.toolbar.addSeparator()
                self.time_label = QLabel()
                self.toolbar.addWidget(self.time_label)
            self.update_time_display()
            self.time_label.setVisible(True)
        elif hasattr(self, 'time_label'):
            self.time_label.setVisible(False)
    
    def exit_preview_mode(self):
        """Exit preview mode and return to admin view"""
        if not self.preview_mode:
            return
        
        # Restore original user info
        self.user_id = self.preview_user_id
        self.username = self.preview_username
        self.role = self.preview_role
        self.permissions = self.preview_permissions
        self.time_remaining = self.preview_time_remaining
        self.lifetime_pass = self.preview_lifetime_pass
        self.is_admin = 'manage_users' in self.permissions
        
        # Reset preview flags
        self.preview_mode = False
        self.preview_user_id = None
        
        # Update UI
        self.setWindowTitle(f'{APP_NAME} v{APP_VERSION} - {self.username} ({USER_ROLES.get(self.role, self.role)})')
        
        # Hide exit preview button
        self.exit_preview_action.setVisible(False)
        
        # Recreate tabs with original permissions
        self.recreate_tabs()
        
        # Hide time label for admin
        if self.is_admin and hasattr(self, 'time_label'):
            self.time_label.setVisible(False)
    
    def recreate_tabs(self):
        """Recreate all tabs with current permissions"""
        # Remember current tab index
        current_index = self.tabs.currentIndex()
        
        # Remove all tabs
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        
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
        
        # Add role management tab for admins with role management permission
        if 'manage_roles' in self.permissions:
            self.roles_tab = QWidget()
            self.setup_roles_tab()
            self.tabs.addTab(self.roles_tab, "Role Management")
        
        # Restore tab index if possible
        if current_index < self.tabs.count():
            self.tabs.setCurrentIndex(current_index)
    
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
        self.capture_position_hotkey = settings.value("capture_position_hotkey", "f11")
    
    def start_time_tracking(self):
        """Start tracking time for non-admin users"""
        if self.is_admin or self.lifetime_pass:
            return
        
        # Create timer to update time every minute
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(60000)  # Update every minute
    
    def update_time(self):
        """Update remaining time and check if time has expired"""
        if self.is_admin or self.lifetime_pass:
            return
        
        # Decrement time
        if self.time_remaining > 0:
            self.db_manager.decrement_user_time(self.user_id, 1)
            self.time_remaining -= 1
            self.update_time_display()
        
        # Check if time has expired
        if self.time_remaining <= 0:
            self.time_expired()
    
    def update_time_display(self):
        """Update the time display in the toolbar"""
        if self.is_admin:
            return
        
        if self.lifetime_pass:
            self.time_label.setText("Lifetime Pass")
            return
        
        hours = self.time_remaining // 60
        minutes = self.time_remaining % 60
        self.time_label.setText(f"Time Remaining: {hours:02d}:{minutes:02d}")
    
    def time_expired(self):
        """Handle time expiration by downgrading to free user"""
        # Stop timer
        if hasattr(self, 'time_timer'):
            self.time_timer.stop()
        
        # Show message
        QMessageBox.warning(self, "Time Expired", 
                           "Your session time has expired. You have been downgraded to a free user.")
        
        # Downgrade to free user permissions
        self.permissions = DEFAULT_ROLE_PERMISSIONS['free']
        
        # Update UI
        self.recreate_tabs()
    
    def logout(self):
        """Log out the current user and show login dialog"""
        reply = QMessageBox.question(self, "Confirm Logout", 
                                    "Are you sure you want to log out?",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Stop time tracking
            if hasattr(self, 'time_timer') and self.time_timer.isActive():
                self.time_timer.stop()
            
            # Close current window
            self.close()
            
            # Show login dialog
            self.show_login_dialog()
    
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
        
        # Check for capture position hotkey in hotkey mode
        elif event.name == self.capture_position_hotkey and 'record_macros' in self.permissions:
            if (self.recorder_tab.recording_thread and 
                self.recorder_tab.recording_thread.running and 
                not self.recorder_tab.continuous_mode):
                self.recorder_tab.capture_position()
        
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
        
        if profile and 'scripts' in profile and profile['scripts']:
            # Execute each script in the profile
            self.execute_profile_scripts(profile)
    
    def execute_profile_scripts(self, profile):
        """Execute all scripts in a profile in order"""
        # Sort scripts by execution order
        scripts = sorted(profile['scripts'], key=lambda s: s['execution_order'])
        
        # Execute first script
        self.current_profile_scripts = scripts
        self.current_profile_script_index = 0
        self.execute_next_profile_script()
    
    def execute_next_profile_script(self):
        """Execute the next script in the profile"""
        if not hasattr(self, 'current_profile_scripts') or not self.current_profile_scripts:
            return
        
        if self.current_profile_script_index >= len(self.current_profile_scripts):
            # All scripts executed
            self.current_profile_scripts = None
            self.current_profile_script_index = 0
            return
        
        # Get current script
        script = self.current_profile_scripts[self.current_profile_script_index]
        
        # Create and start playback thread
        self.playback_thread = PlaybackThread(
            script['content'],
            script.get('speed', 1.0),
            script.get('repeat', 1)
        )
        self.playback_thread.playback_finished.connect(self.on_profile_script_finished)
        self.playback_thread.start()
        
        # Update status bar
        self.statusBar.showMessage(f"Executing script: {script['name']}")
    
    def on_profile_script_finished(self):
        """Handle completion of a script in a profile"""
        # Check if there's an execution time for the current script
        if hasattr(self, 'current_profile_scripts') and self.current_profile_scripts:
            script = self.current_profile_scripts[self.current_profile_script_index]
            execution_time = script.get('execution_time', 0)
            
            if execution_time > 0:
                # Wait for specified time before executing next script
                self.statusBar.showMessage(f"Waiting {execution_time} ms before next script...")
                QTimer.singleShot(execution_time, self.advance_profile_script)
            else:
                # Execute next script immediately
                self.advance_profile_script()
    
    def advance_profile_script(self):
        """Advance to the next script in the profile"""
        if hasattr(self, 'current_profile_scripts') and self.current_profile_scripts:
            self.current_profile_script_index += 1
            self.execute_next_profile_script()
    
    def stop_playback(self):
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
            self.statusBar.showMessage("Playback stopped", 3000)
    
    def closeEvent(self, event):
        settings = QSettings("AutoClick", "AutoClickApp")
        if settings.value("minimize_to_tray", True, type=bool):
            event.ignore()
            self.hide()
        else:
            self.quit_application()
    
    def quit_application(self):
        # Stop any running threads
        if hasattr(self, 'recorder_tab') and self.recorder_tab.recording_thread and self.recorder_tab.recording_thread.running:
            self.recorder_tab.recording_thread.stop()
            self.recorder_tab.recording_thread.wait()
        
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
        
        # Close database connection
        self.db_manager.close()
        
        QApplication.quit()