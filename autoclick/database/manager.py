"""
Database manager for the Auto Click application.
"""
import sqlite3
import json
import uuid
import hashlib
from datetime import datetime

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
                created_by TEXT
            )
            ''')
            
            # Create user permissions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id TEXT,
                permission TEXT,
                PRIMARY KEY (user_id, permission),
                FOREIGN KEY (user_id) REFERENCES users (id)
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
                script_id TEXT,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (script_id) REFERENCES scripts (id)
            )
            ''')
            
            # Check if admin user exists, if not create one
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            if cursor.fetchone()[0] == 0:
                admin_id = str(uuid.uuid4())
                admin_password = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                    (admin_id, DEFAULT_ADMIN_USERNAME, admin_password, "admin")
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
    
    def create_user(self, username, password, role='standard', permissions=None, created_by=None):
        try:
            cursor = self.conn.cursor()
            user_id = str(uuid.uuid4())
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute(
                "INSERT INTO users (id, username, password_hash, role, created_by) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, password_hash, role, created_by)
            )
            
            # Add permissions
            if permissions is None:
                # Use default permissions for role
                permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])
            
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
            
            cursor.execute(
                "SELECT id, role FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            result = cursor.fetchone()
            return result if result else (None, None)
        except Exception as e:
            print(f"Authentication error: {e}")
            return None, None
    
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
                "SELECT id, username, role, created_at FROM users ORDER BY username"
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    def get_user_details(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT username, role FROM users WHERE id = ?",
                (user_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            print(f"Error getting user details: {e}")
            return None
    
    def update_user(self, user_id, role, permissions):
        try:
            cursor = self.conn.cursor()
            
            # Update role
            cursor.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (role, user_id)
            )
            
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
    
    def save_profile(self, user_id, name, hotkey, script_id, settings):
        try:
            cursor = self.conn.cursor()
            profile_id = str(uuid.uuid4())
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO profiles (id, user_id, name, hotkey, script_id, settings, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (profile_id, user_id, name, hotkey, script_id, json.dumps(settings), now, now)
            )
            self.conn.commit()
            return profile_id
        except Exception as e:
            print(f"Error saving profile: {e}")
            return None
    
    def get_user_profiles(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.id, p.name, p.hotkey, s.name 
                FROM profiles p
                JOIN scripts s ON p.script_id = s.id
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
                SELECT p.name, p.hotkey, p.script_id, p.settings, s.content
                FROM profiles p
                JOIN scripts s ON p.script_id = s.id
                WHERE p.id = ?
                """,
                (profile_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'hotkey': result[1],
                    'script_id': result[2],
                    'settings': json.loads(result[3]),
                    'script_content': json.loads(result[4])
                }
            return None
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def close(self):
        if self.conn:
            self.conn.close()