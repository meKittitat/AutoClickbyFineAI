"""
Database manager for the Auto Click application.
"""
import sqlite3
import json
import uuid
import hashlib
from datetime import datetime, timedelta

from autoclick.config import DATABASE_FILE, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, DEFAULT_ROLE_PERMISSIONS, PERMISSIONS

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        try:
            self.conn = sqlite3.connect(DATABASE_FILE)
            cursor = self.conn.cursor()
            
            # Create users table with role field
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                role TEXT DEFAULT 'standard',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                time_remaining INTEGER DEFAULT 0,
                lifetime_pass INTEGER DEFAULT 0
            )
            ''')
            
            # Check if password_reset column exists, if not add it
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'password_reset' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN password_reset INTEGER DEFAULT 0")
            
            # Create user permissions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id TEXT,
                permission TEXT,
                PRIMARY KEY (user_id, permission),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create roles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT
            )
            ''')
            
            # Create role permissions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id TEXT,
                permission TEXT,
                PRIMARY KEY (role_id, permission),
                FOREIGN KEY (role_id) REFERENCES roles (id)
            )
            ''')
            
            # Create scripts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scripts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                description TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create profiles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                hotkey TEXT,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create profile_scripts table for many-to-many relationship
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile_scripts (
                profile_id TEXT,
                script_id TEXT,
                execution_order INTEGER,
                execution_time INTEGER DEFAULT 0,
                PRIMARY KEY (profile_id, script_id),
                FOREIGN KEY (profile_id) REFERENCES profiles (id),
                FOREIGN KEY (script_id) REFERENCES scripts (id)
            )
            ''')
            
            # Check if default roles exist, if not create them
            cursor.execute("SELECT COUNT(*) FROM roles")
            if cursor.fetchone()[0] == 0:
                # Create default roles
                for role_id, role_name in USER_ROLES.items():
                    role_uuid = str(uuid.uuid4())
                    cursor.execute(
                        "INSERT INTO roles (id, name, description) VALUES (?, ?, ?)",
                        (role_uuid, role_name, f"Default {role_name} role")
                    )
                    
                    # Add permissions for this role
                    for permission in DEFAULT_ROLE_PERMISSIONS.get(role_id, []):
                        cursor.execute(
                            "INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
                            (role_uuid, permission)
                        )
            
            # Check if admin user exists, if not create one
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            if cursor.fetchone()[0] == 0:
                admin_id = str(uuid.uuid4())
                admin_password = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
                
                # Get admin role ID
                cursor.execute("SELECT id FROM roles WHERE name = 'Administrator'")
                admin_role_id = cursor.fetchone()[0]
                
                cursor.execute(
                    "INSERT INTO users (id, username, password_hash, role, lifetime_pass) VALUES (?, ?, ?, ?, ?)",
                    (admin_id, DEFAULT_ADMIN_USERNAME, admin_password, admin_role_id, 1)
                )
                
                # Add all permissions for admin
                for permission in PERMISSIONS.keys():
                    cursor.execute(
                        "INSERT INTO user_permissions (user_id, permission) VALUES (?, ?)",
                        (admin_id, permission)
                    )
            
            self.conn.commit()
        except Exception as e:
            print(f"Database setup error: {e}")
    
    def create_user(self, username, password, role='standard', permissions=None, created_by=None, time_minutes=0, lifetime_pass=0):
        try:
            cursor = self.conn.cursor()
            user_id = str(uuid.uuid4())
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                "INSERT INTO users (id, username, password_hash, role, created_by, time_remaining, lifetime_pass) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, password_hash, role, created_by, time_minutes, lifetime_pass)
            )
            
            # Add permissions
            if permissions is None:
                # Get permissions from role
                cursor.execute(
                    "SELECT permission FROM role_permissions WHERE role_id = ?",
                    (role,)
                )
                permissions = [row[0] for row in cursor.fetchall()]
            
            for permission in permissions:
                cursor.execute(
                    "INSERT INTO user_permissions (user_id, permission) VALUES (?, ?)",
                    (user_id, permission)
                )
            
            self.conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None  # Username already exists
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def authenticate_user(self, username, password):
        try:
            cursor = self.conn.cursor()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Check if password_reset column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'password_reset' in columns:
                cursor.execute(
                    "SELECT id, role, password_reset, time_remaining, lifetime_pass FROM users WHERE username = ? AND password_hash = ?",
                    (username, password_hash)
                )
                result = cursor.fetchone()
                
                if result:
                    user_id, role, password_reset, time_remaining, lifetime_pass = result
                    
                    # Check if password reset is required
                    if password_reset == 1:
                        return user_id, "reset_required", 0, 0
                    else:
                        return user_id, role, time_remaining, lifetime_pass
            else:
                # Fallback for older database schema
                cursor.execute(
                    "SELECT id, role FROM users WHERE username = ? AND password_hash = ?",
                    (username, password_hash)
                )
                result = cursor.fetchone()
                if result:
                    return result[0], result[1], 0, 0
            
            return None, None, 0, 0
        except Exception as e:
            print(f"Authentication error: {e}")
            return None, None, 0, 0
    
    def update_user_time(self, user_id, additional_minutes):
        """Add time to a user's account"""
        try:
            cursor = self.conn.cursor()
            
            # Get current time remaining
            cursor.execute("SELECT time_remaining FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                current_time = result[0] or 0
                new_time = current_time + additional_minutes
                
                cursor.execute(
                    "UPDATE users SET time_remaining = ? WHERE id = ?",
                    (new_time, user_id)
                )
                self.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error updating user time: {e}")
            return False
    
    def set_user_lifetime_pass(self, user_id, has_lifetime_pass):
        """Set whether a user has a lifetime pass"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE users SET lifetime_pass = ? WHERE id = ?",
                (1 if has_lifetime_pass else 0, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error setting lifetime pass: {e}")
            return False
    
    def decrement_user_time(self, user_id, minutes_used):
        """Decrement a user's remaining time"""
        try:
            cursor = self.conn.cursor()
            
            # Check if user has lifetime pass
            cursor.execute("SELECT lifetime_pass, time_remaining FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                lifetime_pass, time_remaining = result
                
                if lifetime_pass:
                    return True  # No need to decrement time for lifetime pass users
                
                new_time = max(0, time_remaining - minutes_used)
                cursor.execute(
                    "UPDATE users SET time_remaining = ? WHERE id = ?",
                    (new_time, user_id)
                )
                self.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error decrementing user time: {e}")
            return False
    
    def get_user_time_remaining(self, user_id):
        """Get a user's remaining time in minutes"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT time_remaining, lifetime_pass FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                time_remaining, lifetime_pass = result
                if lifetime_pass:
                    return -1  # -1 indicates lifetime pass
                return time_remaining or 0
            return 0
        except Exception as e:
            print(f"Error getting user time: {e}")
            return 0
    
    def reset_user_password(self, user_id):
        """Mark a user's password as needing reset"""
        try:
            cursor = self.conn.cursor()
            
            # Check if password_reset column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'password_reset' in columns:
                cursor.execute(
                    "UPDATE users SET password_reset = 1 WHERE id = ?",
                    (user_id,)
                )
                self.conn.commit()
                return True
            else:
                # Add the column if it doesn't exist
                cursor.execute("ALTER TABLE users ADD COLUMN password_reset INTEGER DEFAULT 0")
                cursor.execute(
                    "UPDATE users SET password_reset = 1 WHERE id = ?",
                    (user_id,)
                )
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Error resetting password: {e}")
            return False
    
    def update_user_password(self, user_id, new_password):
        """Update a user's password and clear the reset flag"""
        try:
            cursor = self.conn.cursor()
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            # Check if password_reset column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'password_reset' in columns:
                cursor.execute(
                    "UPDATE users SET password_hash = ?, password_reset = 0 WHERE id = ?",
                    (password_hash, user_id)
                )
            else:
                # Fallback for older database schema
                cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (password_hash, user_id)
                )
                
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
    
    def get_user_permissions(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT permission FROM user_permissions WHERE user_id = ?",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting user permissions: {e}")
            return []
    
    def get_all_users(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, username, role, created_at, time_remaining, lifetime_pass FROM users ORDER BY username"
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    def get_user_details(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT username, role, time_remaining, lifetime_pass FROM users WHERE id = ?",
                (user_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"Error getting user details: {e}")
            return None
    
    def update_user(self, user_id, role, permissions=None, time_remaining=None, lifetime_pass=None):
        try:
            cursor = self.conn.cursor()
            
            # Update role
            cursor.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (role, user_id)
            )
            
            # Update time remaining if provided
            if time_remaining is not None:
                cursor.execute(
                    "UPDATE users SET time_remaining = ? WHERE id = ?",
                    (time_remaining, user_id)
                )
            
            # Update lifetime pass if provided
            if lifetime_pass is not None:
                cursor.execute(
                    "UPDATE users SET lifetime_pass = ? WHERE id = ?",
                    (1 if lifetime_pass else 0, user_id)
                )
            
            # Update permissions if provided
            if permissions is not None:
                # Delete existing permissions
                cursor.execute(
                    "DELETE FROM user_permissions WHERE user_id = ?",
                    (user_id,)
                )
                
                # Add new permissions
                for permission in permissions:
                    cursor.execute(
                        "INSERT INTO user_permissions (user_id, permission) VALUES (?, ?)",
                        (user_id, permission)
                    )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def delete_user(self, user_id):
        try:
            cursor = self.conn.cursor()
            
            # Delete user permissions
            cursor.execute(
                "DELETE FROM user_permissions WHERE user_id = ?",
                (user_id,)
            )
            
            # Delete user
            cursor.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def create_role(self, name, description, permissions, created_by=None):
        try:
            cursor = self.conn.cursor()
            role_id = str(uuid.uuid4())
            
            cursor.execute(
                "INSERT INTO roles (id, name, description, created_by) VALUES (?, ?, ?, ?)",
                (role_id, name, description, created_by)
            )
            
            # Add permissions
            for permission in permissions:
                cursor.execute(
                    "INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
                    (role_id, permission)
                )
            
            self.conn.commit()
            return role_id
        except sqlite3.IntegrityError:
            return None  # Role name already exists
        except Exception as e:
            print(f"Error creating role: {e}")
            return None
    
    def update_role(self, role_id, name, description, permissions):
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "UPDATE roles SET name = ?, description = ? WHERE id = ?",
                (name, description, role_id)
            )
            
            # Delete existing permissions
            cursor.execute(
                "DELETE FROM role_permissions WHERE role_id = ?",
                (role_id,)
            )
            
            # Add new permissions
            for permission in permissions:
                cursor.execute(
                    "INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
                    (role_id, permission)
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating role: {e}")
            return False
    
    def delete_role(self, role_id):
        try:
            cursor = self.conn.cursor()
            
            # Check if any users are using this role
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = ?", (role_id,))
            if cursor.fetchone()[0] > 0:
                return False  # Can't delete role in use
            
            # Delete role permissions
            cursor.execute(
                "DELETE FROM role_permissions WHERE role_id = ?",
                (role_id,)
            )
            
            # Delete role
            cursor.execute(
                "DELETE FROM roles WHERE id = ?",
                (role_id,)
            )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting role: {e}")
            return False
    
    def get_all_roles(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, description FROM roles ORDER BY name"
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting roles: {e}")
            return []
    
    def get_role_details(self, role_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name, description FROM roles WHERE id = ?",
                (role_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"Error getting role details: {e}")
            return None
    
    def get_role_permissions(self, role_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT permission FROM role_permissions WHERE role_id = ?",
                (role_id,)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting role permissions: {e}")
            return []
    
    def save_script(self, user_id, name, description, content):
        try:
            cursor = self.conn.cursor()
            script_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO scripts (id, user_id, name, description, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (script_id, user_id, name, description, json.dumps(content), now, now)
            )
            self.conn.commit()
            return script_id
        except Exception as e:
            print(f"Error saving script: {e}")
            return None
    
    def update_script(self, script_id, name, description, content):
        try:
            cursor = self.conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "UPDATE scripts SET name = ?, description = ?, content = ?, updated_at = ? WHERE id = ?",
                (name, description, json.dumps(content), now, script_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating script: {e}")
            return False
    
    def get_user_scripts(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, description, created_at FROM scripts WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting scripts: {e}")
            return []
    
    def get_script(self, script_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name, description, content FROM scripts WHERE id = ?",
                (script_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'description': result[1],
                    'content': json.loads(result[2])
                }
            return None
        except Exception as e:
            print(f"Error getting script: {e}")
            return None
    
    def save_profile(self, user_id, name, hotkey, settings, scripts_data):
        """
        Save a profile with multiple scripts
        scripts_data should be a list of dicts with script_id, execution_order, and execution_time
        """
        try:
            cursor = self.conn.cursor()
            profile_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO profiles (id, user_id, name, hotkey, settings, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (profile_id, user_id, name, hotkey, json.dumps(settings), now, now)
            )
            
            # Add scripts to profile
            for script_data in scripts_data:
                cursor.execute(
                    "INSERT INTO profile_scripts (profile_id, script_id, execution_order, execution_time) VALUES (?, ?, ?, ?)",
                    (profile_id, script_data['script_id'], script_data['execution_order'], script_data['execution_time'])
                )
            
            self.conn.commit()
            return profile_id
        except Exception as e:
            print(f"Error saving profile: {e}")
            return None
    
    def update_profile(self, profile_id, name, hotkey, settings, scripts_data):
        """Update a profile and its associated scripts"""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "UPDATE profiles SET name = ?, hotkey = ?, settings = ?, updated_at = ? WHERE id = ?",
                (name, hotkey, json.dumps(settings), now, profile_id)
            )
            
            # Delete existing script associations
            cursor.execute(
                "DELETE FROM profile_scripts WHERE profile_id = ?",
                (profile_id,)
            )
            
            # Add new script associations
            for script_data in scripts_data:
                cursor.execute(
                    "INSERT INTO profile_scripts (profile_id, script_id, execution_order, execution_time) VALUES (?, ?, ?, ?)",
                    (profile_id, script_data['script_id'], script_data['execution_order'], script_data['execution_time'])
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def get_user_profiles(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.id, p.name, p.hotkey, p.updated_at
                FROM profiles p
                WHERE p.user_id = ?
                ORDER BY p.updated_at DESC
                """,
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting profiles: {e}")
            return []
    
    def get_profile(self, profile_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.name, p.hotkey, p.settings
                FROM profiles p
                WHERE p.id = ?
                """,
                (profile_id,)
            )
            result = cursor.fetchone()
            if not result:
                return None
                
            profile = {
                'name': result[0],
                'hotkey': result[1],
                'settings': json.loads(result[2]),
                'scripts': []
            }
            
            # Get scripts associated with this profile
            cursor.execute(
                """
                SELECT ps.script_id, ps.execution_order, ps.execution_time, s.name, s.content
                FROM profile_scripts ps
                JOIN scripts s ON ps.script_id = s.id
                WHERE ps.profile_id = ?
                ORDER BY ps.execution_order
                """,
                (profile_id,)
            )
            
            for script_id, order, exec_time, name, content in cursor.fetchall():
                profile['scripts'].append({
                    'script_id': script_id,
                    'execution_order': order,
                    'execution_time': exec_time,
                    'name': name,
                    'content': json.loads(content)
                })
            
            return profile
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def delete_profile(self, profile_id):
        try:
            cursor = self.conn.cursor()
            
            # Delete script associations
            cursor.execute(
                "DELETE FROM profile_scripts WHERE profile_id = ?",
                (profile_id,)
            )
            
            # Delete profile
            cursor.execute(
                "DELETE FROM profiles WHERE id = ?",
                (profile_id,)
            )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False
    
    def close(self):
        if self.conn:
            self.conn.close()