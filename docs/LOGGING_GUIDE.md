# 📝 日志系统使用指南

## 概述

本项目集成了统一的日志系统，所有日志都会自动写入到 `logs/` 目录下的文件中，方便调试和监控。

## 日志文件

### 文件命名
- 格式：`rqalpha_crypto_YYYYMMDD.log`
- 示例：`rqalpha_crypto_20250904.log`
- 位置：`logs/` 目录

### 文件轮转
- 单个文件最大：10MB
- 保留文件数：5个
- 自动压缩：旧文件自动压缩

## 日志级别

| 级别 | 说明 | 用途 |
|------|------|------|
| INFO | 信息 | 正常操作记录 |
| WARNING | 警告 | 需要注意的问题 |
| ERROR | 错误 | 错误和异常 |
| DEBUG | 调试 | 详细调试信息 |

## 日志模块

| 模块 | 说明 | 用途 |
|------|------|------|
| strategy | 策略 | 策略执行、交易信号 |
| data | 数据 | 数据下载、处理 |
| api | API | 外部API调用 |
| error | 错误 | 错误处理 |
| performance | 性能 | 性能监控 |

## 使用方法

### 1. 在策略中使用

```python
from scripts.logging_config import (
    get_logger, log_strategy_event, log_trade_action, log_portfolio_status
)

def init(context):
    logger = get_logger("strategy")
    logger.info("策略初始化完成")

def handle_bar(context, bar_dict):
    log_strategy_event("info", "开始调仓")
    log_trade_action("buy", "BTCUSDT", quantity=100, price=50000)
    log_portfolio_status(context.portfolio)
```

### 2. 在数据脚本中使用

```python
from scripts.logging_config import log_data_event, log_api_event

# 数据下载
log_data_event("download", "下载币安数据", symbols=50)

# API调用
log_api_event("request", "请求CoinGecko API", endpoint="/coins/markets")
```

### 3. 错误处理

```python
from scripts.logging_config import log_error

try:
    # 可能出错的代码
    risky_operation()
except Exception as e:
    log_error("operation", "操作失败", exception=e)
```

## 日志查看工具

### 基本命令

```bash
# 列出所有日志文件
python scripts/view_logs.py --list

# 查看最新日志文件
python scripts/view_logs.py

# 查看指定日志文件
python scripts/view_logs.py --view logs/rqalpha_crypto_20250904.log

# 显示最后100行
python scripts/view_logs.py --lines 100

# 实时监控日志
python scripts/view_logs.py --follow
```

### 过滤和搜索

```bash
# 只显示错误日志
python scripts/view_logs.py --level ERROR

# 只显示策略模块日志
python scripts/view_logs.py --module strategy

# 搜索关键词
python scripts/view_logs.py --search "买入"

# 搜索最近3天的日志
python scripts/view_logs.py --search "错误" --days 3
```

## 日志格式

### 标准格式
```
2025-09-04 21:34:05 - strategy - INFO - 🚀 策略初始化完成
```

### 字段说明
- `2025-09-04 21:34:05`: 时间戳
- `strategy`: 模块名称
- `INFO`: 日志级别
- `🚀 策略初始化完成`: 日志消息

## 特殊日志类型

### 交易日志
```
🟢 买入 BTCUSDT 数量: 100 价格: $50000.00 价值: $5,000,000
🔴 卖出 ETHUSDT 数量: 50 价格: $3000.00 价值: $150,000
⏸️ 持有 BNBUSDT
```

### 投资组合日志
```
📊 投资组合状态 - 总价值: $1,000,000, 现金: $100,000, 持仓数: 2
```

### 市值选股日志
```
🎯 市值选股完成 - 选中 5 个币种
  ONEUSDT: 市值 $1,340,000
  WANUSDT: 市值 $2,500,000
```

### 性能日志
```
⏱️ 数据下载 耗时: 2.50s - 下载了100个币种的数据
⏱️ 策略回测 耗时: 10.20s - 回测了30天的数据
```

## 配置选项

### 日志级别设置
```python
from scripts.setup_logging import setup_logging
import logging

# 设置为DEBUG级别
setup_logging(log_level=logging.DEBUG)

# 设置为WARNING级别
setup_logging(log_level=logging.WARNING)
```

### 日志目录设置
```python
# 自定义日志目录
setup_logging(log_dir="custom_logs")
```

## 最佳实践

### 1. 日志记录原则
- **及时记录**: 重要操作立即记录
- **信息完整**: 包含必要的上下文信息
- **级别合适**: 选择合适的日志级别
- **避免敏感**: 不记录敏感信息

### 2. 性能考虑
- 避免在循环中记录大量日志
- 使用适当的日志级别
- 定期清理旧日志文件

### 3. 调试技巧
- 使用搜索功能快速定位问题
- 结合时间范围缩小搜索范围
- 利用模块过滤查看特定功能日志

## 故障排除

### 常见问题

1. **日志文件不生成**
   - 检查 `logs/` 目录权限
   - 确认日志系统初始化成功

2. **日志内容不完整**
   - 检查日志级别设置
   - 确认日志函数调用正确

3. **日志文件过大**
   - 检查日志轮转配置
   - 调整日志级别减少记录

### 调试命令

```bash
# 检查日志目录
ls -la logs/

# 查看日志文件大小
du -h logs/*.log

# 搜索错误信息
python scripts/view_logs.py --search "ERROR" --level ERROR
```

## 扩展功能

### 自定义日志格式
```python
import logging

# 创建自定义格式化器
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

### 日志分析
```python
# 分析日志文件
def analyze_logs(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    error_count = sum(1 for line in lines if 'ERROR' in line)
    warning_count = sum(1 for line in lines if 'WARNING' in line)
    
    print(f"错误数量: {error_count}")
    print(f"警告数量: {warning_count}")
```

---

通过这个日志系统，你可以轻松监控和调试整个项目的运行状态！🎉
