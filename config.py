import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///portfolio_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Scheduler configuration
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "UTC"
    
    # CoinGecko API settings
    COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
    
    # Snapshot settings
    SNAPSHOT_INTERVAL_MINUTES = 15