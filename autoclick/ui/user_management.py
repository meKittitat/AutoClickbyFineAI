"""
User management dialogs for the Auto Click application.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                            QFormLayout, QLineEdit, QComboBox, QGroupBox, 
                            QCheckBox, QDialogButtonBox, QMessageBox, QWidget,
                            QSpinBox, QTimeEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QTime

from autoclick.config import USER_ROLES, PERMISSIONS, DEFAULT_ROLE_PERMISSIONS

class UserManagementDialog(QDialog):
    preview_user = pyqtSignal(str, str, str, list, int, bool)  # user_id, username, role, permissions, time_remaining, lifetime_pass
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.initUI()
        self.load_users()
    
    def initUI(self):
        self.setWindowTitle("User Management")
        self.setMinimumSize(900, 500)
        
        layout = QVBoxLayout()
        
        # User table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["Username", "Role", "Created", "Time Remaining", "Lifetime Pass", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.user_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        ```python
        button_layout = QHBoxLayout()
        
        self.add_user_btn = QPushButton("Add User")
        self.add_user_btn.clicked.connect(self.add_user)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_users)
        
        button_layout.addWidget(self.add_user_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_users(self):
        self.user_table.setRowCount(0)
        users = self.db_manager.get_all_users()
        
        for i, (user_id, username, role, created_at, time_remaining, lifetime_pass) in enumerate(users):
            self.user_table.insertRow(i)
            
            # Username
            username_item = QTableWidgetItem(username)
            username_item.setData(Qt.UserRole, user_id)
            self.user_table.setItem(i, 0, username_item)
            
            # Get role name
            role_name = ""
            roles = self.db_manager.get_all_roles()
            for role_id, name, _ in roles:
                if role_id == role:
                    role_name = name
                    break
            
            # Role (with dropdown)
            role_combo = QComboBox()
            for role_id, name, _ in roles:
                role_combo.addItem(name, role_id)
            
            # Set current role
            index = role_combo.findData(role)
            if index >= 0:
                role_combo.setCurrentIndex(index)
            
            # Connect role change
            role_combo.currentIndexChanged.connect(lambda idx, uid=user_id, combo=role_combo: 
                                                 self.change_user_role(uid, combo.currentData()))
            
            self.user_table.setCellWidget(i, 1, role_combo)
            
            # Created date
            created_item = QTableWidgetItem(created_at)
            self.user_table.setItem(i, 2, created_item)
            
            # Time remaining
            if lifetime_pass:
                time_item = QTableWidgetItem("Lifetime Pass")
            else:
                hours = time_remaining // 60
                minutes = time_remaining % 60
                time_item = QTableWidgetItem(f"{hours:02d}:{minutes:02d}")
            
            self.user_table.setItem(i, 3, time_item)
            
            # Lifetime pass checkbox
            lifetime_check = QCheckBox()
            lifetime_check.setChecked(lifetime_pass == 1)
            lifetime_check.stateChanged.connect(lambda state, uid=user_id: 
                                              self.toggle_lifetime_pass(uid, state == Qt.Checked))
            
            lifetime_widget = QWidget()
            lifetime_layout = QHBoxLayout()
            lifetime_layout.setContentsMargins(0, 0, 0, 0)
            lifetime_layout.addWidget(lifetime_check)
            lifetime_layout.setAlignment(Qt.AlignCenter)
            lifetime_widget.setLayout(lifetime_layout)
            
            self.user_table.setCellWidget(i, 4, lifetime_widget)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            add_time_btn = QPushButton("Add Time")
            add_time_btn.clicked.connect(lambda _, uid=user_id: self.add_time(uid))
            
            reset_pwd_btn = QPushButton("Reset Password")
            reset_pwd_btn.clicked.connect(lambda _, uid=user_id: self.reset_password(uid))
            
            preview_btn = QPushButton("Preview")
            preview_btn.clicked.connect(lambda _, uid=user_id: self.preview_user_role(uid))
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, uid=user_id: self.delete_user(uid))
            
            actions_layout.addWidget(add_time_btn)
            actions_layout.addWidget(reset_pwd_btn)
            actions_layout.addWidget(preview_btn)
            actions_layout.addWidget(delete_btn)
            actions_widget.setLayout(actions_layout)
            
            self.user_table.setCellWidget(i, 5, actions_widget)
    
    def add_user(self):
        dialog = AddUserDialog(self.db_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_users()
    
    def change_user_role(self, user_id, role_id):
        """Change a user's role"""
        # Get permissions for the role
        permissions = self.db_manager.get_role_permissions(role_id)
        
        # Update user
        success = self.db_manager.update_user(user_id, role_id, permissions)
        if not success:
            QMessageBox.critical(self, "Error", "Failed to update user role.")
            self.load_users()  # Reload to reset the combo box
    
    def toggle_lifetime_pass(self, user_id, has_lifetime_pass):
        """Toggle lifetime pass for a user"""
        success = self.db_manager.set_user_lifetime_pass(user_id, has_lifetime_pass)
        if not success:
            QMessageBox.critical(self, "Error", "Failed to update lifetime pass status.")
            self.load_users()  # Reload to reset the checkbox
    
    def add_time(self, user_id):
        """Add time to a user's account"""
        dialog = AddTimeDialog(self.db_manager, user_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_users()
    
    def reset_password(self, user_id):
        # Get user details
        user_details = self.db_manager.get_user_details(user_id)
        if not user_details:
            return
        
        username, _, _, _ = user_details
        
        # Confirm reset
        reply = QMessageBox.question(
            self, 
            "Confirm Password Reset", 
            f"Are you sure you want to reset the password for user '{username}'?\\n\\n"
            "The user will be required to set a new password on next login.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.db_manager.reset_user_password(user_id)
            if success:
                QMessageBox.information(self, "Success", f"Password for user '{username}' has been reset.")
            else:
                QMessageBox.critical(self, "Error", "Failed to reset password.")
    
    def preview_user_role(self, user_id):
        """Preview the application as this user"""
        # Get user details
        user_details = self.db_manager.get_user_details(user_id)
        if not user_details:
            return
        
        username, role, time_remaining, lifetime_pass = user_details
        permissions = self.db_manager.get_user_permissions(user_id)
        
        # Emit signal to main window
        self.preview_user.emit(user_id, username, role, permissions, time_remaining, lifetime_pass == 1)
        self.close()
    
    def delete_user(self, user_id):
        # Get user details
        user_details = self.db_manager.get_user_details(user_id)
        if not user_details:
            return
        
        username, _, _, _ = user_details
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to delete user '{username}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.db_manager.delete_user(user_id)
            if success:
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete user.")

class AddUserDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Add User")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # User info form
        form_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Get roles from database
        roles = self.db_manager.get_all_roles()
        
        self.role_combo = QComboBox()
        for role_id, name, _ in roles:
            self.role_combo.addItem(name, role_id)
        
        # Time settings
        self.time_group = QGroupBox("Time Allocation")
        time_layout = QVBoxLayout()
        
        self.lifetime_pass_cb = QCheckBox("Lifetime Pass")
        self.lifetime_pass_cb.stateChanged.connect(self.toggle_time_input)
        
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setTime(QTime(1, 0))  # Default 1 hour
        
        time_layout.addWidget(self.lifetime_pass_cb)
        time_layout.addWidget(self.time_input)
        self.time_group.setLayout(time_layout)
        
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        form_layout.addRow("Role:", self.role_combo)
        form_layout.addRow("", self.time_group)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def toggle_time_input(self, state):
        """Enable/disable time input based on lifetime pass checkbox"""
        self.time_input.setEnabled(not state)
    
    def accept(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        role = self.role_combo.currentData()
        
        if not username or not password:
            QMessageBox.warning(self, "Warning", "Please enter both username and password.")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Warning", "Password must be at least 6 characters.")
            return
        
        # Calculate time in minutes
        lifetime_pass = self.lifetime_pass_cb.isChecked()
        if lifetime_pass:
            time_minutes = 0
        else:
            time = self.time_input.time()
            time_minutes = time.hour() * 60 + time.minute()
        
        # Create user
        user_id = self.db_manager.create_user(
            username, 
            password, 
            role, 
            None,  # Use role permissions
            None,  # No creator
            time_minutes,
            1 if lifetime_pass else 0
        )
        
        if not user_id:
            QMessageBox.critical(self, "Error", "Failed to create user. Username may already exist.")
            return
        
        super().accept()

class AddTimeDialog(QDialog):
    def __init__(self, db_manager, user_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = user_id
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Add Time")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Get user details
        user_details = self.db_manager.get_user_details(self.user_id)
        if user_details:
            username, _, time_remaining, lifetime_pass = user_details
            
            # User info
            info_label = QLabel(f"Adding time for user: {username}")
            layout.addWidget(info_label)
            
            if lifetime_pass:
                current_time_label = QLabel("User has lifetime pass")
            else:
                hours = time_remaining // 60
                minutes = time_remaining % 60
                current_time_label = QLabel(f"Current time remaining: {hours:02d}:{minutes:02d}")
            
            layout.addWidget(current_time_label)
            
            # Time input
            form_layout = QFormLayout()
            
            self.time_input = QTimeEdit()
            self.time_input.setDisplayFormat("HH:mm")
            self.time_input.setTime(QTime(1, 0))  # Default 1 hour
            
            form_layout.addRow("Add time:", self.time_input)
            layout.addLayout(form_layout)
            
            # Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def accept(self):
        # Calculate time in minutes
        time = self.time_input.time()
        time_minutes = time.hour() * 60 + time.minute()
        
        # Add time to user
        success = self.db_manager.update_user_time(self.user_id, time_minutes)
        if not success:
            QMessageBox.critical(self, "Error", "Failed to add time to user.")
            return
        
        super().accept()

class RoleManagementDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.initUI()
        self.load_roles()
    
    def initUI(self):
        self.setWindowTitle("Role Management")
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout()
        
        # Role table
        self.role_table = QTableWidget()
        self.role_table.setColumnCount(3)
        self.role_table.setHorizontalHeaderLabels(["Role Name", "Description", "Actions"])
        self.role_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.role_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.role_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.role_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_role_btn = QPushButton("Add Role")
        self.add_role_btn.clicked.connect(self.add_role)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_roles)
        
        button_layout.addWidget(self.add_role_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_roles(self):
        self.role_table.setRowCount(0)
        roles = self.db_manager.get_all_roles()
        
        for i, (role_id, name, description) in enumerate(roles):
            self.role_table.insertRow(i)
            
            # Role name
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, role_id)
            self.role_table.setItem(i, 0, name_item)
            
            # Description
            desc_item = QTableWidgetItem(description or "")
            self.role_table.setItem(i, 1, desc_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _, rid=role_id: self.edit_role(rid))
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, rid=role_id: self.delete_role(rid))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions_widget.setLayout(actions_layout)
            
            self.role_table.setCellWidget(i, 2, actions_widget)
    
    def add_role(self):
        dialog = RoleEditDialog(self.db_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_roles()
    
    def edit_role(self, role_id):
        dialog = RoleEditDialog(self.db_manager, role_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_roles()
    
    def delete_role(self, role_id):
        # Get role details
        role_details = self.db_manager.get_role_details(role_id)
        if not role_details:
            return
        
        name, _ = role_details
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to delete role '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.db_manager.delete_role(role_id)
            if success:
                self.load_roles()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete role. It may be in use by one or more users.")

class RoleEditDialog(QDialog):
    def __init__(self, db_manager, role_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.role_id = role_id
        self.initUI()
        
        if role_id:
            self.load_role_data()
    
    def initUI(self):
        self.setWindowTitle("Edit Role" if self.role_id else "Add Role")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Role info form
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.description_input = QLineEdit()
        
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Description:", self.description_input)
        
        layout.addLayout(form_layout)
        
        # Permissions group
        permissions_group = QGroupBox("Permissions")
        permissions_layout = QVBoxLayout()
        
        self.permission_checkboxes = {}
        for perm_id, perm_name in PERMISSIONS.items():
            checkbox = QCheckBox(perm_name)
            self.permission_checkboxes[perm_id] = checkbox
            permissions_layout.addWidget(checkbox)
        
        permissions_group.setLayout(permissions_layout)
        layout.addWidget(permissions_group)
        
        # Role presets
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Apply preset:")
        preset_layout.addWidget(preset_label)
        
        for role_id, role_name in USER_ROLES.items():
            preset_btn = QPushButton(role_name)
            preset_btn.clicked.connect(lambda _, r=role_id: self.apply_role_preset(r))
            preset_layout.addWidget(preset_btn)
        
        layout.addLayout(preset_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_role_data(self):
        # Get role details
        role_details = self.db_manager.get_role_details(self.role_id)
        if not role_details:
            return
        
        name, description = role_details
        
        # Set name and description
        self.name_input.setText(name)
        self.description_input.setText(description or "")
        
        # Get role permissions
        permissions = self.db_manager.get_role_permissions(self.role_id)
        
        # Set permission checkboxes
        for perm_id, checkbox in self.permission_checkboxes.items():
            checkbox.setChecked(perm_id in permissions)
    
    def apply_role_preset(self, role):
        # Get default permissions for this role
        permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])
        
        # Set permission checkboxes
        for perm_id, checkbox in self.permission_checkboxes.items():
            checkbox.setChecked(perm_id in permissions)
        
        # Set name if creating new role
        if not self.role_id:
            self.name_input.setText(USER_ROLES.get(role, role.capitalize()))
    
    def accept(self):
        name = self.name_input.text().strip()
        description = self.description_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the role.")
            return
        
        # Get selected permissions
        permissions = [
            perm_id for perm_id, checkbox in self.permission_checkboxes.items()
            if checkbox.isChecked()
        ]
        
        if self.role_id:
            # Update existing role
            success = self.db_manager.update_role(self.role_id, name, description, permissions)
            if not success:
                QMessageBox.critical(self, "Error", "Failed to update role.")
                return
        else:
            # Create new role
            role_id = self.db_manager.create_role(name, description, permissions)
            if not role_id:
                QMessageBox.critical(self, "Error", "Failed to create role. Role name may already exist.")
                return
        
        super().accept()