"""
Settings tab for the Auto Click application.
"""
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                            QCheckBox, QSpinBox, QDoubleSpinBox, QLineEdit,
                            QPushButton, QMessageBox)
from PyQt5.QtCore import QSettings

class SettingsTab(QWidget):
    def __init__(self, permissions):
        super().__init__()
        self.permissions = permissions
        self.initUI()
        self.load_settings()
    
    def initUI(self):
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
        
        self.setLayout(layout)
        
        # Apply permissions
        self.apply_permissions()
    
    def apply_permissions(self):
        # Settings tab permissions
        can_access_advanced = 'advanced_settings' in self.permissions
        
        # Disable advanced settings if not permitted
        if not can_access_advanced:
            for i in range(self.layout().count()):
                widget = self.layout().itemAt(i).widget()
                if isinstance(widget, QGroupBox) and widget.title() == "Advanced Settings":
                    widget.setEnabled(False)
                    break
    
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
    
    def save_settings(self):
        # Check permission for advanced settings
        if 'advanced_settings' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to change advanced settings.")
            return
            
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
    
    def get_recording_settings(self):
        return {
            'record_mouse_movement': self.record_mouse_movement_cb.isChecked(),
            'movement_threshold': self.movement_threshold_input.value(),
            'movement_interval': self.movement_interval_input.value()
        }
    
    def get_randomize_factor(self):
        return self.randomize_factor_input.value()