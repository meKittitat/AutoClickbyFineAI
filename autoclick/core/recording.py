"""
Recording functionality for the Auto Click application.
"""
import time
import pyautogui
from PyQt5.QtCore import QThread, pyqtSignal
import json

class RecordingThread(QThread):
    action_recorded = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.actions = []
        self.start_time = 0
        self.last_position = None
        self.record_movement = True
        self.movement_threshold = 5  # pixels
        self.movement_interval = 0.1  # seconds
        self.last_movement_time = 0
    
    def run(self):
        self.running = True
        self.start_time = time.time()
        self.last_position = pyautogui.position()
        self.last_movement_time = time.time()
        
        while self.running:
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
                        'time': current_time - self.start_time
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
                
        action = {
            'type': action_type,
            'time': time.time() - self.start_time,
            **serializable_kwargs
        }
        self.actions.append(action)
        self.action_recorded.emit(action)

def format_action(action):
    """Format an action for display in the UI."""
    if action['type'] == 'click':
        return f"[{action['time']:.2f}s] Click at ({action['x']}, {action['y']})"
    elif action['type'] == 'move':
        return f"[{action['time']:.2f}s] Move to ({action['x']}, {action['y']})"
    elif action['type'] == 'keypress':
        return f"[{action['time']:.2f}s] Press key '{action['key']}'"
    elif action['type'] == 'scroll':
        return f"[{action['time']:.2f}s] Scroll {action['amount']}"
    return f"[{action['time']:.2f}s] {action['type']}"