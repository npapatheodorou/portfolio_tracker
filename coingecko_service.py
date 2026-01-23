import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CoinGeckoRateLimitError(Exception):
    """Custom exception for rate limiting"""
    pass


class CoinGeckoService:
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 2.5
        
        if api_key:
            self.session.headers.update({
                'x-cg-demo-api-key': api_key
            })
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a rate-limited request to the CoinGecko API"""
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("CoinGecko rate limit hit")
                raise CoinGeckoRateLimitError("Too many requests. Please wait before trying again.")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                raise CoinGeckoRateLimitError("Too many requests. Please wait before trying again.")
            logger.error(f"CoinGecko API HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGecko API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"CoinGecko API unexpected error: {e}")
            return None
    
    def get_coins_list(self) -> List[Dict]:
        """Get list of all coins"""
        result = self._make_request("coins/list")
        return result if result else []
    
    def get_coins_markets(self, vs_currency: str = "usd", ids: List[str] = None, 
                          per_page: int = 250, page: int = 1) -> List[Dict]:
        """Get market data for coins"""
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }
        
        if ids:
            params["ids"] = ",".join(ids)
        
        result = self._make_request("coins/markets", params)
        return result if result else []
    
    def get_coin_price(self, coin_ids: List[str], vs_currencies: List[str] = None) -> Dict:
        """Get simple price for coins"""
        if vs_currencies is None:
            vs_currencies = ["usd"]
            
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": ",".join(vs_currencies),
            "include_24hr_change": "true",
            "include_last_updated_at": "true"
        }
        
        result = self._make_request("simple/price", params)
        return result if result else {}
    
    def search_coins(self, query: str) -> List[Dict]:
        """Search for coins by name or symbol"""
        params = {"query": query}
        result = self._make_request("search", params)
        
        if result and "coins" in result:
            return result["coins"][:20]
        return []


# Global instance
coingecko = CoinGeckoService()