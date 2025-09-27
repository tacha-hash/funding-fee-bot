#!/usr/bin/env python3
"""
Setup script for AsterDex Funding Bot environment configuration.
This script helps you create the .env file with proper API credentials.
"""
import os
import sys

def create_env_file():
    """Create .env file with user input for API credentials."""
    env_path = ".env"
    
    print("🚀 AsterDex Funding Bot Environment Setup")
    print("=" * 50)
    
    if os.path.exists(env_path):
        response = input(f"⚠️  {env_path} already exists. Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return False
    
    print("\n📝 Please provide your AsterDex API credentials:")
    print("   (You can find these in your AsterDex account settings)")
    
    api_key = input("🔑 API Key: ").strip()
    if not api_key:
        print("❌ API Key is required!")
        return False
    
    api_secret = input("🔐 API Secret: ").strip()
    if not api_secret:
        print("❌ API Secret is required!")
        return False
    
    print("\n⚙️  Bot Configuration (press Enter for defaults):")
    
    capital = input("💰 Capital USD (default: 200000): ").strip() or "200000"
    spot_symbol = input("📈 Spot Symbol (default: ASTERUSDT): ").strip() or "ASTERUSDT"
    futures_symbol = input("📊 Futures Symbol (default: ASTERUSDT): ").strip() or "ASTERUSDT"
    batch_quote = input("💵 Batch Quote (default: 200): ").strip() or "200"
    batch_delay = input("⏱️  Batch Delay seconds (default: 1.0): ").strip() or "1.0"
    mode = input("🎯 Mode (buy_spot_short_futures/sell_spot_long_futures, default: buy_spot_short_futures): ").strip() or "buy_spot_short_futures"
    log_level = input("📋 Log Level (DEBUG/INFO/WARNING/ERROR, default: INFO): ").strip() or "INFO"
    
    env_content = f"""# AsterDex API Credentials
ASTERDEX_API_KEY={api_key}
ASTERDEX_API_SECRET={api_secret}

# Bot Configuration (Optional - can also use CLI arguments)
DEFAULT_CAPITAL_USD={capital}
DEFAULT_SPOT_SYMBOL={spot_symbol}
DEFAULT_FUTURES_SYMBOL={futures_symbol}
DEFAULT_BATCH_QUOTE={batch_quote}
DEFAULT_BATCH_DELAY={batch_delay}
DEFAULT_MODE={mode}
DEFAULT_LOG_LEVEL={log_level}
"""
    
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(f"\n✅ Successfully created {env_path}")
        print("\n🔒 Security reminder:")
        print("   - Never commit your .env file to version control")
        print("   - Keep your API credentials secure")
        print("   - Test with small amounts first")
        return True
    except Exception as e:
        print(f"❌ Error creating {env_path}: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    try:
        import requests
        print(f"✅ requests: {requests.__version__}")
    except ImportError:
        print("❌ requests not found. Install with: pip install requests")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv: available")
    except ImportError:
        print("⚠️  python-dotenv not found. Install with: pip install python-dotenv")
        print("   (Bot will still work, but .env file won't be auto-loaded)")
    
    return True

def main():
    """Main setup function."""
    print("Starting AsterDex Funding Bot setup...\n")
    
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    if create_env_file():
        print("\n🎉 Setup complete! You can now run the bot with:")
        print("   python3 funding_bot.py")
        print("\n💡 For help with command line options:")
        print("   python3 funding_bot.py --help")
    else:
        print("\n❌ Setup failed. Please try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
