"""
Login dialog for the Auto Click application.
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QFormLayout, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

from autoclick.config import APP_VERSION

class PasswordLineEdit(QWidget):
    """Custom password input with visibility toggle"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        self.toggle_btn = QPushButton()
        self.toggle_btn.setIcon(QIcon.fromTheme("eye"))
        self.toggle_btn.setFixedWidth(30)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.toggle_visibility)
        
        layout.addWidget(self.password_input)
        layout.addWidget(self.toggle_btn)
        
        self.setLayout(layout)
    
    def toggle_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_btn.setIcon(QIcon.fromTheme("eye-slash"))
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_btn.setIcon(QIcon.fromTheme("eye"))
    
    def text(self):
        return self.password_input.text()
    
    def clear(self):
        self.password_input.clear()
    
    def setPlaceholderText(self, text):
        self.password_input.setPlaceholderText(text)

class LoginDialog(QWidget):
    login_successful = pyqtSignal(str, str, str, list)  # user_id, username, role, permissions
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.is_register_mode = False
        self.is_reset_mode = False
        self.reset_user_id = None
        self.reset_username = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Auto Click - Login')
        self.setFixedSize(400, 350)
        
        layout = QVBoxLayout()
        
        # Logo or title
        title_label = QLabel("Auto Click")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title_label)
        
        # Version display
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: gray;")
        layout.addWidget(version_label)
        
        # Login form
        self.form_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.password_input = PasswordLineEdit()
        self.confirm_password_input = PasswordLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm password")
        self.confirm_password_input.hide()  # Initially hidden
        
        self.form_layout.addRow("Username:", self.username_input)
        self.form_layout.addRow("Password:", self.password_input)
        self.form_layout.addRow("Confirm:", self.confirm_password_input)
        
        form_container = QWidget()
        form_container.setLayout(self.form_layout)
        layout.addWidget(form_container)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)
        
        self.register_btn = QPushButton("Register")
        self.register_btn.clicked.connect(self.toggle_mode)
        
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
    
    def toggle_mode(self):
        if self.is_reset_mode:
            # Can't toggle when in reset mode
            return
            
        self.is_register_mode = not self.is_register_mode
        
        if self.is_register_mode:
            self.confirm_password_input.show()
            self.login_btn.setText("Register")
            self.register_btn.setText("Back to Login")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.register)
        else:
            self.confirm_password_input.hide()
            self.login_btn.setText("Login")
            self.register_btn.setText("Register")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.login)
        
        # Clear status
        self.status_label.setText("")
    
    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        user_id, role = self.db_manager.authenticate_user(username, password)
        if user_id:
            # Check if password reset is required
            if role == "reset_required":
                self.show_password_reset(user_id, username)
            else:
                permissions = self.db_manager.get_user_permissions(user_id)
                self.login_successful.emit(user_id, username, role, permissions)
                self.close()
        else:
            self.status_label.setText("Invalid username or password")
    
    def show_password_reset(self, user_id, username):
        # Switch to password reset mode
        self.is_reset_mode = True
        self.reset_user_id = user_id
        self.reset_username = username
        
        # Update UI for password reset
        self.setWindowTitle('Auto Click - Password Reset Required')
        self.username_input.setText(username)
        self.username_input.setReadOnly(True)
        self.password_input.clear()
        self.confirm_password_input.show()
        
        self.login_btn.setText("Set New Password")
        self.login_btn.clicked.disconnect()
        self.login_btn.clicked.connect(self.reset_password)
        
        self.register_btn.hide()
        
        self.status_label.setText("Your password has been reset. Please set a new password.")
        self.status_label.setStyleSheet("color: blue;")
    
    def reset_password(self):
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not password:
            self.status_label.setText("Please enter a new password")
            self.status_label.setStyleSheet("color: red;")
            return
        
        if len(password) < 6:
            self.status_label.setText("Password must be at least 6 characters")
            self.status_label.setStyleSheet("color: red;")
            return
        
        if password != confirm_password:
            self.status_label.setText("Passwords do not match")
            self.status_label.setStyleSheet("color: red;")
            return
        
        # Update password in database
        success = self.db_manager.update_user_password(self.reset_user_id, password)
        if success:
            QMessageBox.information(self, "Success", "Password has been updated successfully.")
            
            # Get user role and permissions
            user_details = self.db_manager.get_user_details(self.reset_user_id)
            if user_details:
                _, role = user_details
                permissions = self.db_manager.get_user_permissions(self.reset_user_id)
                self.login_successful.emit(self.reset_user_id, self.reset_username, role, permissions)
                self.close()
        else:
            self.status_label.setText("Failed to update password")
            self.status_label.setStyleSheet("color: red;")
    
    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        if len(password) < 6:
            self.status_label.setText("Password must be at least 6 characters")
            return
        
        if password != confirm_password:
            self.status_label.setText("Passwords do not match")
            return
        
        user_id = self.db_manager.create_user(username, password)
        if user_id:
            self.status_label.setText("Registration successful! You can now login.")
            self.status_label.setStyleSheet("color: green;")
            
            # Switch back to login mode
            self.is_register_mode = False
            self.confirm_password_input.hide()
            self.login_btn.setText("Login")
            self.register_btn.setText("Register")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.login)
        else:
            self.status_label.setText("Username already exists")