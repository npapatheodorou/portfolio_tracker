from flask_apscheduler import APScheduler
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
scheduler = APScheduler()


def update_portfolio_prices(app):
    """Update prices for all holdings in all portfolios"""
    with app.app_context():
        from models import db, Holding
        from coingecko_service import coingecko, CoinGeckoRateLimitError
        
        logger.info("Starting scheduled price update...")
        
        try:
            holdings = Holding.query.all()
            
            if not holdings:
                logger.info("No holdings to update")
                return {'success': True, 'message': 'No holdings to update'}
            
            coin_ids = list(set(h.coin_id for h in holdings))
            
            batch_size = 50
            all_market_data = []
            
            for i in range(0, len(coin_ids), batch_size):
                batch = coin_ids[i:i + batch_size]
                try:
                    market_data = coingecko.get_coins_markets(ids=batch)
                    if market_data:
                        all_market_data.extend(market_data)
                except CoinGeckoRateLimitError:
                    logger.warning("Rate limited during batch fetch")
                    return {'success': False, 'rate_limited': True}
            
            price_lookup = {coin['id']: coin for coin in all_market_data}
            
            for holding in holdings:
                if holding.coin_id in price_lookup:
                    coin_data = price_lookup[holding.coin_id]
                    holding.current_price = coin_data.get('current_price')
                    holding.current_value = (holding.current_price or 0) * (holding.amount or 0)
                    holding.price_change_24h = coin_data.get('price_change_24h')
                    holding.price_change_percentage_24h = coin_data.get('price_change_percentage_24h')
                    holding.image_url = coin_data.get('image')
                    holding.last_updated = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Updated prices for {len(holdings)} holdings")
            return {'success': True, 'updated': len(holdings)}
            
        except CoinGeckoRateLimitError:
            logger.warning("Rate limited during price update")
            return {'success': False, 'rate_limited': True}
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
            return {'success': False, 'error': str(e)}


def create_daily_snapshots(app):
    """Create daily snapshots for all portfolios"""
    with app.app_context():
        from models import db, Portfolio, Snapshot
        
        logger.info("Creating daily snapshots...")
        
        try:
            portfolios = Portfolio.query.all()
            
            for portfolio in portfolios:
                try:
                    Snapshot.create_snapshot(portfolio, is_manual=False)
                    logger.info(f"Created/updated snapshot for portfolio: {portfolio.name}")
                except Exception as e:
                    logger.error(f"Error creating snapshot for portfolio {portfolio.id}: {e}")
            
            db.session.commit()
            logger.info("Daily snapshots completed")
        except Exception as e:
            logger.error(f"Error in create_daily_snapshots: {e}")


def init_scheduler(app):
    """Initialize the scheduler with jobs"""
    scheduler.init_app(app)
    
    scheduler.add_job(
        id='update_prices',
        func=lambda: update_portfolio_prices(app),
        trigger='interval',
        minutes=15,
        replace_existing=True
    )
    
    scheduler.add_job(
        id='create_snapshots',
        func=lambda: create_daily_snapshots(app),
        trigger='interval',
        minutes=15,
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler initialized with jobs")