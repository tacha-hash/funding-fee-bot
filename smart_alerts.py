#!/usr/bin/env python3
"""
Smart Alert System for AsterDex Funding Bot
Intelligent alerts for profit taking and position management
"""
import os
import sys
import json
import time
import requests
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class SmartAlerts:
    def __init__(self):
        self.api_key = os.environ.get("ASTERDEX_API_KEY")
        self.api_secret = os.environ.get("ASTERDEX_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found")
        
        self.spot_base_url = "https://sapi.asterdex.com"
        self.futures_base_url = "https://fapi.asterdex.com"
        
        # Alert thresholds
        self.profit_targets = {
            "small_profit": 10.0,      # Take 25% profit
            "medium_profit": 25.0,     # Take 50% profit  
            "large_profit": 50.0,      # Take 75% profit
            "huge_profit": 100.0       # Consider full exit
        }
        
        self.risk_thresholds = {
            "stop_loss": -30.0,        # Consider cutting losses
            "margin_warning": 0.25,    # 25% margin usage
            "margin_danger": 0.4,      # 40% margin usage
            "liquidation_warning": 0.3 # 30% distance to liquidation
        }
        
        self.funding_thresholds = {
            "high_positive": 0.005,    # 0.5% - great for shorts
            "low_positive": 0.001,     # 0.1% - okay for shorts
            "negative": -0.001,        # Negative - bad for shorts
            "very_negative": -0.005    # Very negative - exit shorts
        }
        
        # Track previous states for trend analysis
        self.previous_pnl = None
        self.previous_price = None
        self.alerts_history = []
        
    def sign_params(self, params):
        """Sign API request parameters"""
        api_secret = self.api_secret.encode('utf-8')
        params.setdefault("recvWindow", 5000)
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params, doseq=True)
        signature = hmac.new(api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params
    
    def make_request(self, base_url, path, params=None, signed=False):
        """Make API request"""
        url = f"{base_url}{path}"
        params = params or {}
        
        headers = {
            "X-MBX-APIKEY": self.api_key,
            "User-Agent": "AsterSmartAlerts/1.0",
        }
        
        if signed:
            params = self.sign_params(params)
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def get_market_data(self):
        """Get comprehensive market data"""
        # Current positions
        positions_data = self.make_request(
            self.futures_base_url, "/fapi/v2/positionRisk", {}, signed=True
        )
        
        # Account info
        account_data = self.make_request(
            self.futures_base_url, "/fapi/v2/account", {}, signed=True
        )
        
        # Funding rate
        funding_data = self.make_request(
            self.futures_base_url, "/fapi/v1/premiumIndex", {"symbol": "ASTERUSDT"}
        )
        
        # Price stats
        ticker_data = self.make_request(
            self.futures_base_url, "/fapi/v1/ticker/24hr", {"symbol": "ASTERUSDT"}
        )
        
        return {
            "positions": positions_data,
            "account": account_data,
            "funding": funding_data,
            "ticker": ticker_data
        }
    
    def analyze_profit_opportunities(self, position, current_pnl):
        """Analyze profit taking opportunities"""
        alerts = []
        
        if current_pnl <= 0:
            return alerts
        
        # Profit target alerts
        for level, threshold in self.profit_targets.items():
            if current_pnl >= threshold:
                if level == "small_profit":
                    action = "Consider taking 25% profit"
                    urgency = "💰"
                elif level == "medium_profit":
                    action = "Consider taking 50% profit"
                    urgency = "💰💰"
                elif level == "large_profit":
                    action = "Consider taking 75% profit"
                    urgency = "💰💰💰"
                else:  # huge_profit
                    action = "Consider full exit - excellent profits!"
                    urgency = "🎉"
                
                alerts.append({
                    "type": "profit_target",
                    "level": level,
                    "message": f"{urgency} PROFIT TARGET: {current_pnl:.2f} USDT - {action}",
                    "urgency": "high" if current_pnl >= self.profit_targets["large_profit"] else "medium",
                    "action": action
                })
                break  # Only show the highest applicable level
        
        # Trend-based alerts
        if self.previous_pnl is not None:
            pnl_change = current_pnl - self.previous_pnl
            if current_pnl > 20 and pnl_change < -5:  # Profit declining
                alerts.append({
                    "type": "trend_warning",
                    "message": f"📉 PROFIT DECLINING: Down {abs(pnl_change):.2f} USDT - Consider partial exit",
                    "urgency": "medium",
                    "action": "Monitor closely or take partial profits"
                })
        
        return alerts
    
    def analyze_risk_management(self, position, account, current_pnl):
        """Analyze risk management needs"""
        alerts = []
        
        # Stop loss alerts
        if current_pnl <= self.risk_thresholds["stop_loss"]:
            alerts.append({
                "type": "stop_loss",
                "message": f"🚨 STOP LOSS: {current_pnl:.2f} USDT - Consider cutting losses",
                "urgency": "high",
                "action": "Consider closing position to limit losses"
            })
        
        # Margin usage alerts
        if account:
            margin_ratio = float(account["totalInitialMargin"]) / float(account["totalWalletBalance"])
            
            if margin_ratio >= self.risk_thresholds["margin_danger"]:
                alerts.append({
                    "type": "margin_danger",
                    "message": f"🚨 HIGH MARGIN USAGE: {margin_ratio*100:.1f}% - Add margin or reduce position",
                    "urgency": "high",
                    "action": "Add margin or reduce position size immediately"
                })
            elif margin_ratio >= self.risk_thresholds["margin_warning"]:
                alerts.append({
                    "type": "margin_warning", 
                    "message": f"⚠️ MARGIN WARNING: {margin_ratio*100:.1f}% - Monitor closely",
                    "urgency": "medium",
                    "action": "Consider adding margin or reducing position"
                })
        
        # Liquidation distance alert
        entry_price = float(position["entryPrice"])
        mark_price = float(position["markPrice"])
        position_size = abs(float(position["positionAmt"]))
        
        # Simplified liquidation calculation for SHORT position
        available_balance = float(account["availableBalance"]) if account else 0
        maintenance_margin = position_size * mark_price * 0.05  # 5% maintenance
        max_loss = available_balance + current_pnl - maintenance_margin
        liquidation_price = entry_price + (max_loss / position_size)
        
        distance_to_liq = (liquidation_price - mark_price) / mark_price
        
        if distance_to_liq <= self.risk_thresholds["liquidation_warning"]:
            alerts.append({
                "type": "liquidation_warning",
                "message": f"⚠️ LIQUIDATION RISK: {distance_to_liq*100:.1f}% away at {liquidation_price:.4f} USDT",
                "urgency": "high",
                "action": "Add margin or reduce position size immediately"
            })
        
        return alerts
    
    def analyze_funding_opportunities(self, funding_data):
        """Analyze funding rate opportunities"""
        alerts = []
        
        if not funding_data:
            return alerts
        
        funding_rate = float(funding_data["lastFundingRate"])
        next_funding = datetime.fromtimestamp(funding_data["nextFundingTime"] / 1000, timezone.utc)
        time_to_funding = next_funding - datetime.now(timezone.utc)
        
        daily_rate = funding_rate * 3 * 100  # 3 times per day, as percentage
        
        if funding_rate >= self.funding_thresholds["high_positive"]:
            alerts.append({
                "type": "funding_excellent",
                "message": f"🎯 EXCELLENT FUNDING: {funding_rate*100:.3f}% ({daily_rate:.2f}% daily) - Great for shorts!",
                "urgency": "low",
                "action": "Excellent conditions for maintaining short positions"
            })
        elif funding_rate >= self.funding_thresholds["low_positive"]:
            alerts.append({
                "type": "funding_good",
                "message": f"✅ POSITIVE FUNDING: {funding_rate*100:.3f}% ({daily_rate:.2f}% daily) - Good for shorts",
                "urgency": "low",
                "action": "Favorable conditions for short positions"
            })
        elif funding_rate <= self.funding_thresholds["very_negative"]:
            alerts.append({
                "type": "funding_very_bad",
                "message": f"🚨 VERY NEGATIVE FUNDING: {funding_rate*100:.3f}% ({daily_rate:.2f}% daily) - Consider closing shorts!",
                "urgency": "high",
                "action": "Consider closing short positions - you're paying high fees"
            })
        elif funding_rate <= self.funding_thresholds["negative"]:
            alerts.append({
                "type": "funding_bad",
                "message": f"⚠️ NEGATIVE FUNDING: {funding_rate*100:.3f}% ({daily_rate:.2f}% daily) - Monitor closely",
                "urgency": "medium",
                "action": "Consider reducing short positions if trend continues"
            })
        
        # Time to next funding alert
        if time_to_funding.total_seconds() <= 3600:  # 1 hour
            minutes = int(time_to_funding.total_seconds() / 60)
            alerts.append({
                "type": "funding_timing",
                "message": f"⏰ FUNDING IN {minutes} MINUTES: {funding_rate*100:.3f}% rate",
                "urgency": "low",
                "action": f"Next funding payment in {minutes} minutes"
            })
        
        return alerts
    
    def analyze_market_conditions(self, ticker_data, current_price):
        """Analyze overall market conditions"""
        alerts = []
        
        if not ticker_data:
            return alerts
        
        price_change_24h = float(ticker_data["priceChangePercent"]) / 100
        volume = float(ticker_data["volume"])
        high_24h = float(ticker_data["highPrice"])
        low_24h = float(ticker_data["lowPrice"])
        
        # Volatility analysis
        volatility = (high_24h - low_24h) / low_24h
        if volatility > 0.2:  # 20% range
            alerts.append({
                "type": "high_volatility",
                "message": f"📊 HIGH VOLATILITY: {volatility*100:.1f}% range today - Increased risk",
                "urgency": "medium",
                "action": "Consider reducing position size due to high volatility"
            })
        
        # Price trend analysis
        if self.previous_price is not None:
            price_trend = (current_price - self.previous_price) / self.previous_price
            if abs(price_trend) > 0.05:  # 5% change since last check
                direction = "up" if price_trend > 0 else "down"
                impact = "negative" if (price_trend > 0) else "positive"  # For short positions
                alerts.append({
                    "type": "price_trend",
                    "message": f"📈 PRICE MOVING {direction.upper()}: {abs(price_trend)*100:.1f}% - {impact.title()} for shorts",
                    "urgency": "medium" if abs(price_trend) > 0.1 else "low",
                    "action": f"Price trending {direction} - monitor position closely"
                })
        
        return alerts
    
    def generate_smart_recommendations(self, all_alerts, current_pnl, position):
        """Generate smart recommendations based on all alerts"""
        recommendations = []
        
        # Categorize alerts by urgency
        high_urgency = [a for a in all_alerts if a.get("urgency") == "high"]
        medium_urgency = [a for a in all_alerts if a.get("urgency") == "medium"]
        
        # Strategic recommendations
        if current_pnl > 50:
            recommendations.append("🎯 STRATEGY: Excellent profits achieved - consider systematic profit taking")
        elif current_pnl > 25:
            recommendations.append("💰 STRATEGY: Good profits - consider taking partial profits and letting rest run")
        elif current_pnl < -20:
            recommendations.append("🛡️ STRATEGY: Significant losses - review position and consider risk management")
        
        # Risk management recommendations
        if high_urgency:
            recommendations.append("🚨 URGENT: High-priority alerts require immediate attention")
        elif medium_urgency:
            recommendations.append("⚠️ MONITOR: Medium-priority alerts - keep close watch")
        else:
            recommendations.append("✅ STATUS: No urgent issues - position appears stable")
        
        return recommendations
    
    def run_analysis(self):
        """Run comprehensive smart analysis"""
        print(f"🤖 Smart Alert Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Get market data
        data = self.get_market_data()
        
        if not data["positions"]:
            print("ℹ️  No active positions to analyze")
            return []
        
        # Find ASTER position
        aster_position = None
        for pos in data["positions"]:
            if pos["symbol"] == "ASTERUSDT" and abs(float(pos["positionAmt"])) > 0:
                aster_position = pos
                break
        
        if not aster_position:
            print("ℹ️  No ASTERUSDT position found")
            return []
        
        # Extract key metrics
        current_pnl = float(aster_position["unRealizedProfit"])
        current_price = float(aster_position["markPrice"])
        position_size = abs(float(aster_position["positionAmt"]))
        entry_price = float(aster_position["entryPrice"])
        
        print(f"\n📊 POSITION OVERVIEW:")
        print(f"   SHORT {position_size:.2f} ASTER @ {entry_price:.4f}")
        print(f"   Current Price: {current_price:.4f} USDT")
        print(f"   Current PnL: {current_pnl:+.2f} USDT")
        
        # Run all analyses
        all_alerts = []
        
        # Profit analysis
        profit_alerts = self.analyze_profit_opportunities(aster_position, current_pnl)
        all_alerts.extend(profit_alerts)
        
        # Risk analysis
        risk_alerts = self.analyze_risk_management(aster_position, data["account"], current_pnl)
        all_alerts.extend(risk_alerts)
        
        # Funding analysis
        funding_alerts = self.analyze_funding_opportunities(data["funding"])
        all_alerts.extend(funding_alerts)
        
        # Market analysis
        market_alerts = self.analyze_market_conditions(data["ticker"], current_price)
        all_alerts.extend(market_alerts)
        
        # Display alerts by priority
        high_alerts = [a for a in all_alerts if a.get("urgency") == "high"]
        medium_alerts = [a for a in all_alerts if a.get("urgency") == "medium"]
        low_alerts = [a for a in all_alerts if a.get("urgency") == "low"]
        
        if high_alerts:
            print(f"\n🚨 HIGH PRIORITY ALERTS ({len(high_alerts)}):")
            for i, alert in enumerate(high_alerts, 1):
                print(f"   {i}. {alert['message']}")
                print(f"      → {alert['action']}")
        
        if medium_alerts:
            print(f"\n⚠️  MEDIUM PRIORITY ALERTS ({len(medium_alerts)}):")
            for i, alert in enumerate(medium_alerts, 1):
                print(f"   {i}. {alert['message']}")
                print(f"      → {alert['action']}")
        
        if low_alerts:
            print(f"\n💡 INFORMATION ALERTS ({len(low_alerts)}):")
            for i, alert in enumerate(low_alerts, 1):
                print(f"   {i}. {alert['message']}")
        
        # Smart recommendations
        recommendations = self.generate_smart_recommendations(all_alerts, current_pnl, aster_position)
        if recommendations:
            print(f"\n🎯 SMART RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Update previous states for trend analysis
        self.previous_pnl = current_pnl
        self.previous_price = current_price
        
        return all_alerts
    
    def monitor_continuous(self, interval_minutes=10):
        """Continuous smart monitoring"""
        print(f"🤖 Starting Smart Alert Monitoring (every {interval_minutes} minutes)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                alerts = self.run_analysis()
                
                # Count urgent alerts
                urgent_count = len([a for a in alerts if a.get("urgency") == "high"])
                
                if urgent_count > 0:
                    print(f"\n🚨 {urgent_count} URGENT ALERT(S) - CHECK IMMEDIATELY!")
                
                print(f"\n⏰ Next analysis in {interval_minutes} minutes...")
                print("=" * 80)
                
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n👋 Smart monitoring stopped")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AsterDex Smart Alert System")
    parser.add_argument("--continuous", "-c", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--interval", "-i", type=int, default=10, help="Monitoring interval in minutes (default: 10)")
    
    args = parser.parse_args()
    
    try:
        alerts = SmartAlerts()
        
        if args.continuous:
            alerts.monitor_continuous(args.interval)
        else:
            alert_list = alerts.run_analysis()
            urgent_alerts = [a for a in alert_list if a.get("urgency") == "high"]
            
            if urgent_alerts:
                print(f"\n🚨 SUMMARY: {len(urgent_alerts)} urgent alert(s) require attention")
                sys.exit(1)
            else:
                print(f"\n✅ SUMMARY: {len(alert_list)} total alerts, no urgent action needed")
                sys.exit(0)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
