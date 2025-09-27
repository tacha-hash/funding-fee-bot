#!/usr/bin/env python3
"""
Safe funding fee analysis for AsterDex Funding Bot.
Focus on maximum safety while collecting funding fees.
"""
import os
import sys
from decimal import Decimal
from typing import Dict, Any, Optional
import json

# Import bot functionality
from funding_bot import AsterDexFundingBot, DEFAULT_SPOT_SYMBOL, DEFAULT_FUTURES_SYMBOL

def analyze_safe_funding_strategy(capital: Decimal, futures_reserve: Decimal) -> Dict[str, Any]:
    """
    Analyze the safest funding fee strategy focusing on risk minimization.
    """
    print("🛡️  SAFE FUNDING FEE STRATEGY ANALYSIS")
    print("=" * 60)
    
    # Load API credentials
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
    
    api_key = os.environ.get("ASTERDEX_API_KEY", "")
    api_secret = os.environ.get("ASTERDEX_API_SECRET", "")
    
    if not api_key or not api_secret:
        print("❌ Missing API credentials. Please set up .env file first.")
        return {}
    
    try:
        # Create bot instance to fetch data
        bot = AsterDexFundingBot(
            capital_usd=Decimal("1000"),
            spot_symbol=DEFAULT_SPOT_SYMBOL,
            futures_symbol=DEFAULT_FUTURES_SYMBOL,
            batch_quote=Decimal("100")
        )
        
        # Get current market data
        spot_price = bot._fetch_spot_price()
        futures_price = bot._fetch_futures_price()
        
        print(f"📊 Current Market Data:")
        print(f"   Spot Price: {spot_price} USDT")
        print(f"   Futures Price: {futures_price} USDT")
        price_diff = abs(spot_price - futures_price)
        price_diff_pct = (price_diff / spot_price) * 100
        print(f"   Price Difference: {price_diff:.6f} USDT ({price_diff_pct:.4f}%)")
        
        # Check symbol info for trading limits
        spot_info = bot._get_spot_symbol_info()
        futures_info = bot._get_futures_symbol_info()
        
        spot_step, spot_min_qty = bot._extract_step_and_min_qty(spot_info)
        futures_step, futures_min_qty = bot._extract_step_and_min_qty(futures_info)
        futures_min_notional = bot._extract_min_notional(futures_info)
        
        print(f"\n📋 Trading Requirements:")
        print(f"   Spot Min Qty: {spot_min_qty} ASTER")
        print(f"   Futures Min Qty: {futures_min_qty} ASTER")
        print(f"   Futures Min Notional: {futures_min_notional} USDT")
        
        # Calculate position sizes
        base_quantity = capital / spot_price
        futures_notional = base_quantity * futures_price
        
        # Conservative margin calculation (5x leverage for safety)
        conservative_leverage = Decimal("5")  # Much safer than 20x
        required_margin = futures_notional / conservative_leverage
        safety_buffer = required_margin * Decimal("2")  # 100% buffer
        total_margin_needed = required_margin + safety_buffer
        
        print(f"\n💰 Position Analysis:")
        print(f"   Spot Capital: {capital} USDT")
        print(f"   Base Quantity: {base_quantity:.2f} ASTER")
        print(f"   Futures Notional: {futures_notional:.2f} USDT")
        print(f"   Required Margin (5x): {required_margin:.2f} USDT")
        print(f"   Safety Buffer: {safety_buffer:.2f} USDT")
        print(f"   Total Margin Needed: {total_margin_needed:.2f} USDT")
        print(f"   Available Reserve: {futures_reserve} USDT")
        
        margin_surplus = futures_reserve - total_margin_needed
        if margin_surplus > 0:
            print(f"   ✅ Margin Surplus: {margin_surplus:.2f} USDT")
            safety_ratio = futures_reserve / total_margin_needed
            print(f"   🛡️  Safety Ratio: {safety_ratio:.1f}x")
        else:
            print(f"   ❌ Margin Shortfall: {abs(margin_surplus):.2f} USDT")
            return {"error": "Insufficient margin for safe operation"}
        
        # Risk analysis
        print(f"\n⚠️  RISK ANALYSIS:")
        print(f"   Price Impact Risk: {'LOW' if price_diff_pct < 0.1 else 'MEDIUM' if price_diff_pct < 0.5 else 'HIGH'}")
        print(f"   Liquidation Risk: {'VERY LOW' if safety_ratio > 3 else 'LOW' if safety_ratio > 2 else 'MEDIUM'}")
        print(f"   Funding Risk: MINIMAL (market neutral position)")
        
        # Safe batch configuration
        # Use smaller batches for better risk control
        safe_batch_sizes = []
        
        # Check for perfect divisors first
        for batch_size in [50, 75, 100, 125, 150, 181]:
            batch_decimal = Decimal(str(batch_size))
            batch_count, remainder = divmod(capital, batch_decimal)
            if remainder == 0 and batch_count > 0:
                execution_time = batch_count * 2  # 2 second delay for safety
                safe_batch_sizes.append({
                    "batch_size": batch_size,
                    "batch_count": int(batch_count),
                    "execution_time": execution_time,
                    "risk_level": "LOW" if batch_count <= 100 else "MEDIUM"
                })
        
        # If no perfect divisors, find close ones
        if not safe_batch_sizes:
            for batch_size in [100, 150, 200]:
                batch_decimal = Decimal(str(batch_size))
                batch_count, remainder = divmod(capital, batch_decimal)
                if batch_count > 0:
                    execution_time = batch_count * 2
                    safe_batch_sizes.append({
                        "batch_size": batch_size,
                        "batch_count": int(batch_count),
                        "remainder": float(remainder),
                        "execution_time": execution_time,
                        "risk_level": "LOW" if batch_count <= 100 else "MEDIUM"
                    })
        
        print(f"\n🎯 SAFE BATCH CONFIGURATIONS:")
        if safe_batch_sizes:
            for config in safe_batch_sizes:
                risk_emoji = "🟢" if config["risk_level"] == "LOW" else "🟡"
                remainder_text = f" + {config.get('remainder', 0):.0f} remainder" if config.get('remainder', 0) > 0 else ""
                print(f"   {risk_emoji} {config['batch_size']} USDT × {config['batch_count']} batches "
                      f"({config['execution_time']/60:.1f}min, {config['risk_level']} risk){remainder_text}")
        else:
            print("   No suitable batch configurations found")
        
        # Funding fee projections (conservative estimates)
        conservative_scenarios = [
            ("Very Conservative", Decimal("0.00005")),  # 0.005% per 8h
            ("Conservative", Decimal("0.0001")),        # 0.01% per 8h
            ("Realistic", Decimal("0.0002")),           # 0.02% per 8h
        ]
        
        print(f"\n📈 CONSERVATIVE PROFIT PROJECTIONS:")
        for scenario_name, funding_rate in conservative_scenarios:
            daily_rate = funding_rate * 3  # 3 times per day
            daily_profit = capital * daily_rate
            weekly_profit = daily_profit * 7
            monthly_profit = daily_profit * 30
            apy = (daily_rate * 365) * 100
            
            print(f"   {scenario_name} ({funding_rate*100:.3f}% per 8h):")
            print(f"     Daily: {daily_profit:.2f} USDT")
            print(f"     Weekly: {weekly_profit:.2f} USDT")
            print(f"     Monthly: {monthly_profit:.2f} USDT")
            print(f"     APY: {apy:.2f}%")
            print()
        
        # Recommended safest configuration
        if safe_batch_sizes:
            # Choose the configuration with lowest risk and reasonable execution time
            recommended = min(safe_batch_sizes, key=lambda x: (x["risk_level"] == "MEDIUM", x["execution_time"]))
            
            print(f"\n🏆 SAFEST RECOMMENDED CONFIGURATION:")
            print("=" * 50)
            print(f"💎 Ultra-Safe Setup:")
            print(f"   Capital: {capital} USDT")
            print(f"   Batch Size: {recommended['batch_size']} USDT")
            print(f"   Batch Count: {recommended['batch_count']}")
            print(f"   Execution Time: {recommended['execution_time']/60:.1f} minutes")
            print(f"   Batch Delay: 2.0 seconds (extra safe)")
            print(f"   Leverage: 5x (very conservative)")
            
            if recommended.get('remainder', 0) > 0:
                print(f"   ⚠️  Remainder: {recommended['remainder']:.0f} USDT (will not be used)")
            print()
            
            print(f"🎯 Command to Run:")
            print(f"python3 funding_bot.py \\")
            print(f"  --capital {capital if recommended.get('remainder', 0) == 0 else capital - Decimal(str(recommended.get('remainder', 0)))} \\")
            print(f"  --batch-quote {recommended['batch_size']} \\")
            print(f"  --spot-symbol ASTERUSDT \\")
            print(f"  --futures-symbol ASTERUSDT \\")
            print(f"  --mode buy_spot_short_futures \\")
            print(f"  --batch-delay 2.0 \\")
            print(f"  --log-level INFO")
            
            print(f"\n🛡️  MAXIMUM SAFETY CHECKLIST:")
            print("   ✅ Conservative 5x leverage equivalent")
            print("   ✅ 100% margin safety buffer")
            print("   ✅ Market neutral position")
            print("   ✅ Small batch sizes for control")
            print("   ✅ Extended delay between batches")
            print("   ✅ Minimal price impact risk")
            
            return {
                "recommended_config": recommended,
                "margin_analysis": {
                    "required_margin": str(required_margin),
                    "safety_buffer": str(safety_buffer),
                    "total_needed": str(total_margin_needed),
                    "available": str(futures_reserve),
                    "surplus": str(margin_surplus),
                    "safety_ratio": float(safety_ratio)
                },
                "current_prices": {
                    "spot": str(spot_price),
                    "futures": str(futures_price),
                    "difference_pct": float(price_diff_pct)
                }
            }
        else:
            print(f"\n❌ No suitable batch configurations found")
            return {}
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return {"error": str(e)}

def main():
    """Main analysis function."""
    # Your specific amounts
    spot_capital = Decimal("13213")
    futures_reserve = Decimal("26000")
    
    result = analyze_safe_funding_strategy(spot_capital, futures_reserve)
    
    if result is None:
        print(f"\n❌ Analysis failed")
        return
    
    if "error" in result:
        print(f"\n❌ Cannot proceed safely: {result['error']}")
        return
    
    print(f"\n💡 ADDITIONAL SAFETY TIPS:")
    print("=" * 40)
    print("   1. 🧪 Test with 100 USDT first")
    print("   2. 📊 Monitor funding rates hourly")
    print("   3. 🚨 Set price alerts for ASTERUSDT")
    print("   4. 📱 Keep AsterDex app open during execution")
    print("   5. ⏰ Run during stable market hours")
    print("   6. 🔄 Plan position closure strategy")
    print("   7. 📋 Keep detailed records")
    print("   8. 🛑 Have stop-loss plan ready")
    
    print(f"\n🎯 FUNDING FEE COLLECTION STRATEGY:")
    print("   • Hold positions through funding periods")
    print("   • Collect fees 3 times per day (every 8 hours)")
    print("   • Maintain market-neutral exposure")
    print("   • Monitor and adjust if needed")
    print("   • Close positions when funding turns negative")

if __name__ == "__main__":
    main()
