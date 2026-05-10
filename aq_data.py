#!/usr/bin/env python3
"""
Pure-requests A-Share Data Fetcher
====================================
Uses free public APIs (East Money, Sina, etc.) - no akshare, no curl_cffi.
Works on macOS 10.14+ with Python 3.7+ and standard requests.
"""
import requests
import json
import time
import re
import sys
from datetime import datetime, timedelta

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
})

def safe_float(v):
    try:
        return float(v) if v is not None and v != '-' and v != '' else None
    except:
        return None

# ─────────────────────────────────────────────────────────────────────
# 1. CSI 800 Index Constituents (中证800成分股)
# ─────────────────────────────────────────────────────────────────────
def get_csi800_constituents():
    """Get CSI 800 (000906) index constituents via East Money API."""
    print("[1] Fetching CSI 800 constituents...", file=sys.stderr)
    # East Money sector/board API for CSI 800
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "1000",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "b:MK0204",  # CSI 800 board
        "fields": "f12,f14",
        "_": str(int(time.time() * 1000)),
    }
    r = session.get(url, params=params, timeout=15)
    data = r.json()
    stocks = []
    if data.get("data") and data["data"].get("diff"):
        for item in data["data"]["diff"]:
            code = item.get("f12", "")
            name = item.get("f14", "")
            if code:
                stocks.append({"code": code, "name": name})
    print(f"  Found {len(stocks)} constituents", file=sys.stderr)
    return stocks

# ─────────────────────────────────────────────────────────────────────
# 2. Real-time Spot Data (all A-shares)
# ─────────────────────────────────────────────────────────────────────
def get_all_spot_data():
    """Get real-time quotes for all A-shares via East Money."""
    print("[2] Fetching real-time spot data...", file=sys.stderr)
    all_data = []
    # Fetch in batches of 5000 (there are ~5000 A-shares)
    for page in range(1, 6):
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": str(page),
            "pz": "500",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # All A-shares (SH+SZ+BJ)
            "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f100,f115",
            "_": str(int(time.time() * 1000)),
        }
        try:
            r = session.get(url, params=params, timeout=15)
            data = r.json()
            if data.get("data") and data["data"].get("diff"):
                all_data.extend(data["data"]["diff"])
            if not data.get("data") or not data["data"].get("diff") or len(data["data"]["diff"]) < 500:
                break
        except Exception as e:
            print(f"  Page {page} error: {e}", file=sys.stderr)
            break
    print(f"  Got {len(all_data)} stocks", file=sys.stderr)
    return all_data

def spot_to_dict(spot_list):
    """Convert spot data list to dict keyed by f12 (code)."""
    result = {}
    for item in spot_list:
        code = item.get("f12", "")
        if code:
            result[code] = {
                "code": code,
                "name": item.get("f14", ""),
                "price": safe_float(item.get("f2")),
                "change_pct": safe_float(item.get("f3")),
                "change_amount": safe_float(item.get("f4")),
                "volume": safe_float(item.get("f5")),
                "amount": safe_float(item.get("f6")),
                "amplitude": safe_float(item.get("f7")),
                "turnover_rate": safe_float(item.get("f8")),
                "pe_ttm": safe_float(item.get("f9")),
                "pb": safe_float(item.get("f23")),
                "market_cap": safe_float(item.get("f20")),
                "circ_market_cap": safe_float(item.get("f21")),
                "high": safe_float(item.get("f15")),
                "low": safe_float(item.get("f16")),
                "open": safe_float(item.get("f17")),
                "prev_close": safe_float(item.get("f18")),
                "industry": item.get("f100", ""),
            }
    return result

# ─────────────────────────────────────────────────────────────────────
# 3. Financial Data (via East Money financial report API)
# ─────────────────────────────────────────────────────────────────────
def get_financial_data_batch(codes, year=2025, quarter=4):
    """
    Fetch financial indicators for a list of stocks.
    Uses East Money's financial summary API (业绩报表).
    Returns dict: code -> financial metrics.
    """
    print(f"[3] Fetching financial data for {len(codes)} stocks...", file=sys.stderr)
    # East Money YJBB (业绩报表) gives all stocks at once
    # URL pattern: https://datacenter.eastmoney.com/securities/api/data/v1/get
    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    params = {
        "reportName": "RPT_DMSK_FN_MAININDICATOR",
        "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,TOTAL_MARKET_CAP,"
                   "ROE_AVG,OPERATE_INCOME_YOY,NET_PROFIT_YOY,"
                   "BASIC_EPS,BPS,TOTAL_ASSETS,DEBT_ASSET_RATIO,"
                   "GROSS_PROFIT_RATIO,NET_PROFIT_RATIO,"
                   "OCFPS,CURRENT_RATIO,QUICK_RATIO",
        "filter": f'(REPORT_DATE=\'{year}-{12 if quarter==4 else quarter*3}-31\')',
        "pageNumber": "1",
        "pageSize": "5000",
        "sortTypes": "-1",
        "sortColumns": "TOTAL_MARKET_CAP",
        "source": "WEB",
        "client": "WEB",
    }
    try:
        r = session.get(url, params=params, timeout=30)
        data = r.json()
        result = {}
        if data.get("success") and data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                code = item.get("SECURITY_CODE", "")
                if code:
                    result[code] = {
                        "name": item.get("SECURITY_NAME_ABBR", ""),
                        "roe": safe_float(item.get("ROE_AVG")),
                        "revenue_growth_yoy": safe_float(item.get("OPERATE_INCOME_YOY")),
                        "profit_growth_yoy": safe_float(item.get("NET_PROFIT_YOY")),
                        "eps": safe_float(item.get("BASIC_EPS")),
                        "bvps": safe_float(item.get("BPS")),
                        "debt_ratio": safe_float(item.get("DEBT_ASSET_RATIO")),
                        "gross_margin": safe_float(item.get("GROSS_PROFIT_RATIO")),
                        "net_margin": safe_float(item.get("NET_PROFIT_RATIO")),
                        "ocf_per_share": safe_float(item.get("OCFPS")),
                        "current_ratio": safe_float(item.get("CURRENT_RATIO")),
                        "market_cap": safe_float(item.get("TOTAL_MARKET_CAP")),
                    }
        print(f"  Got financial data for {len(result)} stocks", file=sys.stderr)
        return result
    except Exception as e:
        print(f"  Financial API error: {e}", file=sys.stderr)
        return {}

# ─────────────────────────────────────────────────────────────────────
# 4. Price History (via East Money K-line API)
# ─────────────────────────────────────────────────────────────────────
def get_price_history(code, days=365):
    """Get daily price history for a single stock."""
    # Determine market: 6xxxxx=SH, 0xxxxx/3xxxxx=SZ, 4xxxxx/8xxxxx=BJ
    if code.startswith("6"):
        secid = f"1.{code}"
    elif code.startswith(("0", "3")):
        secid = f"0.{code}"
    else:
        secid = f"0.{code}"

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days+30)).strftime("%Y%m%d")

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # daily
        "fqt": "1",    # forward adjusted
        "beg": start_date,
        "end": end_date,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "_": str(int(time.time() * 1000)),
    }
    try:
        r = session.get(url, params=params, timeout=10)
        data = r.json()
        closes = []
        if data.get("data") and data["data"].get("klines"):
            for line in data["data"]["klines"]:
                parts = line.split(",")
                if len(parts) >= 3:
                    closes.append(float(parts[2]))  # close price
        return closes
    except:
        return []

def get_price_history_batch(codes, days=365):
    """Get price history for a batch of stocks (with rate limiting)."""
    print(f"[4] Fetching price history for {len(codes)} stocks...", file=sys.stderr)
    result = {}
    for i, code in enumerate(codes):
        if (i+1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(codes)}", file=sys.stderr)
        result[code] = get_price_history(code, days)
        time.sleep(0.03)
    return result

# ─────────────────────────────────────────────────────────────────────
# 5. Macro Economic Data
# ─────────────────────────────────────────────────────────────────────
def get_macro_data():
    """Get key macro indicators via East Money."""
    print("[0] Fetching macro data...", file=sys.stderr)
    result = {}

    # PMI
    try:
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        params = {
            "reportName": "RPT_ECONOMY_PMI",
            "columns": "REPORT_DATE,MAKE_INDEX,NMAKE_INDEX",
            "pageNumber": "1", "pageSize": "12",
            "sortTypes": "-1", "sortColumns": "REPORT_DATE",
            "source": "WEB", "client": "WEB",
        }
        r = session.get(url, params=params, timeout=10)
        d = r.json()
        if d.get("success") and d["result"].get("data"):
            pmi_data = d["result"]["data"]
            result["pmi"] = {
                "latest_manufacturing": safe_float(pmi_data[0].get("MAKE_INDEX")),
                "latest_non_manufacturing": safe_float(pmi_data[0].get("NMAKE_INDEX")),
                "date": pmi_data[0].get("REPORT_DATE", ""),
            }
    except:
        pass

    # CPI
    try:
        params = {
            "reportName": "RPT_ECONOMY_CPI",
            "columns": "REPORT_DATE,NATIONAL_SAME,NATIONAL_BASE",
            "pageNumber": "1", "pageSize": "12",
            "sortTypes": "-1", "sortColumns": "REPORT_DATE",
            "source": "WEB", "client": "WEB",
        }
        r = session.get(url, params=params, timeout=10)
        d = r.json()
        if d.get("success") and d["result"].get("data"):
            cpi_data = d["result"]["data"]
            result["cpi"] = {
                "latest_yoy": safe_float(cpi_data[0].get("NATIONAL_SAME")),
                "date": cpi_data[0].get("REPORT_DATE", ""),
            }
    except:
        pass

    # PPI
    try:
        params = {
            "reportName": "RPT_ECONOMY_PPI",
            "columns": "REPORT_DATE,ALL_SAME",
            "pageNumber": "1", "pageSize": "12",
            "sortTypes": "-1", "sortColumns": "REPORT_DATE",
            "source": "WEB", "client": "WEB",
        }
        r = session.get(url, params=params, timeout=10)
        d = r.json()
        if d.get("success") and d["result"].get("data"):
            ppi_data = d["result"]["data"]
            result["ppi"] = {
                "latest_yoy": safe_float(ppi_data[0].get("ALL_SAME")),
                "date": ppi_data[0].get("REPORT_DATE", ""),
            }
    except:
        pass

    # Social Financing & M2
    try:
        params = {
            "reportName": "RPT_ECONOMY_SOCIAL_FINANCING",
            "columns": "REPORT_DATE,SUM_SOCIAL_FINANCING_GROWTH,M2_GROWTH,M1_GROWTH",
            "pageNumber": "1", "pageSize": "12",
            "sortTypes": "-1", "sortColumns": "REPORT_DATE",
            "source": "WEB", "client": "WEB",
        }
        r = session.get(url, params=params, timeout=10)
        d = r.json()
        if d.get("success") and d["result"].get("data"):
            sf_data = d["result"]["data"]
            result["social_financing"] = {
                "latest_sf_growth": safe_float(sf_data[0].get("SUM_SOCIAL_FINANCING_GROWTH")),
                "latest_m2_growth": safe_float(sf_data[0].get("M2_GROWTH")),
                "latest_m1_growth": safe_float(sf_data[0].get("M1_GROWTH")),
                "date": sf_data[0].get("REPORT_DATE", ""),
            }
    except:
        pass

    return result


# ─────────────────────────────────────────────────────────────────────
# Main test
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test spot data
    spot = get_all_spot_data()
    spot_dict = spot_to_dict(spot)
    print(f"\nSpot data for 600519 (贵州茅台):")
    print(json.dumps(spot_dict.get("600519", {}), ensure_ascii=False, indent=2))

    # Test financial data
    fin = get_financial_data_batch(["600519", "000858", "300750"])
    print(f"\nFinancial data:")
    for k, v in fin.items():
        print(f"  {k}: {v['name']} ROE={v['roe']}%")

    # Test price history
    prices = get_price_history("600519")
    print(f"\nPrice history for 600519: {len(prices)} days")
    if prices:
        print(f"  First: {prices[0]:.2f}, Last: {prices[-1]:.2f}")

    # Test macro
    macro = get_macro_data()
    print(f"\nMacro data: {json.dumps(macro, ensure_ascii=False, indent=2)}")
