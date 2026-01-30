# Portfolio Tracker

A web-based cryptocurrency portfolio tracking application built with Flask that allows you to monitor your crypto holdings, track price changes, and analyze your investment performance over time.

## Features

- **Portfolio Management**: Create and manage multiple cryptocurrency portfolios
- **Holdings Tracking**: Add, update, and remove cryptocurrency holdings from your portfolios (duplicates allowed with notes)
- **Multi-API Price Data**: Fetch prices from CoinCap, CoinGecko, and CoinPaprika with automatic fallback
- **Database Encryption**: Password-protected encrypted database for security
- **Performance Metrics**: Track profit/loss, price changes, and portfolio value over time
- **Portfolio Snapshots**: Automatically capture portfolio snapshots to analyze historical performance
- **Comparison Tool**: Compare multiple portfolios side-by-side
- **Data Export**: Export portfolio data to CSV format
- **Responsive UI**: Clean, modern web interface for easy portfolio management
- **Automatic Database Setup**: Tables and default portfolio created automatically on first run

## Technology Stack

- **Backend**: Flask 3.0.0 - Python web framework
- **Database**: SQLite with encryption - Lightweight relational database
- **Frontend**: HTML5, CSS3, JavaScript
- **API Integration**: Multi-API support (CoinCap, CoinGecko, CoinPaprika) with rate limiting
- **ORM**: Flask-SQLAlchemy for database management
- **HTTP Client**: Requests library for API calls
- **Security**: Database encryption with password authentication

## Project Structure

```
portfolio_tracker/
├── app.py                 # Main Flask application with integrated crypto API service
├── models.py              # Database models (Portfolio, Holding, Snapshot)
├── config.py              # Configuration settings
├── coingecko_service.py   # Legacy CoinGecko API integration
├── scheduler.py           # Background task scheduler for snapshots
├── database_encryption.py # Database encryption and authentication system
├── migrate_to_encrypted.py # Migration script for existing databases
├── ENCRYPTION_README.md   # Database encryption documentation
├── requirements.txt       # Python dependencies
├── LICENSE                # Project license
├── instance/              # Instance folder for encrypted database
│   └── portfolio_encrypted.db  # Encrypted SQLite database
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
    ├── snapshots.html     # Snapshot history page
    └── login.html         # Authentication page
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
- `coin_id`: Multi-API cryptocurrency ID (CoinCap, CoinGecko, or CoinPaprika)
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
- `display_order`: Order for displaying holdings in portfolio
- `note`: Optional note to distinguish duplicate holdings

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
   - Database is automatically configured and encrypted

5. **Run the application**
   ```bash
   python app.py
   ```
   
   The first time you run the application:
   - Database tables will be created automatically
   - A default portfolio named "My Portfolio" will be created
   - You'll be prompted to set up database encryption with a password
   - The encrypted database will be stored in the `/instance/` folder

## Usage

### Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### First-Time Setup

1. Navigate to `http://localhost:5000`
2. You'll be redirected to the login page for database setup
3. Choose a strong password (minimum 8 characters)
4. Confirm your password
5. The encrypted database will be initialized with a default portfolio

### Creating Additional Portfolios

1. After logging in, navigate to the home page
2. Click "Create New Portfolio"
3. Enter portfolio name and description
4. Submit to create

### Adding Holdings

1. Go to your portfolio
2. Click "Add Holding"
3. Search and select cryptocurrency from the list (uses multiple APIs)
4. Enter amount and average buy price
5. Optionally add a note to distinguish holdings
6. Submit to add to portfolio

**Note**: Duplicate holdings are allowed - use the note field to distinguish between different purchase batches or strategies.

### Viewing Portfolio Data

- **Dashboard**: View all portfolios and their current values
- **Portfolio Detail**: See individual holdings, profit/loss, and performance metrics
- **Comparison**: Compare multiple portfolios side-by-side
- **Snapshots**: View historical portfolio value over time

### Exporting Data

- Use the export function to download portfolio data as CSV
- Useful for tax reporting and external analysis

## Configuration

Key settings in `app.py`:

- `SECRET_KEY`: Flask session security key
- `SQLALCHEMY_DATABASE_URI`: Database connection string (encrypted SQLite in instance folder)
- `SQLALCHEMY_TRACK_MODIFICATIONS`: SQLAlchemy modification tracking (disabled for performance)

## Database Security

- **Encryption**: Database is encrypted with AES-256 encryption
- **Authentication**: Password-protected access to database
- **Instance Folder**: Database stored in `/instance/` folder for security
- **Migration**: Automatic migration from unencrypted to encrypted databases

## API Integration

This application uses **multiple cryptocurrency APIs** with automatic fallback:

1. **CoinCap API** (primary)
2. **CoinGecko API** (fallback)
3. **CoinPaprika API** (secondary fallback)

Features:
- **Rate Limiting**: Built-in rate limiting for each API
- **Automatic Fallback**: Switches to next API if one fails or is rate limited
- **No API Keys Required**: All APIs work with free tiers
- **Comprehensive Data**: Prices, 24h changes, metadata, and images

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
- Encrypted database is stored in `/instance/portfolio_encrypted.db`
- Delete both `.db` and `.hash` files to reset database
- Database tables are created automatically on startup
- Default portfolio "My Portfolio" is created if no portfolios exist

### Multi-API Rate Limits
- Each API has different rate limits (CoinCap: 200/min, CoinGecko: 10-30/min, CoinPaprika: 60/min)
- Built-in rate limiting prevents API blocking
- Automatic fallback ensures data availability
- Wait if you receive rate limit warnings

### Authentication Issues
- If you forget your password, you must delete the database and start over
- Password must be at least 8 characters
- Database is encrypted - recovery is impossible without password

### Port Already in Use
- Change the port in `app.py` or use: `python app.py --port 5001`

## Recent Updates

### Version 2.0 - Security & Multi-API Enhancement
- **Database Encryption**: Added AES-256 encrypted database with password protection
- **Multi-API Support**: Integrated CoinCap, CoinGecko, and CoinPaprika APIs with automatic fallback
- **Automatic Setup**: Database tables and default portfolio created automatically
- **Enhanced Holdings**: Support for duplicate holdings with notes and display ordering
- **Rate Limiting**: Built-in rate limiting for all APIs
- **Instance Folder**: Database properly stored in Flask instance folder
- **Migration Tool**: Automatic migration from unencrypted to encrypted databases

## Future Enhancements

- Multi-user support with individual encrypted databases
- Advanced analytics and charting
- Portfolio rebalancing suggestions
- Tax loss harvesting calculator
- Email alerts for price movements
- Mobile application
- Support for additional asset classes (stocks, commodities)
- Cloud backup for encrypted databases

## Support
For issues, questions, or suggestions, please open an issue on the repository.


## Donations
For donations check my btc address: bc1qpg89n7ldgj6yusrtwwjsdnl9a2sw9z3f0w6ux2