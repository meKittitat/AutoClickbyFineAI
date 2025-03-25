"""
Recorder tab for the Auto Click application.
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QGroupBox, QFormLayout, QLineEdit, QTextEdit,
                            QDoubleSpinBox, QSpinBox, QCheckBox, QListWidget,
                            QMessageBox, QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer

import pyautogui
from pynput import mouse, keyboard

from autoclick.ui.widgets import PixelDisplayWidget
from autoclick.core.recording import RecordingThread, format_action
from autoclick.core.playback import PlaybackThread

class RecorderTab(QWidget):
    def __init__(self, db_manager, user_id, permissions):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.permissions = permissions
        
        self.recording_thread = None
        self.playback_thread = None
        self.mouse_listener = None
        self.keyboard_listener = None
        
        self.current_actions = []
        self.current_script_id = None
        self.current_script_name = ""
        self.current_script_description = ""
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Top section with coordinate display and pixel viewer
        top_layout = QHBoxLayout()
        
        # Coordinate display
        coord_group = QGroupBox("Cursor Position")
        coord_layout = QVBoxLayout()
        
        self.coord_label = QLabel("X: 0, Y: 0")
        self.coord_label.setAlignment(Qt.AlignCenter)
        self.coord_label.setStyleSheet("font-size: 16px;")
        coord_layout.addWidget(self.coord_label)
        
        # Color display
        self.color_label = QLabel("RGB: 0, 0, 0")
        self.color_label.setAlignment(Qt.AlignCenter)
        coord_layout.addWidget(self.color_label)
        
        coord_group.setLayout(coord_layout)
        top_layout.addWidget(coord_group)
        
        # Pixel display
        pixel_group = QGroupBox("Pixel View")
        pixel_layout = QVBoxLayout()
        self.pixel_display = PixelDisplayWidget()
        pixel_layout.addWidget(self.pixel_display)
        pixel_group.setLayout(pixel_layout)
        top_layout.addWidget(pixel_group)
        
        # Recording controls
        controls_group = QGroupBox("Recording Controls")
        controls_layout = QVBoxLayout()
        
        # Script info
        script_info_layout = QFormLayout()
        self.script_name_input = QLineEdit()
        self.script_desc_input = QTextEdit()
        self.script_desc_input.setMaximumHeight(60)
        
        script_info_layout.addRow("Name:", self.script_name_input)
        script_info_layout.addRow("Description:", self.script_desc_input)
        controls_layout.addLayout(script_info_layout)
        
        # Record/Stop buttons
        button_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_recording)
        self.play_btn.setEnabled(False)
        
        button_layout.addWidget(self.record_btn)
        button_layout.addWidget(self.play_btn)
        
        controls_layout.addLayout(button_layout)
        
        # Playback settings
        playback_layout = QFormLayout()
        
        self.speed_input = QDoubleSpinBox()
        self.speed_input.setRange(0.1, 10.0)
        self.speed_input.setValue(1.0)
        self.speed_input.setSingleStep(0.1)
        
        self.repeat_input = QSpinBox()
        self.repeat_input.setRange(1, 9999)
        self.repeat_input.setValue(1)
        
        self.randomize_cb = QCheckBox("Add randomization")
        
        # Add randomization radius setting
        self.randomize_radius = QSpinBox()
        self.randomize_radius.setRange(1, 50)
        self.randomize_radius.setValue(3)
        self.randomize_radius.setSuffix(" px")
        
        playback_layout.addRow("Speed:", self.speed_input)
        playback_layout.addRow("Repeat:", self.repeat_input)
        playback_layout.addRow("Randomize:", self.randomize_cb)
        playback_layout.addRow("Random radius:", self.randomize_radius)
        
        controls_layout.addLayout(playback_layout)
        
        # Save/Load buttons
        save_load_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Script")
        self.save_btn.clicked.connect(self.save_script)
        self.save_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_recording)
        
        save_load_layout.addWidget(self.save_btn)
        save_load_layout.addWidget(self.clear_btn)
        
        controls_layout.addLayout(save_load_layout)
        
        controls_group.setLayout(controls_layout)
        top_layout.addWidget(controls_group)
        
        layout.addLayout(top_layout)
        
        # Actions list
        actions_group = QGroupBox("Recorded Actions")
        actions_layout = QVBoxLayout()
        
        self.actions_list = QListWidget()
        self.actions_list.setSelectionMode(QListWidget.SingleSelection)
        self.actions_list.itemDoubleClicked.connect(self.edit_action)
        actions_layout.addWidget(self.actions_list)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        self.setLayout(layout)
        
        # Setup timer to update coordinates
        self.coord_timer = QTimer(self)
        self.coord_timer.timeout.connect(self.update_coordinates)
        self.coord_timer.start(100)  # Update every 100ms
        
        # Apply permissions
        self.apply_permissions()
    
    def apply_permissions(self):
        # Recorder tab permissions
        can_record = 'record_macros' in self.permissions
        can_play = 'play_macros' in self.permissions
        
        self.record_btn.setEnabled(can_record)
        self.play_btn.setEnabled(can_play and len(self.current_actions) > 0)
        self.save_btn.setEnabled('edit_scripts' in self.permissions and len(self.current_actions) > 0)
    
    def update_coordinates(self):
        try:
            x, y = pyautogui.position()
            self.coord_label.setText(f"X: {x}, Y: {y}")
            
            # Get pixel color
            pixel_color = pyautogui.screenshot().getpixel((x, y))
            self.color_label.setText(f"RGB: {pixel_color[0]}, {pixel_color[1]}, {pixel_color[2]}")
        except Exception as e:
            print(f"Error updating coordinates: {e}")
    
    def toggle_recording(self):
        # Check permission
        if 'record_macros' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to record macros.")
            return
            
        if self.recording_thread and self.recording_thread.running:
            # Stop recording
            self.recording_thread.stop()
            self.recording_thread.wait()
            
            # Stop listeners
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                
            self.record_btn.setText("Start Recording")
            self.play_btn.setEnabled('play_macros' in self.permissions)
            self.save_btn.setEnabled('edit_scripts' in self.permissions)
        else:
            # Start recording
            self.recording_thread = RecordingThread()
            self.recording_thread.action_recorded.connect(self.on_action_recorded)
            
            # Clear previous recording
            self.current_actions = []
            self.actions_list.clear()
            
            # Start the thread
            self.recording_thread.start()
            self.record_btn.setText("Stop Recording")
            self.play_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            
            # Setup mouse and keyboard listeners
            self.setup_listeners()
    
    def setup_listeners(self):
        # Mouse listener for clicks
        def on_mouse_click(x, y, button, pressed):
            if not self.recording_thread or not self.recording_thread.running:
                return False
            
            if pressed:
                self.recording_thread.add_action('click', x=x, y=y, button=button)
            return True
        
        # Keyboard listener for key presses
        def on_key_press(key):
            if not self.recording_thread or not self.recording_thread.running:
                return False
            
            try:
                # For normal characters
                key_char = key.char
                self.recording_thread.add_action('keypress', key=key_char)
            except AttributeError:
                # For special keys
                key_name = str(key).replace('Key.', '')
                self.recording_thread.add_action('keypress', key=key_name)
            return True
        
        # Start listeners
        self.mouse_listener = mouse.Listener(on_click=on_mouse_click)
        self.mouse_listener.start()
        
        self.keyboard_listener = keyboard.Listener(on_press=on_key_press)
        self.keyboard_listener.start()
    
    def on_action_recorded(self, action):
        # Add action to the list widget
        action_str = format_action(action)
        item = QListWidgetItem(action_str)
        item.setData(Qt.UserRole, action)
        self.actions_list.addItem(item)
        self.actions_list.scrollToBottom()
        
        # Add to current actions
        self.current_actions.append(action)
    
    def edit_action(self, item):
        # Only allow editing when not recording
        if self.recording_thread and self.recording_thread.running:
            return
            
        # Get the action index
        index = self.actions_list.row(item)
        action = self.current_actions[index]
        
        # Create a simple dialog to edit the action
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Action")
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Different fields based on action type
        if action['type'] == 'click':
            x_input = QSpinBox()
            x_input.setRange(0, 9999)
            x_input.setValue(action['x'])
            
            y_input = QSpinBox()
            y_input.setRange(0, 9999)
            y_input.setValue(action['y'])
            
            form.addRow("X coordinate:", x_input)
            form.addRow("Y coordinate:", y_input)
            
        elif action['type'] == 'move':
            x_input = QSpinBox()
            x_input.setRange(0, 9999)
            x_input.setValue(action['x'])
            
            y_input = QSpinBox()
            y_input.setRange(0, 9999)
            y_input.setValue(action['y'])
            
            form.addRow("X coordinate:", x_input)
            form.addRow("Y coordinate:", y_input)
            
        elif action['type'] == 'keypress':
            key_input = QLineEdit()
            key_input.setText(action['key'])
            form.addRow("Key:", key_input)
            
        layout.addLayout(form)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        # If dialog is accepted, update the action
        if dialog.exec_() == QDialog.Accepted:
            if action['type'] == 'click' or action['type'] == 'move':
                action['x'] = x_input.value()
                action['y'] = y_input.value()
            elif action['type'] == 'keypress':
                action['key'] = key_input.text()
                
            # Update the list item
            item.setText(format_action(action))
            item.setData(Qt.UserRole, action)
            
            # Update the action in the list
            self.current_actions[index] = action
    
    def play_recording(self):
        # Check permission
        if 'play_macros' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to play macros.")
            return
            
        if not self.current_actions:
            QMessageBox.warning(self, "Warning", "No actions to play.")
            return
        
        # Disable UI elements
        self.record_btn.setEnabled(False)
        self.play_btn.setText("Stop")
        self.play_btn.clicked.disconnect()
        self.play_btn.clicked.connect(self.stop_playback)
        
        # Create and start playback thread
        self.playback_thread = PlaybackThread(
            self.current_actions,
            self.speed_input.value(),
            self.repeat_input.value(),
            self.randomize_cb.isChecked(),
            self.randomize_radius.value() / 10.0  # Convert to randomize factor
        )
        self.playback_thread.playback_finished.connect(self.on_playback_finished)
        self.playback_thread.action_played.connect(self.on_action_played)
        self.playback_thread.start()
    
    def stop_playback(self):
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
            self.on_playback_finished()
    
    def on_playback_finished(self):
        # Re-enable UI elements
        self.record_btn.setEnabled('record_macros' in self.permissions)
        self.play_btn.setText("Play")
        self.play_btn.clicked.disconnect()
        self.play_btn.clicked.connect(self.play_recording)
        
        # Clear selection in actions list
        self.actions_list.clearSelection()
    
    def on_action_played(self, index):
        # Highlight the current action in the list
        self.actions_list.setCurrentRow(index)
    
    def clear_recording(self):
        self.current_actions = []
        self.actions_list.clear()
        self.current_script_id = None
        self.current_script_name = ""
        self.current_script_description = ""
        self.script_name_input.clear()
        self.script_desc_input.clear()
        self.play_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
    
    def save_script(self):
        # Check permission
        if 'edit_scripts' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to save scripts.")
            return
            
        name = self.script_name_input.text().strip()
        description = self.script_desc_input.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the script.")
            return
        
        if not self.current_actions:
            QMessageBox.warning(self, "Warning", "No actions to save.")
            return
        
        if self.current_script_id:
            # Update existing script
            success = self.db_manager.update_script(
                self.current_script_id,
                name,
                description,
                self.current_actions
            )
            if success:
                QMessageBox.information(self, "Success", "Script updated successfully.")
            else:
                QMessageBox.critical(self, "Error", "Failed to update script.")
        else:
            # Create new script
            script_id = self.db_manager.save_script(
                self.user_id,
                name,
                description,
                self.current_actions
            )
            if script_id:
                self.current_script_id = script_id
                QMessageBox.information(self, "Success", "Script saved successfully.")
            else:
                QMessageBox.critical(self, "Error", "Failed to save script.")
    
    def load_script(self, script_id, script_name, script_description, script_content):
        self.current_script_id = script_id
        self.current_script_name = script_name
        self.current_script_description = script_description
        self.current_actions = script_content
        
        # Update UI
        self.script_name_input.setText(self.current_script_name)
        self.script_desc_input.setText(self.current_script_description)
        
        # Update actions list
        self.actions_list.clear()
        for action in self.current_actions:
            action_str = format_action(action)
            item = QListWidgetItem(action_str)
            item.setData(Qt.UserRole, action)
            self.actions_list.addItem(item)
        
        # Enable play button
        self.play_btn.setEnabled('play_macros' in self.permissions)
        self.save_btn.setEnabled('edit_scripts' in self.permissions)