# Portfolio Tracker

A web-based cryptocurrency portfolio tracking application built with Flask that allows you to monitor your crypto holdings, track price changes, and analyze your investment performance over time.

## Features

- **Portfolio Management**: Create and manage multiple cryptocurrency portfolios
- **Holdings Tracking**: Add, update, and remove cryptocurrency holdings from your portfolios
- **Real-time Price Data**: Fetch current cryptocurrency prices from CoinGecko API
- **Performance Metrics**: Track profit/loss, price changes, and portfolio value over time
- **Portfolio Snapshots**: Automatically capture portfolio snapshots to analyze historical performance
- **Comparison Tool**: Compare multiple portfolios side-by-side
- **Data Export**: Export portfolio data to CSV format
- **Responsive UI**: Clean, modern web interface for easy portfolio management

## Technology Stack

- **Backend**: Flask 3.0.0 - Python web framework
- **Database**: SQLite - Lightweight relational database
- **Frontend**: HTML5, CSS3, JavaScript
- **API Integration**: CoinGecko API for real-time cryptocurrency data
- **ORM**: Flask-SQLAlchemy for database management
- **HTTP Client**: Requests library for API calls

## Project Structure

```
portfolio_tracker/
├── app.py                 # Main Flask application
├── models.py              # Database models (Portfolio, Holding, Snapshot)
├── config.py              # Configuration settings
├── coingecko_service.py   # CoinGecko API integration
├── scheduler.py           # Background task scheduler for snapshots
├── requirements.txt       # Python dependencies
├── LICENSE                # Project license
├── static/
│   ├── css/
│   │   └── style.css      # Stylesheet
│   └── js/
│       └── main.js        # Frontend JavaScript
└── templates/
    ├── base.html          # Base template
    ├── index.html         # Home/dashboard page
    ├── portfolio.html     # Portfolio detail page
    ├── compare.html       # Portfolio comparison page
    └── snapshots.html     # Snapshot history page
```

## Database Models

### Portfolio
- `id`: Primary key
- `name`: Portfolio name
- `description`: Portfolio description
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `holdings`: List of holdings in the portfolio
- `snapshots`: Historical snapshots of portfolio

### Holding
- `id`: Primary key
- `portfolio_id`: Foreign key to portfolio
- `coin_id`: CoinGecko cryptocurrency ID
- `symbol`: Cryptocurrency symbol (e.g., BTC, ETH)
- `name`: Cryptocurrency name
- `amount`: Quantity held
- `average_buy_price`: Average purchase price
- `current_price`: Current market price
- `current_value`: Total current value (amount × current_price)
- `price_change_24h`: 24-hour price change
- `price_change_percentage_24h`: 24-hour percentage change
- `image_url`: Cryptocurrency logo URL
- `last_updated`: Last price update timestamp
- `created_at`: Creation timestamp

### Snapshot
- `id`: Primary key
- `portfolio_id`: Foreign key to portfolio
- `snapshot_date`: Date of snapshot
- `total_value`: Total portfolio value at snapshot time
- `holdings_data`: JSON data of holdings at snapshot time
- `created_at`: Creation timestamp
- `is_manual`: Whether snapshot was manually created

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd portfolio_tracker
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**
   - Edit `config.py` to customize settings
   - Update `SECRET_KEY` for production use
   - Set database URI if using a different database

5. **Initialize the database**
   ```bash
   python
   >>> from app import app, db
   >>> with app.app_context():
   ...     db.create_all()
   >>> exit()
   ```

## Usage

### Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Creating a Portfolio

1. Navigate to the home page
2. Click "Create New Portfolio"
3. Enter portfolio name and description
4. Submit to create

### Adding Holdings

1. Go to your portfolio
2. Click "Add Holding"
3. Select cryptocurrency from the list
4. Enter amount and average buy price
5. Submit to add to portfolio

### Viewing Portfolio Data

- **Dashboard**: View all portfolios and their current values
- **Portfolio Detail**: See individual holdings, profit/loss, and performance metrics
- **Comparison**: Compare multiple portfolios side-by-side
- **Snapshots**: View historical portfolio value over time

### Exporting Data

- Use the export function to download portfolio data as CSV
- Useful for tax reporting and external analysis

## Configuration

Key settings in `config.py`:

- `SECRET_KEY`: Flask session security key
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `SNAPSHOT_INTERVAL_MINUTES`: How often to take automatic snapshots (default: 15 minutes)
- `COINGECKO_API_URL`: CoinGecko API endpoint

## API Integration

This application uses the **CoinGecko API** (free tier) to fetch:
- Current cryptocurrency prices
- 24-hour price changes
- Cryptocurrency metadata (names, symbols, logos)

No API key is required for the free tier, but there are rate limits.

## Features in Detail

### Real-time Price Updates
- Prices are fetched from CoinGecko API
- Display current value and 24-hour changes
- Automatic price updates when viewing portfolios

### Profit/Loss Calculation
- Calculated based on average buy price and current market price
- Shown as absolute value and percentage change
- Updated with latest market data

### Portfolio Snapshots
- Automatically captures portfolio state at configured intervals
- Manually create snapshots on demand
- View historical portfolio performance
- Analyze trends over time

## License

This project is licensed under the terms specified in the LICENSE file.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a pull request

## Troubleshooting

### Database Issues
- Delete `portfolio_tracker.db` to reset database
- Reinitialize with `db.create_all()`

### CoinGecko API Rate Limits
- Free tier has rate limits
- Wait before retrying if getting rate limit errors
- Consider upgrading API tier for production use

### Port Already in Use
- Change the port in `app.py` or use: `python app.py --port 5001`

## Future Enhancements

- User authentication and multi-user support
- Advanced analytics and charting
- Portfolio rebalancing suggestions
- Tax loss harvesting calculator
- Email alerts for price movements
- Mobile application
- Support for additional asset classes (stocks, commodities)

## Support
For issues, questions, or suggestions, please open an issue on the repository.


## Donations
For donations check my btc address: bc1qpg89n7ldgj6yusrtwwjsdnl9a2sw9z3f0w6ux2