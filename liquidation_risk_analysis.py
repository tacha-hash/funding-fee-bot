#!/usr/bin/env python3
"""
Liquidation risk analysis for futures positions.
Analyze the risk of liquidation based on current position data.
"""
from decimal import Decimal

def analyze_liquidation_risk():
    """Analyze liquidation risk based on current position data."""
    
    print("🚨 LIQUIDATION RISK ANALYSIS")
    print("=" * 60)
    
    # Current position data from the screenshot
    position_size = Decimal("-7302.55")  # Short position
    entry_price = Decimal("1.97185")
    mark_price = Decimal("1.96798")
    margin = Decimal("3592.83")  # Cross margin
    liquidation_price = Decimal("5.30417")
    current_pnl = Decimal("28.22")
    
    print(f"📊 Current Position Data:")
    print(f"   Position Size: {position_size} ASTER (SHORT)")
    print(f"   Entry Price: {entry_price} USDT")
    print(f"   Mark Price: {mark_price} USDT")
    print(f"   Margin: {margin} USDT")
    print(f"   Liquidation Price: {liquidation_price} USDT")
    print(f"   Current PnL: +{current_pnl} USDT")
    print()
    
    # Calculate risk metrics
    price_to_liquidation = liquidation_price - mark_price
    percentage_to_liquidation = (price_to_liquidation / mark_price) * 100
    
    print(f"🎯 Risk Analysis:")
    print(f"   Distance to Liquidation: {price_to_liquidation:.5f} USDT")
    print(f"   Percentage to Liquidation: {percentage_to_liquidation:.2f}%")
    
    # This liquidation price seems extremely high for a short position
    # Let's analyze what might be wrong
    print(f"\n⚠️  CRITICAL ANALYSIS:")
    
    if liquidation_price > mark_price * 2:
        print(f"   🔴 MAJOR ISSUE DETECTED!")
        print(f"   The liquidation price ({liquidation_price}) is {liquidation_price/mark_price:.1f}x higher than mark price!")
        print(f"   This suggests a configuration or calculation error.")
        print()
        
        print(f"💡 Possible Issues:")
        print(f"   1. 🚨 Wrong position direction in system")
        print(f"   2. 🚨 Margin calculation error") 
        print(f"   3. 🚨 Cross margin mode with other positions affecting calculation")
        print(f"   4. 🚨 System bug in liquidation price calculation")
        print()
        
        print(f"🔍 Expected vs Actual:")
        # For a short position, liquidation should be ABOVE entry price
        # But not THIS much above
        expected_liq_range_low = entry_price * Decimal("1.1")  # 10% above entry
        expected_liq_range_high = entry_price * Decimal("1.5")  # 50% above entry
        
        print(f"   Expected Liquidation Range: {expected_liq_range_low:.5f} - {expected_liq_range_high:.5f} USDT")
        print(f"   Actual Liquidation Price: {liquidation_price} USDT")
        print(f"   Difference: {liquidation_price - expected_liq_range_high:.5f} USDT above expected!")
        
    # Calculate what the liquidation price should be for a proper short position
    print(f"\n🧮 Theoretical Liquidation Analysis:")
    
    # Assume reasonable leverage (10x-20x)
    for leverage in [5, 10, 15, 20]:
        # For short position: Liq Price = Entry Price × (1 + 1/leverage)
        theoretical_liq = entry_price * (1 + Decimal("1")/Decimal(str(leverage)))
        margin_needed = abs(position_size) * entry_price / Decimal(str(leverage))
        
        print(f"   {leverage}x Leverage:")
        print(f"     Theoretical Liq Price: {theoretical_liq:.5f} USDT")
        print(f"     Required Margin: {margin_needed:.2f} USDT")
        print(f"     Safety: {theoretical_liq - mark_price:.5f} USDT ({(theoretical_liq/mark_price-1)*100:.1f}%)")
        print()
    
    # Risk assessment
    print(f"🎯 RISK ASSESSMENT:")
    
    if liquidation_price > mark_price * 2:
        risk_level = "🔴 CRITICAL ERROR"
        recommendation = "IMMEDIATE ACTION REQUIRED"
    elif liquidation_price > mark_price * 1.5:
        risk_level = "🟠 VERY HIGH"
        recommendation = "Review position immediately"
    elif liquidation_price > mark_price * 1.2:
        risk_level = "🟡 HIGH"
        recommendation = "Monitor closely"
    else:
        risk_level = "🟢 ACCEPTABLE"
        recommendation = "Normal monitoring"
    
    print(f"   Risk Level: {risk_level}")
    print(f"   Recommendation: {recommendation}")
    print()
    
    # Immediate actions
    print(f"🚨 IMMEDIATE ACTIONS NEEDED:")
    print(f"   1. ✅ Check if position direction is correct in exchange")
    print(f"   2. ✅ Verify margin mode (Isolated vs Cross)")
    print(f"   3. ✅ Check for other positions affecting margin calculation")
    print(f"   4. ✅ Consider adding more margin if calculation is correct")
    print(f"   5. ✅ Contact exchange support if liquidation price seems wrong")
    print()
    
    print(f"🛡️  SAFETY MEASURES:")
    print(f"   • Set price alerts at key levels")
    print(f"   • Keep extra USDT ready for margin top-up")
    print(f"   • Monitor position 24/7 until issue is resolved")
    print(f"   • Have exit strategy ready")
    
    # Calculate safe margin levels
    print(f"\n💰 MARGIN RECOMMENDATIONS:")
    safe_margin_5x = abs(position_size) * entry_price / Decimal("5")  # 5x leverage = safer
    safe_margin_10x = abs(position_size) * entry_price / Decimal("10")  # 10x leverage
    
    print(f"   For 5x leverage safety: {safe_margin_5x:.2f} USDT margin needed")
    print(f"   For 10x leverage safety: {safe_margin_10x:.2f} USDT margin needed")
    print(f"   Current margin: {margin} USDT")
    
    if margin < safe_margin_10x:
        additional_margin_needed = safe_margin_10x - margin
        print(f"   🚨 Recommend adding: {additional_margin_needed:.2f} USDT margin")

if __name__ == "__main__":
    analyze_liquidation_risk()
