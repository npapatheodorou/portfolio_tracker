from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime, date
import json
import csv
import io
import logging
import requests
import time
import os
from functools import wraps
from database_encryption import DatabaseEncryptionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
# Use absolute path to avoid Flask's instance folder behavior
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portfolio_encrypted.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Initialize database encryption with absolute path
db_encryption = DatabaseEncryptionManager(db_path)

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not db_encryption.is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============== MODELS ==============

class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='My Portfolio')
    description = db.Column(db.Text, nullable=True, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    holdings = db.relationship('Holding', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    snapshots = db.relationship('Snapshot', backref='portfolio', lazy=True, cascade='all, delete-orphan')


class Holding(db.Model):
    __tablename__ = 'holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    coin_id = db.Column(db.String(100), nullable=False, default='')
    symbol = db.Column(db.String(20), nullable=False, default='')
    name = db.Column(db.String(100), nullable=False, default='')
    amount = db.Column(db.Float, nullable=False, default=0)
    average_buy_price = db.Column(db.Float, nullable=True)
    current_price = db.Column(db.Float, nullable=True)
    current_value = db.Column(db.Float, nullable=True, default=0)
    price_change_24h = db.Column(db.Float, nullable=True)
    price_change_percentage_24h = db.Column(db.Float, nullable=True)
    image_url = db.Column(db.String(500), nullable=True, default='')
    last_updated = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.String(200), nullable=True, default='')  # Optional note to distinguish duplicates


class Snapshot(db.Model):
    __tablename__ = 'snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False)
    total_value = db.Column(db.Float, nullable=False, default=0)
    holdings_data = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_manual = db.Column(db.Boolean, default=False)


# ============== CRYPTO API SERVICE ==============

class CryptoAPIService:
    """Multi-API service for crypto data with fallbacks"""
    
    def __init__(self):
        self.last_request_time = {}
        self.rate_limits = {
            'coincap': 0.5,      # 200 req/min = ~0.3s, using 0.5s to be safe
            'coingecko': 2.5,    # 10-30 req/min
            'coinpaprika': 1.0   # 60 req/min
        }
        self.current_api = 'coingecko'  # Primary API
    
    def _rate_limit(self, api_name):
        """Apply rate limiting for specific API"""
        now = time.time()
        last = self.last_request_time.get(api_name, 0)
        wait_time = self.rate_limits.get(api_name, 1.0)
        
        elapsed = now - last
        if elapsed < wait_time:
            time.sleep(wait_time - elapsed)
        
        self.last_request_time[api_name] = time.time()
    
    def _make_request(self, url, params=None, api_name='coincap'):
        """Make a rate-limited request"""
        self._rate_limit(api_name)
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 429:
                logger.warning(f"{api_name} rate limited")
                return None, True
            response.raise_for_status()
            return response.json(), False
        except Exception as e:
            logger.error(f"{api_name} API error: {e}")
            return None, False
    
    # ============== COINCAP API ==============
    
    def coincap_search(self, query):
        """Search coins using CoinCap API"""
        url = "https://api.coincap.io/v2/assets"
        params = {"search": query, "limit": 20}
        data, rate_limited = self._make_request(url, params, 'coincap')
        
        if rate_limited:
            return None, True
        
        if data and 'data' in data:
            results = []
            for coin in data['data']:
                results.append({
                    'id': coin.get('id', ''),
                    'symbol': coin.get('symbol', ''),
                    'name': coin.get('name', ''),
                    'thumb': f"https://assets.coincap.io/assets/icons/{coin.get('symbol', '').lower()}@2x.png"
                })
            return results, False
        return [], False
    
    def coincap_get_prices(self, coin_ids):
        """Get prices from CoinCap API"""
        prices = {}
        
        for coin_id in coin_ids:
            url = f"https://api.coincap.io/v2/assets/{coin_id}"
            data, rate_limited = self._make_request(url, api_name='coincap')
            
            if rate_limited:
                return None, True
            
            if data and 'data' in data:
                asset = data['data']
                prices[coin_id] = {
                    'usd': float(asset.get('priceUsd', 0)) if asset.get('priceUsd') else None,
                    'usd_24h_change': float(asset.get('changePercent24Hr', 0)) if asset.get('changePercent24Hr') else None,
                    'image': f"https://assets.coincap.io/assets/icons/{asset.get('symbol', '').lower()}@2x.png"
                }
        
        return prices, False
    
    def coincap_get_markets(self, coin_ids):
        """Get market data from CoinCap API"""
        results = []
        
        for coin_id in coin_ids:
            url = f"https://api.coincap.io/v2/assets/{coin_id}"
            data, rate_limited = self._make_request(url, api_name='coincap')
            
            if rate_limited:
                return None, True
            
            if data and 'data' in data:
                asset = data['data']
                results.append({
                    'id': asset.get('id', ''),
                    'symbol': asset.get('symbol', ''),
                    'name': asset.get('name', ''),
                    'current_price': float(asset.get('priceUsd', 0)) if asset.get('priceUsd') else None,
                    'price_change_24h': None,
                    'price_change_percentage_24h': float(asset.get('changePercent24Hr', 0)) if asset.get('changePercent24Hr') else None,
                    'image': f"https://assets.coincap.io/assets/icons/{asset.get('symbol', '').lower()}@2x.png"
                })
        
        return results, False
    
    # ============== COINGECKO API (Fallback) ==============
    
    def coingecko_search(self, query):
        """Search coins using CoinGecko API"""
        url = "https://api.coingecko.com/api/v3/search"
        data, rate_limited = self._make_request(url, {"query": query}, 'coingecko')
        
        if rate_limited:
            return None, True
        
        if data and 'coins' in data:
            results = []
            for coin in data['coins'][:20]:
                results.append({
                    'id': coin.get('id', ''),
                    'symbol': coin.get('symbol', ''),
                    'name': coin.get('name', ''),
                    'thumb': coin.get('thumb', '')
                })
            return results, False
        return [], False
    
    def coingecko_get_prices(self, coin_ids):
        """Get prices from CoinGecko API"""
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        data, rate_limited = self._make_request(url, params, 'coingecko')
        
        if rate_limited:
            return None, True
        
        if data:
            prices = {}
            for coin_id, price_data in data.items():
                prices[coin_id] = {
                    'usd': price_data.get('usd'),
                    'usd_24h_change': price_data.get('usd_24h_change')
                }
            return prices, False
        return {}, False
    
    def coingecko_get_markets(self, coin_ids):
        """Get market data from CoinGecko API"""
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ",".join(coin_ids),
            "order": "market_cap_desc",
            "per_page": 250,
            "page": 1,
            "sparkline": "false"
        }
        data, rate_limited = self._make_request(url, params, 'coingecko')
        
        if rate_limited:
            return None, True
        
        return data or [], False
    
    # ============== COINPAPRIKA API (Fallback) ==============
    
    def coinpaprika_search(self, query):
        """Search coins using CoinPaprika API"""
        url = "https://api.coinpaprika.com/v1/search"
        params = {"q": query, "limit": 20}
        data, rate_limited = self._make_request(url, params, 'coinpaprika')
        
        if rate_limited:
            return None, True
        
        if data and 'currencies' in data:
            results = []
            for coin in data['currencies']:
                coin_id = coin.get('id', '')
                results.append({
                    'id': coin_id,
                    'symbol': coin.get('symbol', ''),
                    'name': coin.get('name', ''),
                    'thumb': f"https://static.coinpaprika.com/coin/{coin_id}/logo.png" if coin_id else ''
                })
            return results, False
        return [], False
    
    def coinpaprika_get_prices(self, coin_ids):
        """Get prices from CoinPaprika API"""
        prices = {}
        
        for coin_id in coin_ids:
            # CoinPaprika uses different ID format, try to map
            url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
            data, rate_limited = self._make_request(url, api_name='coinpaprika')
            
            if rate_limited:
                return None, True
            
            if data and 'quotes' in data:
                usd_data = data['quotes'].get('USD', {})
                prices[coin_id] = {
                    'usd': usd_data.get('price'),
                    'usd_24h_change': usd_data.get('percent_change_24h'),
                    'image': f"https://static.coinpaprika.com/coin/{coin_id}/logo.png"
                }
        
        return prices, False
    
    # ============== UNIFIED METHODS ==============
    
    def search_coins(self, query):
        """Search coins with fallback"""
        # Try CoinGecko first
        results, rate_limited = self.coingecko_search(query)
        if not rate_limited and results:
            return results, False
        
        # Try CoinCap as fallback
        results, rate_limited = self.coincap_search(query)
        if not rate_limited and results:
            return results, False
        
        # Try CoinPaprika as last resort
        results, rate_limited = self.coinpaprika_search(query)
        return results or [], rate_limited
    
    def get_coin_price(self, coin_ids):
        """Get prices with fallback"""
        # Try CoinGecko first
        prices, rate_limited = self.coingecko_get_prices(coin_ids)
        if not rate_limited and prices:
            return prices, False
        
        # Try CoinCap as fallback
        prices, rate_limited = self.coincap_get_prices(coin_ids)
        if not rate_limited and prices:
            return prices, False
        
        return {}, rate_limited
    
    def get_coins_markets(self, coin_ids):
        """Get market data with fallback"""
        # Try CoinGecko first
        results, rate_limited = self.coingecko_get_markets(coin_ids)
        if not rate_limited and results:
            return results, False
        
        # Try CoinCap as fallback
        results, rate_limited = self.coincap_get_markets(coin_ids)
        return results or [], rate_limited


# Initialize crypto API service
crypto_api = CryptoAPIService()


# ============== HELPER FUNCTIONS ==============

def serialize_portfolio(p):
    """Safely serialize a portfolio"""
    try:
        holdings_list = []
        total_value = 0
        
        # Sort holdings by display_order then id
        ordered_holdings = sorted(
            p.holdings,
            key=lambda h: ((h.display_order or 0), h.id)
        )
        
        for h in ordered_holdings:
            hd = {
                'id': h.id,
                'portfolio_id': h.portfolio_id,
                'coin_id': h.coin_id or '',
                'symbol': h.symbol or '',
                'name': h.name or '',
                'amount': float(h.amount) if h.amount else 0,
                'average_buy_price': float(h.average_buy_price) if h.average_buy_price else None,
                'current_price': float(h.current_price) if h.current_price else None,
                'current_value': float(h.current_value) if h.current_value else 0,
                'price_change_24h': float(h.price_change_24h) if h.price_change_24h else None,
                'price_change_percentage_24h': float(h.price_change_percentage_24h) if h.price_change_percentage_24h else None,
                'image_url': h.image_url or '',
                'last_updated': h.last_updated.isoformat() if h.last_updated else None,
                'profit_loss': 0,
                'profit_loss_percentage': 0,
                'display_order': h.display_order or 0,
                'note': h.note or ''
            }
            
            if hd['average_buy_price'] and hd['current_price'] and hd['amount']:
                hd['profit_loss'] = (hd['current_price'] - hd['average_buy_price']) * hd['amount']
                if hd['average_buy_price'] > 0:
                    hd['profit_loss_percentage'] = ((hd['current_price'] - hd['average_buy_price']) / hd['average_buy_price']) * 100
            
            holdings_list.append(hd)
            total_value += hd['current_value']
        
        return {
            'id': p.id,
            'name': p.name or 'My Portfolio',
            'description': p.description or '',
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'updated_at': p.updated_at.isoformat() if p.updated_at else None,
            'holdings': holdings_list,
            'total_value': total_value
        }
    except Exception as e:
        logger.error(f"Error serializing portfolio {p.id}: {e}")
        return {
            'id': p.id,
            'name': p.name or 'My Portfolio',
            'description': '',
            'holdings': [],
            'total_value': 0
        }


def serialize_snapshot(s):
    """Safely serialize a snapshot"""
    try:
        holdings = json.loads(s.holdings_data) if s.holdings_data else []
    except:
        holdings = []
    
    # Get portfolio name if portfolio relationship exists
    portfolio_name = None
    if hasattr(s, 'portfolio') and s.portfolio:
        portfolio_name = s.portfolio.name
    elif s.portfolio_id:
        # Fallback: query portfolio directly
        portfolio = Portfolio.query.get(s.portfolio_id)
        portfolio_name = portfolio.name if portfolio else 'Unknown'
    else:
        portfolio_name = 'Unknown'
    
    return {
        'id': s.id,
        'portfolio_id': s.portfolio_id,
        'portfolio_name': portfolio_name,
        'snapshot_date': s.snapshot_date.isoformat() if s.snapshot_date else None,
        'total_value': float(s.total_value) if s.total_value else 0,
        'holdings_data': holdings,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'is_manual': bool(s.is_manual)
    }


def update_all_prices():
    """Update prices for all holdings"""
    try:
        holdings = Holding.query.all()
        if not holdings:
            return {'success': True}
        
        # Get unique coin IDs
        coin_ids = list(set(h.coin_id for h in holdings if h.coin_id))
        if not coin_ids:
            return {'success': True}
        
        # Batch process to avoid rate limits
        batch_size = 10
        all_prices = {}
        
        for i in range(0, len(coin_ids), batch_size):
            batch = coin_ids[i:i + batch_size]
            market_data, rate_limited = crypto_api.get_coins_markets(batch)
            
            if rate_limited:
                logger.warning("Rate limited during price update")
                # Continue with what we have
                break
            
            if market_data:
                for coin in market_data:
                    all_prices[coin['id']] = coin
        
        # Update holdings
        for holding in holdings:
            if holding.coin_id in all_prices:
                coin = all_prices[holding.coin_id]
                holding.current_price = coin.get('current_price')
                holding.current_value = (holding.current_price or 0) * (holding.amount or 0)
                holding.price_change_24h = coin.get('price_change_24h')
                holding.price_change_percentage_24h = coin.get('price_change_percentage_24h')
                if coin.get('image'):
                    holding.image_url = coin.get('image')
                holding.last_updated = datetime.utcnow()
        
        db.session.commit()
        return {'success': True}
    except Exception as e:
        logger.error(f"Update prices error: {e}")
        return {'success': False, 'error': str(e)}


def create_snapshot_for_portfolio(portfolio, is_manual=False):
    """Create a snapshot for a portfolio"""
    today = date.today()
    
    # Sort holdings by display_order
    ordered_holdings = sorted(
        portfolio.holdings,
        key=lambda h: ((h.display_order or 0), h.id)
    )
    
    holdings_data = []
    total_value = 0
    
    for h in ordered_holdings:
        hd = {
            'coin_id': h.coin_id or '',
            'symbol': h.symbol or '',
            'name': h.name or '',
            'amount': float(h.amount) if h.amount else 0,
            'current_price': float(h.current_price) if h.current_price else None,
            'current_value': float(h.current_value) if h.current_value else 0,
            'average_buy_price': float(h.average_buy_price) if h.average_buy_price else None,
            'image_url': h.image_url or '',
            'display_order': h.display_order or 0,
            'note': h.note or ''
        }
        holdings_data.append(hd)
        total_value += hd['current_value']
    
    existing = Snapshot.query.filter_by(portfolio_id=portfolio.id, snapshot_date=today).first()
    
    if existing:
        existing.total_value = total_value
        existing.holdings_data = json.dumps(holdings_data)
        existing.created_at = datetime.utcnow()
        existing.is_manual = is_manual
        return existing
    else:
        snapshot = Snapshot(
            portfolio_id=portfolio.id,
            snapshot_date=today,
            total_value=total_value,
            holdings_data=json.dumps(holdings_data),
            is_manual=is_manual
        )
        db.session.add(snapshot)
        return snapshot


# ============== AUTHENTICATION ROUTES ==============

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    info = None
    first_time = False
    
    # Check if database and hash file exist
    db_exists = os.path.exists(db_path)
    hash_file = db_path.replace('.db', '.hash')
    hash_exists = os.path.exists(hash_file)
    
    if not db_exists and not hash_exists:
        first_time = True
        info = "Creating new encrypted database. Please choose a strong password."
    elif db_exists and not hash_exists:
        # Database exists but hash file is missing - corrupted setup
        first_time = True
        info = "Database exists but password file is missing. Please re-create your password to continue."
        # Force user to set password by treating as first-time
    elif not db_exists and hash_exists:
        # Hash exists but database doesn't - corrupted setup
        first_time = True
        info = "Password file exists but database is missing. Please re-create your database."
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password:
            error = "Password is required"
        elif first_time and password != confirm_password:
            error = "Passwords do not match"
        elif len(password) < 8:
            error = "Password must be at least 8 characters long"
        else:
            if first_time:
                # Initialize new database
                if db_encryption.init_database(password):
                    # Try to migrate existing data if available
                    if os.path.exists('portfolio.db'):
                        if db_encryption.migrate_existing_database('portfolio.db', password):
                            info = "Database created and existing data migrated successfully!"
                        else:
                            info = "Database created! (Migration of old data failed)"
                    
                    if db_encryption.authenticate(password):
                        return redirect(url_for('index'))
                else:
                    error = "Failed to initialize database"
            else:
                # Try to authenticate with existing database
                if db_encryption.authenticate(password):
                    return redirect(url_for('index'))
                else:
                    error = "Invalid password"
    
    return render_template('login.html', error=error, info=info, first_time=first_time)


@app.route('/logout')
def logout():
    db_encryption.logout()
    return redirect(url_for('login'))


# ============== PAGE ROUTES ==============

@app.route('/')
@require_auth
def index():
    return render_template('index.html')


@app.route('/portfolio/<int:portfolio_id>')
@require_auth
def portfolio_detail(portfolio_id):
    return render_template('portfolio.html', portfolio_id=portfolio_id)


@app.route('/snapshots')
@require_auth
def snapshots_page():
    return render_template('snapshots.html')


@app.route('/compare')
@require_auth
def compare_page():
    return render_template('compare.html')


# ============== API ROUTES ==============

@app.route('/api/portfolios', methods=['GET'])
@require_auth
def api_get_portfolios():
    try:
        portfolios = Portfolio.query.all()
        result = [serialize_portfolio(p) for p in portfolios]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting portfolios: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios', methods=['POST'])
@require_auth
def api_create_portfolio():
    try:
        data = request.get_json() or {}
        portfolio = Portfolio(
            name=data.get('name') or 'My Portfolio',
            description=data.get('description') or ''
        )
        db.session.add(portfolio)
        db.session.commit()
        return jsonify(serialize_portfolio(portfolio)), 201
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios/<int:portfolio_id>', methods=['GET'])
@require_auth
def api_get_portfolio(portfolio_id):
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        return jsonify(serialize_portfolio(portfolio))
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios/<int:portfolio_id>', methods=['PUT'])
@require_auth
def api_update_portfolio(portfolio_id):
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        data = request.get_json() or {}
        if 'name' in data:
            portfolio.name = data['name']
        if 'description' in data:
            portfolio.description = data['description']
        
        db.session.commit()
        return jsonify(serialize_portfolio(portfolio))
    except Exception as e:
        logger.error(f"Error updating portfolio: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios/<int:portfolio_id>', methods=['DELETE'])
@require_auth
def api_delete_portfolio(portfolio_id):
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        db.session.delete(portfolio)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting portfolio: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios/<int:portfolio_id>/holdings', methods=['POST'])
@require_auth
def api_add_holding(portfolio_id):
    """Add a holding - ALWAYS creates a new row (duplicates allowed)"""
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        data = request.get_json() or {}
        
        if not data.get('coin_id'):
            return jsonify({'error': 'coin_id is required'}), 400
        
        # Determine next display_order
        max_order = db.session.query(func.max(Holding.display_order))\
            .filter_by(portfolio_id=portfolio_id).scalar() or 0
        
        # ALWAYS create a new holding (duplicates allowed)
        holding = Holding(
            portfolio_id=portfolio_id,
            coin_id=data.get('coin_id', ''),
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            amount=data.get('amount') or 0,
            average_buy_price=data.get('average_buy_price'),
            image_url=data.get('image_url', ''),
            display_order=max_order + 1,
            note=data.get('note', '')  # Optional note to distinguish entries
        )
        db.session.add(holding)
        
        # Try to get price
        rate_limited = False
        try:
            prices, rate_limited = crypto_api.get_coin_price([holding.coin_id])
            if prices and holding.coin_id in prices:
                price_data = prices[holding.coin_id]
                holding.current_price = price_data.get('usd')
                holding.current_value = (holding.current_price or 0) * (holding.amount or 0)
                holding.price_change_percentage_24h = price_data.get('usd_24h_change')
                if price_data.get('image'):
                    holding.image_url = price_data.get('image')
                holding.last_updated = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
        
        db.session.commit()
        
        result = {
            'success': True,
            'id': holding.id,
            'coin_id': holding.coin_id,
            'symbol': holding.symbol,
            'name': holding.name,
            'amount': holding.amount,
            'current_price': holding.current_price,
            'current_value': holding.current_value,
            'display_order': holding.display_order,
            'note': holding.note
        }
        
        if rate_limited:
            result['warning'] = 'Rate limited. Price will update later.'
            result['rate_limited'] = True
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error adding holding: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/holdings/<int:holding_id>', methods=['PUT'])
@require_auth
def api_update_holding(holding_id):
    try:
        holding = Holding.query.get(holding_id)
        if not holding:
            return jsonify({'error': 'Holding not found'}), 404
        
        data = request.get_json() or {}
        
        if 'amount' in data:
            holding.amount = data['amount']
        if 'average_buy_price' in data:
            holding.average_buy_price = data['average_buy_price']
        if 'note' in data:
            holding.note = data['note']
        
        if holding.current_price:
            holding.current_value = (holding.current_price or 0) * (holding.amount or 0)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating holding: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/holdings/<int:holding_id>', methods=['DELETE'])
@require_auth
def api_delete_holding(holding_id):
    try:
        holding = Holding.query.get(holding_id)
        if not holding:
            return jsonify({'error': 'Holding not found'}), 404
        
        db.session.delete(holding)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting holding: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/holdings/<int:holding_id>/reorder', methods=['POST'])
@require_auth
def api_reorder_holding(holding_id):
    """Move a holding up or down within its portfolio."""
    try:
        holding = Holding.query.get(holding_id)
        if not holding:
            return jsonify({'error': 'Holding not found'}), 404
        
        data = request.get_json() or {}
        direction = data.get('direction')
        if direction not in ('up', 'down'):
            return jsonify({'error': 'Invalid direction. Use "up" or "down".'}), 400
        
        # Ensure display_order is not NULL
        if holding.display_order is None:
            holding.display_order = Holding.query.filter_by(portfolio_id=holding.portfolio_id).count()
            db.session.commit()
        
        # Find neighbor to swap with
        query = Holding.query.filter_by(portfolio_id=holding.portfolio_id)
        
        if direction == 'up':
            neighbor = query.filter(Holding.display_order < holding.display_order)\
                            .order_by(Holding.display_order.desc()).first()
        else:
            neighbor = query.filter(Holding.display_order > holding.display_order)\
                            .order_by(Holding.display_order.asc()).first()
        
        if not neighbor:
            return jsonify({'success': True, 'message': 'Already at edge'})
        
        # Swap display_order values
        holding.display_order, neighbor.display_order = neighbor.display_order, holding.display_order
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error reordering holding: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios/<int:portfolio_id>/holdings/order', methods=['POST'])
@require_auth
def api_order_holdings(portfolio_id):
    """Order holdings by predefined criteria."""
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        data = request.get_json() or {}
        order_type = data.get('order_type')
        
        if not order_type:
            return jsonify({'error': 'Order type is required'}), 400
        
        # Get all holdings
        holdings = Holding.query.filter_by(portfolio_id=portfolio_id).all()
        
        if not holdings:
            return jsonify({'success': True})
        
        # Apply ordering
        if order_type == 'price_low_to_high':
            holdings.sort(key=lambda h: h.current_price or 0)
        elif order_type == 'price_high_to_low':
            holdings.sort(key=lambda h: h.current_price or 0, reverse=True)
        elif order_type == 'value_low_to_high':
            holdings.sort(key=lambda h: h.current_value or 0)
        elif order_type == 'value_high_to_low':
            holdings.sort(key=lambda h: h.current_value or 0, reverse=True)
        elif order_type == 'name_a_to_z':
            holdings.sort(key=lambda h: h.name or '')
        elif order_type == 'name_z_to_a':
            holdings.sort(key=lambda h: h.name or '', reverse=True)
        elif order_type == 'amount_low_to_high':
            holdings.sort(key=lambda h: h.amount or 0)
        elif order_type == 'amount_high_to_low':
            holdings.sort(key=lambda h: h.amount or 0, reverse=True)
        elif order_type == 'profit_loss_low_to_high':
            holdings.sort(key=lambda h: ((h.current_price or 0) - (h.average_buy_price or 0)) * (h.amount or 0))
        elif order_type == 'profit_loss_high_to_low':
            holdings.sort(key=lambda h: ((h.current_price or 0) - (h.average_buy_price or 0)) * (h.amount or 0), reverse=True)
        else:
            return jsonify({'error': 'Invalid order type'}), 400
        
        # Update display_order
        for i, holding in enumerate(holdings):
            holding.display_order = i + 1
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error ordering holdings: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/order-types', methods=['GET'])
@require_auth
def api_get_order_types():
    """Get available ordering options."""
    order_types = [
        {'type': 'price_low_to_high', 'label': 'Price (Low to High)', 'description': 'Sort by current price from lowest to highest'},
        {'type': 'price_high_to_low', 'label': 'Price (High to Low)', 'description': 'Sort by current price from highest to lowest'},
        {'type': 'value_low_to_high', 'label': 'Value (Low to High)', 'description': 'Sort by current value from lowest to highest'},
        {'type': 'value_high_to_low', 'label': 'Value (High to Low)', 'description': 'Sort by current value from highest to lowest'},
        {'type': 'name_a_to_z', 'label': 'Name (A to Z)', 'description': 'Sort alphabetically by coin name'},
        {'type': 'name_z_to_a', 'label': 'Name (Z to A)', 'description': 'Sort alphabetically by coin name in reverse'},
        {'type': 'amount_low_to_high', 'label': 'Amount (Low to High)', 'description': 'Sort by amount held from lowest to highest'},
        {'type': 'amount_high_to_low', 'label': 'Amount (High to Low)', 'description': 'Sort by amount held from highest to lowest'},
        {'type': 'profit_loss_low_to_high', 'label': 'P/L (Low to High)', 'description': 'Sort by profit/loss from lowest to highest'},
        {'type': 'profit_loss_high_to_low', 'label': 'P/L (High to Low)', 'description': 'Sort by profit/loss from highest to lowest'}
    ]
    return jsonify(order_types)


@app.route('/api/coins/search')
@require_auth
def api_search_coins():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    try:
        results, rate_limited = crypto_api.search_coins(query)
        if rate_limited:
            return jsonify({'error': 'Rate limited. Please try again.', 'rate_limited': True}), 429
        return jsonify(results or [])
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify([])


@app.route('/api/refresh-prices', methods=['POST'])
@require_auth
def api_refresh_prices():
    try:
        result = update_all_prices()
        if result.get('rate_limited'):
            return jsonify({
                'success': False,
                'error': 'Rate limited. Please wait and try again.',
                'rate_limited': True
            }), 429
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error refreshing prices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/snapshots', methods=['GET'])
@require_auth
def api_get_snapshots():
    try:
        portfolio_id = request.args.get('portfolio_id', type=int)
        
        query = Snapshot.query
        if portfolio_id:
            query = query.filter_by(portfolio_id=portfolio_id)
        
        snapshots = query.order_by(Snapshot.snapshot_date.desc()).all()
        return jsonify([serialize_snapshot(s) for s in snapshots])
    except Exception as e:
        logger.error(f"Error getting snapshots: {e}")
        return jsonify([])


@app.route('/api/snapshots/<int:snapshot_id>', methods=['GET'])
@require_auth
def api_get_snapshot(snapshot_id):
    try:
        snapshot = Snapshot.query.get(snapshot_id)
        if not snapshot:
            return jsonify({'error': 'Snapshot not found'}), 404
        return jsonify(serialize_snapshot(snapshot))
    except Exception as e:
        logger.error(f"Error getting snapshot: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/snapshots/<int:snapshot_id>', methods=['DELETE'])
@require_auth
def api_delete_snapshot(snapshot_id):
    try:
        snapshot = Snapshot.query.get(snapshot_id)
        if not snapshot:
            return jsonify({'error': 'Snapshot not found'}), 404
        
        db.session.delete(snapshot)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting snapshot: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios/<int:portfolio_id>/snapshot', methods=['POST'])
@require_auth
def api_create_snapshot(portfolio_id):
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        update_all_prices()
        snapshot = create_snapshot_for_portfolio(portfolio, is_manual=True)
        db.session.commit()
        
        return jsonify({'success': True, 'snapshot': serialize_snapshot(snapshot)})
    except Exception as e:
        logger.error(f"Error creating snapshot: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trigger-all-snapshots', methods=['POST'])
@require_auth
def api_trigger_all_snapshots():
    try:
        update_all_prices()
        
        portfolios = Portfolio.query.all()
        for portfolio in portfolios:
            create_snapshot_for_portfolio(portfolio, is_manual=True)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error triggering snapshots: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/compare-snapshots', methods=['POST'])
@require_auth
def api_compare_snapshots():
    try:
        data = request.get_json() or {}
        snapshot_ids = data.get('snapshot_ids', [])
        
        if len(snapshot_ids) < 2:
            return jsonify({'error': 'Need at least 2 snapshots'}), 400
        
        snapshots = Snapshot.query.filter(Snapshot.id.in_(snapshot_ids))\
            .order_by(Snapshot.snapshot_date.asc()).all()
        
        comparison = {
            'snapshots': [serialize_snapshot(s) for s in snapshots],
            'value_changes': []
        }
        
        for i in range(1, len(snapshots)):
            prev = snapshots[i-1]
            curr = snapshots[i]
            change = (curr.total_value or 0) - (prev.total_value or 0)
            pct = (change / prev.total_value * 100) if prev.total_value else 0
            
            comparison['value_changes'].append({
                'from_date': prev.snapshot_date.isoformat() if prev.snapshot_date else '',
                'to_date': curr.snapshot_date.isoformat() if curr.snapshot_date else '',
                'value_change': change,
                'percentage_change': pct
            })
        
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Error comparing snapshots: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/portfolio/<int:portfolio_id>')
@require_auth
def api_export_portfolio(portfolio_id):
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        # Sort holdings by display_order
        ordered_holdings = sorted(
            portfolio.holdings,
            key=lambda h: ((h.display_order or 0), h.id)
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Portfolio:', portfolio.name])
        writer.writerow(['Export Date:', datetime.now().isoformat()])
        writer.writerow([])
        writer.writerow(['Order', 'Symbol', 'Name', 'Note', 'Amount', 'Price', 'Value', 'Avg Buy', 'P/L'])
        
        for h in ordered_holdings:
            pl = 0
            if h.average_buy_price and h.current_price and h.amount:
                pl = (h.current_price - h.average_buy_price) * h.amount
            
            writer.writerow([
                h.display_order or 0,
                h.symbol or '',
                h.name or '',
                h.note or '',
                h.amount or 0,
                h.current_price or 0,
                h.current_value or 0,
                h.average_buy_price or 0,
                pl
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'portfolio_{portfolio_id}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        logger.error(f"Error exporting: {e}")
        return jsonify({'error': str(e)}), 500
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        # Sort holdings by display_order
        ordered_holdings = sorted(
            portfolio.holdings,
            key=lambda h: ((h.display_order or 0), h.id)
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Portfolio:', portfolio.name])
        writer.writerow(['Export Date:', datetime.now().isoformat()])
        writer.writerow([])
        writer.writerow(['Order', 'Symbol', 'Name', 'Note', 'Amount', 'Price', 'Value', 'Avg Buy', 'P/L'])
        
        for h in ordered_holdings:
            pl = 0
            if h.average_buy_price and h.current_price and h.amount:
                pl = (h.current_price - h.average_buy_price) * h.amount
            
            writer.writerow([
                h.display_order or 0,
                h.symbol or '',
                h.name or '',
                h.note or '',
                h.amount or 0,
                h.current_price or 0,
                h.current_value or 0,
                h.average_buy_price or 0,
                pl
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'portfolio_{portfolio_id}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        logger.error(f"Error exporting: {e}")
        return jsonify({'error': str(e)}), 500


# ============== INITIALIZE ==============

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    
    # Create default portfolio if none exist
    if Portfolio.query.count() == 0:
        default_portfolio = Portfolio(
            name='My Portfolio',
            description='Default portfolio for tracking cryptocurrency holdings'
        )
        db.session.add(default_portfolio)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True, port=5000)