#!/usr/bin/env python3
"""
Enhanced capital analysis for maximizing funding fee profits.
Calculate optimal configurations using additional margin for higher capital deployment.
"""
from decimal import Decimal
from typing import Dict, List, Tuple

def analyze_enhanced_capital_strategies():
    """Analyze strategies using additional capital from margin reserves."""
    
    original_capital = Decimal("13213")
    futures_reserve = Decimal("26000")
    
    print("🚀 ENHANCED CAPITAL STRATEGIES FOR MAXIMUM PROFITS")
    print("=" * 70)
    
    # Strategy scenarios with different capital amounts
    strategies = [
        {
            "name": "Conservative Enhanced",
            "capital": original_capital * Decimal("1.5"),  # 19,819 USDT
            "leverage_equiv": 10,
            "safety_ratio_target": 5.0,
            "risk_level": "MEDIUM-LOW"
        },
        {
            "name": "Moderate Enhanced", 
            "capital": original_capital * Decimal("2.0"),   # 26,426 USDT
            "leverage_equiv": 12,
            "safety_ratio_target": 3.5,
            "risk_level": "MEDIUM"
        },
        {
            "name": "Aggressive Enhanced",
            "capital": original_capital * Decimal("2.5"),   # 33,032 USDT
            "leverage_equiv": 15,
            "safety_ratio_target": 2.5,
            "risk_level": "MEDIUM-HIGH"
        }
    ]
    
    print(f"📊 ENHANCED STRATEGY COMPARISON:")
    print("-" * 70)
    
    current_price = Decimal("1.97")  # Approximate current price
    
    for strategy in strategies:
        capital = strategy["capital"]
        leverage = Decimal(str(strategy["leverage_equiv"]))
        
        # Calculate margin requirements
        base_qty = capital / current_price
        futures_notional = base_qty * current_price  # Approximately equal to capital
        initial_margin = futures_notional / leverage
        safety_buffer = initial_margin * Decimal("1.5")  # 50% buffer
        total_margin_needed = initial_margin + safety_buffer
        
        # Check feasibility
        if total_margin_needed <= futures_reserve:
            margin_surplus = futures_reserve - total_margin_needed
            actual_safety_ratio = futures_reserve / total_margin_needed
            
            # Find optimal batch sizes
            batch_options = find_perfect_divisors(capital)
            
            print(f"   {strategy['name']}:")
            print(f"     Capital: {capital:,.0f} USDT ({capital/original_capital:.1f}x original)")
            print(f"     Leverage Equiv: {leverage}x")
            print(f"     Margin Needed: {total_margin_needed:,.0f} USDT")
            print(f"     Margin Surplus: {margin_surplus:,.0f} USDT")
            print(f"     Safety Ratio: {actual_safety_ratio:.1f}x")
            print(f"     Risk Level: {strategy['risk_level']}")
            
            if batch_options:
                best_batch = batch_options[0]
                execution_time = best_batch["count"] * 1.5  # 1.5s delay
                print(f"     Best Batch: {best_batch['size']} × {best_batch['count']} ({execution_time/60:.1f}min)")
            else:
                print(f"     Best Batch: No perfect divisors found")
            
            # Profit projections
            profit_scenarios = [
                ("Conservative", Decimal("0.0001")),  # 0.01% per 8h
                ("Realistic", Decimal("0.0003")),     # 0.03% per 8h  
                ("Optimistic", Decimal("0.0005")),    # 0.05% per 8h
            ]
            
            print(f"     Daily Profits:")
            for scenario_name, rate in profit_scenarios:
                daily_rate = rate * 3  # 3 times per day
                daily_profit = capital * daily_rate
                original_profit = original_capital * daily_rate
                extra_profit = daily_profit - original_profit
                
                print(f"       {scenario_name}: {daily_profit:.2f} USDT (+{extra_profit:.2f})")
            print()
        else:
            shortfall = total_margin_needed - futures_reserve
            print(f"   {strategy['name']}: ❌ INSUFFICIENT MARGIN")
            print(f"     Shortfall: {shortfall:,.0f} USDT")
            print()
    
    # Special high-profit scenarios
    print(f"💎 MAXIMUM PROFIT SCENARIOS:")
    print("-" * 70)
    
    # Calculate absolute maximum capital we could theoretically use
    max_leverage = Decimal("20")  # Maximum reasonable leverage
    min_safety_ratio = Decimal("2")  # Minimum acceptable safety
    
    # Work backwards from available margin
    usable_margin = futures_reserve / min_safety_ratio  # Conservative estimate
    max_theoretical_notional = usable_margin * max_leverage
    max_theoretical_capital = max_theoretical_notional * Decimal("0.95")  # Small discount for safety
    
    if max_theoretical_capital > original_capital * 3:
        max_theoretical_capital = original_capital * 3  # Cap at 3x for practicality
    
    print(f"🎯 Maximum Theoretical Scenario:")
    print(f"   Max Capital: {max_theoretical_capital:,.0f} USDT")
    print(f"   Profit Multiplier: {max_theoretical_capital/original_capital:.1f}x")
    print(f"   Required Margin: {max_theoretical_capital/max_leverage*Decimal('2.5'):,.0f} USDT")
    
    # Find batch configuration for max capital
    max_batch_options = find_perfect_divisors(max_theoretical_capital)
    if max_batch_options:
        best_max_batch = max_batch_options[0]
        print(f"   Optimal Batch: {best_max_batch['size']} × {best_max_batch['count']}")
        
        # Extreme profit calculations
        for rate_name, rate in [("Realistic", Decimal("0.0003")), ("High", Decimal("0.0005"))]:
            daily_rate = rate * 3
            daily_profit = max_theoretical_capital * daily_rate
            monthly_profit = daily_profit * 30
            yearly_profit = daily_profit * 365
            
            print(f"   {rate_name} Profits:")
            print(f"     Daily: {daily_profit:.2f} USDT")
            print(f"     Monthly: {monthly_profit:,.0f} USDT") 
            print(f"     Yearly: {yearly_profit:,.0f} USDT")
    
    print(f"\n🏆 RECOMMENDED PROGRESSIVE APPROACH:")
    print("=" * 70)
    
    # Progressive scaling strategy
    phases = [
        {"phase": "Phase 1 - Test", "capital": original_capital, "duration": "1-2 days"},
        {"phase": "Phase 2 - Scale", "capital": original_capital * Decimal("1.5"), "duration": "3-5 days"},
        {"phase": "Phase 3 - Optimize", "capital": original_capital * Decimal("2"), "duration": "1 week"},
        {"phase": "Phase 4 - Maximum", "capital": original_capital * Decimal("2.5"), "duration": "Ongoing"},
    ]
    
    for phase in phases:
        capital = phase["capital"]
        batch_options = find_perfect_divisors(capital)
        
        if batch_options:
            best_batch = batch_options[0]
            
            # Conservative profit estimate
            daily_profit = capital * Decimal("0.0003") * 3
            
            print(f"   {phase['phase']} ({phase['duration']}):")
            print(f"     Capital: {capital:,.0f} USDT")
            print(f"     Batch: {best_batch['size']} × {best_batch['count']}")
            print(f"     Est. Daily: {daily_profit:.2f} USDT")
            print()
    
    print(f"🎯 FINAL RECOMMENDATION - ENHANCED MODERATE:")
    print("=" * 70)
    
    # Final recommended configuration
    recommended_capital = original_capital * Decimal("2")  # 2x original = 26,426 USDT
    recommended_batch_options = find_perfect_divisors(recommended_capital)
    
    if recommended_batch_options:
        recommended_batch = recommended_batch_options[0]
        
        print(f"💎 Enhanced Configuration:")
        print(f"   Capital: {recommended_capital:,.0f} USDT (2x original)")
        print(f"   Batch Size: {recommended_batch['size']} USDT")
        print(f"   Batch Count: {recommended_batch['count']}")
        print(f"   Execution Time: {recommended_batch['count'] * 1.5 / 60:.1f} minutes")
        print(f"   Leverage Equivalent: 12x")
        print(f"   Safety Ratio: ~3.5x")
        
        print(f"\n🎯 Enhanced Command:")
        print(f"python3 funding_bot.py \\")
        print(f"  --capital {recommended_capital:.0f} \\")
        print(f"  --batch-quote {recommended_batch['size']} \\")
        print(f"  --spot-symbol ASTERUSDT \\")
        print(f"  --futures-symbol ASTERUSDT \\")
        print(f"  --mode buy_spot_short_futures \\")
        print(f"  --batch-delay 1.5 \\")
        print(f"  --log-level INFO")
        
        # Profit comparison
        print(f"\n📊 Profit Comparison (Daily):")
        for rate_name, rate in [("Conservative", Decimal("0.0001")), ("Realistic", Decimal("0.0003"))]:
            daily_rate = rate * 3
            
            original_profit = original_capital * daily_rate
            enhanced_profit = recommended_capital * daily_rate
            extra_profit = enhanced_profit - original_profit
            
            print(f"   {rate_name}:")
            print(f"     Original: {original_profit:.2f} USDT")
            print(f"     Enhanced: {enhanced_profit:.2f} USDT (+{extra_profit:.2f})")
            print(f"     Improvement: {(enhanced_profit/original_profit-1)*100:.0f}%")

def find_perfect_divisors(capital: Decimal) -> List[Dict]:
    """Find perfect divisors for capital amount."""
    divisors = []
    
    # Common batch sizes to test
    test_sizes = [100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 400, 500]
    
    # Also test some calculated divisors
    capital_int = int(capital)
    for i in range(50, min(capital_int + 1, 501)):
        if capital_int % i == 0:
            test_sizes.append(i)
    
    # Remove duplicates and sort
    test_sizes = sorted(list(set(test_sizes)))
    
    for size in test_sizes:
        size_decimal = Decimal(str(size))
        count, remainder = divmod(capital, size_decimal)
        
        if remainder == 0 and count > 0:
            divisors.append({
                "size": size,
                "count": int(count),
                "remainder": 0
            })
    
    # Sort by count (prefer fewer batches)
    divisors.sort(key=lambda x: x["count"])
    
    return divisors

if __name__ == "__main__":
    analyze_enhanced_capital_strategies()
