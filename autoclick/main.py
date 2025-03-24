"""
Main entry point for the Auto Click application.
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from autoclick.config import APP_ICON
from autoclick.database.manager import DatabaseManager
from autoclick.core.image_recognition import ImageRecognitionTool
from autoclick.ui.main_window import MainWindow
from autoclick.utils.system_utils import ensure_app_data_dir

def main():
    # Ensure application data directory exists
    ensure_app_data_dir()
    
    # Create application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for consistent look
    
    # Set application icon
    app_icon = QIcon.fromTheme(APP_ICON)
    app.setWindowIcon(app_icon)
    
    # Initialize database and image recognition
    db_manager = DatabaseManager()
    image_recognition = ImageRecognitionTool()
    
    # Create and show main window
    window = MainWindow(db_manager, image_recognition)
    
    # Start application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()