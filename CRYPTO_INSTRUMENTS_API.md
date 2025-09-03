# 加密货币合约获取 API

## 概述

`get_all_crypto_instruments(date)` 函数用于获取指定日期的所有加密货币合约信息。

## 函数签名

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

## 使用方法

### 1. 基本使用

```python
from rqalpha.data.crypto_data_source import CryptoDataSource

# 创建数据源
data_source = CryptoDataSource("./test_crypto_bundle")

# 获取所有合约
all_instruments = data_source.get_all_crypto_instruments()
print(f"总共获取到 {len(all_instruments)} 个合约")
```

### 2. 按日期获取

```python
from datetime import date

# 获取指定日期的合约
instruments = data_source.get_all_crypto_instruments(date(2025, 8, 1))
print(f"指定日期获取到 {len(instruments)} 个合约")
```

### 3. 合约信息

每个合约对象包含以下主要属性：

- `order_book_id`: 合约ID（如 "BTCUSDT"）
- `symbol`: 交易对符号（如 "BTCUSDT"）
- `type`: 合约类型（CRYPTO_SPOT 或 CRYPTO_FUTURE）
- `exchange`: 交易所（BINANCE 或 BINANCE_FUTURES）
- `account_type`: 账户类型（CRYPTO）

### 4. 合约过滤

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
- `test_crypto_instruments.py` - 完整测试脚本

## 注意事项

1. **日期参数**: 目前加密货币合约没有日期限制，指定任何日期都会返回所有合约
2. **数据来源**: 合约信息来自 Binance API
3. **更新频率**: 每次运行数据下载脚本都会获取最新的合约信息
4. **性能**: 获取所有合约的速度很快，适合在策略中使用

## 相关函数

- `get_instruments(id_or_syms, types)`: 获取指定合约或类型的合约
- `get_trading_calendars()`: 获取交易日历
- `history_bars()`: 获取历史K线数据
