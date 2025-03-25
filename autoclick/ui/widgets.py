"""
Custom widgets for the Auto Click application.
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QColor, QPainter, QPen
import pyautogui
import numpy as np

class PixelDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.setMaximumSize(150, 150)
        self.pixmap = QPixmap(150, 150)
        self.pixmap.fill(Qt.white)
        self.current_pos = QPoint(0, 0)
        self.zoom_factor = 10  # Each pixel becomes 10x10
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_pixel_display)
        self.update_timer.start(100)  # Update every 100ms
        
    def update_pixel_display(self):
        try:
            x, y = pyautogui.position()
            self.current_pos = QPoint(x, y)
            
            # Capture screen area around cursor
            screenshot = pyautogui.screenshot(region=(x-7, y-7, 15, 15))
            img = np.array(screenshot)
            
            # Create a new pixmap
            self.pixmap = QPixmap(150, 150)
            self.pixmap.fill(Qt.white)
            
            # Draw the zoomed pixels
            qp = QPainter(self.pixmap)
            for i in range(15):
                for j in range(15):
                    try:
                        r, g, b = img[j, i]  # Note: numpy array is [y, x]
                        qp.fillRect(i*self.zoom_factor, j*self.zoom_factor, 
                                   self.zoom_factor, self.zoom_factor, 
                                   QColor(r, g, b))
                    except IndexError:
                        pass
            
            # Draw crosshair at center
            qp.setPen(QPen(Qt.red, 1))
            center = 7 * self.zoom_factor + self.zoom_factor // 2
            qp.drawLine(center, 0, center, 150)
            qp.drawLine(0, center, 150, center)
            qp.end()
            
            self.update()
        except Exception as e:
            print(f"Error updating pixel display: {e}")
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)