# Auto Click Program

A comprehensive auto-clicking and macro recording application built with Python and PyQt5.

## Features

- **User-friendly Interface**: Coordinate selector and live pixel display
- **Recording Capabilities**: Record mouse clicks, keyboard presses, movements, and delays
- **Script Management**: Import/export scripts in JSON format
- **User Authentication**: Secure login system with profile management
- **User Management**: Admin can create users with specific permissions
- **Macro Profiles**: Create multiple profiles with custom hotkeys
- **Advanced Features**: 
  - Randomization to avoid detection
  - Playback speed adjustment
  - Repeat count settings
  - System tray integration
  - Image recognition for dynamic targets

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python main.py
```

## Usage

### Registration and Login

1. When you first run the application, you'll be prompted to register or login
2. Create a new account with a username and password (minimum 6 characters)
3. Default admin account: username: `admin`, password: `admin123`

### User Management (Admin only)

1. Navigate to the "User Management" tab
2. Click "Manage Users" to open the user management dialog
3. Create new users with specific roles and permissions
4. Edit existing users to change their roles and permissions
5. Delete users when they are no longer needed

### Recording Macros

1. Navigate to the "Recorder" tab
2. Enter a name and description for your script
3. Click "Start Recording"
4. Perform the actions you want to record (mouse clicks, movements, keyboard presses)
5. Click "Stop Recording" when finished
6. Click "Save Script" to save your recording

### Playing Back Macros

1. Adjust playback settings (speed, repeat count, randomization)
2. Click "Play" to execute the recorded actions
3. Press ESC to stop playback at any time

### Creating Profiles

1. Navigate to the "Profiles" tab
2. Click "New Profile"
3. Enter a name and assign a hotkey
4. Select a script to associate with the profile
5. Configure playback settings
6. Click "OK" to save the profile

### Settings

The "Settings" tab allows you to configure:
- General application behavior
- Recording parameters
- Randomization factors
- Hotkeys

## User Roles and Permissions

The application supports the following user roles:

- **Administrator**: Full access to all features
- **Power User**: Can record, play, edit scripts, import/export, create profiles, and use image recognition
- **Standard User**: Can record, play, edit scripts, and create profiles
- **Limited User**: Can only play macros

Permissions can be customized for each user regardless of their role.

## Security Features

- Password hashing for secure authentication
- Permission-based access control
- Safeguards against infinite loops
- Error handling to prevent crashes

## System Requirements

- Python 3.6 or higher
- PyQt5
- OpenCV (for image recognition features)
- Windows, macOS, or Linux operating system