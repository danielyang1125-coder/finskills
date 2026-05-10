#!/usr/bin/env python3
"""Fetch index and sector data for strategy report. Single-shot API calls."""
import requests, json, time, os
os.environ['no_proxy'] = '*'

s = requests.Session()
s.trust_env = False
s.proxies = {'http': None, 'https': None}
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
})

print("=== MAJOR INDICES ===")
# Get major indices via push2 API
idx_codes = {
    '1.000001': '上证指数',
    '0.399001': '深证成指',
    '0.399006': '创业板指',
    '1.000688': '科创50',
    '1.000300': '沪深300',
    '1.000905': '中证500',
}
try:
    url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
    params = {
        'fltt': '2', 'invt': '2',
        'fields': 'f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18,f20',
        'secids': ','.join(idx_codes.keys()),
        '_': str(int(time.time()*1000)),
    }
    r = s.get(url, params=params, timeout=15)
    d = r.json()
    if d.get('data') and d['data'].get('diff'):
        for item in d['data']['diff']:
            code = item.get('f12', '')
            name = idx_codes.get(code, code)
            print(f"{name}: price={item.get('f2')}, chg={item.get('f3')}%, "
                  f"high={item.get('f15')}, low={item.get('f16')}, "
                  f"vol={item.get('f5')}, amt={item.get('f6')}")
except Exception as e:
    print(f"Index error: {e}")

print("\n=== SECTOR PERFORMANCE (申万一级) ===")
# Get sector/industry board performance
try:
    url = 'https://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': '1', 'pz': '50', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': 'm:90+t:2',  # 申万行业板块
        'fields': 'f2,f3,f4,f12,f14,f104,f105,f128,f140',
        '_': str(int(time.time()*1000)),
    }
    r = s.get(url, params=params, timeout=15)
    d = r.json()
    if d.get('data') and d['data'].get('diff'):
        sectors = d['data']['diff']
        # Sort by change pct
        sectors.sort(key=lambda x: float(x.get('f3', 0) or 0), reverse=True)
        print("Top 5 gainers:")
        for item in sectors[:5]:
            print(f"  {item.get('f14','')}: {item.get('f3')}%")
        print("Top 5 losers:")
        for item in sectors[-5:]:
            print(f"  {item.get('f14','')}: {item.get('f3')}%")
        print(f"Total sectors: {len(sectors)}")
except Exception as e:
    print(f"Sector error: {e}")

print("\n=== NORTHBOUND FLOW ===")
try:
    url = 'https://push2.eastmoney.com/api/qt/kamt.kline/get'
    params = {
        'fields1': 'f1,f2,f3,f4',
        'fields2': 'f51,f52,f53,f54',
        'klt': '101', 'lmt': '5',
        '_': str(int(time.time()*1000)),
    }
    r = s.get(url, params=params, timeout=10)
    d = r.json()
    if d.get('data'):
        print(f"Recent northbound data: {d['data']}")
except Exception as e:
    print(f"Northbound error: {e}")

print("\n=== MARKET BREADTH ===")
try:
    # Get up/down count
    url = 'https://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': '1', 'pz': '1', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f12,f14,f3',
        '_': str(int(time.time()*1000)),
    }
    r = s.get(url, params=params, timeout=15)
    d = r.json()
    total = d.get('data', {}).get('total', 0)
    print(f"Total A-shares: {total}")
except:
    pass

print("\nDone.")
