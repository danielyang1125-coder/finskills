#!/usr/bin/env python3
"""Debug financial & index APIs."""
import requests, json, os
os.environ['no_proxy'] = '*'

s = requests.Session()
s.trust_env = False
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
})

fin_url = 'https://datacenter.eastmoney.com/secrets/api/data/v1/get'
# Actually the correct URL is securities not secrets
fin_url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'

# Try different report names
reports = [
    'RPT_LICO_FN_CPD',
    'RPT_DMSK_FN_INCOME',
    'RPT_DMSK_FN_MAININDICATOR',
    'RPT_DMSK_FN_BALANCE',
]
for rpt in reports:
    try:
        params = {'reportName': rpt, 'columns': 'SECURITY_CODE',
                  'pageNumber': '1', 'pageSize': '3',
                  'sortTypes': '-1', 'sortColumns': 'NOTICE_DATE',
                  'source': 'WEB', 'client': 'WEB'}
        r = s.get(fin_url, params=params, timeout=10)
        d = r.json()
        success = d.get('success')
        msg = d.get('message', '')
        has_data = d.get('result') is not None
        print(f'{rpt}: success={success}, has_result={has_data}, msg={msg[:80]}')
    except Exception as e:
        print(f'{rpt}: ERROR - {str(e)[:100]}')

# Try CSI 800 index constituents from csindex.com.cn
print('\n=== CSI 800 via csindex ===')
try:
    csindex_url = 'https://www.csindex.com.cn/csindex-home/index-list/query-index-component'
    params = {'indexCode': '000906'}
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.csindex.com.cn/',
    }
    r = s.get(csindex_url, params=params, headers=headers, timeout=15)
    print(f'Status: {r.status_code}, len: {len(r.text)}')
    d = r.json()
    if d.get('result') and d['result'].get('data'):
        items = d['result']['data']
        print(f'Constituents: {len(items)}')
        if items:
            print(f'Sample: {items[0]}')
except Exception as e:
    print(f'CSI 800 ERROR: {str(e)[:200]}')

# Try getting CSI 300 constituents from East Money
print('\n=== CSI 300 via East Money concept board ===')
try:
    url = 'https://push2.eastmoney.com/api/qt/clist/get'
    params = {'pn': '1', 'pz': '5', 'po': '1', 'np': '1',
              'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
              'fltt': '2', 'invt': '2', 'fid': 'f3',
              'fs': 'b:BK0500', 'fields': 'f12,f14'}
    r = s.get(url, params=params, timeout=10)
    print(f'Status: {r.status_code}')
    d = r.json()
    total = d.get('data', {}).get('total', 0)
    print(f'BK0500 (沪深300): total={total}')
    if total > 0:
        print(f'Samples: {d["data"]["diff"][:3]}')
except Exception as e:
    print(f'BK0500 ERROR: {str(e)[:200]}')
