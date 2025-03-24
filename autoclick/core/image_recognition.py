"""
Image recognition functionality for the Auto Click application.
"""
import cv2
import numpy as np
import pyautogui

class ImageRecognitionTool:
    def __init__(self):
        self.templates = {}  # Store loaded templates
    
    def load_template(self, name, image_path):
        try:
            template = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if template is None:
                return False
            self.templates[name] = template
            return True
        except Exception as e:
            print(f"Error loading template: {e}")
            return False
    
    def find_on_screen(self, template_name, confidence=0.8):
        if template_name not in self.templates:
            return None
        
        template = self.templates[template_name]
        screenshot = pyautogui.screenshot()
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            # Get the dimensions of the template
            h, w = template.shape[:2]
            # Calculate the center point of the match
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y, max_val)
        
        return None