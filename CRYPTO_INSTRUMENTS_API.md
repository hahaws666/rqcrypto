# 加密货币合约获取 API

## 概述

`get_all_crypto_instruments(date)` 函数用于获取指定日期的所有加密货币合约信息。

## 函数签名

### 1. 获取合约列表
```python
def get_all_crypto_instruments(self, date: DateLike = None) -> List[Instrument]:
    """
    获取指定日期的所有加密货币合约
    
    Args:
        date: 指定日期，如果为None则返回所有合约
        
    Returns:
        List[Instrument]: 合约列表
    """
```

### 2. 获取DataFrame格式
```python
def get_crypto_instruments_df(self, date: DateLike = None) -> pd.DataFrame:
    """
    获取指定日期的所有加密货币合约，返回DataFrame格式
    
    Args:
        date: 指定日期，如果为None则返回所有合约
        
    Returns:
        pd.DataFrame: 包含合约信息的DataFrame
    """
```

## 使用方法

### 1. 基本使用（列表格式）

```python
from rqalpha.data.crypto_data_source import CryptoDataSource

# 创建数据源
data_source = CryptoDataSource("./test_crypto_bundle")

# 获取所有合约
all_instruments = data_source.get_all_crypto_instruments()
print(f"总共获取到 {len(all_instruments)} 个合约")
```

### 2. DataFrame格式输出（推荐）

```python
from rqalpha.data.crypto_data_source import CryptoDataSource

# 创建数据源
data_source = CryptoDataSource("./test_crypto_bundle")

# 获取DataFrame格式的合约信息
df = data_source.get_crypto_instruments_df()
print("所有加密货币合约:")
print(df[['abbrev_symbol', 'order_book_id', 'type', 'symbol', 'exchange']].head(10))

# 统计信息
print(f"\n总共有 {len(df)} 个加密货币合约")
print(f"现货合约: {len(df[df['type'] == 'CRYPTO_SPOT'])} 个")
print(f"期货合约: {len(df[df['type'] == 'CRYPTO_FUTURE'])} 个")
```

### 3. 按日期获取

```python
from datetime import date

# 获取指定日期的合约（列表格式）
instruments = data_source.get_all_crypto_instruments(date(2025, 8, 1))
print(f"指定日期获取到 {len(instruments)} 个合约")

# 获取指定日期的合约（DataFrame格式）
df = data_source.get_crypto_instruments_df(date(2025, 8, 1))
print(f"指定日期DataFrame获取到 {len(df)} 个合约")
```

### 4. 合约信息

#### DataFrame列说明

DataFrame包含以下列：

- `abbrev_symbol`: 合约简称（如 "BTCUSDT"）
- `order_book_id`: 合约ID（如 "BTCUSDT"）
- `symbol`: 交易对符号（如 "BTCUSDT"）
- `type`: 合约类型（CRYPTO_SPOT 或 CRYPTO_FUTURE）
- `exchange`: 交易所（BINANCE 或 BINANCE_FUTURES）
- `round_lot`: 最小交易单位（通常为1）
- `tick_size`: 最小价格变动单位
- `contract_multiplier`: 合约乘数
- `underlying_symbol`: 标的资产符号
- `quote_currency`: 计价货币
- `listed_date`: 上市日期
- `de_listed_date`: 退市日期

#### 输出示例

```python
# DataFrame输出示例
   abbrev_symbol order_book_id         type   symbol exchange  round_lot
0        ETHBTC        ETHBTC  CRYPTO_SPOT   ETHBTC  BINANCE          1
1        LTCBTC        LTCBTC  CRYPTO_SPOT   LTCBTC  BINANCE          1
2        BNBBTC        BNBBTC  CRYPTO_SPOT   BNBBTC  BINANCE          1
3       BTCUSDT       BTCUSDT  CRYPTO_SPOT  BTCUSDT  BINANCE          1
4       ETHUSDT       ETHUSDT  CRYPTO_SPOT  ETHUSDT  BINANCE          1
```

### 5. 合约过滤

#### 使用DataFrame过滤（推荐）

```python
# 获取DataFrame格式
df = data_source.get_crypto_instruments_df()

# 按类型过滤
spot_df = df[df['type'] == 'CRYPTO_SPOT']
futures_df = df[df['type'] == 'CRYPTO_FUTURE']

# 按交易对过滤
usdt_pairs = df[df['symbol'].str.endswith('USDT')]
btc_pairs = df[df['symbol'].str.endswith('BTC')]

print(f"现货合约: {len(spot_df)} 个")
print(f"期货合约: {len(futures_df)} 个")
print(f"USDT交易对: {len(usdt_pairs)} 个")
print(f"BTC交易对: {len(btc_pairs)} 个")

# 显示前10个USDT交易对
print("\n前10个USDT交易对:")
print(usdt_pairs[['abbrev_symbol', 'order_book_id', 'type', 'symbol']].head(10))
```

#### 使用列表过滤

```python
from rqalpha.const import INSTRUMENT_TYPE

# 获取所有合约
all_instruments = data_source.get_all_crypto_instruments()

# 按类型过滤
spot_instruments = [ins for ins in all_instruments if ins.type == INSTRUMENT_TYPE.CRYPTO_SPOT]
futures_instruments = [ins for ins in all_instruments if ins.type == INSTRUMENT_TYPE.CRYPTO_FUTURE]

# 按交易对过滤
usdt_pairs = [ins for ins in all_instruments if ins.symbol.endswith('USDT')]
btc_pairs = [ins for ins in all_instruments if ins.symbol.endswith('BTC')]

print(f"现货合约: {len(spot_instruments)} 个")
print(f"期货合约: {len(futures_instruments)} 个")
print(f"USDT交易对: {len(usdt_pairs)} 个")
print(f"BTC交易对: {len(btc_pairs)} 个")
```

## 数据统计

根据测试结果，当前数据包包含：

- **总合约数**: 2041 个
- **现货合约**: 1516 个（BINANCE）
- **期货合约**: 525 个（BINANCE_FUTURES）
- **USDT交易对**: 898 个
- **BTC交易对**: 210 个
- **ETH交易对**: 51 个

## 示例代码

完整的使用示例请参考：
- `examples/get_crypto_instruments_example.py` - 基本使用示例
- `examples/crypto_strategy_working.py` - 策略中使用DataFrame格式
- `test_crypto_instruments.py` - 完整测试脚本

### 在策略中使用

```python
def init(context):
    # 创建数据源
    context.crypto_data_source = CryptoDataSource("./test_crypto_bundle")
    
    # 获取所有加密货币合约的DataFrame格式
    all_instruments_df = context.crypto_data_source.get_crypto_instruments_df()
    print("所有加密货币合约:")
    print(all_instruments_df[['abbrev_symbol', 'order_book_id', 'type', 'symbol', 'exchange']].head(10))
    
    # 选择要交易的加密货币
    context.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    print(f"\n选择的交易对: {context.symbols}")
```

## 注意事项

1. **日期参数**: 目前加密货币合约没有日期限制，指定任何日期都会返回所有合约
2. **数据来源**: 合约信息来自 Binance API
3. **更新频率**: 每次运行数据下载脚本都会获取最新的合约信息
4. **性能**: 获取所有合约的速度很快，适合在策略中使用

## 相关函数

- `get_all_crypto_instruments(date)`: 获取所有加密货币合约（列表格式）
- `get_crypto_instruments_df(date)`: 获取所有加密货币合约（DataFrame格式，推荐）
- `get_instruments(id_or_syms, types)`: 获取指定合约或类型的合约
- `get_trading_calendars()`: 获取交易日历
- `history_bars()`: 获取历史K线数据

## 优势对比

| 功能 | 列表格式 | DataFrame格式 |
|------|----------|---------------|
| 数据展示 | 需要循环打印 | 直接表格显示 |
| 数据过滤 | 需要列表推导式 | 使用pandas语法 |
| 统计分析 | 需要手动计算 | 内置统计函数 |
| 性能 | 适合少量数据 | 适合大量数据 |
| 推荐度 | 一般 | ⭐⭐⭐⭐⭐ |

**建议**: 优先使用 `get_crypto_instruments_df()` 函数，它提供了更直观的数据展示和更强大的数据处理能力。
