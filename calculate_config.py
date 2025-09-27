#!/usr/bin/env python3
"""
Configuration calculator for AsterDex Funding Bot.
Calculate optimal batch sizes and validate margin requirements for custom capital amounts.
"""
import math
import os
import sys
from decimal import Decimal, ROUND_DOWN
from typing import List, Tuple, Dict, Any

# Import bot functionality
from funding_bot import AsterDexFundingBot, DEFAULT_SPOT_SYMBOL, DEFAULT_FUTURES_SYMBOL

def find_optimal_batch_sizes(capital: Decimal, min_batch: Decimal = Decimal("50"), max_batch: Decimal = Decimal("1000")) -> List[Tuple[Decimal, int, Decimal]]:
    """
    Find optimal batch sizes that divide evenly into the capital.
    Returns list of (batch_size, batch_count, remainder) tuples.
    """
    optimal_batches = []
    
    # Check common batch sizes
    common_batches = [50, 100, 150, 200, 250, 300, 400, 500, 750, 1000]
    
    for batch_size in common_batches:
        batch_decimal = Decimal(str(batch_size))
        if batch_decimal < min_batch or batch_decimal > max_batch:
            continue
            
        batch_count, remainder = divmod(capital, batch_decimal)
        if remainder == 0 and batch_count > 0:
            optimal_batches.append((batch_decimal, int(batch_count), remainder))
    
    # Find additional divisors
    for divisor in range(1, min(int(capital) + 1, 1000)):
        if capital % divisor == 0:
            batch_size = capital / divisor
            if min_batch <= batch_size <= max_batch:
                optimal_batches.append((batch_size, divisor, Decimal("0")))
    
    # Remove duplicates and sort by batch count (fewer batches preferred)
    seen = set()
    unique_batches = []
    for batch_size, count, remainder in optimal_batches:
        key = (batch_size, count)
        if key not in seen:
            seen.add(key)
            unique_batches.append((batch_size, count, remainder))
    
    # Sort by batch count (fewer batches first), then by batch size
    unique_batches.sort(key=lambda x: (x[1], x[0]))
    
    return unique_batches[:10]  # Return top 10 options

def calculate_margin_requirement(capital: Decimal, current_price: Decimal, leverage: Decimal = Decimal("20")) -> Dict[str, Decimal]:
    """
    Calculate futures margin requirements for the hedge position.
    Assumes we'll be shorting an equivalent amount to the spot purchase.
    """
    # Calculate base quantity we'll be buying in spot
    base_quantity = capital / current_price
    
    # For futures short, we need the same quantity
    futures_notional = base_quantity * current_price  # Should equal capital
    
    # Calculate margin required (assuming 20x leverage as default)
    initial_margin = futures_notional / leverage
    
    # Add buffer for price movements (recommended 2-3x initial margin)
    recommended_margin = initial_margin * Decimal("2.5")
    
    return {
        "base_quantity": base_quantity,
        "futures_notional": futures_notional,
        "initial_margin": initial_margin,
        "recommended_margin": recommended_margin,
        "leverage_used": leverage
    }

def analyze_funding_profitability(capital: Decimal, funding_rate_8h: Decimal = Decimal("0.0001")) -> Dict[str, Decimal]:
    """
    Analyze potential funding fee profits.
    Default funding rate of 0.01% (0.0001) per 8 hours is conservative estimate.
    """
    # Daily funding (3 times per day)
    daily_funding = funding_rate_8h * 3
    
    # Calculate profits
    daily_profit = capital * daily_funding
    weekly_profit = daily_profit * 7
    monthly_profit = daily_profit * 30
    yearly_profit = daily_profit * 365
    
    # Calculate APY
    apy = (daily_funding * 365) * 100
    
    return {
        "funding_rate_8h": funding_rate_8h,
        "daily_funding_rate": daily_funding,
        "daily_profit": daily_profit,
        "weekly_profit": weekly_profit,
        "monthly_profit": monthly_profit,
        "yearly_profit": yearly_profit,
        "apy_percent": apy
    }

def main():
    """Main calculation function."""
    print("🧮 AsterDex Funding Bot - Configuration Calculator")
    print("=" * 60)
    
    # Your specific parameters
    spot_capital = Decimal("13213")  # USDT for spot trading
    futures_reserve = Decimal("26000")  # USDT available for futures margin
    
    print(f"📊 Your Configuration:")
    print(f"   Spot Capital: {spot_capital} USDT")
    print(f"   Futures Reserve: {futures_reserve} USDT")
    print(f"   Total Available: {spot_capital + futures_reserve} USDT")
    print()
    
    # Find optimal batch sizes
    print("🎯 OPTIMAL BATCH SIZE OPTIONS:")
    print("-" * 40)
    
    optimal_batches = find_optimal_batch_sizes(spot_capital)
    
    if not optimal_batches:
        print("❌ No perfect divisors found. Consider adjusting capital amount.")
        # Find closest options
        print("\n📋 Alternative options (with small remainders):")
        for batch_size in [100, 150, 200, 250, 300]:
            batch_decimal = Decimal(str(batch_size))
            batch_count, remainder = divmod(spot_capital, batch_decimal)
            if batch_count > 0:
                print(f"   Batch: {batch_size} USDT → {int(batch_count)} batches + {remainder} USDT remainder")
    else:
        print("✅ Perfect divisor options found:")
        for i, (batch_size, batch_count, remainder) in enumerate(optimal_batches, 1):
            execution_time = batch_count * 1.0  # Assuming 1 second delay
            print(f"   {i:2d}. Batch: {batch_size} USDT × {batch_count} batches (≈{execution_time:.0f}s execution)")
    
    # Get current price for margin calculations (try to connect to API)
    current_price = None
    try:
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
        
        api_key = os.environ.get("ASTERDEX_API_KEY", "")
        api_secret = os.environ.get("ASTERDEX_API_SECRET", "")
        
        if api_key and api_secret:
            print("\n🔍 Fetching current price from AsterDex...")
            bot = AsterDexFundingBot(
                capital_usd=Decimal("1000"),
                spot_symbol=DEFAULT_SPOT_SYMBOL,
                futures_symbol=DEFAULT_FUTURES_SYMBOL,
                batch_quote=Decimal("100")
            )
            current_price = bot._fetch_spot_price()
            print(f"   Current ASTERUSDT price: {current_price}")
        else:
            print("\n⚠️  No API credentials found. Using estimated price.")
    except Exception as e:
        print(f"\n⚠️  Could not fetch current price: {e}")
    
    # Use estimated price if API call failed
    if current_price is None:
        current_price = Decimal("0.05")  # Estimated ASTERUSDT price
        print(f"   Using estimated price: {current_price}")
    
    print(f"\n💰 MARGIN REQUIREMENT ANALYSIS:")
    print("-" * 40)
    
    margin_calc = calculate_margin_requirement(spot_capital, current_price)
    
    print(f"   Spot capital: {spot_capital} USDT")
    print(f"   Est. base quantity: {margin_calc['base_quantity']:.2f} ASTER")
    print(f"   Futures notional: {margin_calc['futures_notional']:.2f} USDT")
    print(f"   Initial margin (20x): {margin_calc['initial_margin']:.2f} USDT")
    print(f"   Recommended margin: {margin_calc['recommended_margin']:.2f} USDT")
    print()
    
    # Check if futures reserve is sufficient
    if futures_reserve >= margin_calc['recommended_margin']:
        surplus = futures_reserve - margin_calc['recommended_margin']
        print(f"   ✅ Futures reserve is SUFFICIENT")
        print(f"   💎 Surplus: {surplus:.2f} USDT (safety buffer)")
    else:
        shortfall = margin_calc['recommended_margin'] - futures_reserve
        print(f"   ⚠️  Futures reserve might be TIGHT")
        print(f"   📉 Shortfall: {shortfall:.2f} USDT")
        print(f"   💡 Consider reducing capital or adding more futures margin")
    
    print(f"\n📈 FUNDING PROFITABILITY ANALYSIS:")
    print("-" * 40)
    
    # Analyze with different funding rate scenarios
    scenarios = [
        ("Conservative", Decimal("0.0001")),  # 0.01% per 8h
        ("Moderate", Decimal("0.0005")),      # 0.05% per 8h
        ("Optimistic", Decimal("0.001")),     # 0.1% per 8h
    ]
    
    for scenario_name, funding_rate in scenarios:
        profit_calc = analyze_funding_profitability(spot_capital, funding_rate)
        print(f"\n   {scenario_name} ({funding_rate*100:.3f}% per 8h):")
        print(f"     Daily: {profit_calc['daily_profit']:.2f} USDT ({profit_calc['daily_funding_rate']*100:.4f}%)")
        print(f"     Weekly: {profit_calc['weekly_profit']:.2f} USDT")
        print(f"     Monthly: {profit_calc['monthly_profit']:.2f} USDT")
        print(f"     APY: {profit_calc['apy_percent']:.2f}%")
    
    print(f"\n🚀 RECOMMENDED CONFIGURATION:")
    print("=" * 60)
    
    if optimal_batches:
        # Recommend the option with reasonable batch count and size
        recommended = None
        for batch_size, batch_count, remainder in optimal_batches:
            if 50 <= batch_count <= 200 and batch_size >= 50:  # Reasonable limits
                recommended = (batch_size, batch_count, remainder)
                break
        
        if not recommended:
            recommended = optimal_batches[0]  # Use first option if no ideal found
        
        batch_size, batch_count, remainder = recommended
        execution_time = batch_count * 1.0  # 1 second delay between batches
        
        print(f"💎 Optimal Configuration:")
        print(f"   --capital {spot_capital}")
        print(f"   --batch-quote {batch_size}")
        print(f"   --spot-symbol ASTERUSDT")
        print(f"   --futures-symbol ASTERUSDT")
        print(f"   --mode buy_spot_short_futures")
        print(f"   --batch-delay 1.0")
        print()
        print(f"📊 Execution Details:")
        print(f"   Total batches: {batch_count}")
        print(f"   Estimated time: {execution_time:.0f} seconds ({execution_time/60:.1f} minutes)")
        print(f"   Average per batch: {batch_size} USDT")
        
        print(f"\n🎯 Complete Command:")
        print("=" * 40)
        print(f"python3 funding_bot.py \\")
        print(f"  --capital {spot_capital} \\")
        print(f"  --batch-quote {batch_size} \\")
        print(f"  --spot-symbol ASTERUSDT \\")
        print(f"  --futures-symbol ASTERUSDT \\")
        print(f"  --mode buy_spot_short_futures \\")
        print(f"  --batch-delay 1.0 \\")
        print(f"  --log-level INFO")
        
    else:
        print("❌ No perfect configuration found. Consider adjusting capital amount.")
    
    print(f"\n⚠️  IMPORTANT REMINDERS:")
    print("-" * 40)
    print("   1. Test with small amount first (e.g., 100 USDT)")
    print("   2. Check current funding rates on AsterDex")
    print("   3. Ensure ASTERUSDT is actively traded")
    print("   4. Monitor positions after execution")
    print("   5. Have a plan to close positions if needed")
    print(f"   6. Keep extra margin buffer in futures account")
    
    if futures_reserve < margin_calc['recommended_margin']:
        print(f"\n🔴 CRITICAL: Consider increasing futures margin or reducing capital!")

if __name__ == "__main__":
    main()
