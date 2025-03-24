"""
Scripts tab for the Auto Click application.
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QListWidget, QListWidgetItem, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
import json

class ScriptsTab(QWidget):
    def __init__(self, db_manager, user_id, permissions, recorder_tab):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.permissions = permissions
        self.recorder_tab = recorder_tab  # Reference to recorder tab for loading scripts
        
        self.initUI()
        self.load_user_scripts()
    
    def initUI(self):
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
        
        self.setLayout(layout)
        
        # Apply permissions
        self.apply_permissions()
    
    def apply_permissions(self):
        # Scripts tab permissions
        can_edit_scripts = 'edit_scripts' in self.permissions
        can_import_export = 'import_export' in self.permissions
        
        self.delete_script_btn.setEnabled(can_edit_scripts)
        self.export_script_btn.setEnabled(can_import_export)
        self.import_script_btn.setEnabled(can_import_export)
    
    def load_user_scripts(self):
        self.scripts_list.clear()
        scripts = self.db_manager.get_user_scripts(self.user_id)
        
        for script_id, name, description, created_at in scripts:
            item = QListWidgetItem(f"{name}")
            item.setData(Qt.UserRole, script_id)
            item.setToolTip(description)
            self.scripts_list.addItem(item)
    
    def load_script(self, item):
        # Check permission
        if 'play_macros' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to load scripts.")
            return
            
        script_id = item.data(Qt.UserRole)
        script = self.db_manager.get_script(script_id)
        
        if script:
            # Load script into recorder tab
            self.recorder_tab.load_script(
                script_id,
                script['name'],
                script['description'],
                script['content']
            )
            
            # Switch to recorder tab
            self.parent().parent().setCurrentIndex(0)  # Assumes recorder tab is at index 0
    
    def delete_script(self):
        # Check permission
        if 'edit_scripts' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete scripts.")
            return
            
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
            if self.recorder_tab.current_script_id == script_id:
                self.recorder_tab.clear_recording()
    
    def export_script(self):
        # Check permission
        if 'import_export' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to export scripts.")
            return
            
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
        # Check permission
        if 'import_export' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to import scripts.")
            return
            
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
                script_id = self.db_manager.```python
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