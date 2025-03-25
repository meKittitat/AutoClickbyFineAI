"""
Recording functionality for the Auto Click application.
"""
import time
import pyautogui
from PyQt5.QtCore import QThread, pyqtSignal
import json

class RecordingThread(QThread):
    action_recorded = pyqtSignal(dict)
    
    def __init__(self, continuous_mode=True):
        super().__init__()
        self.running = False
        self.actions = []
        self.start_time = 0
        self.last_position = None
        self.record_movement = True
        self.movement_threshold = 5  # pixels
        self.movement_interval = 0.1  # seconds
        self.last_movement_time = 0
        self.continuous_mode = continuous_mode  # True for continuous recording, False for hotkey-based
        self.last_press_time = {}  # Track when keys/buttons were pressed
    
    def run(self):
        self.running = True
        self.start_time = time.time()
        self.last_position = pyautogui.position()
        self.last_movement_time = time.time()
        
        while self.running:
            # Only record movements in continuous mode
            if self.continuous_mode:
                # Record mouse position changes
                current_pos = pyautogui.position()
                current_time = time.time()
                
                # Record significant mouse movements
                if self.record_movement and (current_time - self.last_movement_time) >= self.movement_interval:
                    x_diff = abs(current_pos[0] - self.last_position[0])
                    y_diff = abs(current_pos[1] - self.last_position[1])
                    
                    if x_diff > self.movement_threshold or y_diff > self.movement_threshold:
                        action = {
                            'type': 'move',
                            'x': current_pos[0],
                            'y': current_pos[1],
                            'time': int((current_time - self.start_time) * 1000),  # Convert to ms
                            'random_radius': 0,
                            'random_time': 0
                        }
                        self.action_recorded.emit(action)
                        self.actions.append(action)
                        self.last_position = current_pos
                        self.last_movement_time = current_time
            
            # Small sleep to prevent high CPU usage
            time.sleep(0.01)
    
    def stop(self):
        self.running = False
    
    def add_action(self, action_type, **kwargs):
        # Convert any non-serializable objects to strings
        serializable_kwargs = {}
        for key, value in kwargs.items():
            if key == 'button':
                # Convert pynput Button objects to string
                serializable_kwargs[key] = str(value).split('.')[-1].lower()
            else:
                serializable_kwargs[key] = value
        
        current_time = time.time()
        
        # Calculate duration for press/release actions
        duration = 0
        if action_type == 'click':
            button = serializable_kwargs.get('button', 'left')
            key = f"mouse_{button}"
            if key in self.last_press_time:
                duration = int((current_time - self.last_press_time[key]) * 1000)  # ms
                del self.last_press_time[key]
            else:
                self.last_press_time[key] = current_time
        elif action_type == 'keydown':
            key = serializable_kwargs.get('key', '')
            self.last_press_time[key] = current_time
        elif action_type == 'keyup':
            key = serializable_kwargs.get('key', '')
            if key in self.last_press_time:
                duration = int((current_time - self.last_press_time[key]) * 1000)  # ms
                del self.last_press_time[key]
        
        # Create the action with default randomization values
        action = {
            'type': action_type,
            'time': int((current_time - self.start_time) * 1000),  # Convert to ms
            'random_radius': 0,
            'random_time': 0,
            'duration': duration,
            **serializable_kwargs
        }
        
        self.actions.append(action)
        self.action_recorded.emit(action)
    
    def add_position(self):
        """Add current cursor position (for hotkey-based recording)"""
        if not self.continuous_mode:
            x, y = pyautogui.position()
            current_time = time.time()
            
            action = {
                'type': 'move',
                'x': x,
                'y': y,
                'time': int((current_time - self.start_time) * 1000),  # Convert to ms
                'random_radius': 0,
                'random_time': 0
            }
            
            self.action_recorded.emit(action)
            self.actions.append(action)

def format_action(action):
    """Format an action for display in the UI."""
    time_ms = action['time']
    
    if action['type'] == 'click':
        button = action.get('button', 'left')
        duration = action.get('duration', 0)
        return f"[{time_ms}ms] {button.capitalize()} click at ({action['x']}, {action['y']}) - Duration: {duration}ms"
    elif action['type'] == 'move':
        return f"[{time_ms}ms] Move to ({action['x']}, {action['y']})"
    elif action['type'] == 'keypress':
        return f"[{time_ms}ms] Press key '{action['key']}'"
    elif action['type'] == 'keydown':
        return f"[{time_ms}ms] Key down '{action['key']}'"
    elif action['type'] == 'keyup':
        duration = action.get('duration', 0)
        return f"[{time_ms}ms] Key up '{action['key']}' - Duration: {duration}ms"
    elif action['type'] == 'scroll':
        return f"[{time_ms}ms] Scroll {action['amount']}"
    
    return f"[{time_ms}ms] {action['type']}"