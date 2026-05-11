import akshare as ak
import pandas as pd

# Test 1: Index daily data
print('=== Test index daily ===')
for sym in ['sh000001', 'sh000688', 'sz399006']:
    try:
        df = ak.stock_zh_index_daily(symbol=sym)
        if df is not None and not df.empty:
            last_date = df.iloc[-1, 0]
            print(f'{sym}: shape={df.shape}, last_date={last_date}, cols={list(df.columns)}')
        else:
            print(f'{sym}: empty/None')
    except Exception as e:
        print(f'{sym}: ERROR - {str(e)[:100]}')

# Test 2: Sector spot
print()
print('=== Test sector spot ===')
try:
    df = ak.stock_board_industry_name_em()
    print(f'sector_spot: shape={df.shape}, cols={list(df.columns)[:6]}')
    print(f'first row: {df.iloc[0].to_dict()}')
except Exception as e:
    print(f'sector_spot: ERROR - {str(e)[:100]}')

# Test 3: CPI
print()
print('=== Test CPI ===')
try:
    df = ak.macro_china_cpi_yearly()
    print(f'cpi: shape={df.shape}, cols={list(df.columns)}')
    if not df.empty:
        print(f'last row: {df.iloc[-1].to_dict()}')
except Exception as e:
    print(f'cpi: ERROR - {str(e)[:100]}')

# Test 4: PMI
print()
print('=== Test PMI ===')
try:
    df = ak.macro_china_pmi()
    print(f'pmi: shape={df.shape}, cols={list(df.columns)}')
    print(f'last 3 rows:')
    print(df.tail(3))
except Exception as e:
    print(f'pmi: ERROR - {str(e)[:100]}')

# Test 5: Northbound
print()
print('=== Test Northbound ===')
try:
    df = ak.stock_hsgt_hist_em(symbol='北向资金')
    print(f'northbound: shape={df.shape}, cols={list(df.columns)}')
    print(f'last 3 rows:')
    print(df.tail(3))
except Exception as e:
    print(f'northbound: ERROR - {str(e)[:100]}')

# Test 6: SW index
print()
print('=== Test SW index ===')
try:
    df = ak.sw_index_daily(symbol='801010')
    print(f'sw_index: shape={df.shape}, cols={list(df.columns)}')
    if not df.empty:
        print(f'date range: {df.iloc[0,0]} to {df.iloc[-1,0]}')
        print(f'last 3 rows:')
        print(df.tail(3))
except Exception as e:
    print(f'sw_index: ERROR - {str(e)[:100]}')

# Test 7: SW spot
print()
print('=== Test SW spot ===')
try:
    df = ak.sw_index_spot()
    print(f'sw_spot: shape={df.shape}, cols={list(df.columns)[:6]}')
    print(f'first row: {df.iloc[0].to_dict()}')
except Exception as e:
    print(f'sw_spot: ERROR - {str(e)[:100]}')

print()
print('Done.')
