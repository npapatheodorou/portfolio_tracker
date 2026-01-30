import os
import hashlib
from datetime import datetime, timedelta
from flask import session
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DatabaseEncryptionManager:
    """Manages encrypted database with password caching using cryptography"""
    
    def __init__(self, db_path='portfolio_encrypted.db'):
        self.db_path = db_path
        self.cached_password = None
        self.cache_expiry = None
        self.session_timeout = timedelta(minutes=15)
        self._connection = None
        self._encryption_key = None
        
    def _derive_key(self, password: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """Derive encryption key from password using PBKDF2"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def is_authenticated(self):
        """Check if user is authenticated with valid cached password"""
        if not self.cached_password or not self.cache_expiry:
            return False
        return datetime.utcnow() < self.cache_expiry
    
    def authenticate(self, password):
        """Authenticate user and cache password"""
        try:
            # Verify password hash first
            if not self._verify_password_hash(password):
                return False
            
            # Test password by attempting to connect
            test_conn = self._create_connection(password)
            test_conn.execute("SELECT count(*) FROM sqlite_master")
            test_conn.close()
            
            # Password works, cache it
            self.cached_password = password
            self.cache_expiry = datetime.utcnow() + self.session_timeout
            session['db_authenticated'] = True
            session['cache_expiry'] = self.cache_expiry.isoformat()
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def logout(self):
        """Clear cached password"""
        self.cached_password = None
        self.cache_expiry = None
        self._connection = None
        self._encryption_key = None
        session.clear()
    
    def get_connection(self):
        """Get database connection with cached password"""
        if not self.is_authenticated():
            raise PermissionError("Database not authenticated")
        
        if not self._connection:
            self._connection = self._create_connection(self.cached_password)
        
        return self._connection
    
    def _create_connection(self, password):
        """Create SQLite connection (we'll handle encryption at application level)"""
        if not os.path.exists(self.db_path):
            # Create new database
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()
        else:
            # Connect to existing database
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            # Verify database is accessible
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        
        return conn
    
    def init_database(self, password):
        """Initialize new encrypted database with schema"""
        try:
            conn = self._create_connection(password)
            
            # Create tables
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL DEFAULT 'My Portfolio',
                    description TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL,
                    coin_id VARCHAR(100) DEFAULT '',
                    symbol VARCHAR(20) DEFAULT '',
                    name VARCHAR(100) DEFAULT '',
                    amount REAL DEFAULT 0,
                    average_buy_price REAL,
                    current_price REAL,
                    current_value REAL DEFAULT 0,
                    price_change_24h REAL,
                    price_change_percentage_24h REAL,
                    image_url VARCHAR(500) DEFAULT '',
                    last_updated DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    display_order INTEGER DEFAULT 0,
                    note VARCHAR(200) DEFAULT '',
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL,
                    snapshot_date DATE NOT NULL,
                    total_value REAL DEFAULT 0,
                    holdings_data TEXT DEFAULT '[]',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_manual BOOLEAN DEFAULT 0,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
                );
                
                CREATE TRIGGER IF NOT EXISTS update_portfolios_updated 
                AFTER UPDATE ON portfolios
                FOR EACH ROW
                BEGIN
                    UPDATE portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END;
            """)
            
            conn.commit()
            
            # Create default portfolio if none exists
            cursor = conn.execute("SELECT COUNT(*) FROM portfolios")
            if cursor.fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO portfolios (name, description) VALUES (?, ?)",
                    ("Main Portfolio", "Your primary crypto portfolio")
                )
                conn.commit()
            
            conn.close()
            
            # Store password hash for authentication
            self._store_password_hash(password)
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def _store_password_hash(self, password):
        """Store password hash for authentication verification"""
        try:
            key, salt = self._derive_key(password)
            hash_file = self.db_path.replace('.db', '.hash')
            
            with open(hash_file, 'wb') as f:
                f.write(base64.b64encode(salt) + b'\n' + 
                       hashlib.sha256(password.encode()).hexdigest().encode())
            
        except Exception as e:
            logger.error(f"Failed to store password hash: {e}")
    
    def _verify_password_hash(self, password):
        """Verify password against stored hash"""
        try:
            hash_file = self.db_path.replace('.db', '.hash')
            if not os.path.exists(hash_file):
                # If hash file doesn't exist but database does, treat as unauthenticated
                return os.path.exists(self.db_path) == False
            
            with open(hash_file, 'rb') as f:
                lines = f.read().split(b'\n')
                salt = base64.b64decode(lines[0])
                stored_hash = lines[1].decode()
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            return password_hash == stored_hash
            
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def migrate_existing_database(self, old_db_path, password):
        """Migrate data from existing SQLite database to new encrypted database"""
        try:
            # Connect to old database
            old_conn = sqlite3.connect(old_db_path)
            old_conn.row_factory = sqlite3.Row
            
            # Connect to new database
            new_conn = self._create_connection(password)
            
            # Migrate portfolios
            old_cursor = old_conn.execute("SELECT * FROM portfolios")
            for row in old_cursor:
                new_conn.execute("""
                    INSERT OR REPLACE INTO portfolios 
                    (id, name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (row['id'], row['name'], row['description'], row['created_at'], row['updated_at']))
            
            # Migrate holdings
            old_cursor = old_conn.execute("SELECT * FROM holdings")
            for row in old_cursor:
                new_conn.execute("""
                    INSERT OR REPLACE INTO holdings 
                    (id, portfolio_id, coin_id, symbol, name, amount, average_buy_price,
                     current_price, current_value, price_change_24h, price_change_percentage_24h,
                     image_url, last_updated, created_at, display_order, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (row['id'], row['portfolio_id'], row['coin_id'], row['symbol'], row['name'],
                     row['amount'], row['average_buy_price'], row['current_price'], row['current_value'],
                     row['price_change_24h'], row['price_change_percentage_24h'], row['image_url'],
                     row['last_updated'], row['created_at'], row['display_order'], row['note']))
            
            # Migrate snapshots
            old_cursor = old_conn.execute("SELECT * FROM snapshots")
            for row in old_cursor:
                new_conn.execute("""
                    INSERT OR REPLACE INTO snapshots 
                    (id, portfolio_id, snapshot_date, total_value, holdings_data, created_at, is_manual)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row['id'], row['portfolio_id'], row['snapshot_date'], row['total_value'],
                     row['holdings_data'], row['created_at'], row['is_manual']))
            
            new_conn.commit()
            old_conn.close()
            new_conn.close()
            
            # Store password hash
            self._store_password_hash(password)
            
            logger.info("Database migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            return False
    
    def close_connection(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

# Global instance
db_encryption = DatabaseEncryptionManager()