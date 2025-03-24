"""
System-related utilities for the Auto Click application.
"""
import sys
import os

def is_windows():
    """Check if the system is Windows."""
    return sys.platform.startswith('win')

def is_mac():
    """Check if the system is macOS."""
    return sys.platform == 'darwin'

def is_linux():
    """Check if the system is Linux."""
    return sys.platform.startswith('linux')

def get_app_data_path():
    """Get the path to store application data."""
    if is_windows():
        return os.path.join(os.environ['APPDATA'], 'AutoClick')
    elif is_mac():
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'AutoClick')
    else:  # Linux and other platforms
        return os.path.join(os.path.expanduser('~'), '.autoclick')

def ensure_app_data_dir():
    """Ensure the application data directory exists."""
    app_data_path = get_app_data_path()
    if not os.path.exists(app_data_path):
        os.makedirs(app_data_path)
    return app_data_path