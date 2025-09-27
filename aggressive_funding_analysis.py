#!/usr/bin/env python3
"""
Aggressive funding fee analysis for higher profits with controlled risk.
Calculate configurations with higher leverage while maintaining safety margins.
"""
import os
import sys
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
import json

# Import bot functionality
from funding_bot import AsterDexFundingBot, DEFAULT_SPOT_SYMBOL, DEFAULT_FUTURES_SYMBOL

def analyze_aggressive_funding_strategy(capital: Decimal, futures_reserve: Decimal) -> Dict[str, Any]:
    """
    Analyze more aggressive funding fee strategies for higher returns.
    """
    print("🚀 AGGRESSIVE FUNDING FEE STRATEGY ANALYSIS")
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
        
        # Calculate position sizes
        base_quantity = capital / spot_price
        futures_notional = base_quantity * futures_price
        
        print(f"\n💰 Base Position Analysis:")
        print(f"   Spot Capital: {capital} USDT")
        print(f"   Base Quantity: {base_quantity:.2f} ASTER")
        print(f"   Futures Notional: {futures_notional:.2f} USDT")
        
        # Analyze different leverage scenarios
        leverage_scenarios = [
            {"name": "Conservative", "leverage": Decimal("5"), "buffer_mult": Decimal("2")},
            {"name": "Moderate", "leverage": Decimal("10"), "buffer_mult": Decimal("1.5")},
            {"name": "Aggressive", "leverage": Decimal("15"), "buffer_mult": Decimal("1.2")},
            {"name": "High Risk", "leverage": Decimal("20"), "buffer_mult": Decimal("1.0")},
        ]
        
        print(f"\n📊 LEVERAGE SCENARIO ANALYSIS:")
        print("-" * 60)
        
        viable_scenarios = []
        
        for scenario in leverage_scenarios:
            leverage = scenario["leverage"]
            buffer_mult = scenario["buffer_mult"]
            
            # Calculate margin requirements
            initial_margin = futures_notional / leverage
            safety_buffer = initial_margin * buffer_mult
            total_margin_needed = initial_margin + safety_buffer
            
            # Check if viable
            if total_margin_needed <= futures_reserve:
                margin_surplus = futures_reserve - total_margin_needed
                safety_ratio = futures_reserve / total_margin_needed
                liquidation_price_change = Decimal("0.9") / leverage  # Approximate liquidation threshold
                
                # Risk assessment
                if safety_ratio >= 2:
                    risk_level = "LOW"
                elif safety_ratio >= 1.5:
                    risk_level = "MEDIUM"
                else:
                    risk_level = "HIGH"
                
                print(f"   {scenario['name']} ({leverage}x leverage):")
                print(f"     Initial Margin: {initial_margin:.2f} USDT")
                print(f"     Safety Buffer: {safety_buffer:.2f} USDT")
                print(f"     Total Required: {total_margin_needed:.2f} USDT")
                print(f"     Surplus: {margin_surplus:.2f} USDT")
                print(f"     Safety Ratio: {safety_ratio:.1f}x")
                print(f"     Risk Level: {risk_level}")
                print(f"     Liquidation Threshold: ~{liquidation_price_change*100:.1f}% price move")
                print()
                
                viable_scenarios.append({
                    "name": scenario["name"],
                    "leverage": leverage,
                    "initial_margin": initial_margin,
                    "safety_buffer": safety_buffer,
                    "total_needed": total_margin_needed,
                    "surplus": margin_surplus,
                    "safety_ratio": safety_ratio,
                    "risk_level": risk_level,
                    "liquidation_threshold": liquidation_price_change
                })
            else:
                shortfall = total_margin_needed - futures_reserve
                print(f"   {scenario['name']} ({leverage}x leverage): ❌ INSUFFICIENT MARGIN")
                print(f"     Shortfall: {shortfall:.2f} USDT")
                print()
        
        if not viable_scenarios:
            return {"error": "No viable scenarios with available margin"}
        
        # Capital multiplication analysis
        print(f"💎 CAPITAL MULTIPLICATION OPPORTUNITIES:")
        print("-" * 60)
        
        # Since we have extra margin, we could potentially use more capital
        max_capital_scenarios = []
        
        for scenario in viable_scenarios[:3]:  # Top 3 scenarios
            leverage = scenario["leverage"]
            buffer_mult = Decimal("1.5")  # Standard buffer
            
            # Calculate maximum capital we could use with this leverage
            # Working backwards: available_margin = (max_capital / price * futures_price) / leverage * (1 + buffer)
            available_for_trading = futures_reserve * Decimal("0.8")  # Use 80% of available margin
            max_notional = available_for_trading / (Decimal("1") / leverage * (Decimal("1") + buffer_mult))
            max_capital_possible = max_notional * (spot_price / futures_price)
            
            if max_capital_possible > capital:
                extra_capital = max_capital_possible - capital
                extra_profit_multiplier = max_capital_possible / capital
                
                print(f"   {scenario['name']} ({leverage}x):")
                print(f"     Current Capital: {capital} USDT")
                print(f"     Max Possible: {max_capital_possible:.0f} USDT")
                print(f"     Extra Potential: {extra_capital:.0f} USDT")
                print(f"     Profit Multiplier: {extra_profit_multiplier:.1f}x")
                print()
                
                max_capital_scenarios.append({
                    "scenario": scenario["name"],
                    "leverage": leverage,
                    "max_capital": max_capital_possible,
                    "profit_multiplier": extra_profit_multiplier,
                    "extra_capital": extra_capital
                })
        
        # Batch size optimization for different capital amounts
        print(f"🎯 OPTIMIZED BATCH CONFIGURATIONS:")
        print("-" * 60)
        
        recommended_configs = []
        
        # Original capital with different risk levels
        for scenario in viable_scenarios[:3]:
            batch_configs = find_optimal_batches_for_capital(capital)
            if batch_configs:
                best_batch = batch_configs[0]  # First is usually best
                
                # Calculate execution metrics
                execution_time = best_batch["batch_count"] * 1.5  # 1.5s delay for aggressive
                daily_profit_scenarios = []
                
                # Different funding rate scenarios
                for rate_name, rate in [("Conservative", Decimal("0.0001")), ("Moderate", Decimal("0.0003")), ("Aggressive", Decimal("0.0005"))]:
                    daily_rate = rate * 3
                    daily_profit = capital * daily_rate
                    daily_profit_scenarios.append((rate_name, daily_profit))
                
                print(f"   {scenario['name']} Risk Profile:")
                print(f"     Capital: {capital} USDT")
                print(f"     Batch: {best_batch['batch_size']} × {best_batch['batch_count']}")
                print(f"     Execution: {execution_time/60:.1f} minutes")
                print(f"     Safety Ratio: {scenario['safety_ratio']:.1f}x")
                print(f"     Daily Profits:")
                for rate_name, profit in daily_profit_scenarios:
                    print(f"       {rate_name}: {profit:.2f} USDT")
                print()
                
                recommended_configs.append({
                    "risk_profile": scenario["name"],
                    "capital": capital,
                    "batch_size": best_batch["batch_size"],
                    "batch_count": best_batch["batch_count"],
                    "execution_time": execution_time,
                    "safety_ratio": scenario["safety_ratio"],
                    "leverage_equiv": scenario["leverage"],
                    "daily_profits": daily_profit_scenarios
                })
        
        # Higher capital scenarios
        if max_capital_scenarios:
            print(f"🚀 HIGH CAPITAL SCENARIOS (Using Extra Margin):")
            print("-" * 60)
            
            for max_scenario in max_capital_scenarios[:2]:  # Top 2
                higher_capital = min(max_scenario["max_capital"], capital * Decimal("1.5"))  # Cap at 1.5x for safety
                batch_configs = find_optimal_batches_for_capital(higher_capital)
                
                if batch_configs:
                    best_batch = batch_configs[0]
                    execution_time = best_batch["batch_count"] * 1.5
                    
                    # Profit calculations
                    profit_multiplier = higher_capital / capital
                    
                    print(f"   {max_scenario['scenario']} + Extra Capital:")
                    print(f"     Capital: {higher_capital:.0f} USDT ({profit_multiplier:.1f}x)")
                    print(f"     Batch: {best_batch['batch_size']} × {best_batch['batch_count']}")
                    print(f"     Execution: {execution_time/60:.1f} minutes")
                    print(f"     Leverage: {max_scenario['leverage']}x")
                    
                    # Enhanced profit projections
                    for rate_name, rate in [("Moderate", Decimal("0.0003")), ("Aggressive", Decimal("0.0005"))]:
                        daily_rate = rate * 3
                        daily_profit = higher_capital * daily_rate
                        original_profit = capital * daily_rate
                        extra_profit = daily_profit - original_profit
                        
                        print(f"     {rate_name} Daily: {daily_profit:.2f} USDT (+{extra_profit:.2f})")
                    print()
                    
                    recommended_configs.append({
                        "risk_profile": f"{max_scenario['scenario']} + Extra Capital",
                        "capital": higher_capital,
                        "batch_size": best_batch["batch_size"],
                        "batch_count": best_batch["batch_count"],
                        "execution_time": execution_time,
                        "leverage_equiv": max_scenario["leverage"],
                        "profit_multiplier": profit_multiplier
                    })
        
        # Final recommendation
        if recommended_configs:
            # Choose the best balance of risk/reward
            best_config = None
            for config in recommended_configs:
                if "Moderate" in config["risk_profile"] or "Aggressive" in config["risk_profile"]:
                    if config.get("safety_ratio", 2) >= 1.5:  # Minimum safety
                        best_config = config
                        break
            
            if not best_config:
                best_config = recommended_configs[1] if len(recommended_configs) > 1 else recommended_configs[0]
            
            print(f"🏆 RECOMMENDED AGGRESSIVE CONFIGURATION:")
            print("=" * 60)
            print(f"💎 Optimal Risk/Reward Balance:")
            print(f"   Profile: {best_config['risk_profile']}")
            print(f"   Capital: {best_config['capital']:.0f} USDT")
            print(f"   Batch Size: {best_config['batch_size']} USDT")
            print(f"   Batch Count: {best_config['batch_count']}")
            print(f"   Execution Time: {best_config['execution_time']/60:.1f} minutes")
            
            if best_config.get("profit_multiplier"):
                print(f"   Profit Multiplier: {best_config['profit_multiplier']:.1f}x vs original")
            
            print(f"\n🎯 Command to Run:")
            print(f"python3 funding_bot.py \\")
            print(f"  --capital {best_config['capital']:.0f} \\")
            print(f"  --batch-quote {best_config['batch_size']} \\")
            print(f"  --spot-symbol ASTERUSDT \\")
            print(f"  --futures-symbol ASTERUSDT \\")
            print(f"  --mode buy_spot_short_futures \\")
            print(f"  --batch-delay 1.5 \\")
            print(f"  --log-level INFO")
            
            return {
                "recommended_config": best_config,
                "all_scenarios": viable_scenarios,
                "max_capital_options": max_capital_scenarios
            }
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return {"error": str(e)}

def find_optimal_batches_for_capital(capital: Decimal) -> List[Dict]:
    """Find optimal batch sizes for given capital amount."""
    optimal_batches = []
    
    # Check various batch sizes
    batch_sizes = [73, 100, 125, 150, 181, 200, 250, 300]
    
    for batch_size in batch_sizes:
        batch_decimal = Decimal(str(batch_size))
        batch_count, remainder = divmod(capital, batch_decimal)
        
        if remainder == 0 and batch_count > 0:
            optimal_batches.append({
                "batch_size": batch_size,
                "batch_count": int(batch_count),
                "remainder": 0
            })
        elif batch_count > 0 and remainder < batch_decimal * Decimal("0.05"):  # Less than 5% remainder
            optimal_batches.append({
                "batch_size": batch_size,
                "batch_count": int(batch_count),
                "remainder": float(remainder)
            })
    
    # Sort by preference: no remainder first, then by batch count
    optimal_batches.sort(key=lambda x: (x["remainder"] > 0, x["batch_count"]))
    
    return optimal_batches

def main():
    """Main analysis function."""
    # Your specific amounts
    spot_capital = Decimal("13213")
    futures_reserve = Decimal("26000")
    
    print(f"💰 Available Resources:")
    print(f"   Spot Capital: {spot_capital} USDT")
    print(f"   Futures Reserve: {futures_reserve} USDT")
    print(f"   Total Available: {spot_capital + futures_reserve} USDT")
    print()
    
    result = analyze_aggressive_funding_strategy(spot_capital, futures_reserve)
    
    if not result or "error" in result:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        return
    
    print(f"\n⚠️  AGGRESSIVE STRATEGY WARNINGS:")
    print("=" * 40)
    print("   1. 🧪 ALWAYS test with small amounts first")
    print("   2. 📊 Monitor funding rates more frequently")
    print("   3. 🚨 Set tighter price alerts")
    print("   4. 📱 Keep trading app open during high volatility")
    print("   5. ⏰ Avoid running during major news events")
    print("   6. 🔄 Have faster position closure plan")
    print("   7. 📋 Monitor margin levels constantly")
    print("   8. 🛑 Set automatic stop-loss if possible")
    
    print(f"\n💡 RISK MANAGEMENT TIPS:")
    print("   • Start with moderate risk profile")
    print("   • Scale up gradually after successful runs")
    print("   • Monitor liquidation levels closely")
    print("   • Keep some margin in reserve")
    print("   • Close positions if funding turns negative")

if __name__ == "__main__":
    main()
