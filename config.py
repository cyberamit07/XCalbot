import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration manager"""
    
    def __init__(self):
        # Bot token
        self.BOT_TOKEN = os.getenv('8877929696:AAHr9UhWW_iTCJboHGCqgsuERJYotuq23Nc')
        if not self.BOT_TOKEN:
            print("❌ ERROR: BOT_TOKEN environment variable is required!")
            print("Please add BOT_TOKEN=your_bot_token to .env file")
            sys.exit(1)
        
        # Admin ID
        admin_id = os.getenv('8603893462')
        if not admin_id:
            print("❌ ERROR: ADMIN_ID environment variable is required!")
            print("Please add ADMIN_ID=your_telegram_user_id to .env file")
            sys.exit(1)
        
        try:
            self.ADMIN_ID = int(admin_id)
        except ValueError:
            print("❌ ERROR: ADMIN_ID must be a valid integer (Telegram user ID)!")
            sys.exit(1)
        
        # Database path
        self.DATABASE_PATH = os.getenv('DATABASE_PATH', 'xcalbot.db')
        
        # Server port
        self.PORT = int(os.getenv('PORT', 8000))
        
        # Broadcast delay (seconds)
        self.BROADCAST_DELAY = float(os.getenv('BROADCAST_DELAY', '0.1'))
        
        # Max expression length
        self.MAX_EXPRESSION_LENGTH = int(os.getenv('MAX_EXPRESSION_LENGTH', '1000'))
    
    def __repr__(self):
        return f"Config(BOT_TOKEN={'***' if self.BOT_TOKEN else 'MISSING'}, ADMIN_ID={self.ADMIN_ID})"
