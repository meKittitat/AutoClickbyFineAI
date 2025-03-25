"""
Configuration constants for the Auto Click application.
"""

# Application version
APP_VERSION = "1.0.0"

# Define user roles and permissions
USER_ROLES = {
    'admin': 'Administrator',
    'power_user': 'Power User',
    'standard': 'Standard User',
    'limited': 'Limited User'
}

# Define permissions
PERMISSIONS = {
    'record_macros': 'Record Macros',
    'play_macros': 'Play Macros',
    'edit_scripts': 'Edit Scripts',
    'import_export': 'Import/Export Scripts',
    'create_profiles': 'Create Profiles',
    'use_image_recognition': 'Use Image Recognition',
    'manage_users': 'Manage Users',
    'advanced_settings': 'Access Advanced Settings'
}

# Default permissions for each role
DEFAULT_ROLE_PERMISSIONS = {
    'admin': list(PERMISSIONS.keys()),
    'power_```python
    'admin': list(PERMISSIONS.keys()),
    'power_user': ['record_macros', 'play_macros', 'edit_scripts', 'import_export', 'create_profiles', 'use_image_recognition'],
    'standard': ['record_macros', 'play_macros', 'edit_scripts', 'create_profiles'],
    'limited': ['play_macros']
}

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

# Application settings
APP_NAME = "Auto Click"
APP_ICON = "input-mouse"
DATABASE_FILE = "autoclick.db"