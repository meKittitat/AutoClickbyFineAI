"""
Recorder tab for the Auto Click application.
"""
from PyQt5.QtWidgets import (```python
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QGroupBox, QFormLayout, QLineEdit, QTextEdit,
                            QDoubleSpinBox, QSpinBox, QCheckBox, QListWidget,
                            QMessageBox, QListWidgetItem, QTableWidget, QTableWidgetItem,
                            QHeaderView, QComboBox, QDialog, QDialogButtonBox, QMenu,
                            QAction, QTimeEdit)
from PyQt5.QtCore import Qt, QTimer, QTime

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
        
        self.continuous_mode = True  # Default to continuous recording
        self.recording_time = QTime(0, 0, 0)  # Recording timer
        
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
        
        # Recording mode selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Recording Mode:")
        self.continuous_mode_radio = QCheckBox("Continuous")
        self.continuous_mode_radio.setChecked(True)
        self.hotkey_mode_radio = QCheckBox("Hotkey-based")
        
        # Connect mode radio buttons
        self.continuous_mode_radio.clicked.connect(self.toggle_recording_mode)
        self.hotkey_mode_radio.clicked.connect(self.toggle_recording_mode)
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.continuous_mode_radio)
        mode_layout.addWidget(self.hotkey_mode_radio)
        controls_layout.addLayout(mode_layout)
        
        # Recording timer display
        timer_layout = QHBoxLayout()
        timer_label = QLabel("Recording Time:")
        self.timer_display = QLabel("00:00:00")
        self.timer_display.setStyleSheet("font-size: 16px; font-weight: bold;")
        timer_layout.addWidget(timer_label)
        timer_layout.addWidget(self.timer_display)
        controls_layout.addLayout(timer_layout)
        
        # Hotkey info
        hotkey_info = QLabel("Press F9 to start recording, F10 to stop, F11 to capture position (in hotkey mode)")
        hotkey_info.setWordWrap(True)
        controls_layout.addWidget(hotkey_info)
        
        # Playback settings
        playback_layout = QFormLayout()
        
        self.speed_input = QDoubleSpinBox()
        self.speed_input.setRange(0.1, 10.0)
        self.speed_input.setValue(1.0)
        self.speed_input.setSingleStep(0.1)
        
        self.repeat_input = QSpinBox()
        self.repeat_input.setRange(1, 9999)
        self.repeat_input.setValue(1)
        
        playback_layout.addRow("Speed:", self.speed_input)
        playback_layout.addRow("Repeat:", self.repeat_input)
        
        controls_layout.addLayout(playback_layout)
        
        # Save/Load buttons
        save_load_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Script")
        self.save_btn.clicked.connect(self.save_script)
        self.save_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_recording)
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_recording)
        self.play_btn.setEnabled(False)
        
        save_load_layout.addWidget(self.save_btn)
        save_load_layout.addWidget(self.clear_btn)
        save_load_layout.addWidget(self.play_btn)
        
        controls_layout.addLayout(save_load_layout)
        
        controls_group.setLayout(controls_layout)
        top_layout.addWidget(controls_group)
        
        layout.addLayout(top_layout)
        
        # Actions table
        actions_group = QGroupBox("Recorded Actions")
        actions_layout = QVBoxLayout()
        
        # Add button to create new action
        action_buttons_layout = QHBoxLayout()
        self.add_action_btn = QPushButton("Add Action")
        self.add_action_btn.clicked.connect(self.add_action)
        action_buttons_layout.addWidget(self.add_action_btn)
        
        self.delete_action_btn = QPushButton("Delete Action")
        self.delete_action_btn.clicked.connect(self.delete_action)
        action_buttons_layout.addWidget(self.delete_action_btn)
        
        actions_layout.addLayout(action_buttons_layout)
        
        # Actions table
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(7)
        self.actions_table.setHorizontalHeaderLabels(["Action", "Time (ms)", "X", "Y", "Details", "Random Radius (px)", "Random Time (±ms)"])
        self.actions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.actions_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.actions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.actions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.actions_table.itemDoubleClicked.connect(self.edit_action)
        self.actions_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.actions_table.customContextMenuRequested.connect(self.show_context_menu)
        
        actions_layout.addWidget(self.actions_table)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        self.setLayout(layout)
        
        # Setup timer to update coordinates
        self.coord_timer = QTimer(self)
        self.coord_timer.timeout.connect(self.update_coordinates)
        self.coord_timer.start(100)  # Update every 100ms
        
        # Setup recording timer
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_recording_time)
        
        # Apply permissions
        self.apply_permissions()
    
    def apply_permissions(self):
        # Recorder tab permissions
        can_record = 'record_macros' in self.permissions
        can_play = 'play_macros' in self.permissions
        
        self.save_btn.setEnabled('edit_scripts' in self.permissions and len(self.current_actions) > 0)
        self.play_btn.setEnabled(can_play and len(self.current_actions) > 0)
        self.add_action_btn.setEnabled('edit_scripts' in self.permissions)
        self.delete_action_btn.setEnabled('edit_scripts' in self.permissions)
    
    def toggle_recording_mode(self):
        # Ensure only one mode is selected
        sender = self.sender()
        if sender == self.continuous_mode_radio and sender.isChecked():
            self.hotkey_mode_radio.setChecked(False)
            self.continuous_mode = True
        elif sender == self.hotkey_mode_radio and sender.isChecked():
            self.continuous_mode_radio.setChecked(False)
            self.continuous_mode = False
    
    def update_coordinates(self):
        try:
            x, y = pyautogui.position()
            self.coord_label.setText(f"X: {x}, Y: {y}")
            
            # Get pixel color
            pixel_color = pyautogui.screenshot().getpixel((x, y))
            self.color_label.setText(f"RGB: {pixel_color[0]}, {pixel_color[1]}, {pixel_color[2]}")
        except Exception as e:
            print(f"Error updating coordinates: {e}")
    
    def update_recording_time(self):
        """Update the recording timer display"""
        self.recording_time = self.recording_time.addSecs(1)
        self.timer_display.setText(self.recording_time.toString("hh:mm:ss"))
    
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
            
            # Stop timer
            self.recording_timer.stop()
            
            self.play_btn.setEnabled('play_macros' in self.permissions)
            self.save_btn.setEnabled('edit_scripts' in self.permissions)
        else:
            # Start recording
            self.recording_thread = RecordingThread(continuous_mode=self.continuous_mode)
            self.recording_thread.action_recorded.connect(self.on_action_recorded)
            
            # Clear previous recording
            self.current_actions = []
            self.actions_table.setRowCount(0)
            
            # Reset and start timer
            self.recording_time = QTime(0, 0, 0)
            self.timer_display.setText("00:00:00")
            self.recording_timer.start(1000)  # Update every second
            
            # Start the thread
            self.recording_thread.start()
            self.play_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            
            # Setup mouse and keyboard listeners
            self.setup_listeners()
    
    def capture_position(self):
        """Capture current cursor position in hotkey mode"""
        if self.recording_thread and self.recording_thread.running and not self.continuous_mode:
            self.recording_thread.add_position()
    
    def setup_listeners(self):
        # Mouse listener for clicks
        def on_mouse_click(x, y, button, pressed):
            if not self.recording_thread or not self.recording_thread.running:
                return False
            
            if pressed:
                self.recording_thread.add_action('click', x=x, y=y, button=button, pressed=True)
            else:
                # For tracking duration
                self.recording_thread.add_action('click', x=x, y=y, button=button, pressed=False)
            return True
        
        # Keyboard listener for key presses
        def on_key_press(key):
            if not self.recording_thread or not self.recording_thread.running:
                return False
            
            try:
                # For normal characters
                key_char = key.char
                self.recording_thread.add_action('keydown', key=key_char)
            except AttributeError:
                # For special keys
                key_name = str(key).replace('Key.', '')
                self.recording_thread.add_action('keydown', key=key_name)
            return True
        
        def on_key_release(key):
            if not self.recording_thread or not self.recording_thread.running:
                return False
            
            try:
                # For normal characters
                key_char = key.char
                self.recording_thread.add_action('keyup', key=key_char)
            except AttributeError:
                # For special keys
                key_name = str(key).replace('Key.', '')
                self.recording_thread.add_action('keyup', key=key_name)
            return True
        
        # Start listeners
        self.mouse_listener = mouse.Listener(on_click=on_mouse_click)
        self.mouse_listener.start()
        
        self.keyboard_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
        self.keyboard_listener.start()
    
    def on_action_recorded(self, action):
        # Add action to the table
        row = self.actions_table.rowCount()
        self.actions_table.insertRow(row)
        
        # Set action type
        action_type = action['type']
        if action_type == 'click':
            button = action.get('button', 'left')
            pressed = action.get('pressed', True)
            if pressed:
                action_text = f"{button.capitalize()} click"
            else:
                action_text = f"{button.capitalize()} release"
        elif action_type == 'move':
            action_text = "Move"
        elif action_type == 'keydown':
            action_text = f"Key down"
        elif action_type == 'keyup':
            action_text = f"Key up"
        else:
            action_text = action_type.capitalize()
        
        self.actions_table.setItem(row, 0, QTableWidgetItem(action_text))
        
        # Set time
        time_item = QTableWidgetItem(str(action['time']))
        time_item.setData(Qt.UserRole, action['time'])
        self.actions_table.setItem(row, 1, time_item)
        
        # Set X and Y coordinates if applicable
        if 'x' in action and 'y' in action:
            self.actions_table.setItem(row, 2, QTableWidgetItem(str(action['x'])))
            self.actions_table.setItem(row, 3, QTableWidgetItem(str(action['y'])))
        else:
            self.actions_table.setItem(row, 2, QTableWidgetItem(""))
            self.actions_table.setItem(row, 3, QTableWidgetItem(""))
        
        # Set details
        details = ""
        if action_type == 'keydown' or action_type == 'keyup':
            details = f"Key: {action.get('key', '')}"
            if 'duration' in action and action['duration'] > 0:
                details += f", Duration: {action['duration']}ms"
        elif action_type == 'click' and 'duration' in action and action['duration'] > 0:
            details = f"Duration: {action['duration']}ms"
        
        self.actions_table.setItem(row, 4, QTableWidgetItem(details))
        
        # Set randomization values
        random_radius_item = QTableWidgetItem(str(action.get('random_radius', 0)))
        self.actions_table.setItem(row, 5, random_radius_item)
        
        random_time_item = QTableWidgetItem(str(action.get('random_time', 0)))
        self.actions_table.setItem(row, 6, random_time_item)
        
        # Store the full action in the first column's user role
        self.actions_table.item(row, 0).setData(Qt.UserRole, action)
        
        # Add to current actions
        self.current_actions.append(action)
        
        # Scroll to the new row
        self.actions_table.scrollToItem(self.actions_table.item(row, 0))
        
        # Enable save button if we have actions and permission
        if 'edit_scripts' in self.permissions and len(self.current_actions) > 0:
            self.save_btn.setEnabled(True)
    
    def show_context_menu(self, position):
        """Show context menu for actions table"""
        menu = QMenu()
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        
        # Add special action for auto-incrementing text
        increment_action = menu.addAction("Auto-increment Text")
        
        action = menu.exec_(self.actions_table.mapToGlobal(position))
        
        if action == edit_action:
            self.edit_action(self.actions_table.itemAt(position))
        elif action == delete_action:
            self.delete_selected_action()
        elif action == increment_action:
            self.setup_auto_increment()
    
    def setup_auto_increment(self):
        """Setup auto-incrementing text for selected action"""
        selected_rows = self.actions_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an action first.")
            return
        
        row = selected_rows[0].row()
        action_item = self.actions_table.item(row, 0)
        if not action_item:
            return
        
        action = action_item.data(Qt.UserRole)
        if not action or action['type'] not in ['keydown', 'keyup']:
            QMessageBox.warning(self, "Warning", "Auto-increment only works with key actions.")
            return
        
        # Get the current key text
        key_text = action.get('key', '')
        
        # Create dialog for auto-increment setup
        dialog = QDialog(self)
        dialog.setWindowTitle("Auto-increment Setup")
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Text input
        text_input = QLineEdit(key_text)
        text_input.setPlaceholderText("Enter text with number (e.g., meheart0001)")
        form.addRow("Text:", text_input)
        
        layout.addLayout(form)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        # If dialog is accepted, update the action
        if dialog.exec_() == QDialog.Accepted:
            text = text_input.text()
            
            # Check if text contains a number
            import re
            match = re.search(r'\d+', text)
            if not match:
                QMessageBox.warning(self, "Warning", "Text must contain a number for auto-increment.")
                return
            
            # Set the auto-increment flag and text
            action['key'] = text
            action['auto_increment'] = True
            
            # Update the table
            self.update_action_in_table(row, action)
            
            # Update the action in the list
            self.current_actions[row] = action
    
    def add_action(self):
        """Add a new action manually"""
        # Check permission
        if 'edit_scripts' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit scripts.")
            return
        
        # Create dialog for new action
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Action")
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Action type
        action_type = QComboBox()
        action_type.addItems(["Move", "Left click", "Right click", "Middle click", "Key press"])
        form.addRow("Action type:", action_type)
        
        # Time input
        time_input = QSpinBox()
        time_input.setRange(0, 999999)
        time_input.setValue(0)
        form.addRow("Time (ms):", time_input)
        
        # X and Y coordinates
        x_input = QSpinBox()
        x_input.setRange(0, 9999)
        x_input.setValue(0)
        
        y_input = QSpinBox()
        y_input.setRange(0, 9999)
        y_input.setValue(0)
        
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(x_input)
        coord_layout.addWidget(y_input)
        form.addRow("Coordinates (X, Y):", coord_layout)
        
        # Key input (for key press)
        key_input = QLineEdit()
        key_input.setPlaceholderText("Key to press")
        form.addRow("Key:", key_input)
        
        # Duration
        duration_input = QSpinBox()
        duration_input.setRange(0, 10000)
        duration_input.setValue(0)
        form.addRow("Duration (ms):", duration_input)
        
        # Randomization settings
        random_radius = QSpinBox()
        random_radius.setRange(0, 100)
        random_radius.setValue(0)
        form.addRow("Random Radius (px):", random_radius)
        
        random_time = QSpinBox()
        random_time.setRange(0, 1000)
        random_time.setValue(0)
        form.addRow("Random Time (±ms):", random_time)
        
        layout.addLayout(form)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        # Connect action type changes to show/hide relevant fields
        def update_form_visibility():
            is_key_action = action_type.currentText() == "Key press"
            is_mouse_action = action_type.currentText() in ["Left click", "Right click", "Middle click", "Move"]
            
            key_input.setEnabled(is_key_action)
            x_input.setEnabled(is_mouse_action)
            y_input.setEnabled(is_mouse_action)
            random_radius.setEnabled(is_mouse_action)
        
        action_type.currentTextChanged.connect(update_form_visibility)
        update_form_visibility()
        
        # If dialog is accepted, create the action
        if dialog.exec_() == QDialog.Accepted:
            action_text = action_type.currentText()
            
            # Create action based on type
            if action_text == "Move":
                action = {
                    'type': 'move',
                    'x': x_input.value(),
                    'y': y_input.value(),
                    'time': time_input.value(),
                    'random_radius': random_radius.value(),
                    'random_time': random_time.value()
                }
            elif action_text in ["Left click", "Right click", "Middle click"]:
                button = action_text.lower().split()[0]
                action = {
                    'type': 'click',
                    'x': x_input.value(),
                    'y': y_input.value(),
                    'button': button,
                    'time': time_input.value(),
                    'duration': duration_input.value(),
                    'random_radius': random_radius.value(),
                    'random_time': random_time.value()
                }
            elif action_text == "Key press":
                action = {
                    'type': 'keypress',
                    'key': key_input.text(),
                    'time': time_input.value(),
                    'duration': duration_input.value(),
                    'random_time': random_time.value()
                }
            
            # Add action to the list and table
            self.on_action_recorded(action)
    
    def delete_action(self):
        """Delete the selected action"""
        selected_rows = self.actions_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select an action to delete.")
            return
        
        self.delete_selected_action()
    
    def delete_selected_action(self):
        """Delete the currently selected action"""
        # Check permission
        if 'edit_scripts' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit scripts.")
            return
            
        selected_rows = self.actions_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Remove from table
        self.actions_table.removeRow(row)
        
        # Remove from actions list
        if row < len(self.current_actions):
            self.current_actions.pop(row)
        
        # Update UI state
        self.play_btn.setEnabled('play_macros' in self.permissions and len(self.current_actions) > 0)
        self.save_btn.setEnabled('edit_scripts' in self.permissions and len(self.current_actions) > 0)
    
    def edit_action(self, item):
        # Only allow editing when not recording
        if self.recording_thread and self.recording_thread.running:
            return
        
        # Check permission
        if 'edit_scripts' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit scripts.")
            return
        
        # Get the row
        row = item.row()
        
        # Get the action from the first column
        action_item = self.actions_table.item(row, 0)
        if not action_item:
            return
        
        action = action_item.data(Qt.UserRole)
        if not action:
            return
        
        # Create a dialog to edit the action
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Action")
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Time input
        time_input = QSpinBox()
        time_input.setRange(0, 999999)
        time_input.setValue(action['time'])
        form.addRow("Time (ms):", time_input)
        
        # Different fields based on action type
        if action['type'] == 'click' or action['type'] == 'move':
            x_input = QSpinBox()
            x_input.setRange(0, 9999)
            x_input.setValue(action['x'])
            
            y_input = QSpinBox()
            y_input.setRange(0, 9999)
            y_input.setValue(action['y'])
            
            form.addRow("X coordinate:", x_input)
            form.addRow("Y coordinate:", y_input)
            
            if action['type'] == 'click':
                button_input = QComboBox()
                button_input.addItems(['left', 'right', 'middle'])
                button_index = button_input.findText(action.get('button', 'left'))
                if button_index >= 0:
                    button_input.setCurrentIndex(button_index)
                form.addRow("Button:", button_input)
                
                duration_input = QSpinBox()
                duration_input.setRange(0, 10000)
                duration_input.setValue(action.get('duration', 0))
                form.addRow("Duration (ms):", duration_input)
        
        elif action['type'] == 'keydown' or action['type'] == 'keyup' or action['type'] == 'keypress':
            key_input = QLineEdit()
            key_input.setText(action.get('key', ''))
            form.addRow("Key:", key_input)
            
            if action['type'] == 'keyup' or action['type'] == 'keypress':
                duration_input = QSpinBox()
                duration_input.setRange(0, 10000)
                duration_input.setValue(action.get('duration', 0))
                form.addRow("Duration (ms):", duration_input)
            
            # Auto-increment checkbox
            auto_increment = QCheckBox("Auto-increment numbers in text")
            auto_increment.setChecked(action.get('auto_increment', False))
            form.addRow("", auto_increment)
        
        # Randomization settings
        random_radius = QSpinBox()
        random_radius.setRange(0, 100)
        random_radius.setValue(action.get('random_radius', 0))
        form.addRow("Random Radius (px):", random_radius)
        
        random_time = QSpinBox()
        random_time.setRange(0, 1000)
        random_time.setValue(action.get('random_time', 0))
        form.addRow("Random Time (±ms):", random_time)
        
        layout.addLayout(form)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)```python
        dialog.setLayout(layout)
        
        # If dialog is accepted, update the action
        if dialog.exec_() == QDialog.Accepted:
            # Update action time
            action['time'] = time_input.value()
            
            # Update action-specific fields
            if action['type'] == 'click' or action['type'] == 'move':
                action['x'] = x_input.value()
                action['y'] = y_input.value()
                
                if action['type'] == 'click':
                    action['button'] = button_input.currentText()
                    action['duration'] = duration_input.value()
            
            elif action['type'] == 'keydown' or action['type'] == 'keyup' or action['type'] == 'keypress':
                action['key'] = key_input.text()
                action['auto_increment'] = auto_increment.isChecked()
                
                if action['type'] == 'keyup' or action['type'] == 'keypress':
                    action['duration'] = duration_input.value()
            
            # Update randomization settings
            action['random_radius'] = random_radius.value()
            action['random_time'] = random_time.value()
            
            # Update the table
            self.update_action_in_table(row, action)
            
            # Update the action in the list
            self.current_actions[row] = action
    
    def update_action_in_table(self, row, action):
        """Update the table row with the action data"""
        # Set action type
        action_type = action['type']
        if action_type == 'click':
            button = action.get('button', 'left')
            pressed = action.get('pressed', True)
            if pressed:
                action_text = f"{button.capitalize()} click"
            else:
                action_text = f"{button.capitalize()} release"
        elif action_type == 'move':
            action_text = "Move"
        elif action_type == 'keydown':
            action_text = f"Key down"
        elif action_type == 'keyup':
            action_text = f"Key up"
        elif action_type == 'keypress':
            action_text = f"Key press"
        else:
            action_text = action_type.capitalize()
        
        self.actions_table.item(row, 0).setText(action_text)
        self.actions_table.item(row, 0).setData(Qt.UserRole, action)
        
        # Set time
        self.actions_table.item(row, 1).setText(str(action['time']))
        self.actions_table.item(row, 1).setData(Qt.UserRole, action['time'])
        
        # Set X and Y coordinates if applicable
        if 'x' in action and 'y' in action:
            self.actions_table.item(row, 2).setText(str(action['x']))
            self.actions_table.item(row, 3).setText(str(action['y']))
        
        # Set details
        details = ""
        if action_type in ['keydown', 'keyup', 'keypress']:
            details = f"Key: {action.get('key', '')}"
            if action.get('auto_increment', False):
                details += " (auto-increment)"
            if 'duration' in action and action['duration'] > 0:
                details += f", Duration: {action['duration']}ms"
        elif action_type == 'click' and 'duration' in action and action['duration'] > 0:
            details = f"Duration: {action['duration']}ms"
        
        self.actions_table.item(row, 4).setText(details)
        
        # Set randomization values
        self.actions_table.item(row, 5).setText(str(action.get('random_radius', 0)))
        self.actions_table.item(row, 6).setText(str(action.get('random_time', 0)))
    
    def play_recording(self):
        # Check permission
        if 'play_macros' not in self.permissions:
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to play macros.")
            return
            
        if not self.current_actions:
            QMessageBox.warning(self, "Warning", "No actions to play.")
            return
        
        # Process auto-increment for key actions
        actions_to_play = self.process_auto_increment()
        
        # Disable UI elements
        self.play_btn.setText("Stop")
        self.play_btn.clicked.disconnect()
        self.play_btn.clicked.connect(self.stop_playback)
        
        # Create and start playback thread
        self.playback_thread = PlaybackThread(
            actions_to_play,
            self.speed_input.value(),
            self.repeat_input.value()
        )
        self.playback_thread.playback_finished.connect(self.on_playback_finished)
        self.playback_thread.action_played.connect(self.on_action_played)
        self.playback_thread.start()
    
    def process_auto_increment(self):
        """Process auto-incrementing text in actions"""
        import re
        
        # Create a copy of the actions to modify
        actions = []
        counter = 1
        
        for action in self.current_actions:
            action_copy = action.copy()
            
            # Check if this is a key action with auto-increment
            if action.get('auto_increment', False) and 'key' in action:
                key_text = action['key']
                
                # Find numbers in the text
                match = re.search(r'(\d+)', key_text)
                if match:
                    # Get the number and its position
                    num_str = match.group(1)
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                    
                    # Calculate the new number with same number of digits
                    new_num = str(int(num_str) + counter - 1).zfill(len(num_str))
                    
                    # Replace the number in the text
                    new_text = key_text[:start_pos] + new_num + key_text[end_pos:]
                    action_copy['key'] = new_text
            
            actions.append(action_copy)
        
        return actions
    
    def stop_playback(self):
        if self.playback_thread and self.playback_thread.running:
            self.playback_thread.stop()
            self.playback_thread.wait()
            self.on_playback_finished()
    
    def on_playback_finished(self):
        # Re-enable UI elements
        self.play_btn.setText("Play")
        self.play_btn.clicked.disconnect()
        self.play_btn.clicked.connect(self.play_recording)
        
        # Clear selection in actions table
        self.actions_table.clearSelection()
    
    def on_action_played(self, index):
        # Highlight the current action in the table
        if index < self.actions_table.rowCount():
            self.actions_table.selectRow(index)
            self.actions_table.scrollToItem(self.actions_table.item(index, 0))
    
    def clear_recording(self):
        self.current_actions = []
        self.actions_table.setRowCount(0)
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
        
        # Update actions table
        self.actions_table.setRowCount(0)
        for action in self.current_actions:
            self.on_action_recorded(action)
        
        # Enable play button
        self.play_btn.setEnabled('play_macros' in self.permissions)
        self.save_btn.setEnabled('edit_scripts' in self.permissions)