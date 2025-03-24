"""
Profiles tab for the Auto Click application.
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QListWidget, QListWidgetItem, QDialog, QFormLayout,
                            QLineEdit, QComboBox, QGroupBox, QDoubleSpinBox,
                            QSpinBox, QCheckBox, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt

class ProfilesTab(QWidget):
    def __init__(self, db_manager, user_id, permissions, recorder_tab):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.permissions = permissions
        self.recorder_tab = recorder_tab  # Reference to recorder tab for loading scripts
        self.active_profiles = {}  # Store active profiles with their hotkeys
        
        self.initUI()
        self.load_user_profiles()
    
    def initUI(self):
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
        
        self.setLayout(layout)
        
        # Apply permissions
        self.apply_permissions()
    
    def apply_permissions(self):
        # Profiles tab permissions
        can_create_profiles = 'create_profiles' in self.permissions
        
        self.new_profile_btn.setEnabled(can_create_profiles)
        self.delete_profile_btn.setEnabled(can_create_profiles)
    
    def load_user_profiles(self):
        self.profiles_list.clear()
        profiles = self.db_manager.get_user_profiles(self.user_id)
        
        for profile_id, name, hotkey, script_name in profiles:
            item = QListWidgetItem(f"{name} ({hotkey}) - {script_name}")
            item.setData(Qt.UserRole, profile_id)
            self.profiles_list.addItem(item)
            
            # Add to active profiles
            profile = self.db_manager.get_profile(profile_id)
            if profile:
                self.active_profiles[profile_id] = {
                    'hotkey': hotkey,
                    'script_id': profile['script_id'],
                    'settings': profile['settings']
                }
    
    def create_profile(self):
        # Check permission
        if 'create_profiles' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to create profiles.")
            return
            
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
            else:
                QMessageBox.critical(self, "Error", "Failed to create profile.")
    
    def edit_profile(self, item):
        # Check permission
        if 'create_profiles' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit profiles.")
            return
            
        profile_id = item.data(Qt.UserRole)
        profile = self.db_manager.get_profile(profile_id)
        
        if profile:
            # Load the script into recorder tab
            script = self.db_manager.get_script(profile['script_id'])
            if script:
                self.recorder_tab.load_script(
                    profile['script_id'],
                    script['name'],
                    script.get('description', ''),
                    script['content']
                )
                
                # Set playback settings
                self.recorder_tab.speed_input.setValue(profile['settings'].get('speed', 1.0))
                self.recorder_tab.repeat_input.setValue(profile['settings'].get('repeat', 1))
                self.recorder_tab.randomize_cb.setChecked(profile['settings'].get('randomize', False))
                
                # Switch to recorder tab
                self.parent().parent().setCurrentIndex(0)  # Assumes recorder tab is at index 0
    
    def delete_profile(self):
        # Check permission
        if 'create_profiles' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete profiles.")
            return
            
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
    
    def get_active_profiles(self):
        return self.active_profiles