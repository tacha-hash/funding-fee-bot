#!/usr/bin/env python3
"""
Risk Monitor and Alert System for AsterDex Funding Bot
Monitors positions, PnL, funding rates, and market conditions
"""
import os
import sys
import json
import time
import requests
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode
from typing import Dict, List, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class RiskMonitor:
    def __init__(self):
        self.api_key = os.environ.get("ASTERDEX_API_KEY")
        self.api_secret = os.environ.get("ASTERDEX_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found")
        
        self.spot_base_url = "https://sapi.asterdex.com"
        self.futures_base_url = "https://fapi.asterdex.com"
        
        # Risk thresholds
        self.max_loss_threshold = -50.0  # USDT
        self.max_gain_threshold = 100.0   # USDT
        self.funding_rate_threshold = 0.01  # 1%
        self.price_change_threshold = 0.05  # 5%
        self.margin_ratio_threshold = 0.2   # 20%
        
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
            "User-Agent": "AsterRiskMonitor/1.0",
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
    
    def get_current_positions(self):
        """Get current futures positions"""
        positions_data = self.make_request(
            self.futures_base_url, 
            "/fapi/v2/positionRisk", 
            {},
            signed=True
        )
        
        if not positions_data:
            return []
        
        active_positions = []
        for pos in positions_data:
            size = float(pos["positionAmt"])
            if abs(size) > 0:
                active_positions.append({
                    "symbol": pos["symbol"],
                    "size": size,
                    "side": "LONG" if size > 0 else "SHORT",
                    "entry_price": float(pos["entryPrice"]),
                    "mark_price": float(pos["markPrice"]),
                    "pnl": float(pos["unRealizedProfit"]),
                    "percentage": float(pos.get("percentage", "0")),
                    "notional": abs(size * float(pos["markPrice"]))
                })
        
        return active_positions
    
    def get_account_info(self):
        """Get futures account information"""
        account_data = self.make_request(
            self.futures_base_url,
            "/fapi/v2/account",
            {},
            signed=True
        )
        
        if not account_data:
            return None
        
        return {
            "total_balance": float(account_data["totalWalletBalance"]),
            "available_balance": float(account_data["availableBalance"]),
            "total_pnl": float(account_data["totalUnrealizedProfit"]),
            "total_margin": float(account_data["totalInitialMargin"]),
            "margin_ratio": float(account_data["totalInitialMargin"]) / float(account_data["totalWalletBalance"]) if float(account_data["totalWalletBalance"]) > 0 else 0
        }
    
    def get_funding_rate(self, symbol="ASTERUSDT"):
        """Get current funding rate"""
        funding_data = self.make_request(
            self.futures_base_url,
            "/fapi/v1/premiumIndex",
            {"symbol": symbol}
        )
        
        if not funding_data:
            return None
        
        return {
            "symbol": funding_data["symbol"],
            "mark_price": float(funding_data["markPrice"]),
            "index_price": float(funding_data["indexPrice"]),
            "funding_rate": float(funding_data["lastFundingRate"]),
            "next_funding_time": datetime.fromtimestamp(funding_data["nextFundingTime"] / 1000, timezone.utc),
            "funding_rate_8h": float(funding_data["lastFundingRate"]) * 3  # Daily rate (3 times per day)
        }
    
    def get_price_change_24h(self, symbol="ASTERUSDT"):
        """Get 24h price change"""
        ticker_data = self.make_request(
            self.futures_base_url,
            "/fapi/v1/ticker/24hr",
            {"symbol": symbol}
        )
        
        if not ticker_data:
            return None
        
        return {
            "symbol": ticker_data["symbol"],
            "price_change": float(ticker_data["priceChange"]),
            "price_change_percent": float(ticker_data["priceChangePercent"]) / 100,
            "high_price": float(ticker_data["highPrice"]),
            "low_price": float(ticker_data["lowPrice"]),
            "volume": float(ticker_data["volume"])
        }
    
    def analyze_risks(self):
        """Analyze current risks and opportunities"""
        print(f"🔍 Risk Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        alerts = []
        
        # Get data
        positions = self.get_current_positions()
        account = self.get_account_info()
        funding = self.get_funding_rate()
        price_stats = self.get_price_change_24h()
        
        if not positions:
            print("ℹ️  No active positions")
            return alerts
        
        # Position Analysis
        print("\n📊 POSITION ANALYSIS:")
        print("-" * 50)
        
        total_notional = 0
        total_pnl = 0
        
        for pos in positions:
            total_notional += pos["notional"]
            total_pnl += pos["pnl"]
            
            print(f"   {pos['symbol']:>12}: {pos['side']:>5} {abs(pos['size']):>10.2f}")
            print(f"                    Entry: {pos['entry_price']:>8.4f}, Mark: {pos['mark_price']:>8.4f}")
            print(f"                    PnL: {pos['pnl']:>+10.2f} USDT ({pos['percentage']:>+6.2f}%)")
            
            # PnL Alerts
            if pos["pnl"] <= self.max_loss_threshold:
                alert = f"🚨 HIGH LOSS: {pos['symbol']} PnL {pos['pnl']:.2f} USDT"
                alerts.append(alert)
                print(f"   {alert}")
            elif pos["pnl"] >= self.max_gain_threshold:
                alert = f"💰 HIGH GAIN: {pos['symbol']} PnL {pos['pnl']:.2f} USDT - Consider taking profit"
                alerts.append(alert)
                print(f"   {alert}")
        
        # Account Analysis
        if account:
            print(f"\n💰 ACCOUNT OVERVIEW:")
            print("-" * 50)
            print(f"   Total Balance: {account['total_balance']:>12.2f} USDT")
            print(f"   Available: {account['available_balance']:>16.2f} USDT")
            print(f"   Total PnL: {account['total_pnl']:>16.2f} USDT")
            print(f"   Margin Ratio: {account['margin_ratio']*100:>13.2f}%")
            
            # Margin Risk Alert
            if account['margin_ratio'] >= self.margin_ratio_threshold:
                alert = f"⚠️  HIGH MARGIN USAGE: {account['margin_ratio']*100:.2f}%"
                alerts.append(alert)
                print(f"   {alert}")
        
        # Funding Rate Analysis
        if funding:
            print(f"\n📈 FUNDING RATE ANALYSIS:")
            print("-" * 50)
            print(f"   Current Rate: {funding['funding_rate']*100:>13.4f}% (8h)")
            print(f"   Daily Rate: {funding['funding_rate_8h']*100:>15.4f}%")
            print(f"   Next Funding: {funding['next_funding_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Funding Rate Alerts
            if abs(funding['funding_rate']) >= self.funding_rate_threshold:
                direction = "pay" if funding['funding_rate'] > 0 else "receive"
                alert = f"💡 HIGH FUNDING RATE: {funding['funding_rate']*100:.4f}% - Shorts will {direction}"
                alerts.append(alert)
                print(f"   {alert}")
        
        # Price Movement Analysis
        if price_stats:
            print(f"\n📊 PRICE MOVEMENT (24H):")
            print("-" * 50)
            print(f"   Price Change: {price_stats['price_change']:>13.4f} USDT")
            print(f"   Percentage: {price_stats['price_change_percent']*100:>15.2f}%")
            print(f"   High/Low: {price_stats['high_price']:>8.4f} / {price_stats['low_price']:>8.4f}")
            
            # Price Movement Alerts
            if abs(price_stats['price_change_percent']) >= self.price_change_threshold:
                direction = "up" if price_stats['price_change_percent'] > 0 else "down"
                alert = f"📈 HIGH VOLATILITY: Price moved {abs(price_stats['price_change_percent']*100):.2f}% {direction}"
                alerts.append(alert)
                print(f"   {alert}")
        
        # Risk Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 50)
        
        if total_pnl > 50:
            print("   ✅ Consider taking partial profits")
        elif total_pnl < -20:
            print("   ⚠️  Monitor positions closely")
        
        if funding and funding['funding_rate'] > 0.005:  # 0.5%
            print("   💰 High funding rate - good for shorts")
        elif funding and funding['funding_rate'] < -0.005:
            print("   📉 Negative funding rate - consider reducing shorts")
        
        if account and account['margin_ratio'] > 0.15:
            print("   🛡️  Consider reducing position size or adding margin")
        
        return alerts
    
    def monitor_continuous(self, interval_minutes=15):
        """Continuous monitoring with specified interval"""
        print(f"🤖 Starting continuous risk monitoring (every {interval_minutes} minutes)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                alerts = self.analyze_risks()
                
                if alerts:
                    print(f"\n🚨 ACTIVE ALERTS ({len(alerts)}):")
                    for i, alert in enumerate(alerts, 1):
                        print(f"   {i}. {alert}")
                
                print(f"\n⏰ Next check in {interval_minutes} minutes...")
                print("=" * 70)
                
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n👋 Risk monitoring stopped")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AsterDex Risk Monitor")
    parser.add_argument("--continuous", "-c", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--interval", "-i", type=int, default=15, help="Monitoring interval in minutes (default: 15)")
    
    args = parser.parse_args()
    
    try:
        monitor = RiskMonitor()
        
        if args.continuous:
            monitor.monitor_continuous(args.interval)
        else:
            alerts = monitor.analyze_risks()
            if alerts:
                print(f"\n🚨 SUMMARY: {len(alerts)} alert(s) found")
                sys.exit(1)  # Exit with error code if alerts exist
            else:
                print(f"\n✅ All systems normal")
                sys.exit(0)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
