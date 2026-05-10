#!/usr/bin/env python3
"""Quick test of aq_data APIs."""
import sys, json
sys.path.insert(0, "/Users/daniel/finskills")
from aq_data import get_macro_data, get_csi800_constituents, get_financial_data_batch, get_all_spot_data, spot_to_dict, get_price_history

# Test macro
print("=== MACRO ===")
m = get_macro_data()
print(json.dumps(m, ensure_ascii=False, indent=2))

# Test CSI 800
print("\n=== CSI 800 ===")
csi = get_csi800_constituents()
print(f"Count: {len(csi)}")
if csi:
    print(f"First 5: {csi[:5]}")

# Test spot
print("\n=== SPOT ===")
spot = get_all_spot_data()
spot_d = spot_to_dict(spot)
print(f"Total stocks in spot: {len(spot_d)}")
if "600519" in spot_d:
    print(f"600519: {json.dumps(spot_d['600519'], ensure_ascii=False)}")

# Test financial data (empty list = all)
print("\n=== FINANCIAL ===")
fin = get_financial_data_batch([])
if fin:
    sample = list(fin.items())[:5]
    for k, v in sample:
        print(f"  {k}: {v.get('name','')} ROE={v.get('roe')}% RevG={v.get('revenue_growth_yoy')}%")
    print(f"Total records with data: {len(fin)}")

# Test price history
print("\n=== PRICE HISTORY ===")
prices = get_price_history("600519")
print(f"600519: {len(prices)} data points")
if prices:
    print(f"  Latest close: {prices[-1]:.2f}")
    ret_1y = (prices[-1] / prices[0] - 1) * 100 if len(prices) > 1 else 0
    print(f"  ~1Y return: {ret_1y:.1f}%")
