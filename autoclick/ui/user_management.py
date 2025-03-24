"""
User management dialogs for the Auto Click application.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                            QFormLayout, QLineEdit, QComboBox, QGroupBox, 
                            QCheckBox, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt

from autoclick.config import USER_ROLES, PERMISSIONS, DEFAULT_ROLE_PERMISSIONS

class UserManagementDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.initUI()
        self.load_users()
    
    def initUI(self):
        self.setWindowTitle("User Management")
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout()
        
        # User table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(4)
        self.user_table.setHorizontalHeaderLabels(["Username", "Role", "Created", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.user_table.horizontLet me continue with the user management dialog implementation:

{% code path="autoclick/ui/user_management.py" type="update" %}
"""
User management dialogs for the Auto Click application.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                            QFormLayout, QLineEdit, QComboBox, QGroupBox, 
                            QCheckBox, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt

from autoclick.config import USER_ROLES, PERMISSIONS, DEFAULT_ROLE_PERMISSIONS

class UserManagementDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.initUI()
        self.load_users()
    
    def initUI(self):
        self.setWindowTitle("User Management")
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout()
        
        # User table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(4)
        self.user_table.setHorizontalHeaderLabels(["Username", "Role", "Created", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.user_table)
        
        # Buttons
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
        
        for i, (user_id, username, role, created_at) in enumerate(users):
            self.user_table.insertRow(i)
            
            # Username
            username_item = QTableWidgetItem(username)
            username_item.setData(Qt.UserRole, user_id)
            self.user_table.setItem(i, 0, username_item)
            
            # Role
            role_item = QTableWidgetItem(USER_ROLES.get(role, role))
            self.user_table.setItem(i, 1, role_item)
            
            # Created date
            created_item = QTableWidgetItem(created_at)
            self.user_table.setItem(i, 2, created_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _, uid=user_id: self.edit_user(uid))
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, uid=user_id: self.delete_user(uid))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions_widget.setLayout(actions_layout)
            
            self.user_table.setCellWidget(i, 3, actions_widget)
    
    def add_user(self):
        dialog = UserEditDialog(self.db_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_users()
    
    def edit_user(self, user_id):
        dialog = UserEditDialog(self.db_manager, user_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_users()
    
    def delete_user(self, user_id):
        # Get user details
        user_details = self.db_manager.get_user_details(user_id)
        if not user_details:
            return
        
        username, role = user_details
        
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

class UserEditDialog(QDialog):
    def __init__(self, db_manager, user_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = user_id
        self.initUI()
        
        if user_id:
            self.load_user_data()
    
    def initUI(self):
        self.setWindowTitle("Edit User" if self.user_id else "Add User")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # User info form
        form_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        self.role_combo = QComboBox()
        for role_id, role_name in USER_ROLES.items():
            self.role_combo.addItem(role_name, role_id)
        
        form_layout.addRow("Username:", self.username_input)
        if not self.user_id:  # Only show password field for new users
            form_layout.addRow("Password:", self.password_input)
        form_layout.addRow("Role:", self.role_combo)
        
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
    
    def load_user_data(self):
        # Get user details
        user_details = self.db_manager.get_user_details(self.user_id)
        if not user_details:
            return
        
        username, role = user_details
        
        # Set username and role
        self.username_input.setText(username)
        self.username_input.setReadOnly(True)  # Can't change username
        
        # Set role in combo box
        index = self.role_combo.findData(role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        
        # Get user permissions
        permissions = self.db_manager.get_user_permissions(self.user_id)
        
        # Set permission checkboxes
        for perm_id, checkbox in self.permission_checkboxes.items():
            checkbox.setChecked(perm_id in permissions)
    
    def apply_role_preset(self, role):
        # Set role in combo box
        index = self.role_combo.findData(role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        
        # Get default permissions for this role
        permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])
        
        # Set permission checkboxes
        for perm_id, checkbox in self.permission_checkboxes.items():
            checkbox.setChecked(perm_id in permissions)
    
    def accept(self):
        username = self.username_input.text().strip()
        role = self.role_combo.currentData()
        
        # Get selected permissions
        permissions = [
            perm_id for perm_id, checkbox in self.permission_checkboxes.items()
            if checkbox.isChecked()
        ]
        
        if not username:
            QMessageBox.warning(self, "Warning", "Please enter a username.")
            return
        
        if not self.user_id:
            # Creating new user
            password = self.password_input.text()
            if not password:
                QMessageBox.warning(self, "Warning", "Please enter a password.")
                return
            
            if len(password) < 6:
                QMessageBox.warning(self, "Warning", "Password must be at least 6 characters.")
                return
            
            user_id = self.db_manager.create_user(username, password, role, permissions)
            if not user_id:
                QMessageBox.critical(self, "Error", "Failed to create user. Username may already exist.")
                return
        else:
            # Updating existing user
            success = self.db_manager.update_user(self.user_id, role, permissions)
            if not success:
                QMessageBox.critical(self, "Error", "Failed to update user.")
                return
        
        super().accept()