"""
User Management and OAuth Integration Module

Handles user authentication, credential storage, and OAuth flows
for Gmail and Google Calendar access.
"""

import os
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib
import secrets
from cryptography.fernet import Fernet
import sqlite3
from contextlib import contextmanager

class UserManager:
    """Manages user authentication and credential storage"""
    
    def __init__(self, db_path='users.db', encryption_key=None):
        self.db_path = db_path
        self.encryption_key = encryption_key or self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        self.init_database()
    
    def _get_or_create_encryption_key(self):
        """Get or create encryption key for credential storage"""
        key_file = 'encryption.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def init_database(self):
        """Initialize SQLite database for user storage"""
        with self.get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scan TIMESTAMP,
                    settings TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_credentials (
                    user_id TEXT PRIMARY KEY,
                    gmail_credentials TEXT,
                    calendar_credentials TEXT,
                    gmail_token TEXT,
                    calendar_token TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_user(self, email: str, google_oauth_data: Dict) -> Dict:
        """Create new user from OAuth data"""
        user_id = self._generate_user_id(email)
        
        user_data = {
            'user_id': user_id,
            'email': email,
            'name': google_oauth_data.get('name', ''),
            'picture': google_oauth_data.get('picture', ''),
            'google_id': google_oauth_data.get('sub', ''),
            'created_at': datetime.now().isoformat()
        }
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, email, created_at, settings)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                email, 
                user_data['created_at'],
                json.dumps({'name': user_data['name'], 'picture': user_data['picture']})
            ))
        
        return user_data
    
    def store_user_credentials(self, user_id: str, gmail_creds: Dict, calendar_creds: Dict) -> bool:
        """Store encrypted user credentials"""
        try:
            # Encrypt credentials
            encrypted_gmail = self.cipher.encrypt(json.dumps(gmail_creds).encode())
            encrypted_calendar = self.cipher.encrypt(json.dumps(calendar_creds).encode())
            
            with self.get_db_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO user_credentials
                    (user_id, gmail_credentials, calendar_credentials, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    user_id,
                    base64.b64encode(encrypted_gmail).decode(),
                    base64.b64encode(encrypted_calendar).decode(),
                    datetime.now().isoformat()
                ))
            
            return True
            
        except Exception as e:
            print(f"❌ Error storing credentials: {e}")
            return False
    
    def get_user_credentials(self, user_id: str) -> Optional[Dict]:
        """Retrieve and decrypt user credentials"""
        try:
            with self.get_db_connection() as conn:
                result = conn.execute('''
                    SELECT gmail_credentials, calendar_credentials
                    FROM user_credentials
                    WHERE user_id = ?
                ''', (user_id,)).fetchone()
            
            if not result:
                return None
            
            # Decrypt credentials
            gmail_encrypted = base64.b64decode(result['gmail_credentials'])
            calendar_encrypted = base64.b64decode(result['calendar_credentials'])
            
            gmail_creds = json.loads(self.cipher.decrypt(gmail_encrypted).decode())
            calendar_creds = json.loads(self.cipher.decrypt(calendar_encrypted).decode())
            
            return {
                'gmail_credentials': gmail_creds,
                'calendar_credentials': calendar_creds
            }
            
        except Exception as e:
            print(f"❌ Error retrieving credentials: {e}")
            return None
    
    def create_session(self, user_id: str, duration_hours=24) -> str:
        """Create user session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO user_sessions
                (session_id, user_id, expires_at)
                VALUES (?, ?, ?)
            ''', (session_id, user_id, expires_at.isoformat()))
        
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """Validate session and return user_id if valid"""
        with self.get_db_connection() as conn:
            result = conn.execute('''
                SELECT user_id, expires_at
                FROM user_sessions
                WHERE session_id = ? AND is_active = 1
            ''', (session_id,)).fetchone()
        
        if not result:
            return None
        
        expires_at = datetime.fromisoformat(result['expires_at'])
        if datetime.now() > expires_at:
            # Session expired
            self.invalidate_session(session_id)
            return None
        
        return result['user_id']
    
    def invalidate_session(self, session_id: str):
        """Invalidate user session"""
        with self.get_db_connection() as conn:
            conn.execute('''
                UPDATE user_sessions
                SET is_active = 0
                WHERE session_id = ?
            ''', (session_id,))
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user information"""
        with self.get_db_connection() as conn:
            result = conn.execute('''
                SELECT email, created_at, last_scan, settings
                FROM users
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,)).fetchone()
        
        if not result:
            return None
        
        settings = json.loads(result['settings'] or '{}')
        
        return {
            'user_id': user_id,
            'email': result['email'],
            'created_at': result['created_at'],
            'last_scan': result['last_scan'],
            'name': settings.get('name', ''),
            'picture': settings.get('picture', '')
        }
    
    def update_last_scan(self, user_id: str):
        """Update user's last scan timestamp"""
        with self.get_db_connection() as conn:
            conn.execute('''
                UPDATE users
                SET last_scan = ?
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
    
    def _generate_user_id(self, email: str) -> str:
        """Generate unique user ID from email"""
        return hashlib.sha256(f"{email}{secrets.token_hex(8)}".encode()).hexdigest()[:16]

class OAuthHandler:
    """Handles Google OAuth flows for Gmail and Calendar access"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate OAuth authorization URL"""
        from urllib.parse import urlencode
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        if state:
            params['state'] = state
        
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Dict:
        """Exchange authorization code for access tokens"""
        import requests
        
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token exchange failed: {response.text}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        import requests
        
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token refresh failed: {response.text}")
    
    def get_user_info(self, access_token: str) -> Dict:
        """Get user profile information"""
        import requests
        
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user info: {response.text}")

class CredentialManager:
    """Manages user credentials for Gmail and Calendar APIs"""
    
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager
    
    def setup_user_credentials(self, user_id: str, oauth_tokens: Dict) -> bool:
        """Setup user credentials from OAuth tokens"""
        try:
            # Create credential objects for Gmail and Calendar
            gmail_creds = {
                'access_token': oauth_tokens.get('access_token'),
                'refresh_token': oauth_tokens.get('refresh_token'),
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
            }
            
            calendar_creds = {
                'access_token': oauth_tokens.get('access_token'),
                'refresh_token': oauth_tokens.get('refresh_token'),
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                'scopes': ['https://www.googleapis.com/auth/calendar']
            }
            
            return self.user_manager.store_user_credentials(
                user_id, gmail_creds, calendar_creds
            )
            
        except Exception as e:
            print(f"❌ Error setting up credentials: {e}")
            return False
    
    def get_gmail_service(self, user_id: str):
        """Get authenticated Gmail service for user"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            creds_data = self.user_manager.get_user_credentials(user_id)
            if not creds_data:
                return None
            
            gmail_creds = creds_data['gmail_credentials']
            credentials = Credentials.from_authorized_user_info(gmail_creds)
            
            if credentials.expired:
                credentials.refresh(Request())
                # Update stored credentials
                updated_creds = {
                    **gmail_creds,
                    'access_token': credentials.token
                }
                self.user_manager.store_user_credentials(
                    user_id, updated_creds, creds_data['calendar_credentials']
                )
            
            return build('gmail', 'v1', credentials=credentials)
            
        except Exception as e:
            print(f"❌ Error creating Gmail service: {e}")
            return None
    
    def get_calendar_service(self, user_id: str):
        """Get authenticated Calendar service for user"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            creds_data = self.user_manager.get_user_credentials(user_id)
            if not creds_data:
                return None
            
            calendar_creds = creds_data['calendar_credentials']
            credentials = Credentials.from_authorized_user_info(calendar_creds)
            
            if credentials.expired:
                credentials.refresh(Request())
                # Update stored credentials
                updated_creds = {
                    **calendar_creds,
                    'access_token': credentials.token
                }
                self.user_manager.store_user_credentials(
                    user_id, creds_data['gmail_credentials'], updated_creds
                )
            
            return build('calendar', 'v3', credentials=credentials)
            
        except Exception as e:
            print(f"❌ Error creating Calendar service: {e}")
            return None