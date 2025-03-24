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
    
    def __init__(self, actions, speed_factor=1.0, repeat_count=1, randomize=False, randomize_factor=0.1):
        super().__init__()
        self.actions = actions
        self.speed_factor = speed_factor
        self.repeat_count = repeat_count
        self.running = False
        self.randomize = randomize
        self.randomize_factor = randomize_factor
    
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
                    delay = (action['time'] - last_time) / self.speed_factor
                    
                    # Add randomization if enabled
                    if self.randomize:
                        random_factor = 1.0 + (np.random.random() * 2 - 1) * self.randomize_factor
                        delay *= random_factor
                    
                    time.sleep(max(0, delay))
                
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
                if self.randomize:
                    # Add slight randomization to click position
                    rand_x = action['x'] + int((np.random.random() * 2 - 1) * 3)
                    rand_y = action['y'] + int((np.random.random() * 2 - 1) * 3)
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