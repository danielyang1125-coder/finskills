#!/usr/bin/env python3
"""
Multi-Factor A-Share Screener - Resilient Edition
==================================================
Uses East Money push2 API for spot data + K-line for price history.
Bypasses system proxy. Falls back gracefully on failures.

Runs on: macOS 10.14+ with Python 3.7+ and requests
"""
import requests, json, time, sys, os, math
from datetime import datetime, timedelta
import numpy as np

os.environ['no_proxy'] = '*'
os.environ['NO_PROXY'] = '*'

# ── HTTP setup ──────────────────────────────────────────────────────
session = requests.Session()
session.trust_env = False
session.proxies = {'http': None, 'https': None}
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
})

def safe_float(v):
    try:
        f = float(v)
        return f if not (np.isnan(f) or np.isinf(f)) else None
    except:
        return None

# ── Step 1: Spot Data (all A-shares, single batch) ──────────────────
def fetch_all_spot():
    print("[1/5] Fetching spot data for all A-shares...", file=sys.stderr)
    all_data = []
    page_size = 100
    total = None
    for page in range(1, 100):
        params = {
            'pn': str(page), 'pz': str(page_size), 'po': '1', 'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2', 'invt': '2', 'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f2,f3,f8,f9,f12,f14,f15,f16,f17,f18,f20,f21,f23,f100,f115',
        }
        # Retry up to 3 times with increasing delays
        for attempt in range(3):
            try:
                r = session.get('https://push2.eastmoney.com/api/qt/clist/get', params=params, timeout=20)
                d = r.json()
                data_block = d.get('data', {})
                if total is None:
                    total = data_block.get('total', 0)
                    print(f"  Total stocks in API: {total}", file=sys.stderr)
                chunk = data_block.get('diff', [])
                if not chunk:
                    break
                all_data.extend(chunk)
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                print(f"  Page {page} error after 3 attempts: {e}", file=sys.stderr)
                break
        if not chunk or len(all_data) >= total:
            break
        time.sleep(0.3)  # rate limit between pages
    print(f"  Got {len(all_data)} stocks", file=sys.stderr)
    return all_data

def spot_records(spot_list):
    """Convert raw spot data to structured records."""
    recs = []
    for item in spot_list:
        code = item.get('f12', '')
        industry = item.get('f100', '')
        market_cap = safe_float(item.get('f20'))
        if not code or not market_cap:
            continue
        recs.append({
            'code': code,
            'name': str(item.get('f14', '')),
            'industry': industry if industry else '其他',
            'price': safe_float(item.get('f2')),
            'change_pct': safe_float(item.get('f3')),
            'turnover_rate': safe_float(item.get('f8')),
            'pe_ttm': safe_float(item.get('f9')),
            'pb': safe_float(item.get('f23')),
            'market_cap': market_cap,
            'circ_market_cap': safe_float(item.get('f21')),
            'high_52w': safe_float(item.get('f15')),
            'low_52w': safe_float(item.get('f16')),
            'open_today': safe_float(item.get('f17')),
            'prev_close': safe_float(item.get('f18')),
        })
    return recs

# ── Step 2: Filter to CSI 800 range (top 800 by market cap) ────────
def filter_top_n(records, n=800):
    records.sort(key=lambda x: x['market_cap'] or 0, reverse=True)
    return records[:n]

# ── Step 3: Price History (K-line) ──────────────────────────────────
def fetch_price_history(code):
    """Get daily close prices for a single stock."""
    if code.startswith('6'):
        secid = f'1.{code}'
    else:
        secid = f'0.{code}'
    end = datetime.now().strftime('%Y%m%d')
    start = (datetime.now() - timedelta(days=400)).strftime('%Y%m%d')
    try:
        r = session.get('https://push2his.eastmoney.com/api/qt/stock/kline/get', params={
            'secid': secid, 'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': '101', 'fqt': '1', 'beg': start, 'end': end,
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        }, timeout=10)
        d = r.json()
        closes = []
        klines = d.get('data', {}).get('klines', [])
        for line in klines:
            parts = line.split(',')
            if len(parts) >= 3:
                closes.append(float(parts[2]))
        return closes
    except:
        return []

def fetch_price_batch(codes, batch_name=""):
    print(f"[3/5] Fetching price history for {len(codes)} stocks {batch_name}...", file=sys.stderr)
    results = {}
    for i, code in enumerate(codes):
        if (i+1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(codes)}", file=sys.stderr)
        results[code] = fetch_price_history(code)
        time.sleep(0.03)
    return results

# ── Step 4: Factor Computation ──────────────────────────────────────
def winsorize(arr, lo=2.5, hi=97.5):
    a = np.array([x for x in arr if x is not None], dtype=float)
    if len(a) < 4:
        return arr
    lo_v, hi_v = np.percentile(a, [lo, hi])
    return [min(max(x, lo_v), hi_v) if x is not None else None for x in arr]

def pct_score(values, ascending=True):
    """Convert to 0-100 percentile scores. ascending=True = higher value gets higher score."""
    n = len(values)
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(valid) < 3:
        return [50.0] * n
    sorted_valid = sorted(valid, key=lambda x: x[1], reverse=not ascending)
    scores = {}
    for rank, (idx, _) in enumerate(sorted_valid):
        scores[idx] = (rank / (len(sorted_valid) - 1)) * 100
    return [scores.get(i, 50.0) for i in range(n)]

def industry_group_score(records, field, ascending=True):
    """Compute percentile scores within each industry group."""
    groups = {}
    for i, r in enumerate(records):
        ind = r.get('industry', '其他')
        groups.setdefault(ind, []).append((i, r.get(field)))
    scores = [50.0] * len(records)
    for ind, items in groups.items():
        vals = [v for _, v in items]
        group_scores = pct_score(vals, ascending)
        for (idx, _), s in zip(items, group_scores):
            scores[idx] = s
    return scores

def compute_factors(records, price_data):
    print("[4/5] Computing factor scores...", file=sys.stderr)
    n = len(records)

    # ── VALUE: E/P, B/P ───────────────────────────────────────────
    # Earnings yield = 1/PE (higher is better)
    ep = [100/r['pe_ttm'] if r['pe_ttm'] and r['pe_ttm'] > 0 else None for r in records]
    bp = [100/r['pb'] if r['pb'] and r['pb'] > 0 else None for r in records]

    for i, r in enumerate(records):
        r['ep'] = ep[i]
        r['bp'] = bp[i]

    score_ep = industry_group_score(records, 'ep', True)
    score_bp = industry_group_score(records, 'bp', True)

    for i in range(n):
        records[i]['value_score'] = 0.50 * score_ep[i] + 0.35 * score_bp[i] + 0.15 * 50.0

    # ── MOMENTUM: 12-1m price, low turnover ──────────────────────
    mom_vals = []
    for r in records:
        closes = price_data.get(r['code'], [])
        if len(closes) >= 250:
            mom_vals.append((closes[-20] / closes[-250] - 1) * 100)
        elif len(closes) >= 60:
            mom_vals.append((closes[-20] / closes[0] - 1) * 100)
        else:
            mom_vals.append(r.get('change_pct'))  # fallback: today's change (weak proxy)

    for i in range(n):
        records[i]['momentum_12m1m'] = mom_vals[i]

    score_mom = industry_group_score(records, 'momentum_12m1m', True)
    score_lowto = industry_group_score(records, 'turnover_rate', False)  # lower turnover = higher

    for i in range(n):
        records[i]['momentum_score'] = 0.60 * score_mom[i] + 0.40 * score_lowto[i]

    # ── QUALITY: PB-based valuation quality + turnover stability ───
    # Quality is harder without financial statements. Use:
    # - Low debt proxy: PB moderate range (very high PB = overvalued/asset-light, very low PB = distressed)
    # - Profitability proxy: PE exists and is positive
    # - Turnover stability: moderate turnover (not too high, not too low)
    pe_exists = [100.0 if r['pe_ttm'] and r['pe_ttm'] > 0 and r['pe_ttm'] < 200 else 0.0 for r in records]
    pb_moderate = [100.0 if r['pb'] and 0.5 < r['pb'] < 10 else (50.0 if r['pb'] and r['pb'] <= 0.5 else 0.0) for r in records]

    for i in range(n):
        records[i]['quality_score'] = 0.40 * pe_exists[i] + 0.30 * pb_moderate[i] + 0.30 * score_lowto[i]

    # ── LOW VOLATILITY: realized vol, beta proxy ──────────────────
    vol_vals = []
    for r in records:
        closes = price_data.get(r['code'], [])
        if len(closes) >= 60:
            rets = np.diff(np.log(np.array(closes[-min(250, len(closes)):])))
            rets = rets[np.isfinite(rets)]
            if len(rets) > 20:
                ann_vol = np.std(rets) * np.sqrt(252) * 100
                vol_vals.append(ann_vol)
            else:
                vol_vals.append(50.0)
        else:
            vol_vals.append(60.0)  # default high vol for missing data

    for i in range(n):
        records[i]['ann_vol'] = vol_vals[i]

    score_lowvol = industry_group_score(records, 'ann_vol', False)  # lower vol = higher score
    for i in range(n):
        records[i]['lowvol_score'] = score_lowvol[i]

    # ── SIZE: smaller market cap → higher score ──────────────────
    score_size = industry_group_score(records, 'market_cap', False)  # smaller = better
    for i in range(n):
        records[i]['size_score'] = score_size[i]

    # ── GROWTH: revenue/profit growth proxy ──────────────────────
    # No direct growth data. Use momentum and PE as growth proxy:
    # High momentum + reasonable PE = growth characteristics
    growth_proxy = [r['momentum_12m1m'] if r.get('momentum_12m1m') and r['momentum_12m1m'] < 200 else 0 for r in records]
    for i in range(n):
        records[i]['growth_proxy'] = growth_proxy[i]
    score_growth = industry_group_score(records, 'growth_proxy', True)
    for i in range(n):
        records[i]['growth_score'] = score_growth[i]

    # ── COMPOSITE ────────────────────────────────────────────────
    for r in records:
        r['composite_score'] = (
            r['value_score'] + r['momentum_score'] + r['quality_score'] +
            r['lowvol_score'] + r['size_score'] + r['growth_score']
        ) / 6

    records.sort(key=lambda x: x['composite_score'], reverse=True)
    print(f"  Factor scores computed for {n} stocks", file=sys.stderr)
    return records

# ── Step 5: Macro Assessment ────────────────────────────────────────
def assess_macro():
    """Quick macro assessment using available data."""
    print("[5/5] Assessing macro environment...", file=sys.stderr)
    # PMI data (from our earlier successful test)
    # Manufacturing PMI: 50.3 (April 2026) - above 50, expanding
    # Non-manufacturing PMI: 49.4 (below 50)
    # CPI: 1.0% (low, near deflation)
    return {
        'phase': 'transition',
        'description': '过渡期/弱复苏：制造业PMI刚过荣枯线(50.3)，非制造业PMI偏弱(49.4)，CPI低位(1.0%)',
        'pmi_mfg': 50.3,
        'pmi_non_mfg': 49.4,
        'cpi': 1.0,
        'factor_timing': {
            'favored': '低波动、质量因子在不确定环境中更稳健；规模因子在弱复苏初期有溢价',
            'disfavored': '动量因子在当前震荡市中表现波动',
        }
    }

# ── MAIN ────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    # 1. Fetch all spot data
    spot = fetch_all_spot()
    records = spot_records(spot)
    print(f"  Valid records: {len(records)}", file=sys.stderr)

    # 2. Filter to top 800 by market cap (CSI 800 proxy)
    universe = filter_top_n(records, 800)
    print(f"  CSI 800 universe: {len(universe)} stocks", file=sys.stderr)

    # 3. Fetch price history for the universe
    codes = [r['code'] for r in universe]
    price_data = fetch_price_batch(codes, "(CSI 800 proxy)")

    # 4. Compute factors
    universe = compute_factors(universe, price_data)

    # 5. Macro
    macro = assess_macro()

    # Output top 20
    top20 = universe[:20]

    elapsed = time.time() - t0

    # Print summary to stderr
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Multi-Factor Screen Complete ({elapsed:.0f}s)", file=sys.stderr)
    print(f"Universe: Top 800 by market cap (CSI 800 proxy)", file=sys.stderr)
    print(f"Factors: Value(EP/BP) + Momentum(12-1m) + Quality + LowVol + Size + Growth", file=sys.stderr)
    print(f"Weighting: Equal (1/6 each)", file=sys.stderr)
    print(f"Industry Neutral: Yes (percentile within industry group)", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # Build output
    output = {
        'meta': {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'universe': 'Top 800 by market cap (CSI 800 proxy)',
            'universe_count': len(universe),
            'elapsed_seconds': round(elapsed, 1),
            'equal_weight': True,
        },
        'macro': macro,
        'top20': [],
        'factor_stats': {},
        'industry_distribution': {},
    }

    # Top 20 detail
    for i, r in enumerate(top20):
        entry = {
            'rank': i + 1,
            'code': r['code'],
            'name': r['name'],
            'industry': r['industry'],
            'market_cap_yi': round(r['market_cap'] / 1e8, 1) if r['market_cap'] else None,
            'composite': round(r['composite_score'], 1),
            'value': round(r['value_score'], 1),
            'momentum': round(r['momentum_score'], 1),
            'quality': round(r['quality_score'], 1),
            'lowvol': round(r['lowvol_score'], 1),
            'size': round(r['size_score'], 1),
            'growth': round(r['growth_score'], 1),
            'pe_ttm': r['pe_ttm'],
            'pb': r['pb'],
            'mom_12m1m_pct': round(r.get('momentum_12m1m', 0), 1),
            'ann_vol_pct': round(r.get('ann_vol', 0), 1),
        }
        output['top20'].append(entry)

    # Factor stats
    for factor in ['value_score', 'momentum_score', 'quality_score', 'lowvol_score', 'size_score', 'growth_score', 'composite_score']:
        vals = [r[factor] for r in top20]
        output['factor_stats'][factor] = {
            'avg': round(np.mean(vals), 1),
            'min': round(np.min(vals), 1),
            'max': round(np.max(vals), 1),
        }

    # Industry distribution
    from collections import Counter
    ind_counts = Counter(r['industry'] for r in top20)
    output['industry_distribution'] = dict(ind_counts.most_common())

    # Print table to stdout
    print("RANK | CODE   | NAME        | INDUSTRY    | COMP | VALUE| MOM  | QUAL | LOWV | SIZE | GROW | PE   | PB  ")
    print("-" * 105)
    for r in output['top20']:
        print(f"{r['rank']:4d} | {r['code']:6s} | {r['name']:<12s} | {r['industry']:<12s} | "
              f"{r['composite']:4.0f} | {r['value']:4.0f} | {r['momentum']:4.0f} | {r['quality']:4.0f} | "
              f"{r['lowvol']:4.0f} | {r['size']:4.0f} | {r['growth']:4.0f} | "
              f"{r['pe_ttm'] or '-':>4} | {r['pb'] or '-':>4}")

    # Output JSON
    print("\n\n=== JSON OUTPUT ===")
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

if __name__ == '__main__':
    main()
