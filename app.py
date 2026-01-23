from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import json
import csv
import io
import logging
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


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


class Snapshot(db.Model):
    __tablename__ = 'snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False)
    total_value = db.Column(db.Float, nullable=False, default=0)
    holdings_data = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_manual = db.Column(db.Boolean, default=False)


# ============== HELPER FUNCTIONS ==============

def serialize_portfolio(p):
    """Safely serialize a portfolio"""
    try:
        holdings_list = []
        total_value = 0
        
        for h in p.holdings:
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
                'profit_loss_percentage': 0
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
    
    return {
        'id': s.id,
        'portfolio_id': s.portfolio_id,
        'snapshot_date': s.snapshot_date.isoformat() if s.snapshot_date else None,
        'total_value': float(s.total_value) if s.total_value else 0,
        'holdings_data': holdings,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'is_manual': bool(s.is_manual)
    }


def get_coin_price(coin_ids):
    """Get prices from CoinGecko"""
    try:
        time.sleep(1.5)  # Rate limiting
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 429:
            return None, True  # Rate limited
        
        response.raise_for_status()
        return response.json(), False
    except Exception as e:
        logger.error(f"CoinGecko error: {e}")
        return None, False


def search_coins(query):
    """Search coins on CoinGecko"""
    try:
        time.sleep(1.5)  # Rate limiting
        url = "https://api.coingecko.com/api/v3/search"
        response = requests.get(url, params={"query": query}, timeout=30)
        
        if response.status_code == 429:
            return None, True
        
        response.raise_for_status()
        data = response.json()
        return data.get("coins", [])[:20], False
    except Exception as e:
        logger.error(f"Search error: {e}")
        return [], False


def get_coins_markets(coin_ids):
    """Get market data from CoinGecko"""
    try:
        time.sleep(1.5)
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ",".join(coin_ids),
            "order": "market_cap_desc",
            "per_page": 250,
            "page": 1,
            "sparkline": "false"
        }
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 429:
            return None, True
        
        response.raise_for_status()
        return response.json(), False
    except Exception as e:
        logger.error(f"Markets error: {e}")
        return [], False


def update_all_prices():
    """Update prices for all holdings"""
    try:
        holdings = Holding.query.all()
        if not holdings:
            return {'success': True}
        
        coin_ids = list(set(h.coin_id for h in holdings if h.coin_id))
        if not coin_ids:
            return {'success': True}
        
        market_data, rate_limited = get_coins_markets(coin_ids)
        
        if rate_limited:
            return {'success': False, 'rate_limited': True}
        
        if not market_data:
            return {'success': False, 'error': 'No market data'}
        
        price_lookup = {coin['id']: coin for coin in market_data}
        
        for holding in holdings:
            if holding.coin_id in price_lookup:
                coin = price_lookup[holding.coin_id]
                holding.current_price = coin.get('current_price')
                holding.current_value = (holding.current_price or 0) * (holding.amount or 0)
                holding.price_change_24h = coin.get('price_change_24h')
                holding.price_change_percentage_24h = coin.get('price_change_percentage_24h')
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
    
    holdings_data = []
    total_value = 0
    
    for h in portfolio.holdings:
        hd = {
            'coin_id': h.coin_id or '',
            'symbol': h.symbol or '',
            'name': h.name or '',
            'amount': float(h.amount) if h.amount else 0,
            'current_price': float(h.current_price) if h.current_price else None,
            'current_value': float(h.current_value) if h.current_value else 0,
            'average_buy_price': float(h.average_buy_price) if h.average_buy_price else None,
            'image_url': h.image_url or ''
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


# ============== PAGE ROUTES ==============

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/portfolio/<int:portfolio_id>')
def portfolio_detail(portfolio_id):
    return render_template('portfolio.html', portfolio_id=portfolio_id)


@app.route('/snapshots')
def snapshots_page():
    return render_template('snapshots.html')


@app.route('/compare')
def compare_page():
    return render_template('compare.html')


# ============== API ROUTES ==============

@app.route('/api/portfolios', methods=['GET'])
def api_get_portfolios():
    try:
        portfolios = Portfolio.query.all()
        result = [serialize_portfolio(p) for p in portfolios]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting portfolios: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolios', methods=['POST'])
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
def api_add_holding(portfolio_id):
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        data = request.get_json() or {}
        
        if not data.get('coin_id'):
            return jsonify({'error': 'coin_id is required'}), 400
        
        existing = Holding.query.filter_by(
            portfolio_id=portfolio_id,
            coin_id=data['coin_id']
        ).first()
        
        if existing:
            existing.amount = (existing.amount or 0) + (data.get('amount') or 0)
            if data.get('average_buy_price'):
                old_amount = (existing.amount or 0) - (data.get('amount') or 0)
                old_value = old_amount * (existing.average_buy_price or 0)
                new_value = (data.get('amount') or 0) * (data.get('average_buy_price') or 0)
                if existing.amount > 0:
                    existing.average_buy_price = (old_value + new_value) / existing.amount
            holding = existing
        else:
            holding = Holding(
                portfolio_id=portfolio_id,
                coin_id=data.get('coin_id', ''),
                symbol=data.get('symbol', ''),
                name=data.get('name', ''),
                amount=data.get('amount') or 0,
                average_buy_price=data.get('average_buy_price'),
                image_url=data.get('image_url', '')
            )
            db.session.add(holding)
        
        # Try to get price
        rate_limited = False
        try:
            price_data, rate_limited = get_coin_price([holding.coin_id])
            if price_data and holding.coin_id in price_data:
                coin_price = price_data[holding.coin_id]
                holding.current_price = coin_price.get('usd')
                holding.current_value = (holding.current_price or 0) * (holding.amount or 0)
                holding.price_change_percentage_24h = coin_price.get('usd_24h_change')
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
            'current_value': holding.current_value
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
        
        if holding.current_price:
            holding.current_value = (holding.current_price or 0) * (holding.amount or 0)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating holding: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/holdings/<int:holding_id>', methods=['DELETE'])
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


@app.route('/api/coins/search')
def api_search_coins():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    try:
        results, rate_limited = search_coins(query)
        if rate_limited:
            return jsonify({'error': 'Rate limited', 'rate_limited': True}), 429
        return jsonify(results or [])
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify([])


@app.route('/api/refresh-prices', methods=['POST'])
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
def api_export_portfolio(portfolio_id):
    try:
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Portfolio:', portfolio.name])
        writer.writerow(['Export Date:', datetime.now().isoformat()])
        writer.writerow([])
        writer.writerow(['Symbol', 'Name', 'Amount', 'Price', 'Value', 'Avg Buy', 'P/L'])
        
        for h in portfolio.holdings:
            pl = 0
            if h.average_buy_price and h.current_price and h.amount:
                pl = (h.current_price - h.average_buy_price) * h.amount
            
            writer.writerow([
                h.symbol or '',
                h.name or '',
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

with app.app_context():
    db.create_all()
    
    # Create default portfolio if none exists
    if Portfolio.query.count() == 0:
        default = Portfolio(name="Main Portfolio", description="Your primary crypto portfolio")
        db.session.add(default)
        db.session.commit()
        logger.info("Created default portfolio")


if __name__ == '__main__':
    app.run(debug=True, port=5000)