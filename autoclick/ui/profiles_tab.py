"""
Profiles tab for the Auto Click application.
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QListWidget, QListWidgetItem, QDialog, QFormLayout,
                            QLineEdit, QComboBox, QGroupBox, QDoubleSpinBox,
                            QSpinBox, QCheckBox, QDialogButtonBox, QMessageBox,
                            QTableWidget, QTableWidgetItem, QHeaderView, QLabel)
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
        
        for profile_id, name, hotkey, updated_at in profiles:
            item = QListWidgetItem(f"{name} ({hotkey})")
            item.setData(Qt.UserRole, profile_id)
            self.profiles_list.addItem(item)
            
            # Add to active profiles
            profile = self.db_manager.get_profile(profile_id)
            if profile:
                self.active_profiles[profile_id] = {
                    'hotkey': hotkey,
                    'settings': profile['settings'],
                    'scripts': profile['scripts']
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
        dialog = ProfileDialog(self.db_manager, self.user_id, None, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_user_profiles()
    
    def edit_profile(self, item):
        # Check permission
        if 'create_profiles' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit profiles.")
            return
            
        profile_id = item.data(Qt.UserRole)
        
        # Create dialog
        dialog = ProfileDialog(self.db_manager, self.user_id, profile_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_user_profiles()
    
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
            success = self.db_manager.delete_profile(profile_id)
            if success:
                # Remove from active profiles
                if profile_id in self.active_profiles:
                    del self.active_profiles[profile_id]
                
                # Refresh list
                self.load_user_profiles()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete profile.")
    
    def get_active_profiles(self):
        return self.active_profiles

class ProfileDialog(QDialog):
    def __init__(self, db_manager, user_id, profile_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = user_id
        self.profile_id = profile_id
        self.scripts = []  # List to store selected scripts
        
        self.initUI()
        
        if profile_id:
            self.load_profile_data()
    
    def initUI(self):
        self.setWindowTitle("Edit Profile" if self.profile_id else "Create Profile")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        
        # Profile info form
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("Press a key...")
        self.hotkey_input.setReadOnly(True)
        
        # Capture key press for hotkey
        def on_key_press_event(event):
            key = event.text()
            if key and key.isalnum():
                self.hotkey_input.setText(key.lower())
            elif event.key() == Qt.Key_F1:
                self.hotkey_input.setText("f1")
            elif event.key() == Qt.Key_F2:
                self.hotkey_input.setText("f2")
            # Add more function keys as needed
        
        self.hotkey_input.keyPressEvent = on_key_press_event
        
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Hotkey:", self.hotkey_input)
        
        layout.addLayout(form_layout)
        
        # Scripts selection
        scripts_group = QGroupBox("Scripts")
        scripts_layout = QVBoxLayout()
        
        # Available scripts
        available_scripts_label = QLabel("Available Scripts:")
        scripts_layout.addWidget(available_scripts_label)
        
        self.available_scripts_list = QListWidget()
        scripts_layout.addWidget(self.available_scripts_list)
        
        # Load available scripts
        self.load_available_scripts()
        
        # Add/Remove buttons
        buttons_layout = QHBoxLayout()
        
        self.add_script_btn = QPushButton("Add Script →")
        self.add_script_btn.clicked.connect(self.add_script)
        
        self.remove_script_btn = QPushButton("← Remove Script")
        self.remove_script_btn.clicked.connect(self.remove_script)
        
        buttons_layout.addWidget(self.add_script_btn)
        buttons_layout.addWidget(self.remove_script_btn)
        
        scripts_layout.addLayout(buttons_layout)
        
        # Selected scripts
        selected_scripts_label = QLabel("Selected Scripts (Execution Order):")
        scripts_layout.addWidget(selected_scripts_label)
        
        self.selected_scripts_table = QTableWidget()
        self.selected_scripts_table.setColumnCount(4)
        self.selected_scripts_table.setHorizontalHeaderLabels(["Script", "Order", "Execution Time (ms)", "Speed"])
        self.selected_scripts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.selected_scripts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.selected_scripts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.selected_scripts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        scripts_layout.addWidget(self.selected_scripts_table)
        
        # Move up/down buttons
        order_buttons_layout = QHBoxLayout()
        
        self.move_up_btn = QPushButton("Move Up")
        self.move_up_btn.clicked.connect(self.move_script_up)
        
        self.move_down_btn = QPushButton("Move Down")
        self.move_down_btn.clicked.connect(self.move_script_down)
        
        order_buttons_layout.addWidget(self.move_up_btn)
        order_buttons_layout.addWidget(self.move_down_btn)
        
        scripts_layout.addLayout(order_buttons_layout)
        
        scripts_group.setLayout(scripts_layout)
        layout.addWidget(scripts_group)
        
        # Settings
        settings_group = QGroupBox("Playback Settings")
        settings_layout = QFormLayout()
        
        self.speed_input = QDoubleSpinBox()
        self.speed_input.setRange(0.1, 10.0)
        self.speed_input.setValue(1.0)
        self.speed_input.setSingleStep(0.1)
        
        self.repeat_input = QSpinBox()
        self.repeat_input.setRange(1, 9999)
        self.repeat_input.setValue(1)
        
        settings_layout.addRow("Global Speed:", self.speed_input)
        settings_layout.addRow("Repeat Count:", self.repeat_input)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_available_scripts(self):
        """Load available scripts from database"""
        self.available_scripts_list.clear()
        scripts = self.db_manager.get_user_scripts(self.user_id)
        
        for script_id, name, description, _ in scripts:
            # Skip scripts that are already selected
            if any(s['script_id'] == script_id for s in self.scripts):
                continue
                
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, script_id)
            item.setToolTip(description)
            self.available_scripts_list.addItem(item)
    
    def update_selected_scripts_table(self):
        """Update the selected scripts table"""
        self.selected_scripts_table.setRowCount(0)
        
        for i, script in enumerate(self.scripts):
            self.selected_scripts_table.insertRow(i)
            
            # Script name
            self.selected_scripts_table.setItem(i, 0, QTableWidgetItem(script['name']))
            
            # Order (read-only)
            order_item = QTableWidgetItem(str(i + 1))
            order_item.setFlags(order_item.flags() & ~Qt.ItemIsEditable)
            self.selected_scripts_table.setItem(i, 1, order_item)
            
            # Execution time
            exec_time_item = QTableWidgetItem(str(script.get('execution_time', 0)))
            self.selected_scripts_table.setItem(i, 2, exec_time_item)
            
            # Speed
            speed_item = QTableWidgetItem(str(script.get('speed', 1.0)))
            self.selected_scripts_table.setItem(i, 3, speed_item)
    
    def add_script(self):
        """Add selected script to the profile"""
        selected_items = self.available_scripts_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        script_id = item.data(Qt.UserRole)
        script_name = item.text()
        
        # Add to scripts list
        self.scripts.append({
            'script_id': script_id,
            'name': script_name,
            'execution_order': len(self.scripts) + 1,
            'execution_time': 0,
            'speed': 1.0
        })
        
        # Update UI
        self.update_selected_scripts_table()
        self.load_available_scripts()
    
    def remove_script(self):
        """Remove selected script from the profile"""
        selected_rows = self.selected_scripts_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Remove from scripts list
        if row < len(self.scripts):
            self.scripts.pop(row)
            
            # Update execution order
            for i, script in enumerate(self.scripts):
                script['execution_order'] = i + 1
        
        # Update UI
        self.update_selected_scripts_table()
        self.load_available_scripts()
    
    def move_script_up(self):
        """Move selected script up in the execution order"""
        selected_rows = self.selected_scripts_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        if row > 0:
            # Swap with previous script
            self.scripts[row], self.scripts[row-1] = self.scripts[row-1], self.scripts[row]
            
            # Update execution order
            for i, script in enumerate(self.scripts):
                script['execution_order'] = i + 1
            
            # Update UI
            self.update_selected_scripts_table()
            self.selected_scripts_table.selectRow(row-1)
    
    def move_script_down(self):
        """Move selected script down in the execution order"""
        selected_rows = self.selected_scripts_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        if row < len(self.scripts) - 1:
            # Swap with next script
            self.scripts[row], self.scripts[row+1] = self.scripts[row+1], self.scripts[row]
            
            # Update execution order
            for i, script in enumerate(self.scripts):
                script['execution_order'] = i + 1
            
            # Update UI
            self.update_selected_scripts_table()
            self.selected_scripts_table.selectRow(row+1)
    
    def load_profile_data(self):
        """Load profile data from database"""
        profile = self.db_manager.get_profile(self.profile_id)
        if not profile:
            return
        
        # Set basic info
        self.name_input.setText(profile['name'])
        self.hotkey_input.setText(profile['hotkey'])
        
        # Set settings
        settings = profile['settings']
        self.speed_input.setValue(settings.get('speed', 1.0))
        self.repeat_input.setValue(settings.get('repeat', 1))
        
        # Set scripts
        self.scripts = []
        for script in profile['scripts']:
            self.scripts.append({
                'script_id': script['script_id'],
                'name': script['name'],
                'execution_order': script['execution_order'],
                'execution_time': script['execution_time'],
                'speed': script.get('speed', 1.0)
            })
        
        # Update UI
        self.update_selected_scripts_table()
        self.load_available_scripts()
    
    def accept(self):
        """Save profile and close dialog"""
        name = self.name_input.text().strip()
        hotkey = self.hotkey_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the profile.")
            return
        
        if not hotkey:
            QMessageBox.warning(self, "Warning", "Please assign a hotkey for the profile.")
            return
        
        if not self.scripts:
            QMessageBox.warning(self, "Warning", "Please add at least one script to the profile.")
            return
        
        # Update execution times and speeds from table
        for i, script in enumerate(self.scripts):
            try:
                exec_time = int(self.selected_scripts_table.item(i, 2).text())
                speed = float(self.selected_scripts_table.item(i, 3).text())
                script['execution_time'] = exec_time
                script['speed'] = speed
            except (ValueError, AttributeError):
                pass
        
        # Save settings
        settings = {
            'speed': self.speed_input.value(),
            'repeat': self.repeat_input.value()
        }
        
        # Prepare scripts data for database
        scripts_data = []
        for script in self.scripts:
            scripts_data.append({
                'script_id': script['script_id'],
                'execution_order': script['execution_order'],
                'execution_time': script['execution_time']
            })
        
        if self.profile_id:
            # Update existing profile
            success = self.db_manager.update_profile(
                self.profile_id,
                name,
                hotkey,
                settings,
                scripts_data
            )
            if success:
                super().accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update profile.")
        else:
            # Create new profile
            profile_id = self.db_manager.save_profile(
                self.user_id,
                name,
                hotkey,
                settings,
                scripts_data
            )
            if profile_id:
                super().accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to create profile.")