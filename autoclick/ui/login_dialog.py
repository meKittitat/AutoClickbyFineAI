"""
Login dialog for the Auto Click application.
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal

class LoginDialog(QWidget):
    login_successful = pyqtSignal(str, str, str, list)  # user_id, username, role, permissions
    
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
        
        user_id, role = self.db_manager.authenticate_user(username, password)
        if user_id:
            permissions = self.db_manager.get_user_permissions(user_id)
            self.login_successful.emit(user_id, username, role, permissions)
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