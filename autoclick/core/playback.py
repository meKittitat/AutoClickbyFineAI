"""
Playback functionality for the Auto Click application.
"""
import time
import pyautogui
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

class PlaybackThread(QThread):
    playback_finished = pyqtSignal()
    action_played = pyqtSignal(int)
    
    def __init__(self, actions, speed_factor=1.0, repeat_count=1):
        super().__init__()
        self.actions = actions
        self.speed_factor = speed_factor
        self.repeat_count = repeat_count
        self.running = False
    
    def run(self):
        self.running = True
        
        for _ in range(self.repeat_count):
            if not self.running:
                break
                
            last_time = 0
            for i, action in enumerate(self.actions):
                if not self.running:
                    break
                
                # Calculate delay
                if i > 0:
                    delay_ms = (action['time'] - last_time) / self.speed_factor
                    
                    # Add randomization if enabled for this action
                    random_time = action.get('random_time', 0)
                    if random_time > 0:
                        delay_ms += np.random.randint(-random_time, random_time)
                    
                    # Ensure delay is not negative
                    delay_ms = max(0, delay_ms)
                    
                    # Convert ms to seconds for sleep
                    time.sleep(delay_ms / 1000.0)
                
                # Execute action
                self._execute_action(action)
                last_time = action['time']
                
                # Emit signal for UI update
                self.action_played.emit(i)
        
        self.running = False
        self.playback_finished.emit()
    
    def _execute_action(self, action):
        try:
            if action['type'] == 'click':
                # Get randomization radius
                random_radius = action.get('random_radius', 0)
                
                if random_radius > 0:
                    # Add randomization to click position
                    rand_x = action['x'] + np.random.randint(-random_radius, random_radius)
                    rand_y = action['y'] + np.random.randint(-random_radius, random_radius)
                    pyautogui.click(rand_x, rand_y, button=action.get('button', 'left'))
                else:
                    pyautogui.click(action['x'], action['y'], button=action.get('button', 'left'))
                    
            elif action['type'] == 'move':
                pyautogui.moveTo(action['x'], action['y'])
                
            elif action['type'] == 'keypress':
                pyautogui.press(action['key'])
                
            elif action['type'] == 'keydown':
                pyautogui.keyDown(action['key'])
                
            elif action['type'] == 'keyup':
                pyautogui.keyUp(action['key'])
                
            elif action['type'] == 'scroll':
                pyautogui.scroll(action['amount'])
        except Exception as e:
            print(f"Error executing action: {e}")
    
    def stop(self):
        self.running = False