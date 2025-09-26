#!/usr/bin/env python3
"""
Script to check AsterDex account balances and positions
"""
import os
import sys
import json
from decimal import Decimal
import requests
import hashlib
import hmac
import time
from urllib.parse import urlencode

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def sign_params(params, api_secret):
    """Sign API request parameters"""
    api_secret = api_secret.encode('utf-8')
    params.setdefault("recvWindow", 5000)
    params["timestamp"] = int(time.time() * 1000)
    query = urlencode(params, doseq=True)
    signature = hmac.new(api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
    params["signature"] = signature
    return params

def make_request(base_url, path, params=None, api_key=None, api_secret=None):
    """Make API request"""
    url = f"{base_url}{path}"
    params = params or {}
    
    headers = {
        "X-MBX-APIKEY": api_key,
        "User-Agent": "AsterBalanceChecker/1.0",
    }
    
    if api_secret:
        params = sign_params(params, api_secret)
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def check_balances():
    """Check account balances and positions"""
    
    api_key = os.environ.get("ASTERDEX_API_KEY")
    api_secret = os.environ.get("ASTERDEX_API_SECRET")
    
    if not api_key or not api_secret:
        print("❌ API credentials not found in environment variables")
        return
    
    print("🔍 AsterDex Account Summary")
    print("=" * 60)
    
    # Spot balances
    print("\n💰 SPOT WALLET:")
    print("-" * 40)
    spot_data = make_request(
        "https://sapi.asterdex.com", 
        "/api/v1/account", 
        {},
        api_key, 
        api_secret
    )
    
    if spot_data and "balances" in spot_data:
        relevant_balances = []
        for balance in spot_data["balances"]:
            free = float(balance["free"])
            locked = float(balance["locked"])
            total = free + locked
            if total > 0:
                relevant_balances.append({
                    "asset": balance["asset"],
                    "free": free,
                    "locked": locked,
                    "total": total
                })
        
        if relevant_balances:
            for bal in sorted(relevant_balances, key=lambda x: x["total"], reverse=True):
                print(f"   {bal['asset']:>8}: {bal['total']:>12.8f} (Free: {bal['free']:>12.8f}, Locked: {bal['locked']:>12.8f})")
        else:
            print("   No balances found")
    else:
        print("   ❌ Failed to fetch spot balances")
    
    # Futures account
    print("\n📈 FUTURES WALLET:")
    print("-" * 40)
    futures_data = make_request(
        "https://fapi.asterdex.com", 
        "/fapi/v2/account", 
        {},
        api_key, 
        api_secret
    )
    
    if futures_data:
        if "totalWalletBalance" in futures_data:
            print(f"   Total Balance: {float(futures_data['totalWalletBalance']):>12.8f} USDT")
            print(f"   Available Balance: {float(futures_data['availableBalance']):>12.8f} USDT")
            print(f"   Total Unrealized PNL: {float(futures_data['totalUnrealizedProfit']):>12.8f} USDT")
        
        # Show assets with balance
        if "assets" in futures_data:
            print("\n   Assets:")
            for asset in futures_data["assets"]:
                balance = float(asset["walletBalance"])
                if balance > 0:
                    pnl = float(asset["unrealizedProfit"])
                    print(f"     {asset['asset']:>8}: {balance:>12.8f} (PNL: {pnl:>+12.8f})")
    else:
        print("   ❌ Failed to fetch futures account")
    
    # Current positions
    print("\n📊 CURRENT POSITIONS:")
    print("-" * 40)
    positions_data = make_request(
        "https://fapi.asterdex.com", 
        "/fapi/v2/positionRisk", 
        {},
        api_key, 
        api_secret
    )
    
    if positions_data:
        active_positions = []
        for pos in positions_data:
            size = float(pos["positionAmt"])
            if abs(size) > 0:
                active_positions.append(pos)
        
        if active_positions:
            for pos in active_positions:
                symbol = pos["symbol"]
                size = float(pos["positionAmt"])
                entry_price = float(pos["entryPrice"])
                mark_price = float(pos["markPrice"])
                pnl = float(pos["unRealizedProfit"])
                side = "LONG" if size > 0 else "SHORT"
                
                print(f"   {symbol:>12}: {side:>5} {abs(size):>12.4f} @ {entry_price:>8.4f}")
                print(f"                Mark: {mark_price:>8.4f}, PNL: {pnl:>+12.8f} USDT")
        else:
            print("   No active positions")
    else:
        print("   ❌ Failed to fetch positions")
    
    # Recent orders
    print("\n📋 RECENT ORDERS (Last 10):")
    print("-" * 40)
    
    # Spot orders
    spot_orders = make_request(
        "https://sapi.asterdex.com",
        "/api/v1/allOrders",
        {"symbol": "ASTERUSDT", "limit": 5},
        api_key,
        api_secret
    )
    
    if spot_orders:
        print("   Spot Orders:")
        for order in spot_orders[-5:]:
            side = order["side"]
            status = order["status"]
            qty = float(order["executedQty"])
            price = float(order.get("price", 0))
            if price == 0 and "fills" in order and order["fills"]:
                # Calculate average price from fills
                total_qty = sum(float(fill["qty"]) for fill in order["fills"])
                total_value = sum(float(fill["qty"]) * float(fill["price"]) for fill in order["fills"])
                price = total_value / total_qty if total_qty > 0 else 0
            
            print(f"     {side:>4} {qty:>10.4f} ASTER @ {price:>8.4f} [{status}]")
    
    # Futures orders
    futures_orders = make_request(
        "https://fapi.asterdex.com",
        "/fapi/v1/allOrders",
        {"symbol": "ASTERUSDT", "limit": 5},
        api_key,
        api_secret
    )
    
    if futures_orders:
        print("   Futures Orders:")
        for order in futures_orders[-5:]:
            side = order["side"]
            status = order["status"]
            qty = float(order["executedQty"])
            price = float(order.get("avgPrice", 0))
            
            print(f"     {side:>4} {qty:>10.4f} ASTER @ {price:>8.4f} [{status}]")

if __name__ == "__main__":
    check_balances()
