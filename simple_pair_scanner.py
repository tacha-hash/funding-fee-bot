#!/usr/bin/env python3
"""
Simple Trading Pair Scanner for AsterDex
Shows available pairs with funding rates and basic metrics
"""
import os
import sys
import json
import requests
import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import urlencode

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class SimplePairScanner:
    def __init__(self):
        self.api_key = os.environ.get("ASTERDEX_API_KEY")
        self.api_secret = os.environ.get("ASTERDEX_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found")
        
        self.spot_base_url = "https://sapi.asterdex.com"
        self.futures_base_url = "https://fapi.asterdex.com"
    
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
            "User-Agent": "SimplePairScanner/1.0",
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
    
    def get_available_pairs(self):
        """Get available trading pairs"""
        print("🔍 Getting available trading pairs...")
        
        # Get spot pairs
        spot_info = self.make_request(self.spot_base_url, "/api/v1/exchangeInfo")
        spot_pairs = []
        if spot_info:
            for symbol in spot_info.get("symbols", []):
                if (symbol.get("status") == "TRADING" and 
                    symbol.get("quoteAsset") == "USDT"):
                    spot_pairs.append(symbol["symbol"])
        
        # Get futures pairs
        futures_info = self.make_request(self.futures_base_url, "/fapi/v1/exchangeInfo")
        futures_pairs = []
        if futures_info:
            for symbol in futures_info.get("symbols", []):
                if (symbol.get("status") == "TRADING" and 
                    symbol.get("quoteAsset") == "USDT"):
                    futures_pairs.append(symbol["symbol"])
        
        # Find common pairs
        common_pairs = list(set(spot_pairs) & set(futures_pairs))
        
        print(f"📊 Found {len(spot_pairs)} spot pairs")
        print(f"📊 Found {len(futures_pairs)} futures pairs")
        print(f"🎯 Found {len(common_pairs)} common pairs for arbitrage")
        
        return common_pairs
    
    def get_pair_data(self, symbol):
        """Get comprehensive data for a trading pair"""
        print(f"📊 Analyzing {symbol}...")
        
        # Get spot ticker
        spot_ticker = self.make_request(self.spot_base_url, "/api/v1/ticker/24hr", {"symbol": symbol})
        
        # Get futures ticker
        futures_ticker = self.make_request(self.futures_base_url, "/fapi/v1/ticker/24hr", {"symbol": symbol})
        
        # Get funding rate
        funding = self.make_request(self.futures_base_url, "/fapi/v1/premiumIndex", {"symbol": symbol})
        
        if not all([spot_ticker, futures_ticker, funding]):
            print(f"⚠️ Could not get complete data for {symbol}")
            return None
        
        # Calculate metrics
        spot_price = float(spot_ticker["lastPrice"])
        futures_price = float(futures_ticker["lastPrice"])
        funding_rate = float(funding["lastFundingRate"])
        
        price_diff = futures_price - spot_price
        price_diff_pct = (price_diff / spot_price) * 100 if spot_price > 0 else 0
        
        return {
            "symbol": symbol,
            "spot_price": spot_price,
            "futures_price": futures_price,
            "price_diff": price_diff,
            "price_diff_pct": price_diff_pct,
            "funding_rate_8h": funding_rate * 100,
            "funding_rate_daily": funding_rate * 3 * 100,
            "funding_rate_annual": funding_rate * 3 * 365 * 100,
            "spot_volume_24h": float(spot_ticker["quoteVolume"]),
            "futures_volume_24h": float(futures_ticker["quoteVolume"]),
            "price_change_24h": float(spot_ticker["priceChangePercent"]),
            "next_funding": datetime.fromtimestamp(funding["nextFundingTime"] / 1000, timezone.utc)
        }
    
    def analyze_opportunity(self, data):
        """Analyze trading opportunity"""
        funding_8h = data["funding_rate_8h"]
        funding_daily = data["funding_rate_daily"]
        volume = data["spot_volume_24h"]
        price_diff = abs(data["price_diff_pct"])
        
        # Scoring
        score = 0
        recommendation = ""
        
        if funding_8h >= 0.5:  # 0.5% or higher
            score += 40
            recommendation = "🎯 EXCELLENT for shorts"
        elif funding_8h >= 0.1:  # 0.1% or higher
            score += 30
            recommendation = "✅ GOOD for shorts"
        elif funding_8h >= 0:
            score += 10
            recommendation = "💛 NEUTRAL"
        else:
            score -= 20
            recommendation = "⚠️ NEGATIVE funding - good for longs"
        
        # Volume score
        if volume >= 1000000:  # 1M+
            score += 30
        elif volume >= 100000:  # 100k+
            score += 20
        elif volume >= 10000:   # 10k+
            score += 10
        
        # Price difference penalty
        if price_diff > 1:  # More than 1% difference
            score -= 20
        
        data["score"] = max(0, score)
        data["recommendation"] = recommendation
        
        return data
    
    def scan_all_pairs(self):
        """Scan all available pairs"""
        pairs = self.get_available_pairs()
        
        if not pairs:
            print("❌ No pairs found")
            return []
        
        print(f"\n🔄 Analyzing {len(pairs)} pairs...")
        print("=" * 60)
        
        results = []
        for i, symbol in enumerate(pairs, 1):
            print(f"[{i}/{len(pairs)}] ", end="", flush=True)
            
            data = self.get_pair_data(symbol)
            if data:
                analyzed_data = self.analyze_opportunity(data)
                results.append(analyzed_data)
                
                # Show basic info
                funding = analyzed_data["funding_rate_daily"]
                volume_k = analyzed_data["spot_volume_24h"] / 1000
                print(f"Funding: {funding:+.2f}%/day, Volume: {volume_k:.0f}k")
            else:
                print("Failed to get data")
        
        return results
    
    def display_results(self, results):
        """Display scan results"""
        if not results:
            print("❌ No data to display")
            return
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"\n🎯 TRADING PAIR ANALYSIS RESULTS")
        print("=" * 120)
        
        # Header
        print(f"{'Symbol':<12} {'Score':<5} {'Spot Price':<10} {'Futures':<10} {'Spread%':<8} "
              f"{'Fund(8h)%':<10} {'Fund(Day)%':<11} {'Volume(24h)':<12} {'Recommendation'}")
        print("-" * 120)
        
        for data in results:
            volume_k = data["spot_volume_24h"] / 1000
            
            print(f"{data['symbol']:<12} {data['score']:<5.0f} {data['spot_price']:<10.4f} "
                  f"{data['futures_price']:<10.4f} {data['price_diff_pct']:<8.2f} "
                  f"{data['funding_rate_8h']:<10.3f} {data['funding_rate_daily']:<11.2f} "
                  f"{volume_k:<12.0f}k {data['recommendation']}")
        
        # Summary
        print(f"\n📊 SUMMARY")
        print("-" * 50)
        
        positive_funding = [r for r in results if r["funding_rate_8h"] > 0]
        high_score = [r for r in results if r["score"] >= 50]
        
        print(f"Total pairs analyzed: {len(results)}")
        print(f"Positive funding pairs: {len(positive_funding)}")
        print(f"High opportunity pairs (50+ score): {len(high_score)}")
        
        if positive_funding:
            avg_daily = sum(r["funding_rate_daily"] for r in positive_funding) / len(positive_funding)
            print(f"Average daily funding (positive): {avg_daily:.2f}%")
        
        # Top recommendations
        print(f"\n🏆 TOP 3 RECOMMENDATIONS:")
        print("-" * 40)
        
        for i, data in enumerate(results[:3], 1):
            print(f"{i}. {data['symbol']}")
            print(f"   Score: {data['score']}/100")
            print(f"   Daily funding: {data['funding_rate_daily']:+.2f}%")
            print(f"   Volume: {data['spot_volume_24h']/1000:.0f}k USDT")
            print(f"   {data['recommendation']}")
            print()

def main():
    """Main function"""
    try:
        scanner = SimplePairScanner()
        results = scanner.scan_all_pairs()
        scanner.display_results(results)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import time
    main()
