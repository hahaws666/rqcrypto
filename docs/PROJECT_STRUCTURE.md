# 📁 项目结构图

```
rqalpha-爆改/
├── 📄 README.md                    # 项目主文档
├── 📄 QUICKSTART.md               # 快速开始指南
├── 📁 rqalpha/                    # RQAlpha核心框架
│   ├── 📁 data/                   # 数据模块
│   │   ├── 🔧 binance_api.py      # 币安API集成
│   │   ├── 🔧 bundle.py           # Bundle数据生成
│   │   └── 🔧 crypto_data_source.py # 加密货币数据源
│   └── 📁 ...                     # 其他RQAlpha模块
├── 📁 examples/                   # 示例和策略
│   ├── 📁 strategies/             # 量化策略
│   │   ├── 🎯 crypto_market_strategy.py # 市值轮动策略
│   │   └── 🎯 crypto_strategy_working.py # 工作策略示例
│   └── 📄 get_crypto_instruments_example.py
├── 📁 scripts/                    # 数据下载和分析脚本
│   ├── 📥 download_crypto_data.py # 下载加密货币数据
│   ├── 📊 get_binance_market_cap.py # 获取币安市值数据
│   ├── 📊 get_coingecko_market_cap.py # 获取CoinGecko市值数据
│   ├── 🔍 analyze_crypto_spot_h5.py # 分析H5数据文件
│   └── 🧪 test_5year_data.py      # 测试5年数据
├── 📁 data_download/              # 数据文件
│   ├── 📁 bundle/                 # 原始bundle数据
│   │   ├── 📊 crypto_currencies.csv # 币种列表(553个)
│   │   ├── 📊 binance_coingecko_market_cap_365d.csv # 市值数据
│   │   ├── 💾 crypto_spot.h5      # 现货价格数据
│   │   └── 💾 crypto_futures.h5   # 期货价格数据
│   ├── 📁 test_5year_crypto_bundle/ # 5年历史数据
│   │   ├── 💾 crypto_spot.h5      # 现货5年数据(414个交易对)
│   │   └── 💾 crypto_futures.h5   # 期货5年数据(484个交易对)
│   └── 📁 test_crypto_bundle/     # 测试数据
└── 📁 docs/                       # 文档
    ├── 📄 STRATEGY_GUIDE.md       # 策略说明文档
    └── 📄 PROJECT_STRUCTURE.md    # 项目结构说明
```

## 🔄 数据流程

```
币安API ──┐
          ├── 价格数据 ──► H5文件 ──► 策略回测
CoinGecko API ──┘
          └── 市值数据 ──► CSV文件 ──► 选股逻辑
```

## 🎯 策略流程

```
1. 数据加载 ──► 2. 市值排序 ──► 3. 选股(30个) ──► 4. 调仓执行
     ▲                                                      │
     └────────────────── 每日循环 ──────────────────────────┘
```

## 📊 数据统计

- **总币种数量**: 553个
- **可交易币种**: 551个USDT交易对
- **现货交易对**: 414个
- **期货交易对**: 484个
- **历史数据**: 近5年日K线数据
- **市值数据**: 每日更新
