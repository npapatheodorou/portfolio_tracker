from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import json

db = SQLAlchemy()

class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    holdings = db.relationship('Holding', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    snapshots = db.relationship('Snapshot', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        holdings_list = []
        total_value = 0
        
        for h in self.holdings:
            try:
                holding_dict = h.to_dict()
                holdings_list.append(holding_dict)
                total_value += holding_dict.get('current_value') or 0
            except Exception as e:
                print(f"Error serializing holding {h.id}: {e}")
                continue
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'holdings': holdings_list,
            'total_value': total_value
        }


class Holding(db.Model):
    __tablename__ = 'holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    coin_id = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0)
    average_buy_price = db.Column(db.Float, nullable=True)
    current_price = db.Column(db.Float, nullable=True)
    current_value = db.Column(db.Float, nullable=True)
    price_change_24h = db.Column(db.Float, nullable=True)
    price_change_percentage_24h = db.Column(db.Float, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    last_updated = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        profit_loss = self.calculate_profit_loss()
        profit_loss_percentage = self.calculate_profit_loss_percentage()
        
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'coin_id': self.coin_id,
            'symbol': self.symbol or '',
            'name': self.name or '',
            'amount': self.amount or 0,
            'average_buy_price': self.average_buy_price,
            'current_price': self.current_price,
            'current_value': self.current_value or 0,
            'price_change_24h': self.price_change_24h,
            'price_change_percentage_24h': self.price_change_percentage_24h,
            'image_url': self.image_url,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'profit_loss': profit_loss if profit_loss is not None else 0,
            'profit_loss_percentage': profit_loss_percentage if profit_loss_percentage is not None else 0
        }
    
    def calculate_profit_loss(self):
        if self.average_buy_price and self.current_price and self.amount:
            return (self.current_price - self.average_buy_price) * self.amount
        return 0
    
    def calculate_profit_loss_percentage(self):
        if self.average_buy_price and self.current_price and self.average_buy_price > 0:
            return ((self.current_price - self.average_buy_price) / self.average_buy_price) * 100
        return 0


class Snapshot(db.Model):
    __tablename__ = 'snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False)
    total_value = db.Column(db.Float, nullable=False, default=0)
    holdings_data = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_manual = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('portfolio_id', 'snapshot_date', name='unique_portfolio_date'),
    )
    
    def to_dict(self):
        try:
            holdings = json.loads(self.holdings_data) if self.holdings_data else []
        except (json.JSONDecodeError, TypeError):
            holdings = []
        
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'total_value': self.total_value or 0,
            'holdings_data': holdings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_manual': self.is_manual or False
        }
    
    @classmethod
    def create_snapshot(cls, portfolio, is_manual=False):
        """Create or update today's snapshot for a portfolio"""
        today = date.today()
        
        holdings_data = []
        total_value = 0
        
        for holding in portfolio.holdings:
            holding_snapshot = {
                'coin_id': holding.coin_id,
                'symbol': holding.symbol or '',
                'name': holding.name or '',
                'amount': holding.amount or 0,
                'current_price': holding.current_price,
                'current_value': holding.current_value or 0,
                'average_buy_price': holding.average_buy_price,
                'image_url': holding.image_url
            }
            holdings_data.append(holding_snapshot)
            total_value += holding.current_value or 0
        
        existing_snapshot = cls.query.filter_by(
            portfolio_id=portfolio.id,
            snapshot_date=today
        ).first()
        
        if existing_snapshot:
            existing_snapshot.total_value = total_value
            existing_snapshot.holdings_data = json.dumps(holdings_data)
            existing_snapshot.created_at = datetime.utcnow()
            existing_snapshot.is_manual = is_manual
            return existing_snapshot
        else:
            snapshot = cls(
                portfolio_id=portfolio.id,
                snapshot_date=today,
                total_value=total_value,
                holdings_data=json.dumps(holdings_data),
                is_manual=is_manual
            )
            db.session.add(snapshot)
            return snapshot