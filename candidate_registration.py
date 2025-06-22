import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import secrets
import re

class CandidateRegistrationSystem:
    def __init__(self, credentials_path, users_sheet_id=None):
        """
        Initialize the registration system with Google Sheets integration
        
        Args:
            credentials_path: Path to Google service account JSON
            users_sheet_id: ID of the users sheet (will create new if None)
        """
        # Setup Google Sheets connection
        self.scope = ['https://spreadsheets.google.com/feeds',
                      'https://www.googleapis.com/auth/drive']
        self.creds = Credentials.from_service_account_file(credentials_path, scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        
        # Get or create users sheet
        if users_sheet_id:
            self.users_sheet = self.client.open_by_key(users_sheet_id)
        else:
            self.users_sheet = self._create_users_sheet()
        
        # Initialize encryption
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def _create_users_sheet(self):
        """Create a new Google Sheet for storing encrypted user data"""
        sheet_name = f"AI_Recruitment_Users_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sheet = self.client.create(sheet_name)
        
        # Set up the headers
        worksheet = sheet.sheet1
        headers = [
            'user_id',
            'username',
            'email_encrypted',
            'password_hash',
            'salt',
            'created_at',
            'last_login',
            'is_active',
            'candidate_profile_id'
        ]
        worksheet.append_row(headers)
        
        # Make the sheet accessible (optional - adjust permissions as needed)
        sheet.share('', perm_type='anyone', role='reader')
        
        print(f"Created new users sheet: {sheet.id}")
        return sheet
    
    def _get_or_create_encryption_key(self):
        """
        Get encryption key from environment or create a new one
        IMPORTANT: In production, store this key securely!
        """
        key_env = os.getenv('ENCRYPTION_KEY')
        if key_env:
            return key_env.encode()
        else:
            # Generate a new key (save this securely!)
            key = Fernet.generate_key()
            print(f"IMPORTANT: Save this encryption key securely: {key.decode()}")
            return key
    
    def _hash_password(self, password, salt=None):
        """Hash password with salt using PBKDF2"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), base64.b64encode(salt).decode()
    
    def _validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_username(self, username):
        """Validate username format"""
        # Username must be 3-20 characters, alphanumeric with underscores
        pattern = r'^[a-zA-Z0-9_]{3,20}$'
        return re.match(pattern, username) is not None
    
    def _encrypt_data(self, data):
        """Encrypt sensitive data"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data):
        """Decrypt sensitive data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def _username_exists(self, username):
        """Check if username already exists"""
        worksheet = self.users_sheet.sheet1
        all_values = worksheet.get_all_values()
        
        for row in all_values[1:]:  # Skip header
            if row[1] == username:
                return True
        return False
    
    def _email_exists(self, email):
        """Check if email already exists (checks encrypted emails)"""
        worksheet = self.users_sheet.sheet1
        all_values = worksheet.get_all_values()
        
        for row in all_values[1:]:  # Skip header
            if row[2]:  # If there's an encrypted email
                try:
                    decrypted_email = self._decrypt_data(row[2])
                    if decrypted_email == email:
                        return True
                except:
                    continue
        return False
    
    def register_candidate(self, username, email, password):
        """
        Register a new candidate with encrypted email and hashed password
        
        Args:
            username: Unique username
            email: Email address (will be encrypted)
            password: Plain text password (will be hashed)
            
        Returns:
            dict: Registration result with user_id or error message
        """
        try:
            # Validate inputs
            if not self._validate_username(username):
                return {
                    'success': False,
                    'error': 'Invalid username. Must be 3-20 characters, alphanumeric with underscores.'
                }
            
            if not self._validate_email(email):
                return {
                    'success': False,
                    'error': 'Invalid email format.'
                }
            
            if len(password) < 8:
                return {
                    'success': False,
                    'error': 'Password must be at least 8 characters long.'
                }
            
            # Check if username exists
            if self._username_exists(username):
                return {
                    'success': False,
                    'error': 'Username already exists.'
                }
            
            # Check if email exists
            if self._email_exists(email):
                return {
                    'success': False,
                    'error': 'Email already registered.'
                }
            
            # Generate user ID
            user_id = f"USR_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
            
            # Hash password with salt
            password_hash, salt = self._hash_password(password)
            
            # Encrypt email
            encrypted_email = self._encrypt_data(email)
            
            # Prepare row data
            row_data = [
                user_id,
                username,
                encrypted_email,
                password_hash,
                salt,
                datetime.now().isoformat(),
                '',  # last_login
                'true',  # is_active
                ''  # candidate_profile_id (will be linked later)
            ]
            
            # Add to sheet
            worksheet = self.users_sheet.sheet1
            worksheet.append_row(row_data)
            
            return {
                'success': True,
                'user_id': user_id,
                'message': 'Registration successful!',
                'sheet_id': self.users_sheet.id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Registration failed: {str(e)}'
            }
    
    def login_candidate(self, username, password):
        """
        Authenticate a candidate
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            dict: Login result with user data or error
        """
        try:
            worksheet = self.users_sheet.sheet1
            all_values = worksheet.get_all_values()
            
            for i, row in enumerate(all_values[1:], start=2):  # Skip header
                if row[1] == username:
                    # Found user, verify password
                    stored_hash = row[3]
                    salt = base64.b64decode(row[4])
                    
                    # Hash the provided password with stored salt
                    password_hash, _ = self._hash_password(password, salt)
                    
                    if password_hash == stored_hash:
                        # Update last login
                        worksheet.update_cell(i, 7, datetime.now().isoformat())
                        
                        # Decrypt email for response
                        decrypted_email = self._decrypt_data(row[2])
                        
                        return {
                            'success': True,
                            'user_id': row[0],
                            'username': row[1],
                            'email': decrypted_email,
                            'candidate_profile_id': row[8],
                            'message': 'Login successful!'
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'Invalid username or password.'
                        }
            
            return {
                'success': False,
                'error': 'Invalid username or password.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Login failed: {str(e)}'
            }
    
    def get_user_by_id(self, user_id):
        """Get user data by ID (decrypts email)"""
        try:
            worksheet = self.users_sheet.sheet1
            all_values = worksheet.get_all_values()
            
            for row in all_values[1:]:  # Skip header
                if row[0] == user_id:
                    return {
                        'success': True,
                        'user_id': row[0],
                        'username': row[1],
                        'email': self._decrypt_data(row[2]),
                        'created_at': row[5],
                        'last_login': row[6],
                        'is_active': row[7] == 'true',
                        'candidate_profile_id': row[8]
                    }
            
            return {
                'success': False,
                'error': 'User not found.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to retrieve user: {str(e)}'
            }
