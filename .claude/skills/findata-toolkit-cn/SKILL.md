---
name: findata-toolkit-cn
description: A股金融数据工具包。提供脚本获取A股实时行情、财务指标、董监高增减持、北向资金、宏观经济数据（LPR、CPI/PPI、PMI、社融、M2）。用于需要实时A股市场数据支撑投资分析时。所有数据源免费，无需API密钥。
license: Apache-2.0
---

# 金融数据工具包 — A股市场

自包含的数据工具包，提供A股市场实时金融数据和定量计算。所有数据源**免费**，**无需API密钥**。

## 安装

安装依赖（一次性）：

```bash
pip install -r requirements.txt
```

## 可用工具

所有脚本位于 `scripts/` 目录。从技能根目录运行。

### 1. A股数据 (`scripts/stock_data.py`)

通过 AKShare 获取A股基本面、行情、财务指标。

| 命令 | 用途 |
|------|------|
| `python scripts/stock_data.py 600519` | 基本信息（贵州茅台） |
| `python scripts/stock_data.py 600519 --metrics` | 完整财务指标（估值、盈利、杠杆、增长） |
| `python scripts/stock_data.py 600519 --history` | 历史OHLCV行情 |
| `python scripts/stock_data.py 600519 --financials` | 利润表、资产负债表、现金流量表 |
| `python scripts/stock_data.py 600519 --insider` | 董监高增减持数据 |
| `python scripts/stock_data.py --northbound` | 北向资金流向（沪股通/深股通） |
| `python scripts/stock_data.py 600519 000858 --screen` | 批量筛选 |

### 2. 宏观数据 (`scripts/macro_data.py`)

通过 AKShare 获取中国宏观经济指标。

| 命令 | 用途 |
|------|------|
| `python scripts/macro_data.py --dashboard` | 完整宏观仪表盘 |
| `python scripts/macro_data.py --rates` | 利率数据（LPR、Shibor） |
| `python scripts/macro_data.py --inflation` | CPI/PPI数据 |
| `python scripts/macro_data.py --pmi` | PMI数据（制造业/非制造业） |
| `python scripts/macro_data.py --social-financing` | 社会融资规模 + M2 |
| `python scripts/macro_data.py --cycle` | 经济周期阶段判断 |

## 数据来源

| 来源 | 数据内容 | API密钥 |
|------|----------|---------|
| AKShare | A股行情、财务数据、董监高交易、北向资金、宏观指标 | 无需 |

## 输出格式

所有脚本以 **JSON** 输出到标准输出，便于解析。错误信息输出到标准错误。

## 配置

可选：编辑 `config/data_sources.yaml` 自定义速率限制或添加付费数据源API密钥。

---

## 环境与故障排除（实战验证）

### Python 环境探测

Windows 下 Python 可能不可用（WindowsApps 存根）或不在 PATH。启动时应先做系统性探测：

```bash
# 第1步：找到真实Python安装
where python 2>&1
dir /s /b "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe" 2>&1
dir /s /b "C:\Program Files\Python3*\python.exe" 2>&1

# 第2步：排除存根（WindowsApps\python.exe 可能是Store占位符）
%LOCALAPPDATA%\Programs\Python\Python312\python.exe --version

# 第3步：如不存在，用 winget 安装
winget install python.python.3.12 --accept-source-agreements --accept-package-agreements

# 第4步：安装 akshare
%LOCALAPPDATA%\Programs\Python\Python312\python.exe -m pip install akshare --upgrade
```

### API 函数速查与已知问题

AKShare 1.18.60 验证。**所有数据通过 AKShare 封装层调用，不直接访问东方财富裸API。**

| 类别 | 函数 | 可靠度 | 已知陷阱 |
|------|------|--------|---------|
| **指数日线** | `stock_zh_index_daily(symbol='sh000001')` | ✅ | date列为`datetime.date`类型，过滤前需`.apply(lambda v: v.strftime("%Y-%m-%d"))`转字符串。符号: `sh000001`/`sh000688`/`sz399006`/`sh000300`/`sh000905`/`sz399001` |
| **SW行业指数** | `index_hist_sw(symbol='801080')` | ⚠️仅长期 | `sw_index_daily`不存在。close在`iloc[:,4]`非`iloc[:,1]`。返回自2000年起的累计值，不能用于短期收益率计算 |
| **行业板块实时** | `stock_board_industry_spot_em()` | ⚠️需网络 | 依赖东方财富push2 API，网络不通时失败 |
| **LPR** | `macro_china_lpr()` | ✅ | 无已知问题 |
| **PMI制造业** | `index_pmi_man_cx()` | ✅ | `macro_china_pmi()`返回2008年旧数据，不要用 |
| **PMI非制造业** | `index_pmi_ser_cx()` | ✅ | — |
| **CPI** | `macro_china_cpi_yearly()` | ❌ → Tushare | 列`今值`2025-09后NaN。**用 `pro.cn_cpi()`（需积分≥2000）** |
| **PPI** | `macro_china_ppi_yearly()` | ❌ → Tushare | 同上。**用 `pro.cn_ppi()`（需积分≥2000）** |
| **M2** | `macro_china_money_supply()` | ✅ | 单位：亿元 |
| **GDP** | `macro_china_gdp()` | ✅ | 季度数据 |
| **北向资金** | `stock_hsgt_hist_em(symbol='北向资金')` | ❌ → Tushare | `当日成交净买额`全NaN。**用 `pro.moneyflow_hsgt()`→取`hgt`/`sgt`列(万元)** |

### 调试驱动开发原则

**先写5行探测代码，再写200行分析脚本。**

```python
import akshare as ak

# 1. 确认函数存在
print('index_pmi_man_cx' in dir(ak))

# 2. 拉取数据并检查结构
df = ak.index_pmi_man_cx()
print(f"Shape: {df.shape}, Cols: {list(df.columns)}")
print(f"Tail:\n{df.tail(3)}")

# 3. 确认值在合理范围
val = float(df.iloc[-1, 1])
assert 40 < val < 60, f"PMI {val} 超出合理范围"
```

### Shell输出与编码策略（Windows）

**问题**：Windows cmd 重定向默认输出 GBK 编码，导致两个阻塞：
1. `read_file` 读取日志时抛出 "stream did not contain valid UTF-8"
2. `type` 命令在终端显示中文乱码（如 `��ָ֤��`）

**标准解决方案——全链路 UTF-8**：

```bash
# 推荐：运行前切换代码页，一步到位
chcp 65001 >nul && python script.py > _log.txt 2>&1
```

| 场景 | 解法 | 命令/代码 |
|------|------|----------|
| Python脚本输出到文件 | 运行前切 UTF-8 | `chcp 65001 >nul && python script.py > log.txt 2>&1` |
| Python内部读写 | 显式指定编码 | `open(path, 'w', encoding='utf-8')` |
| read_file 报 UTF-8 错误 | type 绕过 | `type log.txt`（仅当 chcp 65001 后） |
| JSON 输出 | ensure_ascii | `json.dumps(data, ensure_ascii=False)` |
| Python stdout 编码 | reconfigure | `sys.stdout.reconfigure(encoding='utf-8')` |

> **注意**：即使终端显示乱码，Python 脚本通过 `open(..., encoding='utf-8')` 写入文件的内容是正确的。乱码仅发生在 cmd→终端传输环节，不影响文件内容。

### 数据源层级与降级

```
L1: AKShare 函数（优先）—— 内部处理代理/SSL/重试
L2: 东方财富push2 API（L1失败且确认网络可达时）
L3: fetch_url 工具（最后手段）
```

### 速率限制

AKShare底层数据源有频率限制。批量拉取行业数据时，每两次请求间隔 >= 0.1秒。大量个股数据分批拉取，每批不超过50只。

---

## Tushare 集成策略

当用户有 Tushare token 时，与 AKShare 互补使用，解决 AKShare 的3个核心短板。

> 📖 **实战数据获取指南**：[references/data-fetching-guide.md](references/data-fetching-guide.md) —
> 提炼了多次实战中的成败经验，包含函数速查、三大陷阱（行排序不一致、SW列结构不同、北向列名含义）、
> 数据验证规则、完整采集流程。**其他技能获取数据前应优先查阅。**

### 互补分工表

| 指标 | 主力数据源 | 原因 |
|------|----------|------|
| 指数日线 | **AKShare** `stock_zh_index_daily()` | 已验证稳定，无需切换 |
| LPR/PMI/M2/GDP | **AKShare** | 已验证稳定 |
| CPI | **Tushare** `pro.cn_cpi()` (需积分≥2000) | AKShare `macro_china_cpi_yearly()` 的 `今值` 列为 NaN |
| PPI | **Tushare** `pro.cn_ppi()` (需积分≥2000) | 同上 |
| 北向资金 | **Tushare** `pro.moneyflow_hsgt()` → 用 `hgt`(沪股通)/`sgt`(深股通)列，单位万元÷10000=亿元 | AKShare `stock_hsgt_hist_em()` 的 `当日成交净买额` 为 NaN |
| 行业分类 | **Tushare** `pro.stock_basic()` | 提供每只股票的申万一级行业归属 |
| SW行业长期趋势 | **AKShare** `index_hist_sw()` | 累计指数适用于1年以上趋势分析 |

### 安装与初始化

```bash
pip install tushare pyyaml
```

```python
# 方式一：从 config/data_sources.yaml 自动读取（推荐）
from common.utils import get_tushare_token
import tushare as ts

token = get_tushare_token()
if not token:
    raise RuntimeError("请在 config/data_sources.yaml 中设置 tushare.token")
ts.set_token(token)
pro = ts.pro_api()

# 方式二：环境变量（备选）
# export TUSHARE_TOKEN=your_token
import os
ts.set_token(os.environ['TUSHARE_TOKEN'])
pro = ts.pro_api()
```

### CPI/PPI/北向资金补缺代码

```python
# ── CPI/PPI（AKShare 失败时的标准替代） ──
cpi_df = pro.cn_cpi()  # 免费token可能因权限不足而失败（需积分≥2000）
# 列: month, nt_val(全国同比%), town_val, cnt_val
latest_cpi = float(cpi_df.iloc[0]['nt_val'])

ppi_df = pro.cn_ppi()  # 免费token可能因权限不足而失败（需积分≥2000）
# 列: month, ppi_yoy(全部工业品当月同比%), ppi_mp_yoy, ...
latest_ppi = float(ppi_df.iloc[0]['ppi_yoy'])

# ── 北向资金（AKShare 失败时的标准替代） ──
nb = pro.moneyflow_hsgt(start_date='20260401', end_date='20260510')
# ⚠️ 列说明: hgt=沪股通(北向净买入/万元), sgt=深股通(北向净买入/万元)
# ⚠️ ggt_ss/ggt_sz 是港股通(南向)不是北向！north_money=hgt+sgt
# 正确的北向净买入计算（north_money 单位万元，÷10000得亿元）：
nb_sorted = nb.sort_values('trade_date')
april_net_wan = nb_sorted[nb_sorted['trade_date'].str.startswith('202604')]['north_money'].astype(float).sum()
april_net_yi = round(april_net_wan / 10000, 2)
# 或分别取沪股通/深股通：
april_hgt = nb_sorted[nb_sorted['trade_date'].str.startswith('202604')]['hgt'].astype(float).sum() / 10000
april_sgt = nb_sorted[nb_sorted['trade_date'].str.startswith('202604')]['sgt'].astype(float).sum() / 10000

# ── 行业归属（补充 AKShare 行业数据缺失） ──
stocks = pro.stock_basic(exchange='', list_status='L', 
                          fields='ts_code,name,industry')
# industry 字段即为申万一级行业分类
```

### 频率限制

Tushare 免费账户有每分钟调用次数限制，建议：
- 批量查询时加 `time.sleep(0.5)` 间隔
- 优先用 AKShare 做大批量，Tushare 做精准补缺
- CPI/PPI/北向属于低频查询（每次分析只调1-2次），不会触发限制

### 降级策略（Tushare 不可用时）

| 指标 | 降级方案 |
|------|---------|
| CPI/PPI | 尝试 AKShare `macro_china_cpi_monthly()`，或从 `aq_data.py` 的东方财富 datacenter API |
| 北向资金 | 尝试 AKShare `stock_hsgt_north_net_flow_in_em()` |
| 行业分类 | 从东方财富 `stock_board_industry_cons_em()` 按行业板块获取成分股 |
