import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self):
        # Set up your database connection
        self.db_path = os.getenv('DATABASE_PATH', 'database.db')
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)  # Added check_same_thread=False
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.create_admin_user()  # Create admin user if not exists

    def create_tables(self):
        # Create tables if they don't already exist
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            dob TEXT,
            gender TEXT,
            allergies TEXT,
            medications TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            is_user_message BOOLEAN,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""")
        
        self.conn.commit()

    def create_admin_user(self):
        # Admin credentials (change these as needed)
        admin_name = 'admin'
        admin_password = 'admin_password'  # Plaintext password for now (will be hashed)

        # Check if admin exists
        existing_admin = self.get_user_by_name(admin_name)
        if not existing_admin:
            # Hash the password
            hashed_password = generate_password_hash(admin_password)
            self.cursor.execute("INSERT INTO users (name, password, is_admin) VALUES (?, ?, ?)", 
                                (admin_name, hashed_password, True))
            self.conn.commit()
            print(f"Admin user '{admin_name}' created successfully.")
        else:
            print(f"Admin user '{admin_name}' already exists.")

    def get_user_by_id(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = self.cursor.fetchone()
        if user:
            return {
                'id': user[0],
                'name': user[1],
                'password': user[2],
                'is_admin': bool(user[3]),
                'last_active': user[4]
            }
        return None

    def get_user_by_name(self, name):
        self.cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
        user = self.cursor.fetchone()
        if user:
            return {
                'id': user[0],
                'name': user[1],
                'password': user[2],
                'is_admin': bool(user[3]),
                'last_active': user[4]
            }
        return None

    def verify_user_by_name(self, name, password):
        user = self.get_user_by_name(name)
        if user and check_password_hash(user['password'], password):
            return user
        return None
    
    def admin_login(self, name, password):
        """
        Verifies admin login credentials.
        Returns user data if the login is successful and the user is an admin.
        """
        user = self.verify_user_by_name(name, password)
        if user and user['is_admin']:
            return user
        return None

    def create_user(self, name, password):
        hashed_password = generate_password_hash(password)
        self.cursor.execute("INSERT INTO users (name, password) VALUES (?, ?)", (name, hashed_password))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_user_last_active(self, user_id):
        self.cursor.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        self.conn.commit()

    def update_user_profile(self, user_id, name, dob, gender, allergies, medications):
        self.cursor.execute("""
        INSERT OR REPLACE INTO user_profile (user_id, name, dob, gender, allergies, medications)
        VALUES (?, ?, ?, ?, ?, ?)""", 
        (user_id, name, dob, gender, allergies, medications))
        self.conn.commit()

    def get_chat_history(self, user_id, limit=10):
        self.cursor.execute("SELECT * FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", 
                            (user_id, limit))
        chats = self.cursor.fetchall()
        return [{
            'id': chat[0],
            'user_id': chat[1],
            'message': chat[2],
            'response': chat[3],
            'is_user_message': chat[4],
            'timestamp': chat[5]
        } for chat in chats]

    def save_chat_message(self, user_id, message, response, is_user_message):
        self.cursor.execute("""
        INSERT INTO chat_history (user_id, message, response, is_user_message)
        VALUES (?, ?, ?, ?)""", (user_id, message, response, is_user_message))
        self.conn.commit()

    def get_all_users(self):
        self.cursor.execute("SELECT * FROM users")
        users = self.cursor.fetchall()
        return [{
            'id': user[0],
            'name': user[1],
            'is_admin': bool(user[3]),
            'last_active': user[4]
        } for user in users]

    def close(self):
        self.conn.close()
