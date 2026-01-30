# Portfolio Tracker with Encryption

This version adds database encryption and password protection to your portfolio tracker.

## New Features

### 🔐 Database Encryption
- **Password Protection**: Your entire database is encrypted and requires a password to access
- **15-Minute Session Cache**: Enter password once, stay authenticated for 15 minutes
- **Automatic Migration**: Existing data can be migrated to encrypted format
- **Secure Storage**: Uses industry-standard encryption (PBKDF2, SHA256)

### 🔑 Authentication System
- **Login Required**: All routes now require authentication
- **Password Strength**: Minimum 8 characters with complexity requirements
- **Session Management**: Automatic logout after 15 minutes of inactivity
- **Logout Option**: Manual logout button in navigation

## Quick Start

### For New Users
1. Run the app: `python app.py`
2. Visit: http://127.0.0.1:5000
3. You'll be prompted to create a password for your encrypted database
4. Choose a strong password (you'll need it every time)
5. Start using your portfolio tracker!

### For Existing Users (Migration)

If you have an existing `portfolio.db` file:

#### Option 1: Automatic Migration (Recommended)
1. Run the app: `python app.py`
2. Visit: http://127.0.0.1:5000
3. The app will detect your existing database and create encrypted version
4. Create a new password
5. Your data will be automatically migrated

#### Option 2: Manual Migration
1. Run migration script: `python migrate_to_encrypted.py`
2. Follow the prompts to create a password
3. The script will migrate your data safely
4. Then run the app normally

## Security Features

### Password Requirements
- Minimum 8 characters
- Mix of uppercase and lowercase letters
- At least one number
- Special characters recommended

### Encryption Details
- **Algorithm**: PBKDF2 with SHA256
- **Iterations**: 100,000 key stretching rounds
- **Salt**: Unique random salt per database
- **Storage**: Password hash stored separately from database

### Session Management
- 15-minute authentication timeout
- Password cached in memory (not stored)
- Automatic logout on timeout
- Manual logout available

## File Changes

### New Files
- `database_encryption.py` - Encryption management system
- `migrate_to_encrypted.py` - Migration script for existing users
- `templates/login.html` - Login page

### Modified Files
- `app.py` - Added authentication, encryption integration
- `requirements.txt` - Added cryptography library
- `templates/base.html` - Added logout button

### Database Files
- `portfolio.db` - Original unencrypted database (unchanged)
- `portfolio_encrypted.db` - New encrypted database
- `portfolio_encrypted.hash` - Password verification file

## Important Notes

⚠️ **CRITICAL**: Your password cannot be recovered!
- Store it securely (password manager, safe, etc.)
- Without it, your data will be permanently lost
- There's no "forgot password" feature

🔒 **Security Best Practices**:
- Use a unique, strong password
- Don't share your password
- Backup your encrypted database file
- Keep the password hash file with your database

📱 **Mobile Access**:
- The encrypted database works with any device
- Just enter your password when prompted
- Same encryption across all platforms

## Troubleshooting

### "Invalid Password" Error
- Double-check your password
- Ensure Caps Lock is off
- Try again carefully - password is case-sensitive

### Migration Issues
- Make sure `portfolio.db` exists in the same directory
- Close the app before running migration
- Check file permissions

### Performance
- First login may be slightly slower (encryption setup)
- Subsequent operations are fast
- 15-minute cache reduces password prompts

## Recovery & Backup

### Backup Your Database
Copy these files regularly:
- `portfolio_encrypted.db` (your encrypted data)
- `portfolio_encrypted.hash` (password verification)

### Emergency Recovery
- If you lose your password, data is unrecoverable
- Keep a secure backup of your password
- Consider encrypted password managers

## Technical Implementation

The encryption system uses:
- **Cryptography Library**: Industry-standard Python cryptography
- **SQLite Storage**: Modified to work with encrypted connections
- **Session Management**: Flask sessions with timeout
- **Password Hashing**: SHA256 with salt for verification

The system provides security while maintaining usability and performance.

---

**Remember**: With great encryption comes great responsibility - keep your password safe! 🔐