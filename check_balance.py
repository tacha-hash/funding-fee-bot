#!/usr/bin/env python3
"""
Balance checker and bot preparation script for AsterDex Funding Bot.
This script checks account balances, symbol information, and validates bot configuration.
"""
import json
import os
import sys
from decimal import Decimal
from typing import Dict, Any, Optional

# Import the bot class to reuse its API functionality
from funding_bot import AsterDexFundingBot, DEFAULT_CAPITAL_USD, DEFAULT_SPOT_SYMBOL, DEFAULT_FUTURES_SYMBOL, DEFAULT_BATCH_QUOTE

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

class BalanceChecker:
    """Helper class to check balances and prepare bot configuration."""
    
    def __init__(self):
        """Initialize with API credentials."""
        api_key = os.environ.get("ASTERDEX_API_KEY", "")
        api_secret = os.environ.get("ASTERDEX_API_SECRET", "")
        
        if not api_key or not api_secret:
            print("❌ Missing API credentials!")
            print("   Please set ASTERDEX_API_KEY and ASTERDEX_API_SECRET environment variables")
            print("   or run: python3 setup_env.py")
            sys.exit(1)
        
        # Create a minimal bot instance just for API access
        self.bot = AsterDexFundingBot(
            capital_usd=Decimal("1000"),  # Minimal capital for initialization
            spot_symbol=DEFAULT_SPOT_SYMBOL,
            futures_symbol=DEFAULT_FUTURES_SYMBOL,
            batch_quote=Decimal("100")
        )
    
    def check_spot_balance(self) -> Dict[str, Any]:
        """Check spot account balance."""
        print("🔍 Checking spot account balance...")
        try:
            response = self.bot._request(
                self.bot.spot_base_url,
                "/api/v1/account",
                signed=True
            )
            balances = {}
            for balance in response.get("balances", []):
                asset = balance.get("asset")
                free = Decimal(balance.get("free", "0"))
                locked = Decimal(balance.get("locked", "0"))
                total = free + locked
                if total > 0:
                    balances[asset] = {
                        "free": str(free),
                        "locked": str(locked),
                        "total": str(total)
                    }
            return balances
        except Exception as e:
            print(f"❌ Error checking spot balance: {e}")
            return {}
    
    def check_futures_balance(self) -> Dict[str, Any]:
        """Check futures account balance."""
        print("🔍 Checking futures account balance...")
        try:
            response = self.bot._request(
                self.bot.futures_base_url,
                "/fapi/v1/account",
                signed=True
            )
            balances = {}
            for balance in response.get("assets", []):
                asset = balance.get("asset")
                wallet_balance = Decimal(balance.get("walletBalance", "0"))
                unrealized_profit = Decimal(balance.get("unrealizedProfit", "0"))
                margin_balance = Decimal(balance.get("marginBalance", "0"))
                if wallet_balance > 0 or unrealized_profit != 0:
                    balances[asset] = {
                        "walletBalance": str(wallet_balance),
                        "unrealizedProfit": str(unrealized_profit),
                        "marginBalance": str(margin_balance)
                    }
            
            # Also get positions
            positions = []
            for position in response.get("positions", []):
                symbol = position.get("symbol")
                position_amt = Decimal(position.get("positionAmt", "0"))
                if position_amt != 0:
                    positions.append({
                        "symbol": symbol,
                        "positionAmt": str(position_amt),
                        "entryPrice": position.get("entryPrice"),
                        "markPrice": position.get("markPrice"),
                        "unRealizedProfit": position.get("unRealizedProfit")
                    })
            
            return {
                "balances": balances,
                "positions": positions
            }
        except Exception as e:
            print(f"❌ Error checking futures balance: {e}")
            return {}
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information for both spot and futures."""
        print(f"📊 Getting symbol information for {symbol}...")
        
        info = {
            "symbol": symbol,
            "spot": {},
            "futures": {}
        }
        
        try:
            # Get spot symbol info
            spot_info = self.bot._get_spot_symbol_info()
            spot_step, spot_min_qty = self.bot._extract_step_and_min_qty(spot_info)
            info["spot"] = {
                "status": spot_info.get("status"),
                "stepSize": str(spot_step),
                "minQty": str(spot_min_qty),
                "filters": spot_info.get("filters", [])
            }
        except Exception as e:
            print(f"⚠️  Error getting spot symbol info: {e}")
        
        try:
            # Get futures symbol info
            futures_info = self.bot._get_futures_symbol_info()
            futures_step, futures_min_qty = self.bot._extract_step_and_min_qty(futures_info)
            futures_min_notional = self.bot._extract_min_notional(futures_info)
            info["futures"] = {
                "status": futures_info.get("status"),
                "stepSize": str(futures_step),
                "minQty": str(futures_min_qty),
                "minNotional": str(futures_min_notional),
                "filters": futures_info.get("filters", [])
            }
        except Exception as e:
            print(f"⚠️  Error getting futures symbol info: {e}")
        
        return info
    
    def get_current_prices(self, symbol: str) -> Dict[str, str]:
        """Get current spot and futures prices."""
        print(f"💰 Getting current prices for {symbol}...")
        
        prices = {}
        try:
            spot_price = self.bot._fetch_spot_price()
            prices["spot"] = str(spot_price)
        except Exception as e:
            print(f"⚠️  Error getting spot price: {e}")
            prices["spot"] = "N/A"
        
        try:
            futures_price = self.bot._fetch_futures_price()
            prices["futures"] = str(futures_price)
        except Exception as e:
            print(f"⚠️  Error getting futures price: {e}")
            prices["futures"] = "N/A"
        
        return prices
    
    def validate_bot_config(self, capital_usd: Decimal, batch_quote: Decimal, symbol: str) -> Dict[str, Any]:
        """Validate bot configuration and calculate requirements."""
        print(f"✅ Validating bot configuration...")
        
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "calculations": {}
        }
        
        # Check capital and batch configuration
        if capital_usd <= 0:
            validation["valid"] = False
            validation["errors"].append("Capital must be greater than zero")
        
        if batch_quote <= 0:
            validation["valid"] = False
            validation["errors"].append("Batch quote must be greater than zero")
        
        if capital_usd > 0 and batch_quote > 0:
            batches, remainder = divmod(capital_usd, batch_quote)
            if remainder != 0:
                validation["valid"] = False
                validation["errors"].append(f"Capital {capital_usd} is not an exact multiple of batch quote {batch_quote}")
            else:
                validation["calculations"]["batch_count"] = int(batches)
                validation["calculations"]["total_capital"] = str(capital_usd)
                validation["calculations"]["per_batch"] = str(batch_quote)
        
        # Check if we can get current price for calculations
        try:
            current_price = self.bot._fetch_spot_price()
            theoretical_base_qty = capital_usd / current_price
            validation["calculations"]["current_price"] = str(current_price)
            validation["calculations"]["theoretical_base_qty"] = str(theoretical_base_qty)
            
            # Check against symbol requirements
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info["spot"].get("minQty"):
                min_qty = Decimal(symbol_info["spot"]["minQty"])
                batch_base_qty = batch_quote / current_price
                if batch_base_qty < min_qty:
                    validation["warnings"].append(f"Batch base quantity {batch_base_qty} may be below minimum {min_qty}")
            
        except Exception as e:
            validation["warnings"].append(f"Could not validate against current prices: {e}")
        
        return validation

def main():
    """Main function to check balances and prepare bot configuration."""
    print("🚀 AsterDex Funding Bot - Balance Check & Preparation")
    print("=" * 60)
    
    # Initialize checker
    try:
        checker = BalanceChecker()
    except SystemExit:
        return
    
    # Get configuration from environment or use defaults
    capital_usd = Decimal(os.environ.get("DEFAULT_CAPITAL_USD", str(DEFAULT_CAPITAL_USD)))
    spot_symbol = os.environ.get("DEFAULT_SPOT_SYMBOL", DEFAULT_SPOT_SYMBOL)
    futures_symbol = os.environ.get("DEFAULT_FUTURES_SYMBOL", DEFAULT_FUTURES_SYMBOL)
    batch_quote = Decimal(os.environ.get("DEFAULT_BATCH_QUOTE", str(DEFAULT_BATCH_QUOTE)))
    
    print(f"📋 Configuration:")
    print(f"   Capital: {capital_usd} USDT")
    print(f"   Spot Symbol: {spot_symbol}")
    print(f"   Futures Symbol: {futures_symbol}")
    print(f"   Batch Quote: {batch_quote} USDT")
    print()
    
    # Check balances
    spot_balances = checker.check_spot_balance()
    futures_data = checker.check_futures_balance()
    
    # Get symbol information
    symbol_info = checker.get_symbol_info(spot_symbol)
    
    # Get current prices
    prices = checker.get_current_prices(spot_symbol)
    
    # Validate configuration
    validation = checker.validate_bot_config(capital_usd, batch_quote, spot_symbol)
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 BALANCE CHECK RESULTS")
    print("=" * 60)
    
    print(f"\n💰 SPOT BALANCES:")
    if spot_balances:
        for asset, balance in spot_balances.items():
            print(f"   {asset}: {balance['total']} (free: {balance['free']}, locked: {balance['locked']})")
    else:
        print("   No balances found or error occurred")
    
    print(f"\n📈 FUTURES ACCOUNT:")
    if futures_data.get("balances"):
        for asset, balance in futures_data["balances"].items():
            print(f"   {asset}: {balance['marginBalance']} (wallet: {balance['walletBalance']}, PnL: {balance['unrealizedProfit']})")
    else:
        print("   No balances found or error occurred")
    
    if futures_data.get("positions"):
        print(f"\n🎯 OPEN POSITIONS:")
        for position in futures_data["positions"]:
            print(f"   {position['symbol']}: {position['positionAmt']} @ {position['entryPrice']} (PnL: {position['unRealizedProfit']})")
    
    print(f"\n💵 CURRENT PRICES ({spot_symbol}):")
    print(f"   Spot: {prices.get('spot', 'N/A')}")
    print(f"   Futures: {prices.get('futures', 'N/A')}")
    
    print(f"\n⚙️  CONFIGURATION VALIDATION:")
    if validation["valid"]:
        print("   ✅ Configuration is valid")
        calc = validation["calculations"]
        if calc:
            print(f"   📊 Calculations:")
            print(f"      Batch count: {calc.get('batch_count', 'N/A')}")
            print(f"      Current price: {calc.get('current_price', 'N/A')}")
            print(f"      Theoretical base qty: {calc.get('theoretical_base_qty', 'N/A')}")
    else:
        print("   ❌ Configuration has errors:")
        for error in validation["errors"]:
            print(f"      - {error}")
    
    if validation["warnings"]:
        print("   ⚠️  Warnings:")
        for warning in validation["warnings"]:
            print(f"      - {warning}")
    
    print(f"\n📋 SYMBOL INFO ({spot_symbol}):")
    if symbol_info["spot"]:
        print(f"   Spot - Status: {symbol_info['spot'].get('status', 'N/A')}")
        print(f"   Spot - Min Qty: {symbol_info['spot'].get('minQty', 'N/A')}")
        print(f"   Spot - Step Size: {symbol_info['spot'].get('stepSize', 'N/A')}")
    
    if symbol_info["futures"]:
        print(f"   Futures - Status: {symbol_info['futures'].get('status', 'N/A')}")
        print(f"   Futures - Min Qty: {symbol_info['futures'].get('minQty', 'N/A')}")
        print(f"   Futures - Min Notional: {symbol_info['futures'].get('minNotional', 'N/A')}")
        print(f"   Futures - Step Size: {symbol_info['futures'].get('stepSize', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("=" * 60)
    
    if validation["valid"] and spot_balances and futures_data:
        print("✅ Ready to run the bot!")
        print("\n📝 Command to run:")
        print(f"   python3 funding_bot.py \\")
        print(f"     --capital {capital_usd} \\")
        print(f"     --spot-symbol {spot_symbol} \\")
        print(f"     --futures-symbol {futures_symbol} \\")
        print(f"     --batch-quote {batch_quote} \\")
        print(f"     --log-level INFO")
        
        # Check if user has enough balance
        usdt_balance = Decimal(spot_balances.get("USDT", {}).get("free", "0"))
        if usdt_balance < capital_usd:
            print(f"\n⚠️  WARNING: Insufficient USDT balance!")
            print(f"   Required: {capital_usd} USDT")
            print(f"   Available: {usdt_balance} USDT")
            print(f"   Shortfall: {capital_usd - usdt_balance} USDT")
    else:
        print("❌ Please fix the issues above before running the bot")
        if not validation["valid"]:
            print("   - Fix configuration errors")
        if not spot_balances:
            print("   - Check spot account access")
        if not futures_data:
            print("   - Check futures account access")
    
    print("\n💡 Tips:")
    print("   - Start with a small amount to test")
    print("   - Monitor positions after execution")
    print("   - Check funding rates on AsterDex")
    print("   - Ensure you have sufficient margin for futures positions")

if __name__ == "__main__":
    main()
